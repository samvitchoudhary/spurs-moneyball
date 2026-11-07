"""Turn player-season rows into per-90 vectors, z-scored within position group."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VALUED_PATH = ROOT / "data" / "processed" / "player_season_valued.csv"
TM_PLAYERS_PATH = ROOT / "data" / "processed" / "tm_players.csv"
VECTORS_PATH = ROOT / "data" / "processed" / "player_vectors.csv"

# Additive columns. Rates are recomputed after stints are combined.
COUNTING_STATS = [
    "minutes",
    "matches",
    "starts",
    "goals",
    "assists",
    "goals_plus_assists",
    "non_penalty_goals",
    "penalty_goals",
    "penalty_attempts",
    "yellow_cards",
    "red_cards",
    "shots",
    "shots_on_target",
    "second_yellow_cards",
    "fouls_committed",
    "fouls_drawn",
    "offsides",
    "crosses",
    "interceptions",
    "tackles_won",
    "penalties_won",
    "penalties_conceded",
    "own_goals",
    "complete_matches",
    "substitute_appearances",
    "unused_substitute",
]

PER90_STATS = [
    "goals",
    "non_penalty_goals",
    "assists",
    "shots",
    "shots_on_target",
    "crosses",
    "tackles_won",
    "interceptions",
    "fouls_committed",
    "fouls_drawn",
    "offsides",
]

SUB_POSITION_GROUP = {
    "Centre-Back": "CB",
    "Left-Back": "FB",
    "Right-Back": "FB",
    "Defensive Midfield": "CM",
    "Central Midfield": "CM",
    "Attacking Midfield": "AM_W",
    "Left Winger": "AM_W",
    "Right Winger": "AM_W",
    "Left Midfield": "AM_W",
    "Right Midfield": "AM_W",
    "Centre-Forward": "ST",
    "Second Striker": "ST",
    "Goalkeeper": "GK",
}

FBREF_FALLBACK = {"DF": "CB", "MF": "CM", "FW": "ST", "GK": "GK"}

METADATA_COLUMNS = [
    "player",
    "team",
    "league",
    "season",
    "age",
    "position_group",
    "minutes",
    "market_value_eur",
    "tm_player_id",
    "birth_year",
    "all_teams",
    "sub_position",
    "position_source",
]


def feature_columns(frame: pd.DataFrame | None = None) -> list[str]:
    """Per-90 rates, plus shot accuracy and goals per shot.

    A saved vector table already uses these names as columns. A stats table
    still has the counting stats, so the same list is the one add_per90 builds.
    """
    names = [f"{stat}_per90" for stat in PER90_STATS] + ["shot_accuracy", "goals_per_shot"]
    if frame is None:
        return names
    present = [name for name in names if name in frame.columns]
    return present or names


def combine_club_stints(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse a mid-season move into one row per player per season.

    Counting stats and minutes are summed. `team` and `league` come from the
    club where he played the most minutes. `all_teams` lists every club,
    highest minutes first.
    """
    frame = df.copy()
    frame["_row"] = np.arange(len(frame))
    present = [col for col in COUNTING_STATS if col in frame.columns]
    for col in present:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)

    keys = ["player", "birth_year", "season"]
    frame["_stint_id"] = frame.groupby(keys, dropna=False).ngroup()
    ordered = frame.sort_values(
        ["_stint_id", "minutes", "team", "_row"],
        ascending=[True, False, True, True],
        kind="mergesort",
    )
    main = ordered.groupby("_stint_id", sort=False).head(1).copy()
    summed = ordered.groupby("_stint_id", sort=False)[present].sum()
    clubs = (
        ordered.groupby("_stint_id", sort=False)["team"]
        .agg(lambda clubs: ", ".join(dict.fromkeys(clubs.dropna().astype(str))))
        .rename("all_teams")
    )
    values = (
        ordered.groupby("_stint_id", sort=False)["market_value_eur"]
        .apply(lambda series: series.dropna().iloc[0] if series.notna().any() else np.nan)
        .rename("market_value_eur")
    )

    main = main.drop(columns=present)
    main = main.join(summed, on="_stint_id")
    main["all_teams"] = main["_stint_id"].map(clubs)
    main["market_value_eur"] = main["_stint_id"].map(values)
    return main.drop(columns=["_row", "_stint_id"]).reset_index(drop=True)


def assign_position_group(df: pd.DataFrame) -> pd.DataFrame:
    """Map Transfermarkt sub_position into CB, FB, CM, AM_W, ST, or GK.

    Players with no usable sub_position fall back to FBref's first listed
    position and are marked position_source='fbref_fallback'.
    """
    frame = df.copy()
    if "sub_position" not in frame.columns:
        tm = pd.read_csv(TM_PLAYERS_PATH, usecols=["player_id", "sub_position"])
        frame = frame.merge(
            tm,
            left_on="tm_player_id",
            right_on="player_id",
            how="left",
        )
        if "player_id" in frame.columns:
            frame = frame.drop(columns=["player_id"])

    frame["position_group"] = frame["sub_position"].map(SUB_POSITION_GROUP)
    first_fbref = (
        frame["position"].astype("string").str.split(",").str[0].str.strip()
        if "position" in frame.columns
        else pd.Series(pd.NA, index=frame.index, dtype="string")
    )
    fallback = first_fbref.map(FBREF_FALLBACK)
    missing = frame["position_group"].isna() & fallback.notna()
    frame.loc[missing, "position_group"] = fallback[missing]
    frame["position_source"] = pd.NA
    frame.loc[frame["position_group"].notna() & ~missing, "position_source"] = "tm"
    frame.loc[missing, "position_source"] = "fbref_fallback"
    return frame


def add_per90(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-90 rates for the counting stats, plus shot accuracy and goals per shot."""
    frame = df.copy()
    minutes = pd.to_numeric(frame["minutes"], errors="coerce")
    per_ninety = minutes.where(minutes > 0) / 90.0
    built = []
    for stat in PER90_STATS:
        if stat not in frame.columns:
            continue
        column = f"{stat}_per90"
        values = pd.to_numeric(frame[stat], errors="coerce").fillna(0.0)
        frame[column] = (values / per_ninety).fillna(0.0)
        built.append(column)

    shots = pd.to_numeric(frame["shots"], errors="coerce").fillna(0.0) if "shots" in frame else 0.0
    on_target = (
        pd.to_numeric(frame["shots_on_target"], errors="coerce").fillna(0.0)
        if "shots_on_target" in frame
        else 0.0
    )
    goals = pd.to_numeric(frame["goals"], errors="coerce").fillna(0.0) if "goals" in frame else 0.0
    frame["shot_accuracy"] = np.where(shots > 0, on_target / shots, 0.0)
    frame["goals_per_shot"] = np.where(shots > 0, goals / shots, 0.0)
    built.extend(["shot_accuracy", "goals_per_shot"])
    print("Feature list:", ", ".join(built))
    return frame


def _age_years(series: pd.Series) -> pd.Series:
    """FBref stores age as years, or as 'years-days'. Keep the years."""
    text = series.astype("string").str.split("-").str[0]
    return pd.to_numeric(text, errors="coerce")


def _zscore(series: pd.Series) -> pd.Series:
    """Population z-score. A feature with no spread becomes 0."""
    std = series.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def build_feature_matrix(
    df: pd.DataFrame, min_minutes: int = 900
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep outfield players with enough minutes and z-score within position group.

    Goalkeepers are left out of the outfield model. The mean and standard
    deviation for each feature come from that position group only. Writes
    metadata plus the z-scored features to data/processed/player_vectors.csv.
    """
    frame = df.copy()
    frame["minutes"] = pd.to_numeric(frame["minutes"], errors="coerce").fillna(0.0)
    frame = frame.loc[frame["position_group"].ne("GK") & frame["position_group"].notna()].copy()
    frame = frame.loc[frame["minutes"] >= min_minutes].copy()

    features = feature_columns(frame)
    for column in features:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    z_scored = frame.groupby("position_group", sort=False)[features].transform(_zscore)
    z_scored = z_scored.fillna(0.0)

    frame["age"] = _age_years(frame["age"]) if "age" in frame.columns else np.nan
    meta_cols = [col for col in METADATA_COLUMNS if col in frame.columns]
    metadata = frame[meta_cols].reset_index(drop=True)
    matrix = z_scored.reset_index(drop=True)
    matrix.columns = features

    saved = pd.concat([metadata, matrix], axis=1)
    VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    saved.to_csv(VECTORS_PATH, index=False)
    return matrix, metadata


def build_player_vectors(valued: pd.DataFrame | None = None) -> pd.DataFrame:
    """Run the full pipeline and return the saved player-vector table."""
    if valued is None:
        valued = pd.read_csv(VALUED_PATH)
    combined = combine_club_stints(valued)
    positioned = assign_position_group(combined)
    rated = add_per90(positioned)
    matrix, metadata = build_feature_matrix(rated)
    return pd.concat([metadata, matrix], axis=1)


if __name__ == "__main__":
    vectors = build_player_vectors()
    print(f"Wrote {len(vectors)} player-seasons to {VECTORS_PATH}")
    print(vectors["position_group"].value_counts().to_string())
