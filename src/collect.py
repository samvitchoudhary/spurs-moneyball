"""Download raw scouting inputs.

FBref is the player-season source used downstream. Understat remains available
for when that site is back, but it is not called from ``main``.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
import soccerdata as sd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

UNDERSTAT_LEAGUES = [
    "ENG-Premier League",
    "ESP-La Liga",
    "GER-Bundesliga",
    "ITA-Serie A",
    "FRA-Ligue 1",
]
# soccerdata accepts "2025-26" and stores the season as "2526".
UNDERSTAT_SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26", "2026-27"]

# Prepared CSVs from dcaribou/transfermarkt-datasets (snapshot through 6 July 2026).
TRANSFERMARKT_BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
TRANSFERMARKT_TABLES = ["players", "player_valuations", "clubs", "transfers"]

# These four pages still return data. passing, defense, and possession do not.
FBREF_LEAGUES = UNDERSTAT_LEAGUES
FBREF_SEASONS = UNDERSTAT_SEASONS
FBREF_STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]


def collect_understat(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    out_path: Path | None = None,
) -> pd.DataFrame:
    """Pull Understat player-season stats and save them as CSV.

    Parameters
    ----------
    leagues
        soccerdata league names. Defaults to the big five.
    seasons
        Season labels such as "2025-26". Defaults to 2022-23 through 2026-27.
    out_path
        Destination CSV. Defaults to data/raw/understat_player_season.csv.
    """
    leagues = leagues or UNDERSTAT_LEAGUES
    seasons = seasons or UNDERSTAT_SEASONS
    out_path = out_path or RAW_DIR / "understat_player_season.csv"

    reader = sd.Understat(leagues=leagues, seasons=seasons)
    # A maintenance HTML page gets cached as leagues.json and then blocks later runs.
    leagues_cache = Path(reader.data_dir) / "leagues.json"
    if leagues_cache.exists():
        cached_start = leagues_cache.read_bytes().lstrip()[:1]
        if cached_start not in (b"{", b"["):
            leagues_cache.unlink()

    try:
        available = reader.read_seasons()
        frame = reader.read_player_season_stats()
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Understat did not return JSON. https://understat.com/getStatData is "
            "serving an HTML maintenance page ('We will come back soon') instead of "
            "player data. soccerdata already uses the JSON API from issue #904 "
            "(fixed in PR #907); this failure is the live site."
        ) from exc

    requested = {
        (league, reader._season_code.parse(season)) for league in leagues for season in seasons
    }
    missing = sorted(requested - set(available.index))
    if missing:
        print(f"Understat has no listing for {len(missing)} league-season pairs: {missing}")
    if frame.empty:
        raise RuntimeError("Understat returned no player season rows.")

    frame = frame.reset_index()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_path, index=False)
    print(f"Wrote {len(frame):,} rows to {out_path}")
    return frame


def _flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Turn a MultiIndex header into single 'Group | Stat' labels."""
    flat = frame.reset_index()
    columns = []
    for column in flat.columns:
        if isinstance(column, tuple):
            parts = [str(part) for part in column if str(part) not in {"", "nan"}]
            columns.append(" | ".join(parts))
        else:
            columns.append(str(column))
    flat.columns = columns
    return flat


def collect_fbref(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    stat_types: list[str] | None = None,
    out_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Pull FBref player-season pages and save one raw CSV per stat type.

    One league-season is requested at a time, on a single browser, so soccerdata
    can wait between downloads and reuse ``~/soccerdata/data/FBref``. A page that
    is already cached is not downloaded again.

    Parameters
    ----------
    leagues
        soccerdata league names. Defaults to the big five.
    seasons
        Season labels such as "2025-26". Defaults to 2022-23 through 2026-27.
    stat_types
        FBref player pages that still return data.
    out_dir
        Directory for ``{stat_type}.csv``. Defaults to data/raw/fbref/.
    """
    leagues = leagues or FBREF_LEAGUES
    seasons = seasons or FBREF_SEASONS
    stat_types = stat_types or FBREF_STAT_TYPES
    out_dir = out_dir or RAW_DIR / "fbref"
    out_dir.mkdir(parents=True, exist_ok=True)

    reader = sd.FBref(leagues=leagues[0], seasons=seasons[0])
    tables: dict[str, pd.DataFrame] = {}

    for stat_type in stat_types:
        pieces = []
        for league in leagues:
            for season in seasons:
                reader._selected_leagues = league
                reader.seasons = season
                parsed = reader.seasons[0]
                cache_path = Path(reader.data_dir) / f"players_{league}_{parsed}_{stat_type}.html"
                state = "cached" if cache_path.exists() else "downloading"
                print(f"FBref {stat_type}: {league} {season} ({state})", flush=True)
                try:
                    piece = reader.read_player_season_stats(stat_type=stat_type)
                except KeyError:
                    print(f"  no FBref season page for {league} {season}", flush=True)
                    continue
                if piece.empty:
                    print(f"  empty table for {league} {season}", flush=True)
                    continue
                pieces.append(piece)

        if not pieces:
            raise RuntimeError(f"FBref returned no rows for {stat_type}.")

        frame = _flatten_columns(pd.concat(pieces))
        path = out_dir / f"{stat_type}.csv"
        frame.to_csv(path, index=False)
        print(f"Wrote {len(frame):,} rows to {path}", flush=True)
        tables[stat_type] = frame

    return tables


def collect_transfermarkt(out_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Download prepared Transfermarkt CSVs into data/raw/transfermarkt/.

    Uses the public gzipped CSV URLs documented in
    dcaribou/transfermarkt-datasets. No API key is required.
    """
    out_dir = out_dir or RAW_DIR / "transfermarkt"
    out_dir.mkdir(parents=True, exist_ok=True)
    tables: dict[str, pd.DataFrame] = {}

    for name in TRANSFERMARKT_TABLES:
        url = f"{TRANSFERMARKT_BASE}/{name}.csv.gz"
        print(f"Downloading {url}")
        request = Request(url, headers={"User-Agent": "spurs-moneyball"})
        with urlopen(request, timeout=300) as response, gzip.GzipFile(fileobj=response) as handle:
            frame = pd.read_csv(handle, low_memory=False)
        path = out_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        print(f"Wrote {len(frame):,} rows to {path}")
        tables[name] = frame

    return tables


if __name__ == "__main__":
    fbref = collect_fbref()
    for stat_type, frame in fbref.items():
        print(stat_type, frame.shape)

    transfermarkt = collect_transfermarkt()
    for table_name, table in transfermarkt.items():
        print(table_name, table.shape)
