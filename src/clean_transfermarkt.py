"""Clean the open Transfermarkt CSVs already stored in data/raw/transfermarkt/.

This module does not download anything. Downstream code reads
data/processed/tm_players.csv and data/processed/tm_season_values.csv.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "transfermarkt"
PLAYERS_OUT = ROOT / "data" / "processed" / "tm_players.csv"
SEASON_VALUES_OUT = ROOT / "data" / "processed" / "tm_season_values.csv"

PLAYER_COLUMNS = [
    "player_id",
    "name",
    "date_of_birth",
    "position",
    "sub_position",
    "foot",
    "height_in_cm",
    "country_of_citizenship",
    "current_club_name",
    "contract_expiration_date",
    "market_value_in_eur",
]

# End of season is June 30 of the second year. 2025-26 closes on 2026-06-30.
SEASON_END = {
    "2022-23": "2023-06-30",
    "2023-24": "2024-06-30",
    "2024-25": "2025-06-30",
    "2025-26": "2026-06-30",
}

TOTTENHAM = "Tottenham Hotspur"
# last_season in this dataset is the start year of the campaign. 2025 is 2025-26.
CURRENT_SQUAD_SEASON = 2025


def normalize_name(name: object) -> str | None:
    """Lowercase, strip accents, and turn hyphens and apostrophes into spaces."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    text = str(name).strip()
    if not text or text.lower() == "nan":
        return None
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = without_accents.lower().replace("-", " ").replace("'", " ").replace("’", " ")
    return re.sub(r"\s+", " ", lowered).strip() or None


def build_tm_players(players: pd.DataFrame | None = None) -> pd.DataFrame:
    """Keep the identity and contract columns and add name_normalized and birth_year."""
    if players is None:
        players = pd.read_csv(RAW_DIR / "players.csv")

    frame = players.loc[:, PLAYER_COLUMNS].copy()
    frame["date_of_birth"] = pd.to_datetime(frame["date_of_birth"], errors="coerce")
    frame["contract_expiration_date"] = pd.to_datetime(
        frame["contract_expiration_date"], errors="coerce"
    )
    frame["height_in_cm"] = pd.to_numeric(frame["height_in_cm"], errors="coerce")
    frame["market_value_in_eur"] = pd.to_numeric(frame["market_value_in_eur"], errors="coerce")
    frame["name_normalized"] = frame["name"].map(normalize_name)
    frame["birth_year"] = frame["date_of_birth"].dt.year.astype("Int64")
    frame["date_of_birth"] = frame["date_of_birth"].dt.date
    frame["contract_expiration_date"] = frame["contract_expiration_date"].dt.date
    return frame.loc[:, PLAYER_COLUMNS + ["name_normalized", "birth_year"]]


def value_at_date(player_valuations: pd.DataFrame, date) -> pd.DataFrame:
    """Most recent market value on or before `date` for each player.

    A valuation dated after the cutoff is never used. Players whose first
    valuation is after the cutoff are left out, so the caller sees no value.
    """
    cutoff = pd.Timestamp(date)
    valuations = player_valuations.loc[:, ["player_id", "date", "market_value_in_eur"]].copy()
    valuations["date"] = pd.to_datetime(valuations["date"], errors="coerce")
    valuations["market_value_in_eur"] = pd.to_numeric(
        valuations["market_value_in_eur"], errors="coerce"
    )
    eligible = valuations.loc[valuations["date"].notna() & (valuations["date"] <= cutoff)]
    columns = ["player_id", "market_value_eur", "value_date"]
    if eligible.empty:
        return pd.DataFrame(columns=columns)

    eligible = eligible.sort_values(["player_id", "date"], kind="mergesort")
    latest = eligible.groupby("player_id", as_index=False).tail(1)
    latest = latest.rename(columns={"market_value_in_eur": "market_value_eur", "date": "value_date"})
    latest["value_date"] = latest["value_date"].dt.date
    return latest.loc[:, columns].reset_index(drop=True)


def _assert_value_at_date() -> None:
    """Three cases: a value straddling the cutoff, a future-only player, an exact date."""
    sample = pd.DataFrame(
        {
            "player_id": [1, 1, 1, 2, 3],
            "date": ["2024-01-15", "2024-06-01", "2024-09-01", "2024-07-01", "2024-06-30"],
            "market_value_in_eur": [1_000_000, 2_000_000, 9_000_000, 5_000_000, 3_000_000],
        }
    )
    found = value_at_date(sample, "2024-06-30").set_index("player_id")

    # Player 1 has values before and after the cutoff. June wins; September must not.
    assert found.loc[1, "market_value_eur"] == 2_000_000
    assert pd.Timestamp(found.loc[1, "value_date"]) == pd.Timestamp("2024-06-01")

    # Player 2's only valuation is after the cutoff, so there is no value.
    assert 2 not in found.index

    # Player 3's valuation falls on the cutoff itself and is kept.
    assert found.loc[3, "market_value_eur"] == 3_000_000
    assert pd.Timestamp(found.loc[3, "value_date"]) == pd.Timestamp("2024-06-30")


def build_season_values(player_valuations: pd.DataFrame | None = None) -> pd.DataFrame:
    """Value every player at June 30 for each season from 2022-23 through 2025-26."""
    if player_valuations is None:
        player_valuations = pd.read_csv(RAW_DIR / "player_valuations.csv")

    frames = []
    for season, end in SEASON_END.items():
        valued = value_at_date(player_valuations, end)
        valued.insert(1, "season", season)
        frames.append(valued)
    return pd.concat(frames, ignore_index=True)


def current_tottenham_ids(players_raw: pd.DataFrame) -> pd.Series:
    """Players whose latest club is Tottenham and who appear in the 2025-26 squad."""
    squad = players_raw.loc[
        (players_raw["current_club_name"] == TOTTENHAM)
        & (players_raw["last_season"] == CURRENT_SQUAD_SEASON),
        "player_id",
    ]
    return squad


def write_tables(players: pd.DataFrame, season_values: pd.DataFrame) -> None:
    PLAYERS_OUT.parent.mkdir(parents=True, exist_ok=True)
    players.to_csv(PLAYERS_OUT, index=False)
    season_values.to_csv(SEASON_VALUES_OUT, index=False)
    print(f"Wrote {len(players):,} rows to {PLAYERS_OUT}")
    print(f"Wrote {len(season_values):,} rows to {SEASON_VALUES_OUT}")


def summarize(players: pd.DataFrame, season_values: pd.DataFrame, squad_ids: pd.Series) -> None:
    valued = players["market_value_in_eur"].notna()
    share = valued.mean() if len(players) else 0.0
    print(f"players: {len(players):,}")
    print(f"share with a market value: {share:.1%} ({int(valued.sum()):,} of {len(players):,})")

    latest = season_values.loc[season_values["season"] == "2025-26"]
    squad = players.loc[players["player_id"].isin(squad_ids), ["player_id", "name", "position"]]
    top = squad.merge(latest, on="player_id", how="inner")
    top = top.sort_values("market_value_eur", ascending=False).head(15)
    print(f"Tottenham 2025-26 end-of-season values, top {len(top)}:")
    show = top.loc[:, ["name", "position", "market_value_eur", "value_date"]]
    show["market_value_eur"] = show["market_value_eur"].map(lambda v: f"{int(v):,}")
    print(show.to_string(index=False))


def main() -> None:
    _assert_value_at_date()
    raw_players = pd.read_csv(RAW_DIR / "players.csv")
    valuations = pd.read_csv(RAW_DIR / "player_valuations.csv")
    players = build_tm_players(raw_players)
    season_values = build_season_values(valuations)
    write_tables(players, season_values)
    summarize(players, season_values, current_tottenham_ids(raw_players))


if __name__ == "__main__":
    main()
