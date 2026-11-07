"""Build the player-season table that later steps read.

Raw FBref pages stay in data/raw/fbref/. This module is the only place that
knows those column names. Downstream code reads data/processed/player_season.csv.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_FBREF = ROOT / "data" / "raw" / "fbref"
OUT_PATH = ROOT / "data" / "processed" / "player_season.csv"

STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]
KEYS = ["league", "season", "team", "player"]

# Flattened FBref header -> output column. The same output name in two pages
# is one column; the earlier stat type wins when both have a value.
COLUMN_MAP = {
    "nation": "nationality",
    "pos": "position",
    "age": "age",
    "born": "birth_year",
    "Playing Time | MP": "matches",
    "Playing Time | Starts": "starts",
    "Playing Time | Min": "minutes",
    "Playing Time | 90s": "nineties",
    "Playing Time | Mn/MP": "minutes_per_match",
    "Playing Time | Min%": "squad_minutes_pct",
    "Performance | Gls": "goals",
    "Performance | Ast": "assists",
    "Performance | G+A": "goals_plus_assists",
    "Performance | G-PK": "non_penalty_goals",
    "Performance | PK": "penalty_goals",
    "Performance | PKatt": "penalty_attempts",
    "Performance | CrdY": "yellow_cards",
    "Performance | CrdR": "red_cards",
    "Performance | 2CrdY": "second_yellow_cards",
    "Performance | Fls": "fouls_committed",
    "Performance | Fld": "fouls_drawn",
    "Performance | Off": "offsides",
    "Performance | Crs": "crosses",
    "Performance | Int": "interceptions",
    "Performance | TklW": "tackles_won",
    "Performance | PKwon": "penalties_won",
    "Performance | PKcon": "penalties_conceded",
    "Performance | OG": "own_goals",
    "Per 90 Minutes | Gls": "goals_per_90",
    "Per 90 Minutes | Ast": "assists_per_90",
    "Per 90 Minutes | G+A": "goals_plus_assists_per_90",
    "Per 90 Minutes | G-PK": "non_penalty_goals_per_90",
    "Per 90 Minutes | G+A-PK": "non_penalty_goals_plus_assists_per_90",
    "90s": "nineties",
    "Standard | Gls": "goals",
    "Standard | Sh": "shots",
    "Standard | SoT": "shots_on_target",
    "Standard | SoT%": "shots_on_target_pct",
    "Standard | Sh/90": "shots_per_90",
    "Standard | SoT/90": "shots_on_target_per_90",
    "Standard | G/Sh": "goals_per_shot",
    "Standard | G/SoT": "goals_per_shot_on_target",
    "Standard | PK": "penalty_goals",
    "Standard | PKatt": "penalty_attempts",
    "Starts | Starts": "starts",
    "Starts | Mn/Start": "minutes_per_start",
    "Starts | Compl": "complete_matches",
    "Subs | Subs": "substitute_appearances",
    "Subs | Mn/Sub": "minutes_per_substitute_appearance",
    "Subs | unSub": "unused_substitute",
    "Team Success | PPM": "points_per_match",
    "Team Success | onG": "team_goals_on_pitch",
    "Team Success | onGA": "team_goals_against_on_pitch",
    "Team Success | +/-": "goal_difference_on_pitch",
    "Team Success | +/-90": "goal_difference_on_pitch_per_90",
    "Team Success | On-Off": "on_off_goal_difference",
}

# Which page a column is documented as coming from, when several pages have it.
COLUMN_SOURCE = {
    "nationality": "standard",
    "position": "standard",
    "age": "standard",
    "birth_year": "standard",
    "matches": "standard",
    "starts": "standard",
    "minutes": "standard",
    "nineties": "standard",
    "goals": "standard",
    "assists": "standard",
    "goals_plus_assists": "standard",
    "non_penalty_goals": "standard",
    "penalty_goals": "standard",
    "penalty_attempts": "standard",
    "yellow_cards": "standard",
    "red_cards": "standard",
    "goals_per_90": "standard",
    "assists_per_90": "standard",
    "goals_plus_assists_per_90": "standard",
    "non_penalty_goals_per_90": "standard",
    "non_penalty_goals_plus_assists_per_90": "standard",
    "shots": "shooting",
    "shots_on_target": "shooting",
    "shots_on_target_pct": "shooting",
    "shots_per_90": "shooting",
    "shots_on_target_per_90": "shooting",
    "goals_per_shot": "shooting",
    "goals_per_shot_on_target": "shooting",
    "minutes_per_match": "playing_time",
    "squad_minutes_pct": "playing_time",
    "minutes_per_start": "playing_time",
    "complete_matches": "playing_time",
    "substitute_appearances": "playing_time",
    "minutes_per_substitute_appearance": "playing_time",
    "unused_substitute": "playing_time",
    "points_per_match": "playing_time",
    "team_goals_on_pitch": "playing_time",
    "team_goals_against_on_pitch": "playing_time",
    "goal_difference_on_pitch": "playing_time",
    "goal_difference_on_pitch_per_90": "playing_time",
    "on_off_goal_difference": "playing_time",
    "second_yellow_cards": "misc",
    "fouls_committed": "misc",
    "fouls_drawn": "misc",
    "offsides": "misc",
    "crosses": "misc",
    "interceptions": "misc",
    "tackles_won": "misc",
    "penalties_won": "misc",
    "penalties_conceded": "misc",
    "own_goals": "misc",
    "source": "assigned here",
}

COLUMN_MEANING = {
    "player": "Player name, as published by FBref. Two people at the same club can share a name; birth year tells them apart.",
    "team": "Club the stats were recorded for. A mid-season move is a second row.",
    "league": "soccerdata league name, such as ENG-Premier League.",
    "season": "soccerdata season code. 2526 means the 2025-26 season.",
    "position": "Position codes from FBref, such as DF or MF,FW.",
    "age": "Age in whole years at the season in question.",
    "birth_year": "Year of birth.",
    "nationality": "Three-letter nationality code.",
    "minutes": "Minutes played for this club in this season.",
    "matches": "Matches played.",
    "starts": "Matches started.",
    "nineties": "Minutes played divided by 90.",
    "goals": "Goals.",
    "assists": "Assists.",
    "goals_plus_assists": "Goals plus assists.",
    "non_penalty_goals": "Goals excluding penalties.",
    "penalty_goals": "Penalty goals.",
    "penalty_attempts": "Penalty kicks taken.",
    "yellow_cards": "Yellow cards.",
    "red_cards": "Red cards.",
    "goals_per_90": "Goals per 90 minutes, as published by FBref. Not recomputed here.",
    "assists_per_90": "Assists per 90 minutes, as published by FBref.",
    "goals_plus_assists_per_90": "Goals plus assists per 90, as published by FBref.",
    "non_penalty_goals_per_90": "Non-penalty goals per 90, as published by FBref.",
    "non_penalty_goals_plus_assists_per_90": "Non-penalty goals plus assists per 90, as published by FBref.",
    "shots": "Shots, excluding penalty kicks.",
    "shots_on_target": "Shots on target, excluding penalty kicks.",
    "shots_on_target_pct": "Shots on target as a percentage of shots.",
    "shots_per_90": "Shots per 90 minutes, as published by FBref.",
    "shots_on_target_per_90": "Shots on target per 90 minutes, as published by FBref.",
    "goals_per_shot": "Goals per shot.",
    "goals_per_shot_on_target": "Goals per shot on target.",
    "minutes_per_match": "Average minutes per match played.",
    "squad_minutes_pct": "Share of the club's season minutes this player was on the pitch.",
    "minutes_per_start": "Average minutes in matches that were started.",
    "complete_matches": "Starts that lasted the full match.",
    "substitute_appearances": "Matches entered as a substitute.",
    "minutes_per_substitute_appearance": "Average minutes after coming on as a substitute.",
    "unused_substitute": "Matches spent on the bench unused.",
    "points_per_match": "Team points per match while the player was on the pitch.",
    "team_goals_on_pitch": "Team goals scored while the player was on the pitch.",
    "team_goals_against_on_pitch": "Team goals conceded while the player was on the pitch.",
    "goal_difference_on_pitch": "Goal difference while the player was on the pitch.",
    "goal_difference_on_pitch_per_90": "On-pitch goal difference per 90 minutes.",
    "on_off_goal_difference": "On-pitch goal difference per 90 minus the same rate when the player was off.",
    "second_yellow_cards": "Second yellow cards.",
    "fouls_committed": "Fouls committed.",
    "fouls_drawn": "Fouls drawn.",
    "offsides": "Offsides.",
    "crosses": "Crosses.",
    "interceptions": "Interceptions.",
    "tackles_won": "Tackles in which the team won the ball.",
    "penalties_won": "Penalties won.",
    "penalties_conceded": "Penalties conceded.",
    "own_goals": "Own goals.",
    "source": "Which feed produced the row. FBref rows are 'fbref'.",
}

IDENTITY = [
    "player",
    "team",
    "league",
    "season",
    "position",
    "age",
    "birth_year",
    "nationality",
    "minutes",
    "matches",
    "starts",
]
NUMERIC = [
    "birth_year",
    "minutes",
    "matches",
    "starts",
    "nineties",
    "goals",
    "assists",
    "goals_plus_assists",
    "non_penalty_goals",
    "penalty_goals",
    "penalty_attempts",
    "yellow_cards",
    "red_cards",
    "goals_per_90",
    "assists_per_90",
    "goals_plus_assists_per_90",
    "non_penalty_goals_per_90",
    "non_penalty_goals_plus_assists_per_90",
    "shots",
    "shots_on_target",
    "shots_on_target_pct",
    "shots_per_90",
    "shots_on_target_per_90",
    "goals_per_shot",
    "goals_per_shot_on_target",
    "minutes_per_match",
    "squad_minutes_pct",
    "minutes_per_start",
    "complete_matches",
    "substitute_appearances",
    "minutes_per_substitute_appearance",
    "unused_substitute",
    "points_per_match",
    "team_goals_on_pitch",
    "team_goals_against_on_pitch",
    "goal_difference_on_pitch",
    "goal_difference_on_pitch_per_90",
    "on_off_goal_difference",
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
]


def _rename_page(frame: pd.DataFrame) -> pd.DataFrame:
    """Rename one raw FBref page and keep the first copy of each output name."""
    renamed = frame.rename(columns=COLUMN_MAP)
    unknown = [column for column in renamed.columns if column not in COLUMN_MAP.values() and column not in KEYS]
    if unknown:
        raise ValueError(f"Unmapped FBref columns: {unknown}")
    keep = []
    for column in renamed.columns:
        if column not in keep:
            keep.append(column)
    return renamed.loc[:, keep]


def _combine(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    """Outer-merge on the player-club key and fill gaps from the right-hand page."""
    merged = left.merge(right, on=KEYS, how="outer", suffixes=("", "_incoming"))
    incoming = [column for column in merged.columns if column.endswith("_incoming")]
    for column in incoming:
        base = column[: -len("_incoming")]
        if base in merged.columns:
            merged[base] = merged[base].combine_first(merged[column])
            merged = merged.drop(columns=column)
        else:
            merged = merged.rename(columns={column: base})
    return merged


def build_player_season_table(
    raw_dir: Path | None = None,
    out_path: Path | None = None,
) -> pd.DataFrame:
    """Merge the four FBref pages into one row per player, club, league, and season.

    Parameters
    ----------
    raw_dir
        Directory of ``{stat_type}.csv`` files. Defaults to data/raw/fbref/.
    out_path
        Destination CSV. Defaults to data/processed/player_season.csv.
    """
    raw_dir = raw_dir or RAW_FBREF
    out_path = out_path or OUT_PATH

    merged = None
    for stat_type in STAT_TYPES:
        page = pd.read_csv(raw_dir / f"{stat_type}.csv")
        page = _rename_page(page)
        merged = page if merged is None else _combine(merged, page)

    if merged is None or merged.empty:
        raise RuntimeError(f"No FBref tables found in {raw_dir}.")

    merged["source"] = "fbref"
    ordered = [column for column in IDENTITY if column in merged.columns]
    ordered += [column for column in merged.columns if column not in ordered and column != "source"]
    ordered.append("source")
    merged = merged.loc[:, ordered]

    for column in NUMERIC:
        if column in merged.columns:
            merged[column] = pd.to_numeric(merged[column], errors="coerce")

    merged = merged.sort_values(KEYS).reset_index(drop=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)
    print(f"Wrote {len(merged):,} rows to {out_path}")
    return merged


def summarize(frame: pd.DataFrame) -> None:
    """Print row counts and the 2025-26 Tottenham squad."""
    print(f"rows: {len(frame):,}")
    counts = frame.groupby(["league", "season"], dropna=False).size().rename("rows")
    print(counts.to_string())
    enough = int((frame["minutes"] >= 900).sum())
    print(f"rows with at least 900 minutes: {enough:,}")

    spurs = frame[
        frame["team"].astype(str).str.contains("Tottenham", case=False, na=False)
        & frame["season"].astype(str).isin(["2526", "2025-26"])
    ]
    columns = [
        "player",
        "position",
        "minutes",
        "goals",
        "assists",
        "shots",
        "tackles_won",
        "interceptions",
    ]
    print(f"Tottenham 2025-26 rows: {len(spurs)}")
    print(spurs[columns].sort_values("minutes", ascending=False).to_string(index=False))


def write_data_dictionary(frame: pd.DataFrame, path: Path | None = None) -> Path:
    """Write reports/data_dictionary.md for the columns actually in the table."""
    path = path or ROOT / "reports" / "data_dictionary.md"
    lines = [
        "# Player-season data dictionary",
        "",
        "One row in `data/processed/player_season.csv` is a player at one club in one league season.",
        "A transfer during the season stays as two rows. Per-90 rates below are the figures FBref publishes;",
        "this table does not recompute them, and it does not drop players below a minutes cutoff.",
        "",
        "| column | meaning | source |",
        "| --- | --- | --- |",
    ]
    for column in frame.columns:
        meaning = COLUMN_MEANING.get(column, "")
        if column in KEYS:
            origin = "all FBref pages (merge key)"
        else:
            origin = COLUMN_SOURCE.get(column, "fbref")
            if origin not in {"assigned here"}:
                origin = f"fbref {origin}"
        lines.append(f"| `{column}` | {meaning} | {origin} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {path}")
    return path


if __name__ == "__main__":
    table = build_player_season_table()
    summarize(table)
    write_data_dictionary(table)
