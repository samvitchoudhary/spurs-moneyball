import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Playing styles", page_icon="⚽", layout="wide")

from utils import ROLE, chart_layout, footer, load_cluster_names, load_clusters, load_vectors, prepare_page
from src.cluster import style_matrix

prepare_page("Playing styles")
st.markdown(
    "Styles come from actions: shots, crosses, tackles, fouls, and the rest. "
    "Goals and assists are left out, so a style is how a player plays, not how often the ball went in."
)

group = st.selectbox("Position group", list(ROLE), format_func=lambda key: ROLE[key])
vectors = load_vectors()
names = load_cluster_names()
clusters = load_clusters()


@st.cache_data
def coordinates(position_group: str) -> pd.DataFrame:
    from sklearn.decomposition import PCA

    pool = vectors.loc[vectors["season"].eq(2526) & vectors["position_group"].eq(position_group)].reset_index(drop=True)
    styled, _features = style_matrix(pool, position_group)
    xy = PCA(n_components=2, random_state=42).fit_transform(styled.to_numpy(dtype=float))
    frame = pool.loc[:, ["player", "team", "minutes"]].copy()
    frame["x"] = xy[:, 0]
    frame["y"] = xy[:, 1]
    labels = clusters.loc[clusters["position_group"].eq(position_group), ["player", "team", "cluster_name"]]
    frame = frame.merge(labels, on=["player", "team"], how="left")
    frame["squad"] = frame["team"].eq("Tottenham").map({True: "Tottenham", False: "Everyone else"})
    frame["marker_size"] = frame["team"].eq("Tottenham").map({True: 16, False: 7})
    return frame


points = coordinates(group)
fig = px.scatter(
    points,
    x="x",
    y="y",
    color="cluster_name",
    symbol="squad",
    symbol_map={"Tottenham": "star", "Everyone else": "circle"},
    hover_name="player",
    hover_data={"team": True, "minutes": True, "x": False, "y": False, "squad": False},
    size="marker_size",
)
chart_layout(fig, f"{ROLE[group]} styles in 2025-26")
fig.update_traces(marker=dict(line=dict(width=0.4, color="white")))
st.plotly_chart(fig, width="stretch")
st.caption(
    "Each dot is a player with at least 900 minutes. Stars are Tottenham. "
    "The axes are the two directions that explain the most of the action profile. Nearby dots play in a similar way."
)

definitions = names.loc[names["position_group"].eq(group), ["cluster_name", "size", "high_features", "low_features"]]
definitions = definitions.rename(
    columns={
        "cluster_name": "Style",
        "size": "Players",
        "high_features": "More of",
        "low_features": "Less of",
    }
)
st.subheader("What each style means")
st.dataframe(definitions, width="stretch", hide_index=True)

spurs = points.loc[points["team"].eq("Tottenham"), ["player", "cluster_name", "minutes"]].sort_values("minutes", ascending=False)
spurs = spurs.rename(columns={"player": "Player", "cluster_name": "Style", "minutes": "Minutes"})
st.subheader("Spurs players in this role")
if spurs.empty:
    st.info("No Tottenham player in this role had 900 minutes in 2025-26.")
else:
    st.dataframe(spurs, width="stretch", hide_index=True)
    st.caption("Minutes are the 2025-26 total. A player on the 2026-27 squad who was elsewhere last season is listed under that club.")

footer()
