import streamlit as st

st.set_page_config(page_title="Moneyball for Spurs", page_icon="⚽", layout="wide")

from utils import footer, load_metrics, load_picks, load_vectors, model_label, percent_change, prepare_page

prepare_page("Moneyball for Spurs")
st.markdown(
    "Can a model find undervalued players who fit what Tottenham needs this January?"
)

metrics = load_metrics()
kept = metrics["kept_model"].iloc[0]
time_split = metrics.loc[
    metrics["model"].eq(kept) & metrics["split"].str.contains("2025-26")
].iloc[0]
picks = load_picks()
scored = picks["log_value_change"].dropna()
players = load_vectors()["player"].nunique()

st.subheader("What the work found")
st.markdown(
    "The value model did not find a reliable edge over the market. "
    f"Across the backtest, the alternative picks' median change in value was {percent_change(scored.median())}, "
    "and fewer than half of them beat players of a similar age in the same role. "
    "The squad work points to two January needs: a penalty-box striker, and a left-back to follow Robertson."
)

one, two, three = st.columns(3)
one.metric("Players analyzed", f"{players:,}")
two.metric("2025-26 R²", f"{time_split['r2']:.2f}")
three.metric("Picks' median change", percent_change(scored.median()))
st.caption(
    f"R² is {model_label(kept)} on the 2025-26 season it never trained on. "
    f"Its typical miss on that season was {time_split['median_abs_pct_error']:.0f}% of the fee. "
    "Picks' median change is the median market-value change for the model's alternative picks. "
    "+0% is a measured median of zero, not a missing result."
)

st.subheader("Walk through it")
links = [
    ("pages/1_Similarity.py", "Similarity explorer", "Find players with a similar per-90 profile."),
    ("pages/2_Playing_styles.py", "Playing styles", "See the action clusters, and where Spurs sit."),
    ("pages/3_Value_model.py", "Value model", "Compare predicted fees with the market."),
    ("pages/4_Backtest.py", "Backtest", "What the model would have bought, and what happened."),
    ("pages/5_Spurs_needs.py", "Spurs needs", "Which roles are short, and why."),
    ("pages/6_January_shortlist.py", "January shortlist", "The striker and left-back lists for a scout to review."),
]
for path, label, blurb in links:
    st.page_link(path, label=label, help=blurb)

footer()
