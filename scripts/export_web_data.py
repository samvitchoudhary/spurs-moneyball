"""Export the committed app tables to compact JSON for the static site.

The site does no ML. Similarity neighbours and the style-map coordinates are
computed here, once, from the same functions the dashboard uses.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

from src.cluster import style_matrix  # noqa: E402
from src.features import feature_columns  # noqa: E402
from src.similarity import cosine_similarity_matrix  # noqa: E402
from utils import FEATURE_LABELS, backtest_headlines, flag_emoji  # noqa: E402

DATA = ROOT / "app_data"
OUT = ROOT / "web" / "public" / "data"
POOL = 2526
NEIGHBOURS = 20

ROLE = {
    "CB": "Centre-back",
    "FB": "Full-back",
    "CM": "Central midfield",
    "AM_W": "Wide attacker",
    "ST": "Striker",
    "GK": "Goalkeeper",
}


def player_id(name: str, birth_year) -> str:
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "player"
    if pd.notna(birth_year):
        slug = f"{slug}-{int(birth_year)}"
    return slug


def num(value, digits: int = 4):
    if value is None or (isinstance(value, float) and np.isnan(value)) or pd.isna(value):
        return None
    number = float(value)
    if digits == 0:
        return int(round(number))
    return round(number, digits)


def season_label(season: int) -> str:
    text = f"{int(season):04d}"
    return f"20{text[:2]}-{text[2:]}"


def write(name: str, payload) -> int:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    size = path.stat().st_size
    print(f"{name:24} {size / 1024:8.1f} KB")
    return size


def main() -> None:
    vectors = pd.read_parquet(DATA / "player_vectors.parquet")
    clusters = pd.read_parquet(DATA / "player_clusters.parquet")
    names = pd.read_parquet(DATA / "cluster_names.parquet")
    predictions = pd.read_parquet(DATA / "value_predictions.parquet")
    picks = pd.read_parquet(DATA / "backtest_model_picks.parquet")
    signings = pd.read_parquet(DATA / "backtest_signings.parquet")
    needs = pd.read_parquet(DATA / "spurs_needs.parquet")
    shortlist = pd.read_parquet(DATA / "shortlist.parquet")
    metrics = pd.read_parquet(DATA / "model_metrics.parquet")

    vectors = vectors.copy()
    vectors["id"] = [player_id(row.player, row.birth_year) for row in vectors.itertuples(index=False)]
    if vectors.groupby("id").player.nunique().gt(1).any():
        raise SystemExit("A player id maps to more than one name.")

    features = feature_columns(vectors)
    # Empirical percentile of each z-score inside that season and role.
    for feature in features:
        vectors[f"pct_{feature}"] = vectors.groupby(["season", "position_group"])[feature].rank(pct=True, method="average") * 100

    pool = vectors.loc[vectors["season"].eq(POOL)].copy()
    by_id = vectors.drop_duplicates("id").set_index("id")

    def resolve(name: str, team: str | None = None) -> str | None:
        hits = vectors.loc[vectors["player"].eq(name)]
        if hits.empty:
            return None
        if team:
            named = hits.loc[hits["team"].eq(team)]
            if not named.empty:
                hits = named
        current = hits.loc[hits["season"].eq(POOL)]
        if not current.empty:
            hits = current
        chosen = hits.sort_values("season").iloc[-1]
        return str(chosen.id)

    page_ids = set(pool["id"])
    for frame, team_col in ((picks, "team"), (signings, "from_club"), (shortlist, "club_now")):
        for row in frame.itertuples(index=False):
            found = resolve(row.player, getattr(row, team_col, None))
            if found:
                page_ids.add(found)
            else:
                print(f"unmatched {row.player}")

    cluster_lookup = clusters.set_index(["player", "team"])["cluster_name"]
    prediction_lookup = predictions.set_index(["player", "team", "season"])

    players = []
    for pid in sorted(page_ids):
        history = vectors.loc[vectors["id"].eq(pid)].sort_values("season")
        display = history.loc[history["season"].eq(POOL)]
        row = (display if not display.empty else history.tail(1)).iloc[-1]
        cluster = cluster_lookup.get((row.player, row.team))
        if isinstance(cluster, pd.Series):
            cluster = cluster.iloc[-1]
        predicted = calibrated = None
        key = (row.player, row.team, int(row.season))
        if key in prediction_lookup.index:
            pred = prediction_lookup.loc[key]
            if isinstance(pred, pd.DataFrame):
                pred = pred.iloc[-1]
            predicted = num(pred.predicted_value, 0)
            calibrated = num(pred.calibrated_gap, 3)
        percentiles = {feature: num(row[f"pct_{feature}"], 1) for feature in features}
        players.append(
            {
                "id": pid,
                "name": str(row.player),
                "birthYear": num(row.birth_year, 0),
                "nationality": None if pd.isna(row.nationality) else str(row.nationality),
                "flag": flag_emoji(row.nationality),
                "team": str(row.team),
                "league": None if pd.isna(row.league) else str(row.league),
                "season": int(row.season),
                "seasonLabel": season_label(int(row.season)),
                "age": num(row.age, 0),
                "positionGroup": str(row.position_group),
                "position": ROLE.get(str(row.position_group), str(row.position_group)),
                "subPosition": None if pd.isna(row.sub_position) else str(row.sub_position),
                "minutes": num(row.minutes, 0),
                "marketValueEur": num(row.market_value_eur, 0),
                "predictedValueEur": predicted,
                "calibratedGap": calibrated,
                "style": None if cluster is None or (isinstance(cluster, float) and np.isnan(cluster)) else str(cluster),
                "percentiles": percentiles,
            }
        )

    search = [
        {"id": player["id"], "name": player["name"], "team": player["team"], "position": player["position"], "positionGroup": player["positionGroup"]}
        for player in players
    ]

    neighbours: dict[str, list[dict]] = {}
    id_by_index = pool["id"].tolist()
    matrix = pool[features].to_numpy(dtype=float)
    # Similarity is within the role. A striker is not a neighbour of a centre-back.
    for group, index in pool.groupby("position_group").groups.items():
        rows = pool.loc[index]
        block = rows[features].to_numpy(dtype=float)
        scores = cosine_similarity_matrix(block)
        np.fill_diagonal(scores, -np.inf)
        ids = rows["id"].tolist()
        take = min(NEIGHBOURS, max(len(ids) - 1, 0))
        for local, pid in enumerate(ids):
            if take == 0:
                neighbours[pid] = []
                continue
            chosen = np.argpartition(scores[local], -take)[-take:]
            chosen = chosen[np.argsort(scores[local, chosen])[::-1]]
            neighbours[pid] = [
                {"id": ids[int(item)], "similarity": round(float(scores[local, int(item)]), 4)}
                for item in chosen
            ]
    del matrix, id_by_index

    pca = {}
    for group, frame in pool.groupby("position_group"):
        frame = frame.reset_index(drop=True)
        if len(frame) < 2:
            continue
        styled, _kept = style_matrix(frame, group)
        if len(styled) < 2:
            continue
        xy = PCA(n_components=2, random_state=42).fit_transform(styled.to_numpy(dtype=float))
        points = []
        for i, row in enumerate(frame.itertuples(index=False)):
            cluster = cluster_lookup.get((row.player, row.team))
            if isinstance(cluster, pd.Series):
                cluster = cluster.iloc[-1]
            points.append(
                {
                    "id": row.id,
                    "x": round(float(xy[i, 0]), 3),
                    "y": round(float(xy[i, 1]), 3),
                    "style": None if cluster is None or (isinstance(cluster, float) and np.isnan(cluster)) else str(cluster),
                }
            )
        pca[str(group)] = points

    cluster_rows = []
    for row in names.itertuples(index=False):
        cluster_rows.append(
            {
                "positionGroup": str(row.position_group),
                "position": ROLE.get(str(row.position_group), str(row.position_group)),
                "id": int(row.cluster_id),
                "name": str(row.cluster_name),
                "size": int(row.size),
                "moreOf": str(row.high_features),
                "lessOf": str(row.low_features),
            }
        )

    scatter = []
    season_predictions = predictions.loc[predictions["season"].eq(POOL)]
    pred_ids = pool.set_index(["player", "team"])["id"]
    for row in season_predictions.itertuples(index=False):
        pid = pred_ids.get((row.player, row.team))
        if pid is None or pd.isna(pid):
            continue
        scatter.append(
            {
                "id": str(pid),
                "actual": num(row.actual_value, 0),
                "predicted": num(row.predicted_value, 0),
                "calibratedGap": num(row.calibrated_gap, 3),
                "decile": num(row.value_decile, 0),
            }
        )
    deciles = (
        season_predictions.groupby("value_decile", as_index=False)
        .agg(players=("player", "size"), meanLogGap=("log_gap", "mean"), low=("actual_value", "min"), high=("actual_value", "max"))
        .sort_values("value_decile")
    )
    decile_rows = [
        {
            "decile": int(row.value_decile),
            "players": int(row.players),
            "meanLogGap": num(row.meanLogGap, 3),
            "low": num(row.low, 0),
            "high": num(row.high, 0),
        }
        for row in deciles.itertuples(index=False)
    ]

    headlines = backtest_headlines(picks, signings)
    windows = ["Summer 2023", "January 2024", "Summer 2024", "January 2025", "Summer 2025", "January 2026"]
    window_rows = []
    for name in windows:
        window_picks = picks.loc[picks["window"].eq(name)]
        window_signings = signings.loc[signings["window"].eq(name), "log_value_change"]
        age_matched = window_picks.drop_duplicates("position_group")["age_matched_median_log_change"]

        def pct(series: pd.Series):
            clean = series.dropna()
            if clean.empty:
                return None
            return round(float((np.exp(clean.median()) - 1) * 100), 1)

        window_rows.append(
            {
                "window": name,
                "picks": pct(window_picks["log_value_change"]),
                "signings": pct(window_signings),
                "ageMatched": pct(age_matched),
            }
        )

    def slim_person(row, team: str) -> dict:
        return {
            "id": resolve(row.player, team),
            "name": str(row.player),
            "team": team,
            "window": str(row.window),
            "positionGroup": None if pd.isna(row.position_group) else str(row.position_group),
            "age": num(getattr(row, "age", None), 0) if hasattr(row, "age") else num(getattr(row, "age_at_window", None), 0),
        }

    pick_rows = []
    for row in picks.itertuples(index=False):
        pick_rows.append(
            {
                **slim_person(row, str(row.team)),
                "rank": int(row.rank),
                "marketValueEur": num(row.value_at_cutoff, 0),
                "modelValueEur": num(row.model_value, 0),
                "calibratedGap": num(row.calibrated_gap, 3),
                "valueChangePct": None if pd.isna(row.log_value_change) else round(float((np.exp(row.log_value_change) - 1) * 100), 1),
            }
        )
    signing_rows = []
    for row in signings.itertuples(index=False):
        signing_rows.append(
            {
                "id": resolve(row.player, str(row.from_club) if pd.notna(row.from_club) else None),
                "name": str(row.player),
                "from": None if pd.isna(row.from_club) else str(row.from_club),
                "window": str(row.window),
                "positionGroup": None if pd.isna(row.position_group) else str(row.position_group),
                "feeEur": num(row.fee_eur, 0),
                "modelValueEur": num(row.model_value, 0),
                "outcome": None if pd.isna(row.outcome) else str(row.outcome),
                "tier": None if pd.isna(row.signing_tier) else str(row.signing_tier),
                "valueChangePct": None if pd.isna(row.log_value_change) else round(float((np.exp(row.log_value_change) - 1) * 100), 1),
            }
        )

    need_rows = []
    for row in needs.sort_values("need_score", ascending=False).itertuples(index=False):
        need_rows.append(
            {
                "positionGroup": str(row.position_group),
                "position": ROLE.get(str(row.position_group), str(row.position_group)),
                "needScore": num(row.need_score, 3),
                "rank": int(row.rank),
                "targetStyle": None if pd.isna(row.target_style) else str(row.target_style),
                "stylesPresent": None if pd.isna(row.styles_present) else str(row.styles_present),
                "stylesMissing": None if pd.isna(row.styles_missing) else str(row.styles_missing),
                "outputPercentile": num(row.output_percentile, 1),
            }
        )

    short_rows = []
    for row in shortlist.sort_values(["need", "rank"]).itertuples(index=False):
        short_rows.append(
            {
                "id": resolve(row.player, str(row.club_now)),
                "need": str(row.need),
                "rank": int(row.rank),
                "name": str(row.player),
                "club": str(row.club_now),
                "age": num(row.age_at_window, 0),
                "targetStyle": None if pd.isna(row.target_style) else str(row.target_style),
                "marketValueEur": num(row.actual_value, 0),
                "predictedValueEur": num(row.predicted_value, 0),
                "totalScore": num(row.total_score, 1),
                "valuePercentile": num(row.value_percentile, 1),
                "stylePercentile": num(row.style_percentile, 1),
                "formPercentile": num(row.form_percentile, 1),
                "reliabilityPercentile": num(row.reliability_percentile, 1),
                "flags": None if pd.isna(row.flags) else str(row.flags),
            }
        )

    kept = metrics["kept_model"].iloc[0]
    time_split = metrics.loc[metrics["model"].eq(kept) & metrics["split"].str.contains("2025-26")].iloc[0]
    examples = {}
    for key, name in (("palhinha", "João Palhinha"), ("porro", "Pedro Porro")):
        match = next(player for player in players if player["name"] == name and player["season"] == POOL)
        examples[key] = {"id": match["id"], "name": match["name"], "style": match["style"], "position": match["position"], "team": match["team"], "age": match["age"], "marketValueEur": match["marketValueEur"]}

    meta = {
        "playersAnalyzed": int(vectors["player"].nunique()),
        "seasons": int(vectors["season"].nunique()),
        "leagues": int(pool["league"].nunique()),
        "poolSeason": season_label(POOL),
        "poolPlayers": int(pool["id"].nunique()),
        "r2": round(float(time_split["r2"]), 2),
        "typicalMissPct": round(float(time_split["median_abs_pct_error"])),
        "headlines": {
            "picksMedianPct": round(headlines["picks_median_pct"], 1),
            "ageMatchedPct": round(headlines["age_matched_pct"], 1),
            "beatSharePct": round(headlines["beat_share"] * 100),
            "signingsMedianPct": round(headlines["signings_median_pct"], 1),
        },
        "examples": examples,
        "featureLabels": {feature: FEATURE_LABELS.get(feature, feature.replace("_", " ")) for feature in features},
        "roles": ROLE,
    }

    total = 0
    total += write("players.json", players)
    total += write("search.json", search)
    total += write("neighbors.json", neighbours)
    total += write("clusters.json", cluster_rows)
    total += write("pca.json", pca)
    total += write("predictions.json", {"points": scatter, "deciles": decile_rows})
    total += write("backtest.json", {"windows": window_rows, "picks": pick_rows, "signings": signing_rows})
    total += write("needs.json", need_rows)
    total += write("shortlist.json", short_rows)
    total += write("meta.json", meta)
    print(f"{'TOTAL':24} {total / 1024:8.1f} KB  ({total / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
