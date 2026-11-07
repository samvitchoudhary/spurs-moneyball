"""Price a season from age, role, and per-90 output, then flag gaps versus the market.

Left out on purpose:
- market_value_eur, and any previous-season value: that is the target. Last year's
  price would let the model copy the market instead of pricing the stats.
- current_club_name: Transfermarkt's club is a July 2026 snapshot, so it would
  attach a player's future club to his 2022-23 row.
- contract_expiration_date and the other contract fields: same July 2026 snapshot,
  so a contract signed later would leak into earlier seasons.
- value_date: it records when the price was observed, not a trait of the player.
- team: club reputation is already baked into the price we are trying to explain.
"""

from __future__ import annotations

import os

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from src.features import (
    VALUED_PATH,
    add_per90,
    assign_position_group,
    combine_club_stints,
    feature_columns,
)

ROOT_PREDICTIONS = VALUED_PATH.parent / "value_predictions.csv"
PREDICTIONS_PATH = ROOT_PREDICTIONS
CLUSTERS_PATH = VALUED_PATH.parent / "player_clusters.csv"
MODEL_SEASONS = (2223, 2324, 2425, 2526)
TRAIN_SEASONS = (2223, 2324, 2425)
TEST_SEASON = 2526
RIDGE_ALPHAS = np.logspace(-2, 4, 29)
LEAGUE_ORDER = [
    "ENG-Premier League",
    "ESP-La Liga",
    "GER-Bundesliga",
    "ITA-Serie A",
    "FRA-Ligue 1",
]
POSITION_ORDER = ["CB", "FB", "CM", "AM_W", "ST"]
REFERENCE_AGE = 25


def build_modeling_frame(valued: pd.DataFrame | None = None) -> pd.DataFrame:
    """Player-seasons with a fee, a role, and raw per-90 rates.

    Mid-season moves are one row. Style is the 2025-26 cluster name, or
    "unknown" in every earlier season.
    """
    if valued is None:
        valued = pd.read_csv(VALUED_PATH)
    frame = add_per90(assign_position_group(combine_club_stints(valued)))
    frame["season"] = frame["season"].astype(int)
    frame["minutes"] = pd.to_numeric(frame["minutes"], errors="coerce")
    frame["market_value_eur"] = pd.to_numeric(frame["market_value_eur"], errors="coerce")
    frame = frame.loc[frame["season"].isin(MODEL_SEASONS)].copy()
    frame = frame.loc[frame["minutes"] >= 900]
    frame = frame.loc[frame["tm_player_id"].notna()]
    frame = frame.loc[frame["market_value_eur"].notna() & (frame["market_value_eur"] > 0)]
    frame = frame.loc[frame["position_group"].ne("GK") & frame["position_group"].notna()]
    frame["age"] = _age_years(frame["age"])
    frame = frame.loc[frame["age"].notna()].copy()
    matches = pd.to_numeric(frame["matches"], errors="coerce")
    starts = pd.to_numeric(frame["starts"], errors="coerce")
    frame["starts_share"] = np.where(matches > 0, starts / matches, 0.0)
    frame["age_sq"] = frame["age"] ** 2
    frame["style_cluster"] = _style_labels(frame)
    frame["log_value"] = np.log(frame["market_value_eur"])
    return frame.reset_index(drop=True)


def design_matrix(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Numeric columns plus one-hot league, role, and style. Premier League and CB are the baselines."""
    rates = [column for column in feature_columns(frame) if column in frame.columns]
    numeric = frame[["age", "age_sq", "minutes", "starts_share", *rates]].apply(pd.to_numeric, errors="coerce")
    numeric = numeric.fillna(0.0)
    leagues = pd.Categorical(frame["league"], categories=LEAGUE_ORDER)
    roles = pd.Categorical(frame["position_group"], categories=POSITION_ORDER)
    styles = sorted(set(frame["style_cluster"].astype(str)) - {"unknown"})
    style = pd.Categorical(frame["style_cluster"].astype(str), categories=["unknown", *styles])
    dummies = pd.get_dummies(
        pd.DataFrame({"league": leagues, "position_group": roles, "style_cluster": style}),
        drop_first=True,
        dtype=float,
    )
    matrix = pd.concat([numeric.reset_index(drop=True), dummies.reset_index(drop=True)], axis=1)
    return matrix, frame["log_value"].reset_index(drop=True)


def evaluate_models(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """GroupKFold by player, and a 2022-23..2024-25 train / 2025-26 test split."""
    if frame is None:
        frame = build_modeling_frame()
    matrix, target = design_matrix(frame)
    groups = frame["tm_player_id"].to_numpy()
    rows = []
    for name in ("ridge", "hist_gradient_boosting"):
        oof = _cross_validate(name, matrix, target, groups)
        rows.append({"model": name, "split": "GroupKFold", **_metrics(target, oof)})
        train = frame["season"].isin(TRAIN_SEASONS).to_numpy()
        test = frame["season"].eq(TEST_SEASON).to_numpy()
        predicted = _fit_predict(name, matrix.loc[train], target.loc[train], matrix.loc[test])
        rows.append({"model": name, "split": "time split 2025-26", **_metrics(target.loc[test], predicted)})
    return pd.DataFrame(rows)


def choose_model(metrics: pd.DataFrame) -> tuple[str, str]:
    """Keep the model that misses by less, in euros, on data it did not train on.

    A gap under one percentage point on the 2025-26 holdout is a tie. The
    player-grouped test breaks it, because that test never lets a player
    score his own other seasons.
    """
    time = metrics.loc[metrics["split"] == "time split 2025-26"].set_index("model")
    grouped = metrics.loc[metrics["split"] == "GroupKFold"].set_index("model")
    holdout_gap = abs(time.loc["ridge", "median_abs_pct_error"] - time.loc["hist_gradient_boosting", "median_abs_pct_error"])
    if holdout_gap < 1:
        winner = str(grouped["median_abs_pct_error"].idxmin())
        kept = "Ridge" if winner == "ridge" else "gradient boosting"
        reason = (
            "On the 2025-26 season neither model trained on, the median errors are "
            f"{time.loc['ridge', 'median_abs_pct_error']:.1f}% for Ridge and "
            f"{time.loc['hist_gradient_boosting', 'median_abs_pct_error']:.1f}% for gradient boosting. "
            "That is a tie. The player-grouped test breaks it: Ridge's median error is "
            f"{grouped.loc['ridge', 'median_abs_pct_error']:.1f}% and its R² is "
            f"{grouped.loc['ridge', 'r2']:.2f}, against "
            f"{grouped.loc['hist_gradient_boosting', 'median_abs_pct_error']:.1f}% and "
            f"{grouped.loc['hist_gradient_boosting', 'r2']:.2f} for gradient boosting. "
            f"We keep {kept}."
        )
        return winner, reason
    winner = str(time["median_abs_pct_error"].idxmin())
    other = "hist_gradient_boosting" if winner == "ridge" else "ridge"
    reason = (
        f"We keep {winner}. On the 2025-26 season it never trained on, its median absolute error "
        f"is {time.loc[winner, 'median_abs_pct_error']:.1f}% of the fee, against "
        f"{time.loc[other, 'median_abs_pct_error']:.1f}% for {other}."
    )
    return winner, reason


def out_of_fold_predictions(frame: pd.DataFrame, model: str) -> pd.DataFrame:
    """Score every row with a model that did not see that player."""
    matrix, target = design_matrix(frame)
    predicted_log = _cross_validate(model, matrix, target, frame["tm_player_id"].to_numpy())
    predicted = np.exp(predicted_log)
    actual = frame["market_value_eur"].to_numpy(dtype=float)
    output = pd.DataFrame(
        {
            "player": frame["player"].to_numpy(),
            "team": frame["team"].to_numpy(),
            "league": frame["league"].to_numpy(),
            "season": frame["season"].to_numpy(),
            "age": frame["age"].to_numpy(),
            "position_group": frame["position_group"].to_numpy(),
            "style_cluster": frame["style_cluster"].to_numpy(),
            "actual_value": actual,
            "predicted_value": predicted,
            "value_gap": predicted / actual,
        }
    )
    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(PREDICTIONS_PATH, index=False)
    return output


def ridge_effects(frame: pd.DataFrame | None = None, n: int = 10) -> pd.DataFrame:
    """Largest Ridge effects, fit on seasons before 2025-26 and translated out of the scaled units."""
    if frame is None:
        frame = build_modeling_frame()
    matrix, target = design_matrix(frame)
    train = frame["season"].isin(TRAIN_SEASONS).to_numpy()
    scaler = StandardScaler()
    scaled = scaler.fit_transform(matrix.loc[train])
    model = RidgeCV(alphas=RIDGE_ALPHAS).fit(scaled, target.loc[train])
    unscaled = model.coef_ / scaler.scale_
    effects = pd.DataFrame(
        {
            "feature": matrix.columns,
            "scaled_coefficient": model.coef_,
            "per_unit_log": unscaled,
        }
    )
    effects["abs_scaled"] = effects["scaled_coefficient"].abs()
    effects = effects.sort_values("abs_scaled", ascending=False).head(n).drop(columns=["abs_scaled"])
    age_slope = float(unscaled[matrix.columns.get_loc("age")])
    age_curve = float(unscaled[matrix.columns.get_loc("age_sq")])
    marginal_at_25 = age_slope + 2 * age_curve * REFERENCE_AGE
    effects["in_words"] = [
        _effect_sentence(row.feature, float(row.per_unit_log), marginal_at_25)
        for row in effects.itertuples(index=False)
    ]
    return effects.reset_index(drop=True)


def top_undervalued(
    season: str = "2526",
    position_group: str | None = None,
    max_age: float | None = 27,
    min_value_eur: float | None = None,
    n: int = 10,
    predictions: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Players whose stats imply a higher fee than the market, largest gap first."""
    table = predictions.copy() if predictions is not None else pd.read_csv(PREDICTIONS_PATH)
    table["season"] = table["season"].map(_season_code)
    table = table.loc[table["season"] == _season_code(season)]
    if position_group is not None:
        table = table.loc[table["position_group"] == position_group]
    if max_age is not None:
        table = table.loc[table["age"] <= max_age]
    if min_value_eur is not None:
        table = table.loc[table["actual_value"] >= min_value_eur]
    table = table.sort_values(["value_gap", "player"], ascending=[False, True]).head(n)
    return table.reset_index(drop=True)


def _style_labels(frame: pd.DataFrame) -> pd.Series:
    labels = pd.Series("unknown", index=frame.index, dtype="object")
    if not CLUSTERS_PATH.exists():
        return labels
    clusters = pd.read_csv(CLUSTERS_PATH)
    clusters = clusters[["player", "team", "position_group", "cluster_name"]].drop_duplicates(
        ["player", "team", "position_group"]
    )
    current = frame.loc[frame["season"] == TEST_SEASON, ["player", "team", "position_group"]]
    matched = current.merge(clusters, on=["player", "team", "position_group"], how="left")
    labels.loc[frame["season"] == TEST_SEASON] = matched["cluster_name"].fillna("unknown").to_numpy()
    return labels


def _cross_validate(model: str, matrix: pd.DataFrame, target: pd.Series, groups: np.ndarray) -> np.ndarray:
    predicted = np.empty(len(target), dtype=float)
    folder = GroupKFold(n_splits=5)
    for train_index, test_index in folder.split(matrix, target, groups):
        predicted[test_index] = _fit_predict(
            model,
            matrix.iloc[train_index],
            target.iloc[train_index],
            matrix.iloc[test_index],
        )
    return predicted


def _fit_predict(model: str, train_x: pd.DataFrame, train_y: pd.Series, test_x: pd.DataFrame) -> np.ndarray:
    if model == "ridge":
        scaler = StandardScaler()
        model_fit = RidgeCV(alphas=RIDGE_ALPHAS).fit(scaler.fit_transform(train_x), train_y)
        return model_fit.predict(scaler.transform(test_x))
    if model == "hist_gradient_boosting":
        booster = HistGradientBoostingRegressor(random_state=42)
        booster.fit(train_x, train_y)
        return booster.predict(test_x)
    raise ValueError(f"Unknown model {model}.")


def _metrics(actual_log, predicted_log) -> dict:
    actual_log = np.asarray(actual_log, dtype=float)
    predicted_log = np.asarray(predicted_log, dtype=float)
    actual = np.exp(actual_log)
    predicted = np.exp(predicted_log)
    percent = np.abs(predicted - actual) / actual
    return {
        "r2": float(r2_score(actual_log, predicted_log)),
        "mae_log": float(mean_absolute_error(actual_log, predicted_log)),
        "median_abs_pct_error": float(np.median(percent) * 100),
    }


def _effect_sentence(feature: str, per_unit_log: float, marginal_age_at_25: float) -> str:
    if feature == "age":
        return (
            f"At age {REFERENCE_AGE}, one more year changes value by about "
            f"{_percent(marginal_age_at_25):+.0f}%, age and age-squared together."
        )
    if feature == "age_sq":
        return "Age-squared bends that curve, so the age effect gets steeper past the mid-twenties."
    if feature == "minutes":
        return f"An extra 1,000 minutes is associated with about {_percent(per_unit_log * 1000):+.0f}% of value."
    if feature == "starts_share":
        return (
            "Starting every match rather than none is associated with about "
            f"{_percent(per_unit_log):+.0f}% of value."
        )
    if feature.startswith("league_"):
        league = _league_label(feature.removeprefix("league_"))
        return f"{league} rather than the Premier League is associated with about {_percent(per_unit_log):+.0f}% of value."
    if feature.startswith("position_group_"):
        role = feature.removeprefix("position_group_")
        return f"A {role} rather than a centre-back is associated with about {_percent(per_unit_log):+.0f}% of value."
    if feature.startswith("style_cluster_"):
        style = feature.removeprefix("style_cluster_").replace("_", " ")
        return (
            f"The 2025-26 style '{style}', versus a season with no style label, "
            f"is associated with about {_percent(per_unit_log):+.0f}% of value."
        )
    if feature.endswith("_per90") or feature in {"shot_accuracy", "goals_per_shot"}:
        label = feature.removesuffix("_per90").replace("_", " ")
        step = 0.1 if feature.endswith("_per90") else 0.05
        unit = "0.1 per 90" if feature.endswith("_per90") else f"{step:g}"
        return (
            f"An extra {unit} of {label} is associated with about {_percent(per_unit_log * step):+.0f}% of value."
        )
    label = feature.replace("_", " ")
    return f"One extra unit of {label} is associated with about {_percent(per_unit_log):+.0f}% of value."


def _league_label(name: str) -> str:
    return {
        "FRA-Ligue 1": "Ligue 1",
        "GER-Bundesliga": "the Bundesliga",
        "ITA-Serie A": "Serie A",
        "ESP-La Liga": "La Liga",
    }.get(name, name)


def _percent(log_change: float) -> float:
    return float((np.exp(log_change) - 1) * 100)


def _age_years(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.split("-").str[0]
    return pd.to_numeric(text, errors="coerce")


def _season_code(value) -> int:
    text = str(value).strip()
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start[-2:] + end[-2:])
    return int(float(text))


if __name__ == "__main__":
    modeling = build_modeling_frame()
    print(f"{len(modeling)} player-seasons")
    comparison = evaluate_models(modeling)
    print(comparison.round(3).to_string(index=False))
    winner, reason = choose_model(comparison)
    print(reason)
    scored = out_of_fold_predictions(modeling, winner)
    print(f"Wrote {len(scored)} rows to {PREDICTIONS_PATH}")
    print(ridge_effects(modeling)[["feature", "in_words"]].to_string(index=False))
