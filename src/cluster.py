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

from src.features import VECTORS_PATH

ROOT = Path(__file__).resolve().parents[1]
CLUSTER_NAMES_PATH = ROOT / "data" / "processed" / "cluster_names.csv"
PLAYER_CLUSTERS_PATH = ROOT / "data" / "processed" / "player_clusters.csv"
POOL_SEASON = 2526
MAX_K = 5
STABILITY_SEEDS = (42, 7, 11, 13, 19, 23, 29, 31, 37, 41)
STYLE_K = (3, 4)
MIN_CLUSTER_SHARE = 0.10

# Outcomes describe what happened. Styles are built from actions only.
OUTCOME_FEATURES = (
    "goals_per90",
    "non_penalty_goals_per90",
    "assists_per90",
    "goals_per_shot",
)
# Volume and ratios of things a player does. shots_on_target_per90 is kept
# here and dropped later if it repeats shots_per90 inside a role.
STYLE_FEATURES = (
    "shots_per90",
    "shots_on_target_per90",
    "shot_accuracy",
    "crosses_per90",
    "tackles_won_per90",
    "interceptions_per90",
    "fouls_committed_per90",
    "fouls_drawn_per90",
    "offsides_per90",
)
# When two columns move together, keep the one earlier in this list.
KEEP_FIRST = (
    "shots_per90",
    "shot_accuracy",
    "crosses_per90",
    "tackles_won_per90",
    "interceptions_per90",
    "fouls_drawn_per90",
    "fouls_committed_per90",
    "offsides_per90",
    "shots_on_target_per90",
)

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


def style_matrix(group: pd.DataFrame, position_group: str) -> tuple[pd.DataFrame, list[str]]:
    """Action features for one role, with collinear columns removed and re-z-scored.

    The incoming columns are the full-sample z-scores. Correlation does not care
    about that scaling. After the drop, each remaining column is z-scored again
    inside this role's 2025-26 pool, which is the scale KMeans sees.
    """
    available = [column for column in STYLE_FEATURES if column in group.columns]
    kept = _drop_collinear(group[available], position_group)
    z_scored = _zscore_columns(group[kept])
    return z_scored, kept


def cluster_playing_styles(vectors: pd.DataFrame | None = None) -> dict:
    """Cluster 2025-26 action profiles and overwrite the style tables.

    Goals, assists, and goals per shot stay in the similarity vectors. They are
    not used here. Names in cluster_names.csv are regenerated from the new centroids.
    """
    if vectors is None:
        vectors = pd.read_csv(VECTORS_PATH)
    pool = vectors.loc[vectors["season"].astype(int) == POOL_SEASON].copy()
    pool = pool.loc[pool["position_group"].ne("GK") & pool["position_group"].notna()]

    name_rows = []
    player_rows = []
    diagnostics = {}
    edited_names = _read_edited_names()
    for position_group, group in pool.groupby("position_group", sort=True):
        group = group.reset_index(drop=True)
        styled, features = style_matrix(group, position_group)
        matrix = styled.to_numpy(dtype=float)
        fits = [_fit_k(matrix, k) for k in STYLE_K]
        chosen, reason = _choose_fit(fits)
        labels = chosen["labels"]
        model = chosen["model"]
        pca = run_pca(matrix, features)
        named = name_clusters(model.cluster_centers_, features, position_group)
        distances = np.linalg.norm(matrix - model.cluster_centers_[labels], axis=1)

        for row in named.itertuples(index=False):
            name_rows.append(
                {
                    "position_group": position_group,
                    "cluster_id": int(row.cluster_id),
                    "proposed_name": row.proposed_name,
                    "cluster_name": edited_names.get(
                        (position_group, int(row.cluster_id)), row.proposed_name
                    ),
                    "high_features": row.high_features,
                    "low_features": row.low_features,
                    "size": int((labels == row.cluster_id).sum()),
                }
            )
        name_lookup = {
            row["cluster_id"]: row["cluster_name"]
            for row in name_rows
            if row["position_group"] == position_group
        }
        assigned = group[["player", "team", "league", "position_group", "minutes", "sub_position"]].copy()
        assigned["cluster_id"] = labels
        assigned["cluster_name"] = assigned["cluster_id"].map(name_lookup)
        assigned["distance_to_centroid"] = distances
        player_rows.append(assigned)
        diagnostics[position_group] = {
            "k": chosen["k"],
            "silhouette": chosen["silhouette"],
            "stability": chosen["stability"],
            "reason": reason,
            "comparison": [
                {
                    "k": fit["k"],
                    "silhouette": fit["silhouette"],
                    "mean_ari": fit["stability"]["mean_ari"],
                    "stable": fit["stability"]["stable"],
                    "sizes": fit["sizes"],
                }
                for fit in fits
            ],
            "pca": pca,
            "centroids": model.cluster_centers_,
            "features": features,
        }

    names = pd.DataFrame(name_rows)[NAME_COLUMNS]
    players = pd.concat(player_rows, ignore_index=True)
    CLUSTER_NAMES_PATH.parent.mkdir(parents=True, exist_ok=True)
    names.to_csv(CLUSTER_NAMES_PATH, index=False)
    players.to_csv(PLAYER_CLUSTERS_PATH, index=False)
    return {"names": names, "players": players, "diagnostics": diagnostics, "features": STYLE_FEATURES}


def _kmeans(X, k: int, random_state: int) -> KMeans:
    return KMeans(n_clusters=k, n_init=20, random_state=random_state)


def _zscore_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Population z-score. A column with no spread becomes 0."""
    std = frame.std(ddof=0)
    std = std.mask(std == 0)
    return frame.sub(frame.mean()).div(std).fillna(0.0)


def _drop_collinear(frame: pd.DataFrame, position_group: str) -> list[str]:
    """Drop one column from every pair whose absolute correlation exceeds 0.8."""
    kept = list(frame.columns)
    while len(kept) > 1:
        corr = frame[kept].corr()
        pair = None
        strongest = 0.0
        for i, left in enumerate(kept):
            for right in kept[i + 1 :]:
                value = float(corr.loc[left, right])
                if abs(value) > 0.8 and abs(value) > strongest:
                    strongest = abs(value)
                    pair = (left, right, value)
        if pair is None:
            break
        left, right, value = pair
        drop = left if KEEP_FIRST.index(left) > KEEP_FIRST.index(right) else right
        keep = right if drop == left else left
        print(f"{position_group}: drop {drop} (|r|={abs(value):.2f} with {keep}). {_drop_reason(drop, keep)}")
        kept.remove(drop)
    return kept


def _drop_reason(dropped: str, kept: str) -> str:
    if {dropped, kept} == {"shots_per90", "shots_on_target_per90"}:
        return "Shots on target per 90 repeats shot volume, and shot accuracy already keeps the on-target share."
    if dropped == "shots_on_target_per90" and kept == "shot_accuracy":
        return "The on-target count and the on-target ratio describe the same touch; the ratio is the one that is not just more shots."
    if {dropped, kept} <= {"tackles_won_per90", "fouls_committed_per90"}:
        return "Fouls committed track the same aggression as tackles won, so the tackle count is enough."
    return f"{dropped} moves with {kept}, so it repeats the same action."


def _fit_k(matrix: np.ndarray, k: int) -> dict:
    model = _kmeans(matrix, k, random_state=42).fit(matrix)
    labels = model.labels_
    sizes = [int((labels == i).sum()) for i in range(k)]
    stability = stability_check(matrix, k)
    return {
        "k": k,
        "model": model,
        "labels": labels,
        "sizes": sizes,
        "min_share": min(sizes) / len(labels),
        "silhouette": float(silhouette_score(matrix, labels)),
        "stability": stability,
    }


def _centroid_gap(model: KMeans) -> float:
    """Smallest distance between two centroids. Larger means the styles sit further apart."""
    centers = model.cluster_centers_
    gaps = [
        float(np.linalg.norm(centers[i] - centers[j]))
        for i in range(len(centers))
        for j in range(i + 1, len(centers))
    ]
    return min(gaps) if gaps else 0.0


def _sharp_styles(model: KMeans, threshold: float = 0.5) -> int:
    """How many centroids are clearly high on at least one action, not a near-average leftover."""
    return int(sum(float(center.max()) >= threshold for center in model.cluster_centers_))


def _choose_fit(fits: list[dict]) -> tuple[dict, str]:
    """Prefer a split whose clusters are large enough and each style has its own action."""
    large_enough = [fit for fit in fits if fit["min_share"] >= MIN_CLUSTER_SHARE]
    if not large_enough:
        chosen = min(fits, key=lambda fit: fit["k"])
        small = min(chosen["sizes"])
        share = small / sum(chosen["sizes"])
        reason = (
            f"Both k=3 and k=4 leave a cluster under 10% of the role "
            f"({small} players, {share:.0%}). k={chosen['k']} is the cleaner reading, "
            f"because splitting further does not absorb that small group."
        )
        return chosen, reason
    if len(large_enough) == 1:
        chosen = large_enough[0]
        rejected = next(fit for fit in fits if fit is not chosen)
        share = min(rejected["sizes"]) / sum(rejected["sizes"])
        reason = (
            f"k={rejected['k']} leaves a cluster at {share:.0%} of the role, under 10%. "
            f"k={chosen['k']} keeps every style large enough to describe."
        )
        return chosen, reason
    stable = [fit for fit in large_enough if fit["stability"]["stable"]]
    if len(stable) == 1:
        chosen = stable[0]
        other = next(fit for fit in large_enough if fit is not chosen)
        reason = (
            f"k={chosen['k']} comes back across seeds (ARI {chosen['stability']['mean_ari']:.2f}) "
            f"and k={other['k']} does not (ARI {other['stability']['mean_ari']:.2f}). "
            f"Every cluster is at least 10% of the role."
        )
        return chosen, reason
    pool = stable or large_enough
    ranked = sorted(
        pool,
        key=lambda fit: (_sharp_styles(fit["model"]), _centroid_gap(fit["model"])),
        reverse=True,
    )
    chosen, other = ranked[0], ranked[1]
    reason = (
        f"k={chosen['k']} separates more styles that are each high on their own action "
        f"({_sharp_styles(chosen['model'])} clear profiles, versus {_sharp_styles(other['model'])} for k={other['k']}). "
        f"Every cluster is at least 10% of the role."
    )
    return chosen, reason


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
    """Name a centroid from the actions that sit high or low, never from goals or assists."""
    shots = z.get("shots_per90", 0.0)
    accuracy = z.get("shot_accuracy", 0.0)
    crosses = z.get("crosses_per90", 0.0)
    tackles = z.get("tackles_won_per90", 0.0)
    interceptions = z.get("interceptions_per90", 0.0)
    fouls = z.get("fouls_committed_per90", 0.0)
    drawn = z.get("fouls_drawn_per90", 0.0)
    offsides = z.get("offsides_per90", 0.0)
    shooting = max(shots, z.get("shots_on_target_per90", shots))
    defending = max(tackles, interceptions)

    if position_group == "FB":
        if shooting >= 0.45 and crosses >= 0.2:
            return "Attacking wing-back"
        if crosses >= 0.45:
            return "Crossing fullback"
        if shooting >= 0.45:
            return "Inverted fullback"
        if defending >= 0.35 and crosses <= 0.15:
            return "Defensive fullback"
        if tackles >= 0.3 or (fouls >= 0.3 and defending >= 0.15):
            return "Ball-winning fullback"
        return "Holding fullback"

    if position_group == "CB":
        if crosses >= 0.8:
            return "Wide centre-back"
        if shooting >= 0.45:
            return "Stepping-out centre-back"
        if tackles >= 0.25 and interceptions >= 0.2:
            return "Aggressive centre-back"
        if fouls >= 0.35 or (fouls >= 0.25 and defending >= 0.25):
            return "Physical centre-back"
        if interceptions >= 0.3 and tackles < 0.15:
            return "Cover centre-back"
        if defending >= 0.25:
            return "Front-foot centre-back"
        return "Positional centre-back"

    if position_group == "CM":
        if defending >= 0.35 and shooting < 0.2:
            return "Ball-winning destroyer"
        if shooting >= 0.35 and defending >= 0.15:
            return "Box-to-box midfielder"
        if shooting >= 0.4:
            return "Arriving midfielder"
        if crosses >= 0.35 and shooting < 0.25:
            return "Wide midfielder"
        if drawn >= 0.35 and defending < 0.2:
            return "Press-resistant midfielder"
        if defending >= 0.2:
            return "Screening midfielder"
        return "Link midfielder"

    if position_group == "AM_W":
        if drawn >= 0.45 and fouls >= 0.4:
            return "Foul-drawing winger"
        if crosses >= 0.4:
            return "Crossing winger"
        if defending >= 0.4 and shooting <= 0.15:
            return "Tracking winger"
        if shooting >= 0.3 and crosses < shooting:
            return "Inside forward"
        if defending >= 0.25:
            return "Pressing winger"
        return "Wide support"

    if position_group == "ST":
        if crosses >= 0.4 and (defending >= 0.2 or shooting < 0.3):
            return "Dropping forward"
        if fouls >= 0.4 or (fouls >= 0.25 and defending >= 0.2):
            return "Pressing striker"
        if shooting >= 0.3 and offsides >= 0.2:
            return "Box striker"
        if accuracy >= 0.25 and defending < 0.15:
            return "Penalty-box striker"
        if shooting >= 0.3:
            return "Volume shooter"
        if drawn >= 0.3:
            return "Foul-drawing striker"
        return "Link striker"

    if defending >= 0.3:
        return "Ball winner"
    if crosses >= 0.3:
        return "Crosser"
    if shooting >= 0.3:
        return "Shooter"
    return "Balanced profile"


if __name__ == "__main__":
    result = cluster_playing_styles()
    for group, info in result["diagnostics"].items():
        print(f"\n{group}: {info['reason']}")
        for row in info["comparison"]:
            print(
                f"  k={row['k']} silhouette={row['silhouette']:.3f} "
                f"ARI={row['mean_ari']:.3f} sizes={row['sizes']}"
            )
        centers = pd.DataFrame(info["centroids"], columns=info["features"])
        print(centers.round(2).to_string())
    print(result["names"][["position_group", "cluster_name", "size", "high_features", "low_features"]].to_string(index=False))
