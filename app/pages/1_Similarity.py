import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Similarity explorer", page_icon="⚽", layout="wide")

from utils import (
    chart_layout,
    feature_label,
    footer,
    load_clusters,
    load_vectors,
    player_card,
    prepare_page,
    same_side_applies,
    season_label,
    show_cards,
    similarity_empty_message,
)
from src.similarity import explain_match, find_similar

prepare_page("Similarity explorer")
st.markdown(
    "Pick a player and see who else has a similar per-90 profile. "
    "The search uses the 2025-26 pool. Filters narrow that pool. They do not change the target."
)

vectors = load_vectors()
clusters = load_clusters()
styles = clusters.set_index(["player", "team"])["cluster_name"]
people = (
    vectors.loc[:, ["player", "birth_year", "team", "season", "nationality"]]
    .drop_duplicates(["player", "birth_year"])
    .sort_values("player")
)
labels = {
    f"{row.player} ({int(row.birth_year)})" if pd.notna(row.birth_year) else row.player: (row.player, row.birth_year)
    for row in people.itertuples(index=False)
}
spurs = vectors.loc[vectors["team"].eq("Tottenham") & vectors["season"].eq(2526)].sort_values("minutes", ascending=False)
default_label = next(iter(labels))
if not spurs.empty:
    top = spurs.iloc[0]
    default_label = f"{top.player} ({int(top.birth_year)})"

choice = st.selectbox("Player", list(labels), index=list(labels).index(default_label))
player, birth_year = labels[choice]
history = vectors.loc[vectors["player"].eq(player) & vectors["birth_year"].eq(birth_year)].sort_values("season")
season = st.selectbox(
    "Season of the target profile",
    history["season"].tolist(),
    index=int(history["season"].tolist().index(2526)) if 2526 in set(history["season"]) else len(history) - 1,
    format_func=season_label,
)

target = history.loc[history["season"].eq(season)].iloc[0]
side_relevant = same_side_applies(target.position_group)
with st.sidebar:
    st.header("Filters")
    max_age = st.slider("Max age", 17, 40, 27)
    max_value_m = st.number_input("Max value, €m (0 = no cap)", min_value=0.0, value=0.0, step=1.0)
    same_side = False
    if side_relevant:
        same_side = st.checkbox("Same side", value=False, help="Left stays left, right stays right.")
    else:
        st.caption("Same side is only for full-backs and wide attackers. It is not applied to this player.")
    league_options = sorted(vectors.loc[vectors["season"].eq(2526), "league"].dropna().unique())
    leagues = st.multiselect("Leagues", league_options, default=league_options)
    st.caption("Clearing every league returns nobody. It does not silently mean all leagues.")
style = styles.get((target.player, target.team), "")
st.markdown(
    player_card(
        target.player,
        target.team,
        target.age,
        target.nationality,
        target.position_group,
        style,
        target.market_value_eur,
        note=f"Target profile, {season_label(season)}",
    ),
    unsafe_allow_html=True,
)

other_year = vectors["player"].eq(player) & vectors["birth_year"].ne(birth_year)
scoped = vectors.loc[~other_year].copy()
if not leagues:
    matches = pd.DataFrame()
else:
    try:
        matches = find_similar(
            player,
            season=str(season),
            n=10,
            cheaper_only=False,
            max_value_eur=None if max_value_m == 0 else max_value_m * 1_000_000,
            max_age=max_age,
            leagues=list(leagues),
            same_side=same_side,
            vectors=scoped,
        )
    except ValueError as error:
        matches = pd.DataFrame()
        st.warning(str(error))

lookup = vectors.loc[vectors["season"].eq(2526)].drop_duplicates(["player", "birth_year"])
cards = []
for match in matches.itertuples(index=False):
    row = lookup.loc[lookup["player"].eq(match.player)]
    info = row.iloc[0] if not row.empty else None
    cards.append(
        player_card(
            match.player,
            match.team,
            match.age if info is None else info.age,
            "" if info is None else info.nationality,
            "" if info is None else info.position_group,
            "" if info is None else styles.get((info.player, info.team), ""),
            match.market_value_eur,
            figure=f"{match.similarity * 100:.0f}%",
        )
    )
st.subheader("Ten closest profiles")
if not leagues or not cards:
    st.info(similarity_empty_message(max_age, max_value_m, list(leagues), same_side))
else:
    show_cards(cards)

if not matches.empty:
    choice_col, chart_col = st.columns([1, 2], vertical_alignment="top")
    with choice_col:
        compared = st.selectbox("Compare features with", matches["player"].tolist())
    try:
        detail = explain_match(player, compared, season="2526", vectors=scoped)
    except ValueError as error:
        detail = None
        st.warning(str(error))
    if detail is not None:
        fig = go.Figure()
        fig.add_bar(name=player, x=detail["feature"].map(feature_label), y=detail["z_a"], marker_color="#132257")
        fig.add_bar(name=compared, x=detail["feature"].map(feature_label), y=detail["z_b"], marker_color="#C45C26")
        chart_layout(fig, "Where the two profiles sit closest, and furthest")
        with chart_col:
            st.plotly_chart(fig, width="stretch")
            st.caption(
                "Each bar is a z-score inside the position group. The three features on the left of the pairing are the closest. "
                "The three on the right are the furthest apart. Zero is an average player in that role."
            )

footer()
