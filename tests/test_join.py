"""Matching checks against the real FBref and Transfermarkt tables."""

from pathlib import Path

import pandas as pd
import pytest

from src.join import (
    CLUB_MAP_PATH,
    MAP_PATH,
    OVERRIDES_PATH,
    PLAYER_SEASON_PATH,
    TM_CLUBS_PATH,
    TM_PLAYERS_PATH,
    build_club_name_map,
    build_player_id_map,
    load_overrides,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def player_map() -> pd.DataFrame:
    player_season = pd.read_csv(PLAYER_SEASON_PATH)
    tm_players = pd.read_csv(TM_PLAYERS_PATH)
    club_names = set(tm_players["current_club_name"].dropna())
    if TM_CLUBS_PATH.exists():
        club_names.update(pd.read_csv(TM_CLUBS_PATH)["name"].dropna())
    club_map = build_club_name_map(player_season["team"].dropna().unique().tolist(), list(club_names))
    return build_player_id_map(player_season, tm_players, club_map, load_overrides(OVERRIDES_PATH))


def _row(player_map: pd.DataFrame, player: str, birth_year: int) -> pd.Series:
    hits = player_map.loc[
        player_map["player"].eq(player) & (player_map["birth_year"] == birth_year)
    ]
    assert len(hits) == 1, f"expected one map row for {player} {birth_year}"
    return hits.iloc[0]


def test_vuskovic_matches_the_unaccented_transfermarkt_name(player_map):
    row = _row(player_map, "Luka Vušković", 2007)
    assert row["tm_player_id"] == 892160
    assert row["match_method"] == "tier1"


def test_matthew_smith_arsenal_2000_not_matched_to_st_johnstone(player_map):
    row = _row(player_map, "Matthew Smith", 2000)
    assert pd.isna(row["tm_player_id"])


def test_accented_tottenham_names_match(player_map):
    kinsky = _row(player_map, "Antonín Kinský", 2003)
    dragusin = _row(player_map, "Radu Drăgușin", 2002)
    assert kinsky["tm_player_id"] == 725912
    assert dragusin["tm_player_id"] == 568559


def test_souza_is_the_tottenham_player_or_unmatched(player_map):
    row = _row(player_map, "Souza", 2006)
    if pd.notna(row["tm_player_id"]):
        assert int(row["tm_player_id"]) == 1086258
        assert row["match_method"] == "tier3"
    else:
        assert row["match_method"] in {"ambiguous", "conflict"}


def test_a_transfermarkt_id_is_not_shared(player_map):
    matched = player_map.loc[player_map["tm_player_id"].notna(), "tm_player_id"]
    assert matched.duplicated().sum() == 0


def test_saved_club_map_sits_outside_the_match_table():
    assert CLUB_MAP_PATH.name == "club_name_map.csv"
    assert MAP_PATH.parent.name == "processed"
    assert OVERRIDES_PATH.name == "manual_overrides.csv"
