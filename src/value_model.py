"""Price a season from age, role, and per-90 output, then flag gaps versus the market.

Left out on purpose:
- market_value_eur, and any previous-season value: that is the target. Last year's
  price would let the model copy the market instead of pricing the stats.
- current_club_name: Transfermarkt's club is a July 2026 snapshot, so it would
  attach a player's future club to his 2022-23 row.
- contract_expiration_date and the other contract fields: same July 2026 snapshot,
  so a contract signed later would leak into earlier seasons.
- value_date: it records when the price was observed, not a trait of the player.
- team, as a name: a club dummy would just memorize which clubs are expensive.
  Teammates' fees are summarized instead, with the player's own fee removed.
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
STRENGTH_COLUMNS = ("team_strength", "league_value_share", "minutes_x_team_strength")
MIN_VALUE_EUR = 2_000_000


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
    frame = _attach_team_strength(frame, valued)
    return frame.reset_index(drop=True)


def design_matrix(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Numeric columns plus one-hot league, role, and style. Premier League and CB are the baselines."""
    rates = [column for column in feature_columns(frame) if column in frame.columns]
    strength = [column for column in STRENGTH_COLUMNS if column in frame.columns]
    numeric = frame[["age", "age_sq", "minutes", "starts_share", *strength, *rates]].apply(
        pd.to_numeric, errors="coerce"
    )
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


def out_of_fold_predictions(frame: pd.DataFrame, model: str, save: bool = True) -> pd.DataFrame:
    """Score every row with a model that did not see that player."""
    matrix, target = design_matrix(frame)
    predicted_log = _cross_validate(model, matrix, target, frame["tm_player_id"].to_numpy())
    actual = frame["market_value_eur"].to_numpy(dtype=float)
    actual_log = np.log(actual)
    predicted = np.exp(predicted_log)
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
            "log_gap": predicted_log - actual_log,
        }
    )
    output = add_calibrated_gap(output)
    if save:
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


def value_decile_table(predictions: pd.DataFrame, season: str = "2526") -> pd.DataFrame:
    """Mean out-of-fold log gap in each decile of the actual fee."""
    frame = predictions.copy()
    frame["season"] = frame["season"].map(_season_code)
    frame = frame.loc[frame["season"] == _season_code(season)].copy()
    if "log_gap" not in frame.columns:
        frame["log_gap"] = np.log(frame["predicted_value"]) - np.log(frame["actual_value"])
    frame["value_decile"] = _decile_labels(frame["actual_value"])
    table = frame.groupby("value_decile", as_index=False).agg(
        players=("player", "size"),
        min_value_eur=("actual_value", "min"),
        max_value_eur=("actual_value", "max"),
        mean_log_gap=("log_gap", "mean"),
    )
    return table.sort_values("value_decile").reset_index(drop=True)


def cheap_players_look_undervalued(table: pd.DataFrame) -> bool:
    """True when the cheap half of the fee range is over-predicted and the expensive half under-predicted."""
    means = table.sort_values("value_decile")["mean_log_gap"].reset_index(drop=True)
    half = len(means) // 2
    if half == 0:
        return False
    return bool((means.iloc[:half] > 0).all() and (means.iloc[half:] < 0).all())


def add_calibrated_gap(predictions: pd.DataFrame) -> pd.DataFrame:
    """Subtract the leave-one-out mean log gap of the player's own fee decile.

    Deciles are cut inside each season. The player's own gap is left out of the
    mean, so the adjustment is not fitted on the residual it then removes.
    """
    frame = predictions.copy()
    frame["season"] = frame["season"].map(_season_code)
    if "log_gap" not in frame.columns:
        frame["log_gap"] = np.log(frame["predicted_value"]) - np.log(frame["actual_value"])
    frame["value_decile"] = frame.groupby("season", sort=False)["actual_value"].transform(_decile_labels)
    grouped = frame.groupby(["season", "value_decile"], sort=False)["log_gap"]
    counts = grouped.transform("count")
    sums = grouped.transform("sum")
    leave_one_out = np.where(counts > 1, (sums - frame["log_gap"]) / (counts - 1), 0.0)
    frame["decile_mean_log_gap"] = leave_one_out
    frame["calibrated_gap"] = frame["log_gap"] - frame["decile_mean_log_gap"]
    return frame


def calibrate_against_reference(
    reference_value: pd.Series,
    reference_log_gap: pd.Series,
    reference_id: pd.Series,
    score_value: pd.Series,
    score_log_gap: pd.Series,
    score_id: pd.Series,
) -> pd.DataFrame:
    """Calibrate score rows with decile means taken only from the reference rows.

    The reference is a window's training predictions. A scored player who also
    appears there is left out of his own decile mean.
    """
    reference_value = pd.Series(reference_value).reset_index(drop=True).astype(float)
    reference_log_gap = pd.Series(reference_log_gap).reset_index(drop=True).astype(float)
    reference_id = pd.Series(reference_id).reset_index(drop=True)
    score_value = pd.Series(score_value).reset_index(drop=True).astype(float)
    score_log_gap = pd.Series(score_log_gap).reset_index(drop=True).astype(float)
    score_id = pd.Series(score_id).reset_index(drop=True)
    bounds = _decile_bounds(reference_value)
    reference_decile = _decile_from_bounds(reference_value, bounds)
    score_decile = _decile_from_bounds(score_value, bounds)
    reference = pd.DataFrame(
        {
            "tm_player_id": pd.to_numeric(reference_id, errors="coerce"),
            "value_decile": reference_decile,
            "log_gap": reference_log_gap,
        }
    )
    totals = reference.groupby("value_decile")["log_gap"].agg(decile_sum="sum", decile_n="count")
    own = reference.groupby(["tm_player_id", "value_decile"], as_index=False).agg(
        own_log_gap=("log_gap", "sum"), own_n=("log_gap", "count")
    )
    scored = pd.DataFrame(
        {
            "tm_player_id": pd.to_numeric(score_id, errors="coerce"),
            "value_decile": score_decile.to_numpy(),
            "log_gap": score_log_gap.to_numpy(),
        }
    )
    scored = scored.merge(totals, left_on="value_decile", right_index=True, how="left")
    scored = scored.merge(own, on=["tm_player_id", "value_decile"], how="left")
    has_own = scored["own_n"].fillna(0) > 0
    decile_sum = scored["decile_sum"] - np.where(has_own, scored["own_log_gap"].fillna(0), 0.0)
    decile_n = scored["decile_n"] - np.where(has_own, scored["own_n"].fillna(0), 0.0)
    decile_mean = np.where(decile_n > 0, decile_sum / decile_n, 0.0)
    return pd.DataFrame(
        {
            "value_decile": scored["value_decile"].to_numpy(),
            "decile_mean_log_gap": decile_mean,
            "calibrated_gap": scored["log_gap"].to_numpy() - decile_mean,
        }
    )


def top_undervalued(
    season: str = "2526",
    position_group: str | None = None,
    max_age: float | None = 27,
    min_value_eur: float | None = MIN_VALUE_EUR,
    n: int = 10,
    predictions: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Players whose stats imply a higher fee than the market.

    The rank uses the calibrated log gap when cheap fees are systematically
    over-predicted: raw log gap minus the mean log gap of that fee decile.
    value_gap and log_gap stay on the row. Fees under €2m are left out unless
    min_value_eur is set lower.
    """
    table = predictions.copy() if predictions is not None else pd.read_csv(PREDICTIONS_PATH)
    table["season"] = table["season"].map(_season_code)
    if "log_gap" not in table.columns:
        table["log_gap"] = np.log(table["predicted_value"]) - np.log(table["actual_value"])
    season_code = _season_code(season)
    rank = "log_gap"
    if "calibrated_gap" in table.columns and cheap_players_look_undervalued(value_decile_table(table, season_code)):
        rank = "calibrated_gap"
    table = table.loc[table["season"] == season_code]
    if position_group is not None:
        table = table.loc[table["position_group"] == position_group]
    if max_age is not None:
        table = table.loc[table["age"] <= max_age]
    if min_value_eur is not None:
        table = table.loc[table["actual_value"] >= min_value_eur]
    table = table.sort_values([rank, "player"], ascending=[False, True]).head(n)
    return table.reset_index(drop=True)


def _decile_labels(values: pd.Series) -> pd.Series:
    labels = pd.qcut(values, 10, labels=False, duplicates="drop")
    return labels.astype(int) + 1


def _decile_bounds(values: pd.Series) -> np.ndarray:
    _, bounds = pd.qcut(values, 10, retbins=True, duplicates="drop")
    bounds = bounds.astype(float).copy()
    bounds[0] = -np.inf
    bounds[-1] = np.inf
    return bounds


def _decile_from_bounds(values: pd.Series, bounds: np.ndarray) -> pd.Series:
    return pd.cut(values.astype(float), bounds, labels=False, include_lowest=True).astype(int) + 1


def weak_club_count(
    predictions: pd.DataFrame,
    n: int = 50,
    max_age: float = 27,
    min_value_eur: float = MIN_VALUE_EUR,
    season: str = "2526",
    valued: pd.DataFrame | None = None,
) -> int:
    """How many of the top undervalued players play for a bottom-third squad in their league."""
    shortlist = top_undervalued(
        season=season,
        max_age=max_age,
        min_value_eur=min_value_eur,
        n=n,
        predictions=predictions,
    )
    weak = _bottom_third_clubs(valued)
    season_code = _season_code(season)
    weak = weak.loc[weak["season"] == season_code, ["team", "league"]]
    marked = shortlist.merge(weak.assign(weak=True), on=["team", "league"], how="left")
    return int(marked["weak"].fillna(False).sum())


def _attach_team_strength(frame: pd.DataFrame, valued: pd.DataFrame) -> pd.DataFrame:
    """Leave-one-out teammate fees, plus the club's share of its league's squad value.

    The pool is every matched player at the club that season, including those under
    900 minutes. The player's own fee is subtracted so it cannot leak into his row.
    """
    squads = _squad_rows(valued)
    club = (
        squads.groupby(["team", "league", "season"], as_index=False)
        .agg(
            squad_value=("market_value_eur", "sum"),
            squad_log_sum=("log_value", "sum"),
            squad_n=("tm_player_id", "count"),
        )
    )
    league_total = club.groupby(["league", "season"])["squad_value"].sum().rename("league_value")
    club = club.merge(league_total.reset_index(), on=["league", "season"], how="left")
    own = squads[["tm_player_id", "team", "season", "market_value_eur", "log_value"]].rename(
        columns={"market_value_eur": "own_value", "log_value": "own_log"}
    )
    enriched = frame.copy()
    enriched["tm_player_id"] = pd.to_numeric(enriched["tm_player_id"], errors="coerce").astype("int64")
    enriched["season"] = enriched["season"].astype(int)
    enriched = enriched.merge(club, on=["team", "league", "season"], how="left")
    enriched = enriched.merge(own, on=["tm_player_id", "team", "season"], how="left")
    present = enriched["own_log"].notna()
    loo_n = enriched["squad_n"].fillna(0) - present.astype(int)
    loo_log = enriched["squad_log_sum"].fillna(0) - np.where(present, enriched["own_log"].fillna(0), 0)
    enriched["team_strength"] = np.where(loo_n > 0, loo_log / loo_n, np.nan)
    own_value = np.where(present, enriched["own_value"].fillna(0), 0)
    loo_league = enriched["league_value"].fillna(0) - own_value
    loo_squad = enriched["squad_value"].fillna(0) - own_value
    enriched["league_value_share"] = np.where(loo_league > 0, loo_squad / loo_league, np.nan)
    league_fallback = (
        club.assign(mean_log=club["squad_log_sum"] / club["squad_n"])
        .groupby(["league", "season"])["mean_log"]
        .mean()
        .rename("league_fallback")
    )
    enriched = enriched.merge(league_fallback.reset_index(), on=["league", "season"], how="left")
    enriched["team_strength"] = enriched["team_strength"].fillna(enriched["league_fallback"])
    enriched["league_value_share"] = enriched["league_value_share"].fillna(0.0)
    enriched["minutes_x_team_strength"] = enriched["minutes"] * enriched["team_strength"]
    drop = [
        "squad_value",
        "squad_log_sum",
        "squad_n",
        "league_value",
        "own_value",
        "own_log",
        "league_fallback",
    ]
    return enriched.drop(columns=drop)


def _squad_rows(valued: pd.DataFrame) -> pd.DataFrame:
    """One fee per matched player at each club and season, including short seasons."""
    rows = valued.loc[
        valued["season"].isin(MODEL_SEASONS)
        & valued["tm_player_id"].notna()
        & valued["market_value_eur"].notna()
        & (valued["market_value_eur"] > 0),
        ["tm_player_id", "team", "league", "season", "market_value_eur"],
    ].copy()
    rows["season"] = rows["season"].astype(int)
    rows["tm_player_id"] = pd.to_numeric(rows["tm_player_id"], errors="coerce").astype("int64")
    rows["market_value_eur"] = pd.to_numeric(rows["market_value_eur"], errors="coerce")
    rows = rows.groupby(["tm_player_id", "team", "league", "season"], as_index=False)["market_value_eur"].first()
    rows["log_value"] = np.log(rows["market_value_eur"])
    return rows


def _bottom_third_clubs(valued: pd.DataFrame | None = None) -> pd.DataFrame:
    """Clubs in the bottom third of their league by total squad value that season."""
    if valued is None:
        valued = pd.read_csv(VALUED_PATH)
    squads = _squad_rows(valued)
    club = squads.groupby(["team", "league", "season"], as_index=False)["market_value_eur"].sum()
    club = club.rename(columns={"market_value_eur": "squad_value"})
    club["pct"] = club.groupby(["league", "season"])["squad_value"].rank(method="average", pct=True, ascending=True)
    return club.loc[club["pct"] <= (1 / 3), ["team", "league", "season"]]


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
    if feature == "team_strength":
        return (
            "A doubling of the typical teammate's fee is associated with about "
            f"{_percent(per_unit_log * np.log(2)):+.0f}% of value."
        )
    if feature == "league_value_share":
        return (
            "A 10-point larger share of the league's squad value is associated with about "
            f"{_percent(per_unit_log * 0.10):+.0f}% of value."
        )
    if feature == "minutes_x_team_strength":
        return (
            "The same 1,000 minutes are worth about "
            f"{_percent(per_unit_log * 1000):+.0f}% more when teammates' fees are 2.7 times higher."
        )
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
    before = modeling.drop(columns=list(STRENGTH_COLUMNS))
    print("BEFORE")
    before_metrics = evaluate_models(before)
    print(before_metrics.round(3).to_string(index=False))
    before_scores = out_of_fold_predictions(before, "ridge", save=False)
    print("before weak clubs", weak_club_count(before_scores))
    print("AFTER")
    comparison = evaluate_models(modeling)
    print(comparison.round(3).to_string(index=False))
    winner, reason = choose_model(comparison)
    print(reason)
    scored = out_of_fold_predictions(modeling, winner)
    print("after weak clubs", weak_club_count(scored))
    print(f"Wrote {len(scored)} rows to {PREDICTIONS_PATH}")
