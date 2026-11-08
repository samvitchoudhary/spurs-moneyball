"""Where the current Spurs squad is short of the richest Premier League clubs.

The squad is whoever FBref lists at Tottenham in 2026-27. Quality and the
output profile use 2025-26 per-90 numbers, because most 2026-27 samples are
only a few matches. A 2026-27 arrival with no 2025-26 season in the top five
leagues is marked "no prior data" and does not enter the quality or output
averages.

Contracts are Transfermarkt's July 2026 snapshot, not a live expiry list.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.cluster import CLUSTER_NAMES_PATH, PLAYER_CLUSTERS_PATH
from src.features import (
    TM_PLAYERS_PATH,
    VALUED_PATH,
    add_per90,
    assign_position_group,
    combine_club_stints,
)
from src.value_model import POSITION_ORDER, PREDICTIONS_PATH

NEEDS_PATH = VALUED_PATH.parent / "spurs_needs.csv"
SPURS = "Tottenham"
CURRENT_SEASON = 2627
PRIOR_SEASON = 2526
LEAGUE = "ENG-Premier League"
N_BENCHMARK = 6
DEPTH_SHARE = 0.25
AGE_RISK = 30
CONTRACT_CUTOFF = pd.Timestamp("2027-06-30")
TOP_N_QUALITY = 2
# Same bar the value model uses. A shorter 2025-26 season is prior data, but
# its per-90 rates are too noisy to put in the output profile.
MIN_PRIOR_MINUTES = 900

# Higher means more of the action. The percentile says where Spurs' weighted
# rate sits among the benchmark players. Fouls are included as an action, the
# same way the style clusters use them.
PROFILE_STATS = {
    "CB": ("tackles_won_per90", "interceptions_per90", "fouls_committed_per90", "shot_accuracy"),
    "FB": ("crosses_per90", "tackles_won_per90", "interceptions_per90", "shots_per90"),
    "CM": ("shots_per90", "assists_per90", "tackles_won_per90", "interceptions_per90"),
    "AM_W": ("shots_per90", "shots_on_target_per90", "assists_per90", "crosses_per90"),
    "ST": ("shots_per90", "shots_on_target_per90", "goals_per90", "non_penalty_goals_per90"),
}
STAT_LABELS = {
    "tackles_won_per90": "tackles won",
    "interceptions_per90": "interceptions",
    "fouls_committed_per90": "fouls",
    "shot_accuracy": "shot accuracy",
    "crosses_per90": "crosses",
    "shots_per90": "shots",
    "assists_per90": "assists",
    "shots_on_target_per90": "shots on target",
    "goals_per90": "goals",
    "non_penalty_goals_per90": "non-penalty goals",
}

# Gaps are signed so a larger number means Spurs are further behind.
WEIGHTS = {
    "quality": 0.35,
    "output": 0.25,
    "depth": 0.20,
    "age": 0.10,
    "contract": 0.10,
}


def build_needs(
    valued: pd.DataFrame | None = None,
    predictions: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Need score for each outfield role, plus the player rows behind it."""
    if valued is None:
        valued = pd.read_csv(VALUED_PATH)
    if predictions is None:
        predictions = pd.read_csv(PREDICTIONS_PATH)
    benchmark = benchmark_clubs(valued)
    clubs = [SPURS, *benchmark]
    squad = _current_squad(valued, clubs)
    prior = _prior_season(valued, predictions)
    squad = squad.merge(prior, on="player", how="left", suffixes=("", "_prior"))
    squad["no_prior_data"] = squad["prior_minutes"].isna() | squad["prior_minutes"].le(0)
    squad["usable_prior"] = squad["prior_minutes"].ge(MIN_PRIOR_MINUTES)
    squad = _attach_contracts(squad)
    squad = _attach_styles(squad)
    needs = _score_groups(squad, benchmark)
    return needs, squad


def benchmark_clubs(valued: pd.DataFrame | None = None, n: int = N_BENCHMARK) -> list[str]:
    """The n Premier League clubs with the biggest 2025-26 squad value, Spurs excluded."""
    if valued is None:
        valued = pd.read_csv(VALUED_PATH, usecols=["team", "league", "season", "tm_player_id", "market_value_eur"])
    frame = valued.loc[
        (valued["season"] == PRIOR_SEASON) & (valued["league"] == LEAGUE) & (valued["team"] != SPURS)
    ].copy()
    frame["tm_player_id"] = pd.to_numeric(frame["tm_player_id"], errors="coerce")
    frame["market_value_eur"] = pd.to_numeric(frame["market_value_eur"], errors="coerce")
    frame = frame.loc[frame["tm_player_id"].notna() & frame["market_value_eur"].gt(0)]
    frame = frame.groupby(["team", "tm_player_id"], as_index=False)["market_value_eur"].first()
    totals = frame.groupby("team")["market_value_eur"].sum().sort_values(ascending=False)
    return totals.head(n).index.tolist()


def _current_squad(valued: pd.DataFrame, clubs: list[str]) -> pd.DataFrame:
    """2026-27 rows for Spurs and the benchmark, with a role and minutes so far."""
    frame = valued.loc[
        (valued["season"] == CURRENT_SEASON) & (valued["league"] == LEAGUE) & valued["team"].isin(clubs)
    ].copy()
    frame = assign_position_group(frame)
    frame = frame.loc[frame["position_group"].isin(POSITION_ORDER)].copy()
    frame["minutes"] = pd.to_numeric(frame["minutes"], errors="coerce").fillna(0.0)
    frame["matches"] = pd.to_numeric(frame["matches"], errors="coerce")
    frame["age"] = _age_years(frame["age"])
    available = frame.groupby("team")["matches"].max() * 90.0
    frame["available_minutes"] = frame["team"].map(available)
    frame["minutes_share"] = np.where(frame["available_minutes"] > 0, frame["minutes"] / frame["available_minutes"], 0.0)
    frame["is_depth"] = frame["minutes_share"] >= DEPTH_SHARE
    frame["age_risk"] = frame["age"] >= AGE_RISK
    # A mid-season move can leave a zero-minute row at the old club. That stub
    # is not a squad member once he has minutes somewhere else.
    played = set(frame.loc[frame["minutes"] > 0, "player"])
    stub = frame["player"].isin(played) & frame["minutes"].le(0)
    return frame.loc[~stub].reset_index(drop=True)


def _prior_season(valued: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    """One 2025-26 row per player: per-90 rates and the model's predicted fee."""
    prior = valued.loc[valued["season"] == PRIOR_SEASON].copy()
    prior = add_per90(assign_position_group(combine_club_stints(prior)))
    stats = [column for columns in PROFILE_STATS.values() for column in columns]
    keep = ["player", "minutes", "position_group", *dict.fromkeys(stats)]
    prior = prior.loc[:, [column for column in keep if column in prior.columns]]
    prior = prior.rename(columns={"minutes": "prior_minutes", "position_group": "prior_position_group"})
    predicted = predictions.loc[predictions["season"].map(_season_code) == PRIOR_SEASON, ["player", "predicted_value"]]
    predicted = predicted.groupby("player", as_index=False)["predicted_value"].mean()
    return prior.merge(predicted, on="player", how="left")


def _score_groups(squad: pd.DataFrame, benchmark: list[str]) -> pd.DataFrame:
    rows = []
    for group in POSITION_ORDER:
        spurs = squad.loc[(squad["team"] == SPURS) & (squad["position_group"] == group)]
        others = [
            squad.loc[(squad["team"] == club) & (squad["position_group"] == group)]
            for club in benchmark
        ]
        depth = _depth(spurs, others)
        quality = _quality(spurs, others)
        output = _output(spurs, others, PROFILE_STATS[group])
        age = _minute_share(spurs, others, "age_risk")
        contract = _contract_share(spurs, others)
        styles = _styles(spurs, squad.loc[squad["team"].isin(benchmark) & (squad["position_group"] == group)])
        rows.append(
            {
                "position_group": group,
                "benchmark_clubs": ", ".join(benchmark),
                "profile_stats": ", ".join(STAT_LABELS[stat] for stat in PROFILE_STATS[group]),
                "spurs_players": spurs["player"].nunique(),
                "no_prior_data": ", ".join(sorted(spurs.loc[spurs["no_prior_data"], "player"])),
                "position_fallback": ", ".join(
                    sorted(spurs.loc[spurs["position_source"].eq("fbref_fallback"), "player"])
                ),
                **depth,
                **quality,
                **output,
                **age,
                **contract,
                **styles,
            }
        )
    needs = pd.DataFrame(rows)
    needs["quality_gap"] = needs["benchmark_quality"] - needs["spurs_quality"]
    needs["output_gap"] = 50.0 - needs["output_percentile"]
    needs["depth_gap"] = needs["benchmark_depth"] - needs["spurs_depth"]
    needs["age_gap"] = needs["spurs_age_share"] - needs["benchmark_age_share"]
    needs["contract_gap"] = needs["spurs_contract_share"] - needs["benchmark_contract_share"]
    for component in WEIGHTS:
        needs[f"z_{component}"] = _zscore(needs[f"{component}_gap"])
    needs["need_score"] = sum(weight * needs[f"z_{name}"] for name, weight in WEIGHTS.items())
    needs["rank"] = needs["need_score"].rank(ascending=False, method="min").astype(int)
    needs = _sensitivity(needs)
    return needs.sort_values("need_score", ascending=False).reset_index(drop=True)


def _depth(spurs: pd.DataFrame, others: list[pd.DataFrame]) -> dict:
    spurs_depth = int(spurs["is_depth"].sum())
    benchmark = [int(frame["is_depth"].sum()) for frame in others]
    return {"spurs_depth": spurs_depth, "benchmark_depth": float(np.mean(benchmark))}


def _quality(spurs: pd.DataFrame, others: list[pd.DataFrame]) -> dict:
    return {
        "spurs_quality": _top_predicted(spurs),
        "spurs_quality_n": _quality_count(spurs),
        "benchmark_quality": float(np.nanmean([_top_predicted(frame) for frame in others])),
        "spurs_quality_players": ", ".join(_top_names(spurs)),
    }


def _quality_count(frame: pd.DataFrame) -> int:
    ranked = frame.sort_values(["minutes", "player"], ascending=[False, True]).head(TOP_N_QUALITY)
    return int(ranked["predicted_value"].notna().sum())


def _top_predicted(frame: pd.DataFrame) -> float:
    ranked = frame.sort_values(["minutes", "player"], ascending=[False, True]).head(TOP_N_QUALITY)
    values = ranked["predicted_value"].dropna()
    if values.empty:
        return np.nan
    return float(values.mean())


def _top_names(frame: pd.DataFrame) -> list[str]:
    ranked = frame.sort_values(["minutes", "player"], ascending=[False, True]).head(TOP_N_QUALITY)
    return [str(name) for name in ranked["player"]]


def _output(spurs: pd.DataFrame, others: list[pd.DataFrame], stats: tuple[str, ...]) -> dict:
    benchmark_players = pd.concat(others, ignore_index=True) if others else pd.DataFrame()
    percentiles = []
    detail = {}
    for stat in stats:
        spurs_rate = _weighted_rate(spurs, stat)
        if stat in benchmark_players.columns and "usable_prior" in benchmark_players.columns:
            sample = benchmark_players.loc[benchmark_players["usable_prior"], stat].dropna()
        else:
            sample = pd.Series(dtype=float)
        percentile = _percentile(spurs_rate, sample)
        percentiles.append(percentile)
        detail[f"pct_{stat}"] = percentile
    finite = [value for value in percentiles if pd.notna(value)]
    detail["output_percentile"] = float(np.mean(finite)) if finite else np.nan
    if "usable_prior" in benchmark_players.columns:
        detail["output_comparison_n"] = int(benchmark_players["usable_prior"].sum())
    else:
        detail["output_comparison_n"] = 0
    return detail


def _weighted_rate(frame: pd.DataFrame, stat: str) -> float:
    if stat not in frame.columns:
        return np.nan
    usable = frame.loc[frame["usable_prior"].fillna(False) & frame[stat].notna() & frame["minutes"].gt(0), [stat, "minutes"]]
    if usable.empty or usable["minutes"].sum() <= 0:
        return np.nan
    return float(np.average(usable[stat], weights=usable["minutes"]))


def _minute_share(spurs: pd.DataFrame, others: list[pd.DataFrame], flag: str) -> dict:
    return {
        "spurs_age_share": _share(spurs, flag),
        "benchmark_age_share": float(np.nanmean([_share(frame, flag) for frame in others])),
    }


def _contract_share(spurs: pd.DataFrame, others: list[pd.DataFrame]) -> dict:
    return {
        "spurs_contract_share": _share(spurs, "contract_risk", known="contract_known"),
        "benchmark_contract_share": float(
            np.nanmean([_share(frame, "contract_risk", known="contract_known") for frame in others])
        ),
    }


def _share(frame: pd.DataFrame, flag: str, known: str | None = None) -> float:
    rows = frame.loc[frame[known]] if known else frame
    minutes = rows["minutes"].sum()
    if minutes <= 0:
        return np.nan
    return float(rows.loc[rows[flag].fillna(False), "minutes"].sum() / minutes)


def _styles(spurs: pd.DataFrame, benchmark_players: pd.DataFrame) -> dict:
    names = pd.read_csv(CLUSTER_NAMES_PATH)
    if len(spurs):
        group = spurs["position_group"].iloc[0]
    elif len(benchmark_players):
        group = benchmark_players["position_group"].iloc[0]
    else:
        group = None
    catalogue = names.loc[names["position_group"] == group, "cluster_name"]
    present = sorted(spurs["style_cluster"].dropna().unique())
    catalogue = [str(name) for name in catalogue if pd.notna(name)]
    missing = [name for name in catalogue if name not in present]
    benchmark_styles = benchmark_players["style_cluster"].dropna()
    target = ""
    if missing:
        counts = benchmark_styles.value_counts()
        ranked = sorted(missing, key=lambda name: (-int(counts.get(name, 0)), name))
        target = ranked[0]
    return {
        "styles_present": ", ".join(present),
        "styles_missing": ", ".join(missing),
        "target_style": target,
    }


def _sensitivity(needs: pd.DataFrame) -> pd.DataFrame:
    """Equal weights, and quality lifted to half with the other weights scaled to match."""
    frame = needs.copy()
    equal = {name: 1.0 / len(WEIGHTS) for name in WEIGHTS}
    rest = 1.0 - WEIGHTS["quality"]
    quality_half = {
        name: (0.50 if name == "quality" else 0.50 * weight / rest)
        for name, weight in WEIGHTS.items()
    }
    frame["need_score_equal"] = sum(weight * frame[f"z_{name}"] for name, weight in equal.items())
    frame["need_score_quality50"] = sum(weight * frame[f"z_{name}"] for name, weight in quality_half.items())
    base_top = set(frame.nlargest(2, "need_score")["position_group"])
    frame["top2_equal_changed"] = set(frame.nlargest(2, "need_score_equal")["position_group"]) != base_top
    frame["top2_quality50_changed"] = set(frame.nlargest(2, "need_score_quality50")["position_group"]) != base_top
    return frame


def _attach_contracts(squad: pd.DataFrame) -> pd.DataFrame:
    players = pd.read_csv(TM_PLAYERS_PATH, usecols=["player_id", "contract_expiration_date"])
    players["player_id"] = pd.to_numeric(players["player_id"], errors="coerce")
    players["contract_expiration_date"] = pd.to_datetime(players["contract_expiration_date"], errors="coerce")
    frame = squad.copy()
    frame["tm_player_id"] = pd.to_numeric(frame["tm_player_id"], errors="coerce")
    frame = frame.merge(players, left_on="tm_player_id", right_on="player_id", how="left")
    frame = frame.drop(columns=["player_id"])
    frame["contract_known"] = frame["contract_expiration_date"].notna()
    frame["contract_risk"] = frame["contract_expiration_date"].le(CONTRACT_CUTOFF)
    return frame


def _attach_styles(squad: pd.DataFrame) -> pd.DataFrame:
    """2025-26 style. A player keeps the style from the club where he played most."""
    clusters = pd.read_csv(PLAYER_CLUSTERS_PATH)
    clusters["minutes"] = pd.to_numeric(clusters["minutes"], errors="coerce").fillna(0.0)
    clusters = clusters.sort_values(["player", "position_group", "minutes"], ascending=[True, True, False])
    clusters = clusters.drop_duplicates(["player", "position_group"])
    styles = clusters.loc[:, ["player", "position_group", "cluster_name"]].rename(columns={"cluster_name": "style_cluster"})
    return squad.merge(styles, on=["player", "position_group"], how="left")


def _percentile(value, sample: pd.Series) -> float:
    values = pd.to_numeric(sample, errors="coerce").dropna().to_numpy(dtype=float)
    if not np.isfinite(value) or len(values) == 0:
        return np.nan
    below = np.mean(values < value)
    tied = np.mean(values == value)
    return float((below + 0.5 * tied) * 100.0)


def _zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


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
    needs, squad = build_needs()
    NEEDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    needs.to_csv(NEEDS_PATH, index=False)
    show = [
        "position_group",
        "need_score",
        "spurs_depth",
        "benchmark_depth",
        "spurs_quality",
        "benchmark_quality",
        "output_percentile",
        "spurs_age_share",
        "spurs_contract_share",
        "styles_missing",
        "target_style",
        "top2_equal_changed",
        "top2_quality50_changed",
    ]
    print(needs[show].round(3).to_string(index=False))
    print(f"Wrote {len(needs)} rows to {NEEDS_PATH}")
    spurs = squad.loc[squad["team"] == SPURS, ["player", "position_group", "minutes", "no_prior_data", "style_cluster"]]
    print(spurs.sort_values(["position_group", "minutes"], ascending=[True, False]).to_string(index=False))
