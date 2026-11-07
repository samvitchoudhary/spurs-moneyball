"""Map each FBref player to at most one Transfermarkt player, then attach values.

A wrong match is dropped. An ambiguous tier stays unmatched.
"""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from src.clean_transfermarkt import normalize_name

ROOT = Path(__file__).resolve().parents[1]
PLAYER_SEASON_PATH = ROOT / "data" / "processed" / "player_season.csv"
TM_PLAYERS_PATH = ROOT / "data" / "processed" / "tm_players.csv"
TM_VALUES_PATH = ROOT / "data" / "processed" / "tm_season_values.csv"
TM_CLUBS_PATH = ROOT / "data" / "raw" / "transfermarkt" / "clubs.csv"
TM_TRANSFERS_PATH = ROOT / "data" / "raw" / "transfermarkt" / "transfers.csv"
OVERRIDES_PATH = ROOT / "data" / "manual_overrides.csv"
MAP_PATH = ROOT / "data" / "processed" / "player_id_map.csv"
CLUB_MAP_PATH = ROOT / "data" / "processed" / "club_name_map.csv"
VALUED_PATH = ROOT / "data" / "processed" / "player_season_valued.csv"
UNMATCHED_PATH = ROOT / "reports" / "unmatched_players.csv"

SEASON_LABEL = {
    2223: "2022-23",
    2324: "2023-24",
    2425: "2024-25",
    2526: "2025-26",
    2627: "2026-27",
}
PRESEASON_SEASONS = {2627}
TIER_RANK = {"override": 4, "tier1": 3, "tier2": 2, "tier3": 1}
# Club tokens that are not the place name. "real" and "athletic" stay.
CLUB_FILLER = {
    "fc", "cf", "ac", "afc", "sc", "bc", "ud", "cd", "ca", "us", "ssc", "acf",
    "aj", "as", "uc", "vfl", "vfb", "tsg", "sv", "hsc", "cfc", "rc", "rcd",
    "ogc", "sco", "estac", "losc", "ssv", "fsv", "spvgg", "club",
}


def _birth_year(value) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return None
    return int(value)


def _tokens(name: str | None) -> set[str]:
    if not name:
        return set()
    return set(name.split())


def load_overrides(path: Path = OVERRIDES_PATH) -> pd.DataFrame:
    """Read hand fixes. Missing file is treated as an empty list."""
    columns = ["fbref_player", "birth_year", "tm_player_id"]
    if not path.exists():
        return pd.DataFrame(columns=columns)
    overrides = pd.read_csv(path)
    for column in columns:
        if column not in overrides.columns:
            raise ValueError(f"{path} must have columns {columns}")
    overrides = overrides.loc[:, columns].dropna(how="all")
    if overrides.empty:
        return pd.DataFrame(columns=columns)
    overrides["birth_year"] = overrides["birth_year"].map(_birth_year)
    overrides["tm_player_id"] = pd.to_numeric(overrides["tm_player_id"], errors="coerce").astype("Int64")
    return overrides


def _club_tokens(name: str) -> list[str]:
    normalized = normalize_name(name) or ""
    normalized = normalized.replace("&", " ").replace(".", " ")
    return [token for token in normalized.split() if token not in CLUB_FILLER and not token.isdigit()]


def build_club_name_map(fbref_teams: list[str], tm_club_names: list[str]) -> pd.DataFrame:
    """Map each FBref team to one Transfermarkt club, or to nothing if it is unclear.

    A team is mapped only when one candidate is clearly ahead of the rest.
    """
    clubs = sorted({name for name in tm_club_names if isinstance(name, str) and name.strip()})
    prepared = [(club, normalize_name(club) or "", _club_tokens(club)) for club in clubs]
    rows = []
    for team in sorted(set(fbref_teams)):
        query_norm = (normalize_name(team) or "").replace("&", " ").replace(".", " ")
        query_tokens = _club_tokens(team)
        scored = []
        for club, club_norm, club_tokens in prepared:
            ratio = fuzz.token_sort_ratio(query_norm, club_norm.replace("&", " ").replace(".", " "))
            tokens_fit = bool(query_tokens) and set(query_tokens) <= set(club_tokens)
            if tokens_fit or ratio >= 90:
                scored.append((ratio, club))
        scored.sort(key=lambda item: (-item[0], item[1]))
        chosen = ""
        status = "unmatched"
        score = None
        alternatives = ""
        if scored:
            best_score, best_club = scored[0]
            near = [club for ratio, club in scored if best_score - ratio < 5]
            alternatives = "; ".join(club for _, club in scored[:3])
            exact = [club for club, _, tokens in prepared if tokens == query_tokens and set(query_tokens) <= set(tokens)]
            exact = [club for club in exact if any(club == candidate for _, candidate in scored)]
            if len(exact) == 1 and exact[0] in near:
                chosen, score, status = exact[0], best_score, "matched"
            elif len(near) == 1 and (best_score >= 68 or set(query_tokens) == _club_tokens(best_club)):
                chosen, score, status = best_club, best_score, "matched"
            else:
                status = "ambiguous"
                score = best_score
        rows.append(
            {
                "fbref_team": team,
                "tm_club_name": chosen,
                "score": score,
                "status": status,
                "alternatives": alternatives,
            }
        )
    return pd.DataFrame(rows)


def _identities(player_season: pd.DataFrame) -> pd.DataFrame:
    """One row per FBref name and birth year, with the clubs and minutes attached."""
    frame = player_season.loc[:, ["player", "birth_year", "team", "minutes"]].copy()
    frame["birth_year"] = frame["birth_year"].map(_birth_year).astype("Int64")
    frame["name_normalized"] = frame["player"].map(normalize_name)
    grouped = (
        frame.groupby(["player", "birth_year"], dropna=False)
        .agg(
            name_normalized=("name_normalized", "first"),
            teams=("team", lambda series: tuple(sorted(set(series.dropna())))),
            minutes=("minutes", lambda series: float(pd.to_numeric(series, errors="coerce").sum(min_count=1) or 0)),
        )
        .reset_index()
    )
    return grouped


def _apply_overrides(identities: pd.DataFrame, overrides: pd.DataFrame, valid_ids: set[int]) -> pd.DataFrame:
    mapped = identities.copy()
    mapped["tm_player_id"] = pd.Series(pd.NA, index=mapped.index, dtype="Int64")
    mapped["match_method"] = pd.NA
    mapped["score"] = pd.NA
    if overrides.empty:
        return mapped
    overrides = overrides.copy()
    overrides["player_key"] = overrides["fbref_player"].map(normalize_name)
    for index, row in mapped.iterrows():
        birth = _birth_year(row["birth_year"])
        hits = overrides.loc[
            (overrides["player_key"] == row["name_normalized"]) & (overrides["birth_year"] == birth)
        ]
        if hits.empty:
            continue
        ids = [int(player_id) for player_id in hits["tm_player_id"].dropna().unique()]
        ids = [player_id for player_id in ids if player_id in valid_ids]
        if len(ids) == 1:
            mapped.at[index, "tm_player_id"] = ids[0]
            mapped.at[index, "match_method"] = "override"
            mapped.at[index, "score"] = 100.0
        elif len(hits):
            mapped.at[index, "match_method"] = "ambiguous"
    return mapped


def _still_open(mapped: pd.DataFrame) -> pd.Index:
    return mapped.index[mapped["tm_player_id"].isna() & mapped["match_method"].isna()]


def _matched_club_lookup(club_map: pd.DataFrame) -> dict[str, str]:
    """FBref team name -> Transfermarkt club name."""
    return {
        row.fbref_team: row.tm_club_name
        for row in club_map.itertuples(index=False)
        if row.status == "matched" and row.tm_club_name
    }


def load_transfer_clubs(path: Path = TM_TRANSFERS_PATH) -> dict[int, set[str]]:
    """Every club a Transfermarkt player has been associated with in transfers.csv."""
    if not path.exists():
        return {}
    transfers = pd.read_csv(path, usecols=["player_id", "from_club_name", "to_club_name"])
    clubs: dict[int, set[str]] = {}
    for row in transfers.itertuples(index=False):
        player_id = int(row.player_id)
        bucket = clubs.setdefault(player_id, set())
        if isinstance(row.from_club_name, str) and row.from_club_name.strip():
            bucket.add(row.from_club_name.strip())
        if isinstance(row.to_club_name, str) and row.to_club_name.strip():
            bucket.add(row.to_club_name.strip())
    return clubs


def _tm_club_set(
    player_id: int,
    current_club: object,
    transfer_clubs: dict[int, set[str]],
) -> set[str]:
    """Current club plus every club name seen in that player's transfer history."""
    clubs = set(transfer_clubs.get(player_id, set()))
    if isinstance(current_club, str) and current_club.strip():
        clubs.add(current_club.strip())
    return clubs


def _tier2_club_agrees(
    fbref_teams: tuple,
    tm_player_id: int,
    current_club: object,
    club_lookup: dict[str, str],
    transfer_clubs: dict[int, set[str]],
) -> bool:
    """True when a mapped FBref club appears on the TM player's current club or transfers."""
    allowed = {club_lookup[team] for team in fbref_teams if team in club_lookup} - {None, ""}
    if not allowed:
        return False
    history = _tm_club_set(tm_player_id, current_club, transfer_clubs)
    return bool(allowed & history)


def _tier1(mapped: pd.DataFrame, tm_players: pd.DataFrame) -> None:
    """Exact normalized name and the same birth year. One-word names wait for tier 3."""
    grouped: dict[tuple[str, int], list[int]] = {}
    for player_id, name, birth in tm_players.loc[:, ["player_id", "name_normalized", "birth_year"]].itertuples(index=False):
        if not name or _birth_year(birth) is None:
            continue
        grouped.setdefault((name, _birth_year(birth)), []).append(int(player_id))

    for index, row in mapped.loc[_still_open(mapped)].iterrows():
        name = row["name_normalized"]
        birth = _birth_year(row["birth_year"])
        if not name or birth is None or len(_tokens(name)) < 2:
            continue
        hits = list(dict.fromkeys(grouped.get((name, birth), [])))
        if len(hits) == 1:
            mapped.at[index, "tm_player_id"] = hits[0]
            mapped.at[index, "match_method"] = "tier1"
            mapped.at[index, "score"] = 100.0
        elif len(hits) > 1:
            mapped.at[index, "match_method"] = "ambiguous"


def _tier2(
    mapped: pd.DataFrame,
    tm_players: pd.DataFrame,
    club_map: pd.DataFrame,
    transfer_clubs: dict[int, set[str]],
) -> None:
    """Fuzzy name, birth year within one year. A one-year gap also needs club agreement."""
    club_lookup = _matched_club_lookup(club_map)
    by_year: dict[int, pd.DataFrame] = {}
    usable = tm_players.loc[tm_players["name_normalized"].notna() & tm_players["birth_year"].notna()]
    for year, group in usable.groupby(usable["birth_year"].map(_birth_year)):
        by_year[int(year)] = group

    queries_by_year: dict[int, list[tuple]] = {}
    for index in _still_open(mapped):
        row = mapped.loc[index]
        name = row["name_normalized"]
        birth = _birth_year(row["birth_year"])
        if not name or birth is None or len(_tokens(name)) < 2:
            continue
        queries_by_year.setdefault(birth, []).append((index, name))

    for birth, queries in queries_by_year.items():
        pieces = [by_year[year] for year in (birth - 1, birth, birth + 1) if year in by_year]
        if not pieces:
            continue
        choices = pd.concat(pieces, ignore_index=True)
        names = choices["name_normalized"].tolist()
        scores = process.cdist(
            [name for _, name in queries],
            names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=90,
            workers=1,
        )
        for row_number, (index, name) in enumerate(queries):
            identity = mapped.loc[index]
            passing = [column for column, score in enumerate(scores[row_number]) if score >= 90]
            accepted = []
            for column in passing:
                candidate = choices.iloc[column]
                candidate_birth = _birth_year(candidate.birth_year)
                if candidate_birth == birth:
                    accepted.append(column)
                elif candidate_birth is not None and abs(candidate_birth - birth) == 1:
                    if _tier2_club_agrees(
                        identity["teams"],
                        int(candidate.player_id),
                        candidate.current_club_name,
                        club_lookup,
                        transfer_clubs,
                    ):
                        accepted.append(column)
            ids = list(dict.fromkeys(int(choices.iloc[column]["player_id"]) for column in accepted))
            if len(ids) == 1:
                column = max(accepted, key=lambda item: scores[row_number][item])
                mapped.at[index, "tm_player_id"] = ids[0]
                mapped.at[index, "match_method"] = "tier2"
                mapped.at[index, "score"] = float(scores[row_number][column])
            elif len(ids) > 1:
                mapped.at[index, "match_method"] = "ambiguous"


def _tier3(mapped: pd.DataFrame, tm_players: pd.DataFrame, club_map: pd.DataFrame) -> None:
    """Partial or one-word names. Same birth year, contained tokens, and the same club."""
    club_of = {
        row.fbref_team: row.tm_club_name
        for row in club_map.itertuples(index=False)
        if row.status == "matched" and row.tm_club_name
    }
    by_year: dict[int, pd.DataFrame] = {}
    usable = tm_players.loc[tm_players["name_normalized"].notna() & tm_players["birth_year"].notna()]
    for year, group in usable.groupby(usable["birth_year"].map(_birth_year)):
        by_year[int(year)] = group

    for index in _still_open(mapped):
        row = mapped.loc[index]
        name = row["name_normalized"]
        birth = _birth_year(row["birth_year"])
        if not name or birth is None or birth not in by_year:
            continue
        query_tokens = _tokens(name)
        if not query_tokens:
            continue
        allowed_clubs = {club_of.get(team) for team in row["teams"]} - {None, ""}
        if not allowed_clubs:
            continue
        hits = []
        for candidate in by_year[birth].itertuples(index=False):
            candidate_tokens = _tokens(candidate.name_normalized)
            if not query_tokens <= candidate_tokens:
                continue
            if fuzz.token_set_ratio(name, candidate.name_normalized) < 100:
                continue
            if candidate.current_club_name not in allowed_clubs:
                continue
            hits.append(candidate)
        ids = list(dict.fromkeys(int(candidate.player_id) for candidate in hits))
        if len(ids) == 1:
            score = fuzz.token_sort_ratio(name, hits[0].name_normalized)
            mapped.at[index, "tm_player_id"] = ids[0]
            mapped.at[index, "match_method"] = "tier3"
            mapped.at[index, "score"] = float(score)
        elif len(ids) > 1:
            mapped.at[index, "match_method"] = "ambiguous"


def _resolve_conflicts(mapped: pd.DataFrame) -> pd.DataFrame:
    """Two FBref players cannot keep the same Transfermarkt id. The weaker tier loses."""
    result = mapped.copy()
    claimed = result.loc[result["tm_player_id"].notna()]
    for player_id, group in claimed.groupby("tm_player_id"):
        if len(group) < 2:
            continue
        ranks = group["match_method"].map(TIER_RANK).fillna(0)
        best = ranks.max()
        winners = group.loc[ranks == best]
        print(
            f"conflict on tm_player_id {int(player_id)}: "
            + ", ".join(f"{row.player} ({row.match_method})" for row in group.itertuples())
        )
        if len(winners) > 1:
            result.loc[group.index, "tm_player_id"] = pd.NA
            result.loc[group.index, "score"] = pd.NA
            result.loc[group.index, "match_method"] = "conflict"
        else:
            losers = group.index.difference(winners.index)
            result.loc[losers, "tm_player_id"] = pd.NA
            result.loc[losers, "score"] = pd.NA
            result.loc[losers, "match_method"] = "conflict"
    return result


def build_player_id_map(
    player_season: pd.DataFrame,
    tm_players: pd.DataFrame,
    club_map: pd.DataFrame,
    overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Map each FBref name and birth year to at most one Transfermarkt player."""
    identities = _identities(player_season)
    valid_ids = set(int(player_id) for player_id in tm_players["player_id"].dropna())
    mapped = _apply_overrides(identities, overrides if overrides is not None else load_overrides(), valid_ids)
    transfer_clubs = load_transfer_clubs()
    _tier1(mapped, tm_players)
    _tier2(mapped, tm_players, club_map, transfer_clubs)
    _tier3(mapped, tm_players, club_map)
    mapped = _resolve_conflicts(mapped)
    columns = ["player", "birth_year", "tm_player_id", "match_method", "score"]
    return mapped.loc[:, columns].sort_values(["player", "birth_year"], na_position="last").reset_index(drop=True)


def _latest_values(season_values: pd.DataFrame) -> pd.DataFrame:
    values = season_values.copy()
    values["value_date"] = pd.to_datetime(values["value_date"], errors="coerce")
    values = values.sort_values(["player_id", "value_date"], kind="mergesort")
    latest = values.groupby("player_id", as_index=False).tail(1)
    return latest.loc[:, ["player_id", "market_value_eur", "value_date"]]


def attach_market_values(
    player_season: pd.DataFrame,
    player_map: pd.DataFrame,
    season_values: pd.DataFrame,
) -> pd.DataFrame:
    """Add the season-end value. 2026-27 uses the latest value and is marked preseason."""
    frame = player_season.copy()
    frame["birth_year"] = frame["birth_year"].map(_birth_year).astype("Int64")
    id_map = player_map.loc[:, ["player", "birth_year", "tm_player_id", "match_method"]].copy()
    id_map["birth_year"] = id_map["birth_year"].astype("Int64")
    frame = frame.merge(id_map, on=["player", "birth_year"], how="left")
    frame["season_label"] = frame["season"].map(lambda code: SEASON_LABEL.get(int(code), None))
    frame["value_is_preseason"] = frame["season"].map(lambda code: int(code) in PRESEASON_SEASONS)

    values = season_values.copy()
    values["player_id"] = values["player_id"].astype("Int64")
    values = values.rename(columns={"player_id": "tm_player_id"})
    seasonal = values.loc[:, ["tm_player_id", "season", "market_value_eur", "value_date"]]
    seasonal = seasonal.rename(columns={"season": "season_label"})
    ended = frame.loc[~frame["value_is_preseason"]].merge(
        seasonal, on=["tm_player_id", "season_label"], how="left"
    )
    latest = _latest_values(season_values).rename(columns={"player_id": "tm_player_id"})
    latest["tm_player_id"] = latest["tm_player_id"].astype("Int64")
    preseason = frame.loc[frame["value_is_preseason"]].drop(columns=[], errors="ignore").merge(
        latest, on="tm_player_id", how="left"
    )
    combined = pd.concat([ended, preseason], ignore_index=True)
    combined["value_date"] = pd.to_datetime(combined["value_date"], errors="coerce").dt.date
    combined = combined.drop(columns=["season_label"])
    front = list(player_season.columns) + [
        "tm_player_id",
        "market_value_eur",
        "value_date",
        "value_is_preseason",
        "match_method",
    ]
    return combined.loc[:, front].sort_values(["league", "season", "team", "player"]).reset_index(drop=True)


def _candidate_table(identities: pd.DataFrame, tm_players: pd.DataFrame) -> pd.DataFrame:
    """Top three fuzzy Transfermarkt names for players we did not match."""
    by_year: dict[int, pd.DataFrame] = {}
    usable = tm_players.loc[tm_players["name_normalized"].notna() & tm_players["birth_year"].notna()]
    for year, group in usable.groupby(usable["birth_year"].map(_birth_year)):
        by_year[int(year)] = group.reset_index(drop=True)

    rows = []
    for identity in identities.itertuples(index=False):
        birth = _birth_year(identity.birth_year)
        pieces = []
        if birth is not None:
            pieces = [by_year[year] for year in (birth - 1, birth, birth + 1) if year in by_year]
        record = {
            "player": identity.player,
            "birth_year": birth,
            "minutes": identity.minutes,
            "teams": ", ".join(identity.teams),
            "match_method": identity.match_method,
        }
        if pieces and identity.name_normalized:
            choices = pd.concat(pieces, ignore_index=True)
            found = process.extract(
                identity.name_normalized,
                choices["name_normalized"].tolist(),
                scorer=fuzz.token_sort_ratio,
                limit=3,
            )
            for rank, (matched_name, score, position) in enumerate(found, start=1):
                candidate = choices.iloc[position]
                record[f"candidate_{rank}_name"] = candidate["name"]
                record[f"candidate_{rank}_id"] = int(candidate["player_id"])
                record[f"candidate_{rank}_score"] = round(float(score), 1)
                record[f"candidate_{rank}_birth_year"] = _birth_year(candidate["birth_year"])
                record[f"candidate_{rank}_club"] = candidate["current_club_name"]
        rows.append(record)
    return pd.DataFrame(rows)


def unmatched_report(
    player_season: pd.DataFrame,
    player_map: pd.DataFrame,
    tm_players: pd.DataFrame,
    minimum_minutes: float = 900,
) -> pd.DataFrame:
    """Unmatched FBref players with enough minutes, plus three nearest names."""
    identities = _identities(player_season)
    status = player_map.loc[:, ["player", "birth_year", "tm_player_id", "match_method"]]
    status["birth_year"] = status["birth_year"].astype("Int64")
    identities = identities.merge(status, on=["player", "birth_year"], how="left")
    missed = identities.loc[identities["tm_player_id"].isna() & (identities["minutes"] >= minimum_minutes)]
    missed = missed.sort_values("minutes", ascending=False)
    report = _candidate_table(missed, tm_players)
    return report.sort_values("minutes", ascending=False).reset_index(drop=True)


def _rate(frame: pd.DataFrame) -> float:
    if frame.empty:
        return 0.0
    return float(frame["tm_player_id"].notna().mean())


def summarize(valued: pd.DataFrame, player_map: pd.DataFrame, tm_players: pd.DataFrame) -> None:
    """Print match rates and a sample of the fuzzy tiers."""
    print(f"identities: {len(player_map):,}")
    print(f"match rate, all rows: {_rate(valued):.1%}")
    regulars = valued.loc[valued["minutes"] >= 900]
    print(f"match rate, >=900 minutes: {_rate(regulars):.1%} ({len(regulars):,} rows)")
    print("by league, all rows:")
    for league, group in valued.groupby("league"):
        print(f"  {league}: {_rate(group):.1%}")
    print("by league, >=900 minutes:")
    for league, group in regulars.groupby("league"):
        print(f"  {league}: {_rate(group):.1%}")
    print("match_method counts (identities):")
    print(player_map["match_method"].fillna("(unmatched)").value_counts(dropna=False).to_string())

    names = tm_players.loc[:, ["player_id", "name", "birth_year", "current_club_name"]].rename(
        columns={"birth_year": "tm_birth_year", "name": "tm_name"}
    )
    sample_pool = player_map.loc[player_map["match_method"].isin(["tier2", "tier3"])].merge(
        names, left_on="tm_player_id", right_on="player_id", how="left"
    )
    teams = (
        valued.groupby(["player", "birth_year"], dropna=False)["team"]
        .agg(lambda series: ", ".join(sorted(set(series.dropna()))))
        .rename("fbref_teams")
        .reset_index()
    )
    teams["birth_year"] = teams["birth_year"].astype("Int64")
    sample_pool["birth_year"] = sample_pool["birth_year"].astype("Int64")
    sample_pool = sample_pool.merge(teams, on=["player", "birth_year"], how="left")
    for method in ("tier2", "tier3"):
        pool = sample_pool.loc[sample_pool["match_method"] == method]
        print(f"\n{method} spot check ({len(pool)} identities):")
        if pool.empty:
            continue
        picked = pool.sample(n=min(15, len(pool)), random_state=7)
        show = picked.loc[
            :,
            ["player", "tm_name", "birth_year", "tm_birth_year", "fbref_teams", "current_club_name", "score"],
        ]
        show = show.rename(
            columns={
                "player": "fbref",
                "tm_name": "tm",
                "birth_year": "fbref_birth",
                "current_club_name": "tm_club",
            }
        )
        print(show.to_string(index=False))


def build_all() -> dict[str, pd.DataFrame]:
    """Run the mapping and write the four output tables."""
    player_season = pd.read_csv(PLAYER_SEASON_PATH)
    tm_players = pd.read_csv(TM_PLAYERS_PATH)
    season_values = pd.read_csv(TM_VALUES_PATH)
    club_names = set(tm_players["current_club_name"].dropna())
    if TM_CLUBS_PATH.exists():
        club_names.update(pd.read_csv(TM_CLUBS_PATH)["name"].dropna())
    club_map = build_club_name_map(player_season["team"].dropna().unique().tolist(), list(club_names))
    overrides = load_overrides()
    player_map = build_player_id_map(player_season, tm_players, club_map, overrides)
    valued = attach_market_values(player_season, player_map, season_values)
    missed = unmatched_report(player_season, player_map, tm_players)

    for path, frame in (
        (CLUB_MAP_PATH, club_map),
        (MAP_PATH, player_map),
        (VALUED_PATH, valued),
        (UNMATCHED_PATH, missed),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(f"Wrote {len(frame):,} rows to {path}")
    return {
        "club_map": club_map,
        "player_map": player_map,
        "valued": valued,
        "unmatched": missed,
        "tm_players": tm_players,
    }


def main() -> None:
    random.seed(7)
    tables = build_all()
    summarize(tables["valued"], tables["player_map"], tables["tm_players"])


if __name__ == "__main__":
    main()
