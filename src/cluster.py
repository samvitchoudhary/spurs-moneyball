"""Cluster 2025-26 player vectors into playing styles within each position group."""

from __future__ import annotations

import os
from pathlib import Path

# joblib warns on this machine when it cannot read the physical core count.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score

from src.features import VECTORS_PATH, feature_columns

ROOT = Path(__file__).resolve().parents[1]
CLUSTER_NAMES_PATH = ROOT / "data" / "processed" / "cluster_names.csv"
PLAYER_CLUSTERS_PATH = ROOT / "data" / "processed" / "player_clusters.csv"
POOL_SEASON = 2526
MAX_K = 5
STABILITY_SEEDS = (42, 7, 11, 13, 19, 23, 29, 31, 37, 41)

# Hand-editable column. proposed_name is what the rules suggested on the last run.
NAME_COLUMNS = [
    "position_group",
    "cluster_id",
    "proposed_name",
    "cluster_name",
    "high_features",
    "low_features",
    "size",
]


def run_pca(X, feature_names: list[str] | None = None) -> dict:
    """Project players onto the two directions that spread them out the most.

    PCA takes the eigenvectors of the covariance matrix of the feature columns.
    Those eigenvectors are the axes of greatest variance, and PC1 is the single
    direction along which the player profiles differ most.
    """
    frame = np.asarray(X, dtype=float)
    names = list(feature_names) if feature_names is not None else [f"f{i}" for i in range(frame.shape[1])]
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(frame)
    loadings = {}
    for axis, component in enumerate(pca.components_, start=1):
        order = np.argsort(np.abs(component))[::-1][:3]
        loadings[f"PC{axis}"] = [(names[i], float(component[i])) for i in order]
    return {
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "loadings": loadings,
        "coords": coords,
    }


def choose_k(X, k_range=range(2, 7)) -> dict:
    """Silhouette score for each k. The chosen k is the best score at or below 5."""
    frame = np.asarray(X, dtype=float)
    scores = {}
    for k in k_range:
        labels = _kmeans(frame, k, random_state=42).fit_predict(frame)
        scores[int(k)] = float(silhouette_score(frame, labels))
    eligible = {k: score for k, score in scores.items() if k <= MAX_K}
    best = max(eligible, key=eligible.get)
    return {"scores": scores, "k": best, "silhouette": eligible[best]}


def stability_check(X, k: int) -> dict:
    """Mean adjusted Rand index of nine fresh seeds against the first KMeans run.

    A group is unstable when that mean is below 0.8. The first seed matches the
    published clustering (random_state=42).
    """
    frame = np.asarray(X, dtype=float)
    reference = _kmeans(frame, k, random_state=STABILITY_SEEDS[0]).fit_predict(frame)
    agreements = []
    for seed in STABILITY_SEEDS[1:]:
        labels = _kmeans(frame, k, random_state=seed).fit_predict(frame)
        agreements.append(float(adjusted_rand_score(reference, labels)))
    mean_ari = float(np.mean(agreements))
    return {"mean_ari": mean_ari, "stable": mean_ari >= 0.8, "aris": agreements}


def name_clusters(
    centroids,
    feature_names: list[str],
    position_group: str | None = None,
) -> pd.DataFrame:
    """Three highest and two lowest centroid z-scores, plus a short style name.

    Names are proposals. Edit cluster_name in data/processed/cluster_names.csv
    and those labels are what the player file keeps.
    """
    matrix = np.asarray(centroids, dtype=float)
    rows = []
    used = set()
    for cluster_id, centroid in enumerate(matrix):
        order = np.argsort(centroid)
        high_idx = order[::-1][:3]
        low_idx = order[:2]
        high = [(feature_names[i], float(centroid[i])) for i in high_idx]
        low = [(feature_names[i], float(centroid[i])) for i in low_idx]
        proposed = _unique_name(
            _propose_name(dict(zip(feature_names, centroid)), position_group),
            used,
        )
        used.add(proposed)
        rows.append(
            {
                "cluster_id": cluster_id,
                "proposed_name": proposed,
                "high_features": _format_features(high),
                "low_features": _format_features(low),
                "high": high,
                "low": low,
            }
        )
    return pd.DataFrame(rows)


def cluster_playing_styles(vectors: pd.DataFrame | None = None) -> dict:
    """Cluster the 2025-26 pool and write cluster names plus player assignments."""
    if vectors is None:
        vectors = pd.read_csv(VECTORS_PATH)
    pool = vectors.loc[vectors["season"].astype(int) == POOL_SEASON].copy()
    pool = pool.loc[pool["position_group"].ne("GK") & pool["position_group"].notna()]
    features = feature_columns(pool)
    existing_names = _read_edited_names()

    name_rows = []
    player_rows = []
    diagnostics = {}
    for position_group, group in pool.groupby("position_group", sort=True):
        group = group.reset_index(drop=True)
        matrix = group[features].to_numpy(dtype=float)
        selection = choose_k(matrix)
        k = selection["k"]
        model = _kmeans(matrix, k, random_state=42).fit(matrix)
        labels = model.labels_
        stability = stability_check(matrix, k)
        pca = run_pca(matrix, features)
        named = name_clusters(model.cluster_centers_, features, position_group)
        distances = np.linalg.norm(matrix - model.cluster_centers_[labels], axis=1)

        for row in named.itertuples(index=False):
            edited = existing_names.get((position_group, int(row.cluster_id)))
            cluster_name = edited if edited else row.proposed_name
            name_rows.append(
                {
                    "position_group": position_group,
                    "cluster_id": int(row.cluster_id),
                    "proposed_name": row.proposed_name,
                    "cluster_name": cluster_name,
                    "high_features": row.high_features,
                    "low_features": row.low_features,
                    "size": int((labels == row.cluster_id).sum()),
                }
            )
        name_lookup = {row["cluster_id"]: row["cluster_name"] for row in name_rows if row["position_group"] == position_group}
        assigned = group[["player", "team", "league", "position_group", "minutes", "sub_position"]].copy()
        assigned["cluster_id"] = labels
        assigned["cluster_name"] = assigned["cluster_id"].map(name_lookup)
        assigned["distance_to_centroid"] = distances
        player_rows.append(assigned)
        diagnostics[position_group] = {
            "scores": selection["scores"],
            "k": k,
            "silhouette": selection["silhouette"],
            "stability": stability,
            "pca": pca,
            "centroids": model.cluster_centers_,
            "features": features,
        }

    names = pd.DataFrame(name_rows)[NAME_COLUMNS]
    players = pd.concat(player_rows, ignore_index=True)
    CLUSTER_NAMES_PATH.parent.mkdir(parents=True, exist_ok=True)
    names.to_csv(CLUSTER_NAMES_PATH, index=False)
    players.to_csv(PLAYER_CLUSTERS_PATH, index=False)
    return {"names": names, "players": players, "diagnostics": diagnostics, "features": features}


def _kmeans(X, k: int, random_state: int) -> KMeans:
    return KMeans(n_clusters=k, n_init=20, random_state=random_state)


def _read_edited_names() -> dict[tuple[str, int], str]:
    """Keep a cluster_name when someone has changed it away from the proposal."""
    if not CLUSTER_NAMES_PATH.exists():
        return {}
    saved = pd.read_csv(CLUSTER_NAMES_PATH)
    if "cluster_name" not in saved.columns or "proposed_name" not in saved.columns:
        return {}
    edited = saved.loc[saved["cluster_name"].fillna("") != saved["proposed_name"].fillna("")]
    return {
        (row.position_group, int(row.cluster_id)): row.cluster_name
        for row in edited.itertuples(index=False)
    }


def _format_features(pairs: list[tuple[str, float]]) -> str:
    return ", ".join(f"{name} ({value:+.2f})" for name, value in pairs)


def _unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        return name
    suffix = 2
    while f"{name} {suffix}" in used:
        suffix += 1
    return f"{name} {suffix}"


def _propose_name(z: dict[str, float], position_group: str | None) -> str:
    """Pick a football label from the features that sit high or low at this centroid."""
    goals = max(z.get("goals_per90", 0.0), z.get("non_penalty_goals_per90", 0.0))
    shots = max(z.get("shots_per90", 0.0), z.get("shots_on_target_per90", 0.0))
    crosses = z.get("crosses_per90", 0.0)
    tackles = z.get("tackles_won_per90", 0.0)
    interceptions = z.get("interceptions_per90", 0.0)
    assists = z.get("assists_per90", 0.0)
    drawn = z.get("fouls_drawn_per90", 0.0)
    offsides = z.get("offsides_per90", 0.0)
    attack = max(goals, shots)
    defending = max(tackles, interceptions)

    # The strongest split in these features is scorers versus the rest of the role.
    if attack >= 0.45:
        return {
            "FB": "Goal-scoring fullback",
            "CB": "Goal-scoring centre-back",
            "CM": "Goalscoring midfielder",
            "AM_W": "Inside forward",
            "ST": "Box striker",
        }.get(position_group, "Goal threat")
    if crosses >= 0.4 and attack >= 0.15:
        return "Attacking wing-back" if position_group == "FB" else "Crossing wide player"
    if defending >= 0.35 and attack < 0.2:
        return {
            "FB": "Ball-winning fullback",
            "CB": "Aggressive centre-back",
            "CM": "Ball-winning destroyer",
            "AM_W": "Pressing winger",
            "ST": "Pressing striker",
        }.get(position_group, "Ball winner")
    if attack <= -0.25:
        return {
            "FB": "Holding fullback",
            "CB": "Stay-at-home centre-back",
            "CM": "Holding midfielder",
            "AM_W": "Tracking winger",
            "ST": "Support striker",
        }.get(position_group, "Low-scoring profile")
    if assists >= 0.3 and attack < 0.35:
        return "Chance-creating midfielder" if position_group == "CM" else "Creative wide player"
    if offsides >= 0.25 and position_group == "ST":
        return "Penalty-box forward"
    if drawn >= 0.35:
        return "Foul-drawing forward"
    return {
        "FB": "Holding fullback",
        "CB": "Stay-at-home centre-back",
        "CM": "Holding midfielder",
        "AM_W": "Tracking winger",
        "ST": "Support striker",
    }.get(position_group, "Balanced profile")


if __name__ == "__main__":
    result = cluster_playing_styles()
    for group, info in result["diagnostics"].items():
        stability = info["stability"]
        flag = "stable" if stability["stable"] else "UNSTABLE"
        print(
            f"{group}: k={info['k']} silhouette={info['silhouette']:.3f} "
            f"ARI={stability['mean_ari']:.3f} ({flag})"
        )
    print(result["names"][["position_group", "cluster_id", "cluster_name", "size", "high_features"]].to_string(index=False))
