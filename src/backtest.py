"""Replay the value model at each Tottenham window, using only what was known then.

The transfers file spells the senior club "Tottenham" (club id 148). clubs.csv
calls the same club Tottenham Hotspur. Youth sides are a different club id and
are not Spurs signings.

A loan is not labeled in the file. A zero-fee move is marked a loan only when
the player returns to the same club for no fee, or this row is that return.
A free permanent transfer stays a free transfer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from src.clean_transfermarkt import RAW_DIR, value_at_date
from src.features import SUB_POSITION_GROUP, VALUED_PATH
from src.value_model import (
    MIN_VALUE_EUR,
    POSITION_ORDER,
    _fit_predict,
    build_modeling_frame,
    design_matrix,
)

TRANSFERS_PATH = RAW_DIR / "transfers.csv"
VALUATIONS_PATH = RAW_DIR / "player_valuations.csv"
TM_PLAYERS_PATH = RAW_DIR / "players.csv"
SIGNINGS_PATH = VALUED_PATH.parent / "backtest_signings.csv"
PICKS_PATH = VALUED_PATH.parent / "backtest_model_picks.csv"

# FBref's Premier League denominator: 38 matches x 90 minutes.
SPURS_SEASON_MINUTES = 38 * 90
TOTTENHAM_CLUB_ID = 148
TOTTENHAM_TEAM = "Tottenham"
VALUE_DROP = np.log(0.75)
N_FOLDS = 5

# season code -> the day that season ends. A season is usable only after this date.
SEASON_END = {
    2223: pd.Timestamp("2023-06-30"),
    2324: pd.Timestamp("2024-06-30"),
    2425: pd.Timestamp("2025-06-30"),
    2526: pd.Timestamp("2026-06-30"),
}
SEASON_ORDER = (2223, 2324, 2425, 2526)


@dataclass(frozen=True)
class Window:
    name: str
    cutoff: pd.Timestamp
    closes: pd.Timestamp
    kind: str

    @property
    def too_early_after(self) -> pd.Timestamp:
        return self.cutoff + pd.DateOffset(months=12)


WINDOWS = (
    Window("Summer 2023", pd.Timestamp("2023-07-01"), pd.Timestamp("2023-09-01"), "summer"),
    Window("January 2024", pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-03"), "january"),
    Window("Summer 2024", pd.Timestamp("2024-07-01"), pd.Timestamp("2024-09-01"), "summer"),
    Window("January 2025", pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-03"), "january"),
    Window("Summer 2025", pd.Timestamp("2025-07-01"), pd.Timestamp("2025-09-01"), "summer"),
    Window("January 2026", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-02-03"), "january"),
)


def season_in_progress(cutoff) -> int:
    """The FBref season that is underway on `cutoff`. Its totals include later games."""
    day = pd.Timestamp(cutoff)
    start_year = day.year if day.month >= 7 else day.year - 1
    return int(f"{str(start_year)[-2:]}{str(start_year + 1)[-2:]}")


def seasons_ended_before(cutoff) -> tuple[int, ...]:
    day = pd.Timestamp(cutoff)
    return tuple(season for season, end in SEASON_END.items() if end < day)


def assert_values_before_cutoff(valued: pd.DataFrame, cutoff) -> None:
    """Every fee used to train or to build team strength is dated on or before the cutoff."""
    day = pd.Timestamp(cutoff)
    dates = pd.to_datetime(valued["value_date"], errors="coerce")
    assert dates.notna().all(), "a squad value is missing its date"
    assert dates.max() <= day, f"value_date {dates.max().date()} is after cutoff {day.date()}"
    ends = pd.to_datetime(valued["season"].map(SEASON_END))
    assert ends.notna().all(), "a row uses a season with no end date"
    assert (ends < day).all(), "a training season had not ended before the cutoff"


def assert_window_cutoff(prepared: "Prepared") -> None:
    """The five leakage rules, for one window."""
    cutoff = prepared.window.cutoff
    assert_values_before_cutoff(prepared.train_valued, cutoff)
    assert_values_before_cutoff(prepared.score_valued, cutoff)
    in_progress = season_in_progress(cutoff)
    assert in_progress not in set(prepared.train_valued["season"].astype(int))
    assert prepared.feature_season != in_progress
    assert set(prepared.score_valued["season"].astype(int)) == {prepared.feature_season}
    assert prepared.feature_season == max(seasons_ended_before(cutoff))
    # Rule 2, January: the season that contains the window is never a feature.
    if prepared.window.kind == "january":
        assert in_progress not in set(prepared.score_frame["season"].astype(int))
        assert in_progress not in set(prepared.train_frame["season"].astype(int))
    # Rule 5: Spurs' later minutes are an outcome, not a column the model can see.
    matrix, _ = design_matrix(prepared.train_frame)
    banned = [
        column
        for column in matrix.columns
        if any(word in column.lower() for word in ("spurs", "tottenham", "outcome", "transfer", "fee"))
    ]
    assert banned == [], f"model features include post-signing information: {banned}"
    assert (prepared.train_frame["style_cluster"] == "unknown").all()
    assert (prepared.score_frame["style_cluster"] == "unknown").all()
    assert not prepared.train_frame["team"].eq(TOTTENHAM_TEAM).any()
    assert not prepared.score_frame["team"].eq(TOTTENHAM_TEAM).any()
    for column in ("all_teams",):
        if column in prepared.score_frame.columns:
            assert not prepared.score_frame[column].astype(str).str.contains(TOTTENHAM_TEAM).any()


@dataclass
class Prepared:
    window: Window
    feature_season: int
    train_valued: pd.DataFrame
    score_valued: pd.DataFrame
    train_frame: pd.DataFrame
    score_frame: pd.DataFrame


def prepare_window(
    window: Window,
    valued: pd.DataFrame,
    valuations: pd.DataFrame,
    values_at: dict | None = None,
) -> Prepared:
    """Stats from seasons that had ended, priced with valuations dated on or before the cutoff."""
    allowed = seasons_ended_before(window.cutoff)
    assert allowed, f"{window.name} has no completed season before {window.cutoff.date()}"
    feature_season = max(allowed)
    train_valued = _price_seasons(valued, valuations, {season: SEASON_END[season] for season in allowed}, values_at)
    score_valued = _price_seasons(valued, valuations, {feature_season: window.cutoff}, values_at)
    # A spell at Tottenham is the outcome, or a loan that already happened. Either way
    # it is not a feature. Minutes at the selling club are kept.
    train_valued = _drop_spurs_stints(train_valued)
    score_valued = _drop_spurs_stints(score_valued)
    train_frame = _modeling_frame(train_valued)
    score_frame = _modeling_frame(score_valued)
    prepared = Prepared(window, feature_season, train_valued, score_valued, train_frame, score_frame)
    assert_window_cutoff(prepared)
    return prepared


def score_window(prepared: Prepared) -> pd.DataFrame:
    """Predict every regular with a model that did not train on him.

    Holding the player out is what makes the gap mean something. A model that
    trained on his own season-end fee would just hand that fee back, and the
    summer windows are only a day after the season ends.
    """
    train = prepared.train_frame.reset_index(drop=True)
    score = prepared.score_frame.reset_index(drop=True)
    train_x, train_y = design_matrix(train)
    score_x, _ = design_matrix(score)
    score_x = score_x.reindex(columns=train_x.columns, fill_value=0.0)
    groups = train["tm_player_id"].astype(int).to_numpy()
    predicted = np.empty(len(score), dtype=float)
    fold_of_player: dict[int, int] = {}
    train_ids_by_fold: dict[int, set[int]] = {}
    folder = GroupKFold(n_splits=N_FOLDS)
    for fold, (train_index, test_index) in enumerate(folder.split(train_x, train_y, groups)):
        held_out = set(int(player_id) for player_id in groups[test_index])
        fitted_on = set(int(player_id) for player_id in groups[train_index])
        train_ids_by_fold[fold] = fitted_on
        for player_id in held_out:
            fold_of_player[player_id] = fold
        # The fold that holds a player out must not have trained on him.
        assert held_out.isdisjoint(fitted_on)
        mask = score["tm_player_id"].astype(int).isin(held_out).to_numpy()
        if not mask.any():
            continue
        predicted[mask] = _fit_predict(
            "hist_gradient_boosting",
            train_x.iloc[train_index],
            train_y.iloc[train_index],
            score_x.iloc[np.flatnonzero(mask)],
        )
    known = score["tm_player_id"].astype(int).map(fold_of_player)
    missing = known.isna().to_numpy()
    if missing.any():
        predicted[missing] = _fit_predict(
            "hist_gradient_boosting", train_x, train_y, score_x.iloc[np.flatnonzero(missing)]
        )
    for player_id, fold in known.dropna().astype(int).items():
        assert int(score.loc[player_id, "tm_player_id"]) not in train_ids_by_fold[fold]

    actual = score["market_value_eur"].to_numpy(dtype=float)
    actual_log = np.log(actual)
    output = score[
        ["player", "team", "league", "season", "age", "position_group", "tm_player_id", "market_value_eur", "value_date"]
    ].copy()
    output["model_value"] = np.exp(predicted)
    output["value_gap"] = output["model_value"] / actual
    output["log_gap"] = predicted - actual_log
    output["gap_percentile"] = output.groupby("position_group")["log_gap"].rank(method="average", pct=True) * 100
    output["value_date"] = pd.to_datetime(output["value_date"])
    assert output["value_date"].max() <= prepared.window.cutoff
    return output.reset_index(drop=True)


def classify_outcome(minutes_share, log_change, too_early: bool) -> str:
    """Hit, miss, or mixed. January 2026 has no 12-month value yet."""
    if too_early:
        return "too early"
    share_missing = pd.isna(minutes_share)
    change_missing = pd.isna(log_change)
    if share_missing and change_missing:
        return "unmeasured"
    value_up = (not change_missing) and float(log_change) > 0
    value_down = (not change_missing) and float(log_change) < VALUE_DROP
    low_minutes = (not share_missing) and float(minutes_share) < 0.25
    high_minutes = (not share_missing) and float(minutes_share) >= 0.50
    if low_minutes or value_down:
        return "miss"
    if high_minutes and value_up:
        return "hit"
    if share_missing or change_missing:
        return "unmeasured"
    return "mixed"


def run_backtest(
    valued: pd.DataFrame | None = None,
    valuations: pd.DataFrame | None = None,
    transfers: pd.DataFrame | None = None,
    players: pd.DataFrame | None = None,
    save: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score every window and write the signings and the model's alternative picks."""
    if valued is None:
        valued = pd.read_csv(VALUED_PATH)
    if valuations is None:
        valuations = pd.read_csv(VALUATIONS_PATH)
    if transfers is None:
        transfers = pd.read_csv(TRANSFERS_PATH)
    if players is None:
        players = pd.read_csv(TM_PLAYERS_PATH, usecols=["player_id", "sub_position"])
    valuations = _valuations_for(valued, valuations)
    values_at: dict = {}
    latest_valuation = pd.to_datetime(valuations["date"]).max()
    signings_frames = []
    pick_frames = []
    for window in WINDOWS:
        print(f"{window.name}: training on seasons that ended before {window.cutoff.date()}")
        prepared = prepare_window(window, valued, valuations, values_at)
        print(
            f"  feature season {prepared.feature_season}, "
            f"{len(prepared.train_frame)} training rows, {len(prepared.score_frame)} scored"
        )
        scored = score_window(prepared)
        signings = _window_signings(window, transfers, players, scored, valuations, values_at, latest_valuation)
        picks = _window_picks(window, signings, scored, valuations, values_at, latest_valuation)
        signings_frames.append(signings)
        pick_frames.append(picks)
    signings_out = pd.concat(signings_frames, ignore_index=True)
    picks_out = pd.concat(pick_frames, ignore_index=True) if any(len(frame) for frame in pick_frames) else pd.DataFrame()
    _assert_outcome_dates(signings_out)
    _assert_outcome_dates(picks_out)
    if save:
        SIGNINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        signings_out.to_csv(SIGNINGS_PATH, index=False)
        picks_out.to_csv(PICKS_PATH, index=False)
        print(f"Wrote {len(signings_out)} signings to {SIGNINGS_PATH}")
        print(f"Wrote {len(picks_out)} model picks to {PICKS_PATH}")
    return signings_out, picks_out


def _drop_spurs_stints(valued: pd.DataFrame) -> pd.DataFrame:
    return valued.loc[valued["team"] != TOTTENHAM_TEAM].copy()


def _modeling_frame(valued: pd.DataFrame) -> pd.DataFrame:
    """Same frame as the value model, with the 2025-26 style labels removed.

    Those labels were fit on the whole 2025-26 season, which none of these
    windows are allowed to know.
    """
    frame = build_modeling_frame(valued)
    frame["style_cluster"] = "unknown"
    return frame


def _price_seasons(
    valued: pd.DataFrame,
    valuations: pd.DataFrame,
    season_dates: dict[int, pd.Timestamp],
    values_at: dict | None,
) -> pd.DataFrame:
    """Replace the stored fees with value_at_date for each season's own cutoff."""
    frames = []
    base = valued.loc[valued["season"].astype(int).isin(season_dates)].copy()
    base["season"] = base["season"].astype(int)
    base["tm_player_id"] = pd.to_numeric(base["tm_player_id"], errors="coerce")
    base = base.loc[base["tm_player_id"].notna()].copy()
    base["tm_player_id"] = base["tm_player_id"].astype(int)
    for season, day in season_dates.items():
        part = base.loc[base["season"] == season].drop(columns=["market_value_eur", "value_date"], errors="ignore")
        prices = _cached_values(valuations, day, values_at).rename(columns={"player_id": "tm_player_id"})
        part = part.merge(prices, on="tm_player_id", how="left")
        part = part.loc[part["market_value_eur"].notna() & (part["market_value_eur"] > 0)]
        frames.append(part)
    priced = pd.concat(frames, ignore_index=True)
    priced["value_date"] = pd.to_datetime(priced["value_date"])
    return priced


def _cached_values(valuations: pd.DataFrame, day, values_at: dict | None) -> pd.DataFrame:
    key = pd.Timestamp(day).normalize()
    if values_at is not None and key in values_at:
        return values_at[key]
    prices = value_at_date(valuations, key)
    prices["value_date"] = pd.to_datetime(prices["value_date"])
    if values_at is not None:
        values_at[key] = prices
    return prices


def _valuations_for(valued: pd.DataFrame, valuations: pd.DataFrame) -> pd.DataFrame:
    """Keep valuations for players who appear in the FBref seasons. Same rule, less sorting."""
    ids = set(pd.to_numeric(valued["tm_player_id"], errors="coerce").dropna().astype(int))
    frame = valuations.loc[valuations["player_id"].isin(ids), ["player_id", "date", "market_value_in_eur"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame


def _window_signings(
    window: Window,
    transfers: pd.DataFrame,
    players: pd.DataFrame,
    scored: pd.DataFrame,
    valuations: pd.DataFrame,
    values_at: dict,
    latest_valuation: pd.Timestamp,
) -> pd.DataFrame:
    arrivals = transfers.loc[transfers["to_club_id"] == TOTTENHAM_CLUB_ID].copy()
    arrivals["transfer_date"] = pd.to_datetime(arrivals["transfer_date"], errors="coerce")
    arrivals = arrivals.loc[
        (arrivals["transfer_date"] >= window.cutoff) & (arrivals["transfer_date"] <= window.closes)
    ].copy()
    positions = players.rename(columns={"player_id": "tm_player_id"})
    arrivals = arrivals.rename(columns={"player_id": "tm_player_id", "player_name": "player"})
    arrivals["tm_player_id"] = arrivals["tm_player_id"].astype(int)
    arrivals = arrivals.merge(positions, on="tm_player_id", how="left")
    arrivals["position_group"] = arrivals["sub_position"].map(SUB_POSITION_GROUP)
    arrivals["is_loan"] = [
        _is_loan(row, transfers) for row in arrivals.itertuples(index=False)
    ]
    scored_ids = scored.set_index("tm_player_id")
    rows = []
    too_early = _too_early(window, latest_valuation)
    outcome_season, minutes_label = _outcome_season(window, too_early)
    for arrival in arrivals.itertuples(index=False):
        matched = scored_ids.loc[arrival.tm_player_id] if arrival.tm_player_id in scored_ids.index else None
        if isinstance(matched, pd.DataFrame):
            matched = matched.iloc[0]
        scorable = matched is not None
        reason = "" if scorable else _unscored_reason(
            arrival.position_group, int(arrival.tm_player_id), max(seasons_ended_before(window.cutoff))
        )
        value = float(matched["market_value_eur"]) if scorable else np.nan
        value_date = matched["value_date"] if scorable else pd.NaT
        model_value = float(matched["model_value"]) if scorable else np.nan
        gap = float(matched["value_gap"]) if scorable else np.nan
        log_gap = float(matched["log_gap"]) if scorable else np.nan
        percentile = float(matched["gap_percentile"]) if scorable else np.nan
        if scorable and not arrival.is_loan and pd.notna(arrival.transfer_fee) and arrival.transfer_fee > 0:
            overpaid = "yes" if float(arrival.transfer_fee) > model_value else "no"
        elif arrival.is_loan:
            overpaid = "loan"
        else:
            overpaid = ""
        minutes, share = _spurs_minutes(arrival.tm_player_id, outcome_season)
        log_change, value_12, value_12_date = _value_change(
            arrival.tm_player_id, window, valuations, values_at, too_early
        )
        rows.append(
            {
                "window": window.name,
                "cutoff": window.cutoff.date().isoformat(),
                "player": arrival.player,
                "tm_player_id": int(arrival.tm_player_id),
                "transfer_date": pd.Timestamp(arrival.transfer_date).date().isoformat(),
                "from_club": arrival.from_club_name,
                "fee_eur": arrival.transfer_fee,
                "is_loan": bool(arrival.is_loan),
                "position_group": arrival.position_group if pd.notna(arrival.position_group) else (matched["position_group"] if scorable else pd.NA),
                "scorable": scorable,
                "not_scorable_reason": reason,
                "value_at_cutoff": value,
                "value_date": pd.Timestamp(value_date).date().isoformat() if pd.notna(value_date) else pd.NA,
                "model_value": model_value,
                "value_gap": gap,
                "log_gap": log_gap,
                "gap_percentile": percentile,
                "overpaid_vs_model": overpaid,
                "outcome_season": outcome_season,
                "minutes_label": minutes_label,
                "minutes": minutes,
                "minutes_share": share,
                "value_12m": value_12,
                "value_12m_date": value_12_date,
                "log_value_change": log_change,
                "outcome": classify_outcome(share, log_change, too_early),
            }
        )
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    if table["value_date"].notna().any():
        assert pd.to_datetime(table.loc[table["value_date"].notna(), "value_date"]).max() <= window.cutoff
    return table.sort_values(["scorable", "transfer_date", "player"], ascending=[False, True, True]).reset_index(drop=True)


def _window_picks(
    window: Window,
    signings: pd.DataFrame,
    scored: pd.DataFrame,
    valuations: pd.DataFrame,
    values_at: dict,
    latest_valuation: pd.Timestamp,
) -> pd.DataFrame:
    """Top 3 undervalued players in each role Spurs actually bought."""
    if signings.empty:
        return pd.DataFrame()
    roles = [
        role
        for role in signings["position_group"].dropna().unique()
        if role in POSITION_ORDER
    ]
    too_early = _too_early(window, latest_valuation)
    signed_ids = set(signings["tm_player_id"].astype(int))
    rows = []
    changes = _changes_for(scored["tm_player_id"].astype(int), window, valuations, values_at, too_early)
    scored = scored.copy()
    scored["tm_player_id"] = scored["tm_player_id"].astype(int)
    scored = scored.merge(changes, on="tm_player_id", how="left")
    for role in roles:
        role_signings = signings.loc[signings["position_group"] == role]
        spurs_change = role_signings["log_value_change"].dropna()
        spurs_median = float(spurs_change.median()) if len(spurs_change) else np.nan
        pool = scored.loc[
            (scored["position_group"] == role)
            & (scored["age"] <= 27)
            & (scored["market_value_eur"] >= MIN_VALUE_EUR)
        ].sort_values(["log_gap", "player"], ascending=[False, True])
        position_change = scored.loc[scored["position_group"] == role, "log_value_change"].dropna()
        position_median = float(position_change.median()) if len(position_change) else np.nan
        for rank, pick in enumerate(pool.head(3).itertuples(index=False), start=1):
            rows.append(
                {
                    "window": window.name,
                    "cutoff": window.cutoff.date().isoformat(),
                    "position_group": role,
                    "rank": rank,
                    "player": pick.player,
                    "team": pick.team,
                    "age": pick.age,
                    "tm_player_id": int(pick.tm_player_id),
                    "value_at_cutoff": pick.market_value_eur,
                    "value_date": pd.Timestamp(pick.value_date).date().isoformat(),
                    "model_value": pick.model_value,
                    "value_gap": pick.value_gap,
                    "log_gap": pick.log_gap,
                    "value_12m": pick.value_12m,
                    "value_12m_date": pick.value_12m_date,
                    "log_value_change": pick.log_value_change,
                    "signed_by_spurs": int(pick.tm_player_id) in signed_ids,
                    "spurs_median_log_change": spurs_median,
                    "position_median_log_change": position_median,
                }
            )
    table = pd.DataFrame(rows)
    if not table.empty and table["value_date"].notna().any():
        assert pd.to_datetime(table["value_date"]).max() <= window.cutoff
    return table


def _changes_for(player_ids, window, valuations, values_at, too_early: bool) -> pd.DataFrame:
    rows = [
        _value_change(int(player_id), window, valuations, values_at, too_early)
        for player_id in player_ids
    ]
    return pd.DataFrame(
        {
            "tm_player_id": list(player_ids),
            "log_value_change": [row[0] for row in rows],
            "value_12m": [row[1] for row in rows],
            "value_12m_date": [row[2] for row in rows],
        }
    )


def _value_change(player_id: int, window: Window, valuations, values_at, too_early: bool):
    if too_early:
        return np.nan, np.nan, pd.NA
    at_cutoff = _cached_values(valuations, window.cutoff, values_at)
    at_later = _cached_values(valuations, window.too_early_after, values_at)
    before = at_cutoff.loc[at_cutoff["player_id"] == player_id]
    after = at_later.loc[at_later["player_id"] == player_id]
    if before.empty or after.empty:
        return np.nan, np.nan, pd.NA
    start = float(before["market_value_eur"].iloc[0])
    end = float(after["market_value_eur"].iloc[0])
    end_date = pd.Timestamp(after["value_date"].iloc[0])
    assert pd.Timestamp(before["value_date"].iloc[0]) <= window.cutoff
    assert end_date <= window.too_early_after
    if start <= 0 or end <= 0:
        return np.nan, np.nan, pd.NA
    return float(np.log(end / start)), end, end_date.date().isoformat()


def _too_early(window: Window, latest_valuation: pd.Timestamp) -> bool:
    """No 12-month reading if the file ends more than a month short of the anniversary."""
    return pd.Timestamp(latest_valuation) < window.too_early_after - pd.Timedelta(days=31)


def _outcome_season(window: Window, too_early: bool) -> tuple[int, str]:
    """First full league season after a summer move, or after a January move.

    January 2026 has not had a full season. The minutes are the season they joined.
    """
    in_progress = season_in_progress(window.cutoff)
    if too_early:
        return in_progress, "so far"
    if window.kind == "summer":
        return in_progress, "full season"
    nxt = SEASON_ORDER[SEASON_ORDER.index(in_progress) + 1]
    return nxt, "full season"


def _spurs_minutes(player_id: int, season: int) -> tuple[float, float]:
    """League minutes at Tottenham only. A loan spell elsewhere counts as zero."""
    if not hasattr(_spurs_minutes, "table"):
        valued = pd.read_csv(VALUED_PATH, usecols=["tm_player_id", "team", "season", "minutes"])
        valued = valued.loc[valued["team"] == TOTTENHAM_TEAM].copy()
        valued["tm_player_id"] = pd.to_numeric(valued["tm_player_id"], errors="coerce")
        valued["minutes"] = pd.to_numeric(valued["minutes"], errors="coerce").fillna(0.0)
        _spurs_minutes.table = valued
    rows = _spurs_minutes.table.loc[
        (_spurs_minutes.table["tm_player_id"] == player_id) & (_spurs_minutes.table["season"] == season)
    ]
    minutes = float(rows["minutes"].sum()) if len(rows) else 0.0
    return minutes, minutes / SPURS_SEASON_MINUTES


def _unscored_reason(position_group, player_id: int, feature_season: int) -> str:
    if position_group == "GK":
        return "goalkeeper: the model does not price them"
    clubs = _feature_clubs(player_id, feature_season)
    if clubs and set(clubs) == {TOTTENHAM_TEAM}:
        return "the only top-5 minutes before the window were at Tottenham, so they are not used"
    if TOTTENHAM_TEAM in clubs:
        return "Tottenham minutes were removed, and what was left was under 900"
    return "no 900-minute season in a top-5 league before the window"


def _feature_clubs(player_id: int, season: int) -> list[str]:
    if not hasattr(_feature_clubs, "table"):
        valued = pd.read_csv(VALUED_PATH, usecols=["tm_player_id", "team", "season", "minutes"])
        valued["tm_player_id"] = pd.to_numeric(valued["tm_player_id"], errors="coerce")
        valued["minutes"] = pd.to_numeric(valued["minutes"], errors="coerce").fillna(0.0)
        _feature_clubs.table = valued
    rows = _feature_clubs.table.loc[
        (_feature_clubs.table["tm_player_id"] == player_id) & (_feature_clubs.table["season"] == season)
    ]
    played = rows.loc[rows["minutes"] > 0, "team"]
    return [str(team) for team in played.dropna().unique()]


def _is_loan(arrival, transfers: pd.DataFrame) -> bool:
    fee = arrival.transfer_fee
    if pd.notna(fee) and float(fee) > 0:
        return False
    moved = transfers.loc[transfers["player_id"] == arrival.tm_player_id].copy()
    moved["transfer_date"] = pd.to_datetime(moved["transfer_date"], errors="coerce")
    arrived = pd.Timestamp(arrival.transfer_date)
    later = moved.loc[
        (moved["transfer_date"] > arrived)
        & (moved["transfer_date"] <= arrived + pd.Timedelta(days=730))
        & (moved["from_club_id"] == TOTTENHAM_CLUB_ID)
        & (moved["to_club_id"] == arrival.from_club_id)
    ]
    later_fee = pd.to_numeric(later["transfer_fee"], errors="coerce").fillna(0)
    prior = moved.loc[
        (moved["transfer_date"] < arrived)
        & (moved["transfer_date"] >= arrived - pd.Timedelta(days=400))
        & (moved["from_club_id"] == TOTTENHAM_CLUB_ID)
        & (moved["to_club_id"] == arrival.from_club_id)
    ]
    prior_fee = pd.to_numeric(prior["transfer_fee"], errors="coerce").fillna(0)
    returned = (later_fee == 0).any()
    came_back = (prior_fee == 0).any()
    return bool(returned or came_back)


def _assert_outcome_dates(table: pd.DataFrame) -> None:
    if table.empty or "value_12m_date" not in table.columns:
        return
    dated = table.loc[table["value_12m_date"].notna(), ["window", "value_12m_date", "cutoff"]]
    if dated.empty:
        return
    anniversary = pd.to_datetime(dated["cutoff"]) + pd.DateOffset(months=12)
    assert (pd.to_datetime(dated["value_12m_date"]) <= anniversary).all()


if __name__ == "__main__":
    run_backtest()
