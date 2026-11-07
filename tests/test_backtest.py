"""Cutoff checks for the transfer-window backtest.

These fail when a training season, a squad fee, or a January window uses
information from after the window opened.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest import (
    WINDOWS,
    Prepared,
    assert_values_before_cutoff,
    assert_window_cutoff,
    classify_outcome,
    prepare_window,
    season_in_progress,
    seasons_ended_before,
)
from src.clean_transfermarkt import RAW_DIR
from src.features import VALUED_PATH


@pytest.fixture(scope="module")
def valued() -> pd.DataFrame:
    return pd.read_csv(VALUED_PATH)


@pytest.fixture(scope="module")
def valuations(valued: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_csv(RAW_DIR / "player_valuations.csv", usecols=["player_id", "date", "market_value_in_eur"])
    ids = set(pd.to_numeric(valued["tm_player_id"], errors="coerce").dropna().astype(int))
    return raw.loc[raw["player_id"].isin(ids)]


@pytest.fixture(scope="module")
def prepared_windows(valued, valuations) -> dict[str, Prepared]:
    values_at: dict = {}
    return {
        window.name: prepare_window(window, valued, valuations, values_at)
        for window in WINDOWS
    }


def test_future_value_date_is_rejected():
    window = WINDOWS[0]
    valued = pd.DataFrame(
        {
            "season": [2223],
            "value_date": [window.cutoff + pd.Timedelta(days=1)],
        }
    )
    with pytest.raises(AssertionError):
        assert_values_before_cutoff(valued, window.cutoff)


def test_season_still_in_progress_is_rejected():
    window = next(item for item in WINDOWS if item.name == "January 2024")
    valued = pd.DataFrame(
        {
            "season": [2324],
            "value_date": ["2023-06-30"],
        }
    )
    with pytest.raises(AssertionError):
        assert_values_before_cutoff(valued, window.cutoff)


def test_every_window_keeps_training_rows_before_the_cutoff(prepared_windows):
    for window in WINDOWS:
        prepared = prepared_windows[window.name]
        assert_window_cutoff(prepared)
        train_dates = pd.to_datetime(prepared.train_valued["value_date"])
        score_dates = pd.to_datetime(prepared.score_valued["value_date"])
        assert train_dates.max() <= window.cutoff
        assert score_dates.max() <= window.cutoff
        ends = prepared.train_frame["season"].map(
            {2223: "2023-06-30", 2324: "2024-06-30", 2425: "2025-06-30", 2526: "2026-06-30"}
        )
        assert (pd.to_datetime(ends) < window.cutoff).all()
        assert season_in_progress(window.cutoff) not in set(prepared.train_frame["season"].astype(int))


def test_january_windows_use_the_last_completed_season_only(prepared_windows):
    """FBref's in-progress totals include games played after the January window."""
    # feature season, and the in-progress season that must be absent
    expected = {
        "January 2024": (2223, 2324),
        "January 2025": (2324, 2425),
        "January 2026": (2425, 2526),
    }
    for window in WINDOWS:
        if window.kind != "january":
            continue
        prepared = prepared_windows[window.name]
        feature, banned = expected[window.name]
        assert prepared.feature_season == feature
        assert set(prepared.score_frame["season"].astype(int)) == {feature}
        assert banned not in set(prepared.train_valued["season"].astype(int))
        assert banned not in set(prepared.score_valued["season"].astype(int))
        assert banned not in set(prepared.train_frame["season"].astype(int))
        assert max(seasons_ended_before(window.cutoff)) == feature
        assert (pd.to_datetime(prepared.score_valued["value_date"]).max() <= window.cutoff)


def test_spurs_minutes_are_not_a_feature(prepared_windows):
    for prepared in prepared_windows.values():
        assert not prepared.train_frame["team"].eq("Tottenham").any()
        assert not prepared.score_frame["team"].eq("Tottenham").any()
        assert not prepared.score_frame["all_teams"].astype(str).str.contains("Tottenham").any()


def test_style_labels_from_later_seasons_are_not_used(prepared_windows):
    for prepared in prepared_windows.values():
        assert (prepared.train_frame["style_cluster"] == "unknown").all()
        assert (prepared.score_frame["style_cluster"] == "unknown").all()


def test_outcome_labels():
    assert classify_outcome(0.60, 0.20, too_early=False) == "hit"
    assert classify_outcome(0.10, 0.20, too_early=False) == "miss"
    assert classify_outcome(0.80, -0.40, too_early=False) == "miss"
    assert classify_outcome(0.40, 0.10, too_early=False) == "mixed"
    assert classify_outcome(0.90, 0.50, too_early=True) == "too early"
