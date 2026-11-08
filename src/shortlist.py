"""January shortlist for the two roles Spurs need.

The pool is the 2025-26 season: 900 minutes, a Transfermarkt match, and not
Tottenham. A player already on the 2026-27 Tottenham list is left out too.
Each part is a 0–100 percentile inside that need's own pool. Age and contract
dates use Transfermarkt. The contract file is the July 2026 snapshot.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.cluster import PLAYER_CLUSTERS_PATH, style_matrix
from src.features import (
    TM_PLAYERS_PATH,
    VALUED_PATH,
    add_per90,
    assign_position_group,
    combine_club_stints,
    feature_columns,
)
from src.needs import benchmark_clubs
from src.similarity import cosine_similarity_matrix, explain_match, load_vectors
from src.value_model import PREDICTIONS_PATH

SHORTLIST_PATH = VALUED_PATH.parent / "shortlist.csv"
CHECKS_PATH = VALUED_PATH.parent.parent / "manual_checks.csv"
SPURS = "Tottenham"
PRIOR_SEASON = 2526
CURRENT_SEASON = 2627
WINDOW = pd.Timestamp("2027-01-01")
CONTRACT_CUTOFF = pd.Timestamp("2027-06-30")
MIN_MINUTES = 900
FORM_MINUTES = 450
FULL_SEASON_MINUTES = 38 * 90
TOP_N = 10
PREMIER_LEAGUE = "ENG-Premier League"

NEEDS = (
    {
        "need": "ST",
        "position_group": "ST",
        "sub_position": None,
        "target_style": "Penalty-box striker",
        "label": "Penalty-box striker",
    },
    {
        "need": "FB",
        "position_group": "FB",
        "sub_position": "Left-Back",
        "target_style": "Defensive fullback",
        "label": "Left-back to follow Robertson",
    },
)
WEIGHTS = {"value": 0.40, "style": 0.30, "form": 0.20, "reliability": 0.10}
HARD_TO_BUY = "Hard to buy in January, maybe a loan."
CHEAPER = "Cheaper now, or a free transfer in the summer."
NO_ADAPTATION = "No adaptation risk."


def build_shortlist(
    valued: pd.DataFrame | None = None,
    predictions: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Score every candidate, then keep the top 10 in each need."""
    if valued is None:
        valued = pd.read_csv(VALUED_PATH)
    if predictions is None:
        predictions = pd.read_csv(PREDICTIONS_PATH)
    prior = _season_table(valued, PRIOR_SEASON)
    current = _season_table(valued, CURRENT_SEASON)
    prior = _attach_predictions(prior, predictions)
    prior = _attach_birth_dates(prior)
    prior["age_at_window"] = prior["date_of_birth"].map(_age_on_window)
    missing_day = prior["age_at_window"].isna() & prior["birth_year"].notna()
    prior.loc[missing_day, "age_at_window"] = WINDOW.year - 1 - prior.loc[missing_day, "birth_year"]
    spurs_now = set(current.loc[current["team"].eq(SPURS), "player"])
    prior = prior.loc[~prior["player"].isin(spurs_now)]
    prior = prior.loc[~prior["all_teams"].fillna(prior["team"]).astype(str).str.contains(SPURS)]
    elite = _elite_clubs(valued)
    benchmark = benchmark_clubs(valued)
    pieces = [_score_need(spec, prior, current, elite, benchmark) for spec in NEEDS]
    shortlist = pd.concat(pieces, ignore_index=True)
    return shortlist.sort_values(["need", "rank", "player"]).reset_index(drop=True)


def write_manual_checks(shortlist: pd.DataFrame, path=CHECKS_PATH) -> pd.DataFrame:
    """A blank review sheet. The three note columns are for a person to fill in."""
    sheet = shortlist.loc[:, ["need", "rank", "player", "team", "league", "age_at_window", "total_score", "flags", "value_date"]].copy()
    sheet["current_tm_value_eur"] = ""
    sheet["availability_notes"] = ""
    sheet["human_screen"] = ""
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(path, index=False)
    return sheet


def archetype_profiles(shortlist: pd.DataFrame, valued: pd.DataFrame | None = None) -> pd.DataFrame:
    """Style z-scores for the target centroid and the top three names in each need."""
    if valued is None:
        valued = pd.read_csv(VALUED_PATH)
    vectors = load_vectors()
    rows = []
    for spec in NEEDS:
        styled, features, centroid = _style_space(vectors, spec)
        names = ["Archetype"] + shortlist.loc[shortlist["need"].eq(spec["need"])].nsmallest(3, "rank")["player"].tolist()
        lookup = styled.copy()
        lookup["player"] = _style_players(vectors, spec["position_group"])["player"].to_numpy()
        for name in names:
            if name == "Archetype":
                values = centroid
            else:
                hit = lookup.loc[lookup["player"].eq(name)]
                if hit.empty:
                    continue
                values = hit.iloc[0][features]
            for feature in features:
                rows.append(
                    {
                        "need": spec["need"],
                        "who": name,
                        "feature": feature,
                        "z": float(values[feature]),
                    }
                )
    return pd.DataFrame(rows)


def explain_top_picks(shortlist: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """How each top pick differs from the nearest benchmark player in the target style."""
    vectors = load_vectors()
    clusters = pd.read_csv(PLAYER_CLUSTERS_PATH)
    benchmark = benchmark_clubs()
    rows = []
    for spec in NEEDS:
        picks = shortlist.loc[shortlist["need"].eq(spec["need"])].nsmallest(n, "rank")
        styled, features, _centroid = _style_space(vectors, spec)
        players = _style_players(vectors, spec["position_group"]).reset_index(drop=True)
        styled = styled.reset_index(drop=True)
        styled["player"] = players["player"].to_numpy()
        styled["team"] = players["team"].to_numpy()
        peers = clusters.loc[
            clusters["position_group"].eq(spec["position_group"])
            & clusters["cluster_name"].eq(spec["target_style"])
            & clusters["team"].isin(benchmark)
        ]
        peer_vectors = styled.loc[styled["player"].isin(peers["player"])]
        for pick in picks.itertuples(index=False):
            candidate = styled.loc[styled["player"].eq(pick.player)]
            others = peer_vectors.loc[~peer_vectors["player"].eq(pick.player)]
            if candidate.empty or others.empty:
                rows.append(
                    {
                        "need": spec["need"],
                        "player": pick.player,
                        "peer": "",
                        "peer_team": "",
                        "note": "No benchmark-club player in this style to compare.",
                    }
                )
                continue
            scores = cosine_similarity_matrix(
                np.vstack([candidate.iloc[0][features].to_numpy(dtype=float), others[features].to_numpy(dtype=float)])
            )[0, 1:]
            peer = others.iloc[int(np.nanargmax(scores))]
            detail = explain_match(pick.player, peer["player"], season="2526", vectors=vectors)
            for item in detail.itertuples(index=False):
                rows.append(
                    {
                        "need": spec["need"],
                        "player": pick.player,
                        "peer": peer["player"],
                        "peer_team": peer["team"],
                        "kind": item.kind,
                        "feature": item.feature,
                        "z_candidate": item.z_a,
                        "z_peer": item.z_b,
                        "note": "",
                    }
                )
    return pd.DataFrame(rows)


def _score_need(spec: dict, prior: pd.DataFrame, current: pd.DataFrame, elite: set[str], benchmark: list[str]) -> pd.DataFrame:
    pool = prior.loc[prior["minutes"].ge(MIN_MINUTES) & prior["tm_player_id"].notna() & prior["calibrated_gap"].notna()].copy()
    pool = pool.loc[pool["age_at_window"].le(27)]
    pool = pool.loc[pool["position_group"].eq(spec["position_group"])]
    if spec["sub_position"]:
        pool = pool.loc[pool["sub_position"].eq(spec["sub_position"])]
    if pool.empty:
        return pd.DataFrame()
    vectors = load_vectors()
    styled, features, centroid = _style_space(vectors, spec)
    style_players = _style_players(vectors, spec["position_group"]).reset_index(drop=True)
    styled = styled.reset_index(drop=True)
    styled["player"] = style_players["player"].to_numpy()
    styled["birth_year"] = style_players["birth_year"].to_numpy()
    style_named = styled.loc[:, ["player", "birth_year", *features]].rename(
        columns={name: f"style_{name}" for name in features}
    )
    pool = pool.merge(style_named, on=["player", "birth_year"], how="left")
    pool["style_similarity"] = _cosine_to_centroid(pool[[f"style_{name}" for name in features]], centroid)
    rate_names = [name for name in feature_columns(current) if name in pool.columns and name in current.columns]
    this_season = current.loc[:, ["player", "birth_year", "minutes", "team", "league", *rate_names]].rename(
        columns={"minutes": "minutes_this_season", "team": "club_now", "league": "league_now", **{name: f"now_{name}" for name in rate_names}}
    )
    pool = pool.merge(this_season, on=["player", "birth_year"], how="left")
    pool["minutes_this_season"] = pool["minutes_this_season"].fillna(0.0)
    pool["club_now"] = pool["club_now"].fillna(pool["team"])
    pool["league_now"] = pool["league_now"].fillna(pool["league"])
    last_year = pool[rate_names].to_numpy(dtype=float)
    this_year = pool[[f"now_{name}" for name in rate_names]].to_numpy(dtype=float)
    played = pool["minutes_this_season"].to_numpy(dtype=float)
    pool["form_similarity"] = [
        _cosine(left, right) if minutes >= FORM_MINUTES else np.nan
        for left, right, minutes in zip(last_year, this_year, played)
    ]
    pool["reliability"] = pool["squad_minutes_pct"] / 100.0
    missing_share = pool["reliability"].isna()
    pool.loc[missing_share, "reliability"] = (pool.loc[missing_share, "minutes"] / FULL_SEASON_MINUTES).clip(upper=1)
    pool["value_percentile"] = _percentile(pool["calibrated_gap"])
    pool["style_percentile"] = _percentile(pool["style_similarity"])
    pool["form_percentile"] = _percentile(pool["form_similarity"])
    pool.loc[pool["form_similarity"].isna(), "form_percentile"] = 50.0
    pool["reliability_percentile"] = _percentile(pool["reliability"])
    pool["total_score"] = (
        WEIGHTS["value"] * pool["value_percentile"]
        + WEIGHTS["style"] * pool["style_percentile"]
        + WEIGHTS["form"] * pool["form_percentile"]
        + WEIGHTS["reliability"] * pool["reliability_percentile"]
    )
    pool["flags"] = [
        _flags(row.club_now, row.league_now, row.contract_expiration_date, elite)
        for row in pool.itertuples(index=False)
    ]
    pool["need"] = spec["need"]
    pool["target_style"] = spec["target_style"]
    pool["benchmark_clubs"] = ", ".join(benchmark)
    pool["elite_clubs"] = ", ".join(sorted(elite))
    pool = pool.sort_values(["total_score", "player"], ascending=[False, True]).head(TOP_N).copy()
    pool["rank"] = np.arange(1, len(pool) + 1)
    keep = [
        "need",
        "rank",
        "player",
        "team",
        "league",
        "club_now",
        "age_at_window",
        "sub_position",
        "minutes",
        "minutes_this_season",
        "calibrated_gap",
        "value_percentile",
        "style_similarity",
        "style_percentile",
        "form_similarity",
        "form_percentile",
        "reliability",
        "reliability_percentile",
        "total_score",
        "flags",
        "value_date",
        "target_style",
        "predicted_value",
        "actual_value",
    ]
    return pool.loc[:, keep]


def _season_table(valued: pd.DataFrame, season: int) -> pd.DataFrame:
    frame = valued.loc[valued["season"].eq(season)].copy()
    frame = assign_position_group(frame)
    frame = add_per90(combine_club_stints(frame))
    frame["minutes"] = pd.to_numeric(frame["minutes"], errors="coerce").fillna(0.0)
    frame["birth_year"] = pd.to_numeric(frame["birth_year"], errors="coerce")
    frame["squad_minutes_pct"] = pd.to_numeric(frame["squad_minutes_pct"], errors="coerce")
    frame["tm_player_id"] = pd.to_numeric(frame["tm_player_id"], errors="coerce")
    return frame


def _attach_predictions(prior: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    scored = predictions.loc[predictions["season"].map(_season_code).eq(PRIOR_SEASON)].copy()
    scored = scored.groupby("player", as_index=False).agg(
        calibrated_gap=("calibrated_gap", "mean"),
        predicted_value=("predicted_value", "mean"),
        actual_value=("actual_value", "mean"),
    )
    return prior.merge(scored, on="player", how="left")


def _attach_birth_dates(prior: pd.DataFrame) -> pd.DataFrame:
    people = pd.read_csv(TM_PLAYERS_PATH, usecols=["player_id", "date_of_birth", "contract_expiration_date"])
    people["player_id"] = pd.to_numeric(people["player_id"], errors="coerce")
    people["date_of_birth"] = pd.to_datetime(people["date_of_birth"], errors="coerce")
    people["contract_expiration_date"] = pd.to_datetime(people["contract_expiration_date"], errors="coerce")
    frame = prior.merge(people, left_on="tm_player_id", right_on="player_id", how="left")
    return frame.drop(columns=["player_id"])


def _style_space(vectors: pd.DataFrame, spec: dict) -> tuple[pd.DataFrame, list[str], pd.Series]:
    """Action z-scores on the same scale the clusters used, plus the target centroid."""
    group = vectors.loc[
        (vectors["season"].eq(PRIOR_SEASON)) & (vectors["position_group"].eq(spec["position_group"]))
    ].reset_index(drop=True)
    styled, features = style_matrix(group, spec["position_group"])
    clusters = pd.read_csv(PLAYER_CLUSTERS_PATH)
    members = set(
        clusters.loc[
            clusters["position_group"].eq(spec["position_group"]) & clusters["cluster_name"].eq(spec["target_style"]),
            "player",
        ]
    )
    mask = group["player"].isin(members).to_numpy()
    centroid = styled.loc[mask, features].mean()
    return styled, features, centroid


def _style_players(vectors: pd.DataFrame, position_group: str) -> pd.DataFrame:
    return vectors.loc[
        (vectors["season"].eq(PRIOR_SEASON)) & (vectors["position_group"].eq(position_group))
    ].reset_index(drop=True)


def _elite_clubs(valued: pd.DataFrame) -> set[str]:
    """The six richest Premier League squads, plus the top two squads in every league."""
    clubs = set(benchmark_clubs(valued))
    frame = valued.loc[valued["season"].eq(PRIOR_SEASON)].copy()
    frame["tm_player_id"] = pd.to_numeric(frame["tm_player_id"], errors="coerce")
    frame["market_value_eur"] = pd.to_numeric(frame["market_value_eur"], errors="coerce")
    frame = frame.loc[frame["tm_player_id"].notna() & frame["market_value_eur"].gt(0)]
    frame = frame.groupby(["league", "team", "tm_player_id"], as_index=False)["market_value_eur"].first()
    totals = frame.groupby(["league", "team"])["market_value_eur"].sum().reset_index()
    for _league, group in totals.groupby("league"):
        clubs.update(group.nlargest(2, "market_value_eur")["team"])
    clubs.discard(SPURS)
    return clubs


def _flags(club: str, league: str, contract_end, elite: set[str]) -> str:
    notes = []
    if club in elite:
        notes.append(HARD_TO_BUY)
    if pd.notna(contract_end) and pd.Timestamp(contract_end) <= CONTRACT_CUTOFF:
        notes.append(CHEAPER)
    if league == PREMIER_LEAGUE:
        notes.append(NO_ADAPTATION)
    return " ".join(notes)


def _cosine_to_centroid(frame: pd.DataFrame, centroid: pd.Series) -> pd.Series:
    usable = frame.dropna()
    scores = pd.Series(np.nan, index=frame.index, dtype=float)
    if usable.empty:
        return scores
    block = np.vstack([centroid.to_numpy(dtype=float), usable.to_numpy(dtype=float)])
    scores.loc[usable.index] = cosine_similarity_matrix(block)[0, 1:]
    return scores


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        return np.nan
    left_norm = np.linalg.norm(left)
    right_norm = np.linalg.norm(right)
    if left_norm == 0 or right_norm == 0:
        return np.nan
    return float(np.dot(left, right) / (left_norm * right_norm))


def _percentile(series: pd.Series) -> pd.Series:
    return series.rank(method="average", pct=True) * 100.0


def _age_on_window(dob) -> float:
    if pd.isna(dob):
        return np.nan
    birthday_still_ahead = (WINDOW.month, WINDOW.day) < (dob.month, dob.day)
    return float(WINDOW.year - dob.year - int(birthday_still_ahead))


def _season_code(value) -> int:
    text = str(value).strip()
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start[-2:] + end[-2:])
    return int(float(text))


if __name__ == "__main__":
    shortlist = build_shortlist()
    SHORTLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    shortlist.to_csv(SHORTLIST_PATH, index=False)
    write_manual_checks(shortlist)
    show = [
        "need",
        "rank",
        "player",
        "team",
        "age_at_window",
        "total_score",
        "value_percentile",
        "style_percentile",
        "form_percentile",
        "reliability_percentile",
        "flags",
        "value_date",
    ]
    print(shortlist[show].round(1).to_string(index=False))
    print(f"Wrote {len(shortlist)} rows to {SHORTLIST_PATH}")
    print(f"Wrote the review sheet to {CHECKS_PATH}")
