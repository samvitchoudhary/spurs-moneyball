import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Backtest", page_icon="⚽", layout="wide")

from utils import ROLE, chart_layout, footer, load_picks, load_signings, money, percent_change, prepare_page

prepare_page("Backtest")
st.markdown(
    "Six windows, from summer 2023 to January 2026. For each one the model is trained again "
    "and pointed at players Spurs could have signed that day."
)

signings = load_signings()
picks = load_picks()
windows = ["Summer 2023", "January 2024", "Summer 2024", "January 2025", "Summer 2025", "January 2026"]
window = st.selectbox("Window", windows)

rows = []
for name in windows:
    window_picks = picks.loc[picks["window"].eq(name)]
    window_signings = signings.loc[signings["window"].eq(name), "log_value_change"]
    age_matched = window_picks.drop_duplicates("position_group")["age_matched_median_log_change"]
    rows.append(
        {
            "Window": name,
            "Model picks": np.nan if window_picks["log_value_change"].dropna().empty else (np.exp(window_picks["log_value_change"].median()) - 1) * 100,
            "Spurs signings": np.nan if window_signings.dropna().empty else (np.exp(window_signings.median()) - 1) * 100,
            "Age-matched role": np.nan if age_matched.dropna().empty else (np.exp(age_matched.median()) - 1) * 100,
        }
    )
summary = pd.DataFrame(rows)
long = summary.melt("Window", var_name="Group", value_name="Change")
fig = px.bar(long, x="Window", y="Change", color="Group", barmode="group")
fig.update_yaxes(title="Median change in value, %")
chart_layout(fig, "Did the picks gain value?")
st.plotly_chart(fig, width="stretch")
st.caption(
    "Each bar is a median percentage change in market value over the following year. "
    "Age-matched role is players in the same position, aged 27 or under, valued at €2m or more. "
    "January 2026 has no follow-up value yet."
)

chosen = signings.loc[signings["window"].eq(window)].copy()
st.subheader(f"Spurs signings, {window}")
signing_table = pd.DataFrame(
    {
        "Player": chosen["player"],
        "From": chosen["from_club"],
        "Role": chosen["position_group"].map(ROLE),
        "Fee": chosen["fee_eur"].map(money),
        "Model": chosen["model_value"].map(money),
        "Gap": chosen["log_gap"].map(lambda value: "—" if pd.isna(value) else f"{value:+.2f}"),
        "Outcome": chosen["outcome"],
        "Tier": chosen["signing_tier"],
        "Value change": chosen["log_value_change"].map(percent_change),
    }
)
st.dataframe(signing_table, width="stretch", hide_index=True)
scorable = chosen.loc[chosen["model_value"].notna() & chosen["fee_eur"].gt(0)]
if not scorable.empty:
    fee_fig = go.Figure()
    fee_fig.add_bar(name="Fee", x=scorable["player"], y=scorable["fee_eur"], marker_color="#C45C26")
    fee_fig.add_bar(name="Model", x=scorable["player"], y=scorable["model_value"], marker_color="#132257")
    chart_layout(fee_fig, "Fee paid against the model's value")
    st.plotly_chart(fee_fig, width="stretch")
    st.caption("Only signings the model could score, and only where a fee was paid. A loan has no fee to put on this chart.")

st.subheader("Players the model preferred")
window_picks = picks.loc[picks["window"].eq(window)].sort_values(["position_group", "rank"])
pick_table = pd.DataFrame(
    {
        "Role": window_picks["position_group"].map(ROLE),
        "Rank": window_picks["rank"],
        "Player": window_picks["player"],
        "Club": window_picks["team"],
        "Age": window_picks["age"].round(0),
        "Market": window_picks["value_at_cutoff"].map(money),
        "Model": window_picks["model_value"].map(money),
        "Calibrated gap": window_picks["calibrated_gap"].map(lambda value: "—" if pd.isna(value) else f"{value:+.2f}"),
        "Value change": window_picks["log_value_change"].map(percent_change),
    }
)
st.dataframe(pick_table, width="stretch", hide_index=True)
st.caption("These are the highest calibrated gaps in the roles Spurs actually bought that window, with the same age and value filters as the backtest.")

st.subheader("First-team deals and development deals")
split = (
    signings.groupby(["signing_tier", "outcome"], dropna=False)
    .size()
    .reset_index(name="Arrivals")
)
split_fig = px.bar(split, x="outcome", y="Arrivals", color="signing_tier", barmode="group")
chart_layout(split_fig, "Hits were first-team arrivals")
st.plotly_chart(split_fig, width="stretch")
st.caption(
    "A first-team deal is a fee of at least €10m, or a loan for a player who had already played 900 minutes. "
    "Everything else is a development move. The counts cover all six windows, not only the one selected above."
)

st.subheader("Verdict")
st.markdown(
    "The fairness checks take away the result that looked good. The picks' median value change is still 0%. "
    "Once the comparison is players in the same role who are also 27 or under and cost at least €2m, that benchmark is about −6%, "
    "and 47% of the picks beat the bar in their own window. Spurs' arrivals gained +10%. "
    "Joining a richer club does not explain it: signings who moved up gained +10%, and signings who did not gained +11%. "
    "Among the age-matched players, those who moved up gained slightly less (−8%) than those who stayed (−5%)."
)
st.markdown(
    "All 7 hits were first-team arrivals (7 hits, 7 mixed, 8 misses, 2 too early). "
    "Development moves were 0 hits, 1 mixed and 11 misses. "
    "The sample is small, 13 scored signings out of 38 arrivals, so this is evidence about these windows, not proof."
)

with st.expander("How we prevented leakage"):
    st.markdown(
        """
1. **Training seasons had already ended.** A season ends on 30 June. Summer windows open on 1 July, so the season that just finished is allowed. The new season is not.
2. **January uses the last completed season only.** FBref's season totals include games played after the window. January 2024 is scored on 2022-23, not on 2023-24. January 2025 uses 2023-24. January 2026 uses 2024-25.
3. **Fees are the value on the cutoff, or earlier.** The latest value date in that window's training and scoring tables has to be on or before the day the window opened.
4. **Team strength is rebuilt from those same fees.** It is the leave-one-out average of teammates' values dated on or before the cutoff, not the July 2026 snapshot.
5. **Nothing about how a player did at Spurs is a feature.** Stints at Tottenham are dropped before the features are built. Minutes at Spurs are used only afterwards, as the outcome.

Two further safeguards. Style labels from the 2025-26 clustering are wiped, because those clusters were fit on a season these windows are not allowed to see. And the player being scored is held out of the fit, so the model cannot hand back a fee it just trained on.
        """
    )

footer()
