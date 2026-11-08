import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Value model", page_icon="⚽", layout="wide")

from utils import (
    ROLE,
    apply_euro_log_ticks,
    chart_layout,
    footer,
    humanize_model_sentence,
    load_metrics,
    load_predictions,
    model_label,
    money,
    prepare_page,
)

prepare_page("Value model")
st.markdown(
    "The model prices a season from age, role, team strength, and basic per-90 stats. "
    "A positive gap means the stats implied a higher fee than the market."
)

metrics = load_metrics()
show = metrics.loc[:, ["model", "split", "r2", "median_abs_pct_error"]].copy()
show["model"] = show["model"].map(model_label)
show["R²"] = show["r2"].map(lambda value: f"{value:.2f}")
show["Typical miss"] = show["median_abs_pct_error"].map(lambda value: f"{value:.0f}% of the fee")
show = show.rename(columns={"model": "Model", "split": "Test"}).drop(columns=["r2", "median_abs_pct_error"])

predictions = load_predictions()
season = predictions.loc[predictions["season"].eq(2526)].copy()
fig = px.scatter(
    season,
    x="actual_value",
    y="predicted_value",
    hover_name="player",
    hover_data={"team": True, "position_group": True, "actual_value": False, "predicted_value": False},
    opacity=0.75,
)
fig.update_traces(marker=dict(color="#132257", size=7))
upper = float(max(season["actual_value"].max(), season["predicted_value"].max()))
fig.add_trace(
    go.Scatter(
        x=[1e5, upper],
        y=[1e5, upper],
        mode="lines",
        name="Predicted = actual",
        line=dict(color="#C45C26", dash="dash"),
    )
)
fig.update_xaxes(type="log", title="Market value")
fig.update_yaxes(type="log", title="Model value")
chart_layout(fig, "2025-26 predicted fee against the market")
apply_euro_log_ticks(fig)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Both axes are on a log scale, so a move from €2m to €4m is the same distance as €20m to €40m. "
    "Points above the line were priced higher by the stats than by the market. These are out-of-fold predictions: the model did not train on that player."
)

deciles = (
    season.groupby("value_decile", as_index=False)
    .agg(players=("player", "size"), mean_log_gap=("log_gap", "mean"), low=("actual_value", "min"), high=("actual_value", "max"))
    .sort_values("value_decile")
)
deciles["label"] = deciles.apply(lambda row: f"D{int(row.value_decile)}", axis=1)
bars = go.Figure(go.Bar(x=deciles["label"], y=deciles["mean_log_gap"], marker_color="#132257", hovertext=deciles.apply(lambda row: f"{money(row.low)} to {money(row.high)}", axis=1)))
bars.update_yaxes(title="Mean log gap")
chart_layout(bars, "Cheap fees were over-predicted, expensive fees under-predicted")
st.plotly_chart(bars, width="stretch")
st.caption(
    "Each bar is a tenth of the 2025-26 fee range, cheapest on the left. "
    "A positive bar means the model aimed high for that price band. The shortlist uses the gap left after this pattern is removed."
)

with st.expander("Which model was kept"):
    st.dataframe(show, width="stretch", hide_index=True)
    st.caption(humanize_model_sentence(metrics["reason"].iloc[0]))

st.subheader("Largest calibrated gaps")
role = st.selectbox("Position group", ["All", *ROLE], format_func=lambda key: "All roles" if key == "All" else ROLE[key])
max_age = st.slider("Max age", 17, 40, 27)
min_value = st.number_input("Minimum market value, €m", min_value=0.0, value=2.0, step=0.5)

ranked = season.loc[season["age"].le(max_age) & season["actual_value"].ge(min_value * 1_000_000)].copy()
if role != "All":
    ranked = ranked.loc[ranked["position_group"].eq(role)]
ranked = ranked.sort_values(["calibrated_gap", "player"], ascending=[False, True]).head(25)
table = pd.DataFrame(
    {
        "Player": ranked["player"],
        "Club": ranked["team"],
        "Role": ranked["position_group"].map(ROLE),
        "Age": ranked["age"].round(0).astype("Int64"),
        "Market": ranked["actual_value"].map(money),
        "Model": ranked["predicted_value"].map(money),
        "Calibrated gap": ranked["calibrated_gap"].map(lambda value: f"{value:+.2f}"),
    }
)
if table.empty:
    role_text = "in any role" if role == "All" else f"listed as {ROLE[role].lower()}"
    st.info(
        f"No 2025-26 player is {role_text}, aged {int(max_age)} or under, "
        f"and valued at €{min_value:.1f}m or more."
    )
else:
    st.dataframe(table, width="stretch", hide_index=True)
st.caption(
    "Ranked by calibrated gap, the log gap minus the average gap in that player's fee band. "
    "A larger number means the stats implied more value than players with a similar fee. This is a watch list, not a bid list."
)

footer()
