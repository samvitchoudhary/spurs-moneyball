"""Cosine similarity search over the z-scored player vectors."""

from __future__ import annotations

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from sklearn.metrics.pairwise import cosine_similarity

from src.clean_transfermarkt import normalize_name
from src.features import VECTORS_PATH, feature_columns

POOL_SEASON = 2526
RESULT_COLUMNS = [
    "player",
    "team",
    "league",
    "age",
    "minutes",
    "market_value_eur",
    "similarity",
    "value_pct",
]


def cosine_similarity_matrix(X) -> np.ndarray:
    """Pairwise cosine similarity, written out as a matrix product.

    Cosine similarity is the cosine of the angle between two vectors, which
    equals their dot product once each vector has length 1. Dividing every
    row by its Euclidean norm puts the players on the unit sphere, and the
    Gram matrix of that normalized block is every pairwise cosine.
    """
    matrix = np.asarray(X, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("X must be a 2-D array of player vectors.")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    normalized = matrix / norms
    ours = normalized @ normalized.T
    reference = cosine_similarity(matrix)
    if not np.allclose(ours, reference, atol=1e-9, rtol=0, equal_nan=True):
        gap = np.nanmax(np.abs(ours - reference))
        raise AssertionError(f"Hand-rolled cosine differs from sklearn by {gap}.")
    return ours


def load_vectors(path=VECTORS_PATH) -> pd.DataFrame:
    """Read the saved z-scored player table."""
    vectors = pd.read_csv(path)
    vectors["season"] = vectors["season"].map(_season_code)
    return vectors


def find_similar(
    player: str,
    season: str = "2526",
    n: int = 10,
    cheaper_only: bool = True,
    max_value_eur: float | None = None,
    max_age: float | None = None,
    leagues: list[str] | None = None,
    vectors: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Closest 2025-26 players in the same position group.

    The search pool is always 2025-26. `season` chooses which of the named
    player's vectors is the target. The player himself is excluded. With
    cheaper_only, a match must be valued below the target.
    """
    table = vectors.copy() if vectors is not None else load_vectors()
    table["season"] = table["season"].map(_season_code)
    target_season = _season_code(season)
    target = _resolve_player(player, table.loc[table["season"] == target_season])
    features = feature_columns(table)
    pool = table.loc[
        (table["season"] == POOL_SEASON) & (table["position_group"] == target["position_group"])
    ].copy()
    pool = pool.loc[~_same_player(pool, target)]
    if cheaper_only:
        if pd.isna(target["market_value_eur"]):
            raise ValueError(f"{target['player']} has no market value, so cheaper_only cannot be applied.")
        pool = pool.loc[pool["market_value_eur"] < target["market_value_eur"]]
    if max_value_eur is not None:
        pool = pool.loc[pool["market_value_eur"] <= max_value_eur]
    if max_age is not None:
        pool = pool.loc[pool["age"] <= max_age]
    if leagues is not None:
        pool = pool.loc[pool["league"].isin(leagues)]
    if pool.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    scores = cosine_similarity_matrix(
        np.vstack([target[features].to_numpy(dtype=float), pool[features].to_numpy(dtype=float)])
    )[0, 1:]
    pool = pool.copy()
    pool["similarity"] = scores
    target_value = target["market_value_eur"]
    pool["value_pct"] = np.where(
        pd.notna(target_value) & (target_value != 0),
        100.0 * pool["market_value_eur"] / target_value,
        np.nan,
    )
    pool = pool.sort_values(["similarity", "player"], ascending=[False, True]).head(n)
    return pool[RESULT_COLUMNS].reset_index(drop=True)


def explain_match(
    player_a: str,
    player_b: str,
    season: str = "2526",
    vectors: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Three z-score features where two players are closest, and three where they are furthest."""
    table = vectors.copy() if vectors is not None else load_vectors()
    table["season"] = table["season"].map(_season_code)
    season_code = _season_code(season)
    season_rows = table.loc[table["season"] == season_code]
    left = _resolve_player(player_a, season_rows)
    right = _resolve_player(player_b, season_rows)
    features = feature_columns(table)
    gap = (left[features].astype(float) - right[features].astype(float)).abs()
    order = gap.sort_values(kind="mergesort")
    alike = order.head(3).index.tolist()
    different = order.tail(3).sort_values(ascending=False).index.tolist()
    rows = []
    for kind, names in (("alike", alike), ("different", different)):
        for name in names:
            rows.append(
                {
                    "kind": kind,
                    "feature": name,
                    "z_a": float(left[name]),
                    "z_b": float(right[name]),
                    "abs_diff": float(gap[name]),
                }
            )
    return pd.DataFrame(rows)


def _season_code(value) -> int:
    text = str(value).strip()
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start[-2:] + end[-2:])
    return int(float(text))


def _same_player(frame: pd.DataFrame, target: pd.Series) -> pd.Series:
    if pd.notna(target.get("tm_player_id")):
        by_id = frame["tm_player_id"] == target["tm_player_id"]
    else:
        by_id = pd.Series(False, index=frame.index)
    by_name = (frame["player"] == target["player"]) & (frame["birth_year"] == target["birth_year"])
    return by_id | by_name


def _resolve_player(query: str, pool: pd.DataFrame) -> pd.Series:
    """Match a typed name to one player. Raise if nobody is close, or more than one is."""
    if pool.empty:
        raise ValueError(f"No players to search for '{query}'.")
    needle = normalize_name(query)
    if not needle:
        raise ValueError("Player name is empty.")
    people = pool.drop_duplicates(["player", "birth_year"]).copy()
    people["name_normalized"] = people["player"].map(normalize_name)
    exact = people.loc[people["name_normalized"] == needle]
    if len(exact) == 1:
        chosen = exact.iloc[0]
        return pool.loc[
            (pool["player"] == chosen["player"]) & (pool["birth_year"] == chosen["birth_year"])
        ].iloc[0]
    if len(exact) > 1:
        options = ", ".join(exact["player"].astype(str))
        raise ValueError(f"'{query}' matches more than one player: {options}.")
    people["match_score"] = people["name_normalized"].map(
        lambda name: fuzz.token_set_ratio(needle, name or "")
    )
    best = int(people["match_score"].max())
    if best < 80:
        raise ValueError(f"No player close to '{query}'. Best score was {best}.")
    # A partial name such as "Porro" scores 100 against the one player who contains it.
    # Anyone else that close is a different person, so the query is ambiguous.
    close = people.loc[people["match_score"] >= max(best - 5, 80)]
    identities = close.drop_duplicates(["player", "birth_year"])
    if len(identities) > 1:
        options = ", ".join(
            f"{row.player} ({int(row.match_score)})" for row in identities.itertuples()
        )
        raise ValueError(f"'{query}' matches more than one player: {options}.")
    chosen = identities.iloc[0]
    return pool.loc[
        (pool["player"] == chosen["player"]) & (pool["birth_year"] == chosen["birth_year"])
    ].iloc[0]
