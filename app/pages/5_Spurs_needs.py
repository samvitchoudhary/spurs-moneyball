import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Spurs needs", page_icon="⚽", layout="wide")

from utils import ROLE, chart_layout, footer, load_needs, prepare_page

prepare_page("Where Spurs need to recruit")
st.markdown(
    "The squad is whoever FBref lists at Tottenham in 2026-27. "
    "Quality uses 2025-26, because this season is only a handful of matches. "
    "The comparison is the six Premier League clubs with the highest squad value, Spurs excluded."
)

needs = load_needs().sort_values("need_score", ascending=True)
needs["role"] = needs["position_group"].map(ROLE)
colors = ["#132257" if score > 0 else "#8d8d8d" for score in needs["need_score"]]
fig = go.Figure(go.Bar(y=needs["role"], x=needs["need_score"], orientation="h", marker_color=colors, text=needs["need_score"].map(lambda value: f"{value:.2f}"), textposition="outside"))
fig.update_xaxes(title="Need score")
chart_layout(fig, "Roles furthest behind the six richest squads")
st.plotly_chart(fig, width="stretch")
st.caption(
    "A bar to the right is a stronger case for recruiting there. "
    "Quality, output, and depth are z-scores across the five roles. Age and contract are the raw minute share times two, so a small share stays small."
)

ordered = load_needs().sort_values("need_score", ascending=False)
components = [
    ("z_quality", "Quality 35%"),
    ("z_output", "Output 25%"),
    ("z_depth", "Depth 20%"),
    ("z_age", "Age 10%"),
    ("z_contract", "Contract 10%"),
]
z = ordered[[column for column, _label in components]].to_numpy()
text = [[f"{value:.2f}" for value in row] for row in z]
heat = go.Figure(
    go.Heatmap(
        z=z,
        x=[label for _column, label in components],
        y=ordered["position_group"].map(ROLE),
        colorscale="RdBu_r",
        zmid=0,
        text=text,
        texttemplate="%{text}",
        colorbar=dict(title="More need"),
    )
)
chart_layout(heat, "What is driving each score")
st.plotly_chart(heat, width="stretch")
st.caption(
    "Red pushes a role up the list. Blue means Spurs are in better shape than the other roles on that check. "
    "Age and contract are not z-scores. They are the share of minutes, times two."
)

st.subheader("Verdict")
st.markdown(
    "**Striker — a penalty-box striker.** Solanke, Tel and Richarlison all drop deep. "
    "Nobody in the group is a penalty-box striker, and nobody is a pressing striker either. "
    "The output profile is the loudest gap: the minute-weighted 2025-26 rates sit at the 9th percentile. "
    "The model puts Solanke near €30m, against about €58m for the benchmark pair. "
    "Marmoush has the most striker minutes this season, but 700 minutes last season is under the line the model uses, so he has no prediction. "
    "Depth is not the problem."
)
st.markdown(
    "**Full-back — a defensive full-back.** Porro is an attacking wing-back, Robertson is a holding full-back, "
    "and Udogie sits in the quieter holding group. Robertson is 32 and has played most of the full-back minutes, "
    "so 56% of those minutes are aged 30 or older. Robertson and Porro average about €23m on the model, against about €41m for the benchmark pair."
)
st.markdown(
    "Wide attacker falls below zero once Sávio's minutes are counted there. "
    "Central midfield already has every style. Centre-back is the lowest score: van Hecke and van de Ven still outscore the benchmark pair."
)

footer()
