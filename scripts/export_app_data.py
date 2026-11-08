"""Write the tables the dashboard reads. Derived outputs only, no raw scrapes.

Run from the repo root:

    .venv/bin/python scripts/export_app_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.value_model import build_modeling_frame, choose_model, evaluate_models

PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "app_data"

VECTORS = [
    "player",
    "team",
    "league",
    "season",
    "age",
    "position_group",
    "minutes",
    "market_value_eur",
    "birth_year",
    "sub_position",
    "nationality",
    "goals_per90",
    "non_penalty_goals_per90",
    "assists_per90",
    "shots_per90",
    "shots_on_target_per90",
    "crosses_per90",
    "tackles_won_per90",
    "interceptions_per90",
    "fouls_committed_per90",
    "fouls_drawn_per90",
    "offsides_per90",
    "shot_accuracy",
    "goals_per_shot",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    vectors = _vectors()
    _write("player_vectors", vectors)
    _write("player_clusters", pd.read_csv(PROCESSED / "player_clusters.csv"))
    _write("cluster_names", pd.read_csv(PROCESSED / "cluster_names.csv"))
    _write("value_predictions", pd.read_csv(PROCESSED / "value_predictions.csv"))
    _write("backtest_signings", pd.read_csv(PROCESSED / "backtest_signings.csv"))
    _write("backtest_model_picks", pd.read_csv(PROCESSED / "backtest_model_picks.csv"))
    _write("spurs_needs", pd.read_csv(PROCESSED / "spurs_needs.csv"))
    _write("shortlist", pd.read_csv(PROCESSED / "shortlist.csv"))
    _write("model_metrics", _metrics())
    total = sum(path.stat().st_size for path in OUT.glob("*.parquet"))
    print(f"app_data total {total / 1_000_000:.2f} MB across {len(list(OUT.glob('*.parquet')))} files")


def _vectors() -> pd.DataFrame:
    """Z-scored profiles plus the nationality used for the flag on a card."""
    vectors = pd.read_csv(PROCESSED / "player_vectors.csv")
    valued = pd.read_csv(
        PROCESSED / "player_season_valued.csv",
        usecols=["player", "birth_year", "nationality", "minutes"],
    )
    valued["birth_year"] = pd.to_numeric(valued["birth_year"], errors="coerce")
    valued["minutes"] = pd.to_numeric(valued["minutes"], errors="coerce").fillna(0)
    valued = valued.sort_values("minutes", ascending=False)
    nationality = valued.drop_duplicates(["player", "birth_year"])[["player", "birth_year", "nationality"]]
    vectors["birth_year"] = pd.to_numeric(vectors["birth_year"], errors="coerce")
    vectors = vectors.merge(nationality, on=["player", "birth_year"], how="left")
    keep = [column for column in VECTORS if column in vectors.columns]
    frame = vectors.loc[:, keep].copy()
    for column in frame.select_dtypes(include="float").columns:
        frame[column] = frame[column].astype("float32")
    return frame


def _metrics() -> pd.DataFrame:
    """Ridge against gradient boosting, including the 2025-26 season the model never trained on."""
    frame = build_modeling_frame()
    metrics = evaluate_models(frame)
    winner, reason = choose_model(metrics)
    metrics["kept_model"] = winner
    metrics["reason"] = reason
    return metrics


def _write(name: str, frame: pd.DataFrame) -> None:
    path = OUT / f"{name}.parquet"
    frame.to_parquet(path, index=False)
    print(f"{name}: {len(frame):,} rows, {path.stat().st_size / 1_000:.0f} KB")


if __name__ == "__main__":
    main()
