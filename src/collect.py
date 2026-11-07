"""Download raw scouting inputs from Understat and Transfermarkt."""

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
    understat_error = None
    try:
        understat = collect_understat()
        print(understat.shape)
    except RuntimeError as exc:
        understat_error = exc
        print(exc)

    transfermarkt = collect_transfermarkt()
    for table_name, table in transfermarkt.items():
        print(table_name, table.shape)

    if understat_error is not None:
        raise understat_error
