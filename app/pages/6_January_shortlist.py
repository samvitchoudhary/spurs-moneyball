import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="January shortlist", page_icon="⚽", layout="wide")

from utils import chart_layout, flag_badges, footer, load_shortlist, load_vectors, player_card, prepare_page, show_cards

prepare_page("January shortlist")
st.info(
    "These scores rank candidates for a human scout to review. They are not recommendations on their own. "
    "The names still need the manual checks in data/manual_checks.csv: a current Transfermarkt value, whether a deal is realistic, and a keep or drop."
)

shortlist = load_shortlist()
vectors = load_vectors()
latest = vectors.sort_values("season").drop_duplicates(["player", "birth_year"], keep="last")
meta = latest.set_index("player")

striker, left_back = st.tabs(["Striker", "Left-back"])
pages = {"Striker": ("ST", "Penalty-box striker"), "Left-back": ("FB", "Left-back, defensive full-back preferred")}


def draw(need: str, title: str) -> None:
    frame = shortlist.loc[shortlist["need"].eq(need)].sort_values("rank")
    long_rows = []
    for row in frame.itertuples(index=False):
        long_rows.extend(
            [
                {"Player": row.player, "Part": "Value", "Points": 0.40 * row.value_percentile},
                {"Player": row.player, "Part": "Style", "Points": 0.30 * row.style_percentile},
                {"Player": row.player, "Part": "Form", "Points": 0.20 * row.form_percentile},
                {"Player": row.player, "Part": "Reliability", "Points": 0.10 * row.reliability_percentile},
            ]
        )
    import pandas as pd

    parts = pd.DataFrame(long_rows)
    order = frame["player"].tolist()
    fig = go.Figure()
    colors = {"Value": "#132257", "Style": "#6B4C9A", "Form": "#C45C26", "Reliability": "#1F7A4D"}
    for part, color in colors.items():
        chunk = parts.loc[parts["Part"].eq(part)].set_index("Player").loc[order]
        fig.add_bar(name=part, y=order, x=chunk["Points"], orientation="h", marker_color=color)
    fig.update_layout(barmode="stack", yaxis=dict(autorange="reversed"))
    fig.update_xaxes(title="Weighted points")
    chart_layout(fig, title)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Each bar is the score. Value is 40% of its percentile, style 30%, form 20%, reliability 10%. "
        "A form block of 10 points is the neutral 50 given to anyone with under 450 minutes this season."
    )
    cards = []
    for row in frame.itertuples(index=False):
        info = meta.loc[row.player] if row.player in meta.index else None
        if isinstance(info, pd.DataFrame):
            info = info.iloc[-1]
        nationality = "" if info is None else info.nationality
        position = row.need if info is None else info.position_group
        cards.append(
            player_card(
                row.player,
                row.club_now,
                row.age_at_window,
                nationality,
                position,
                row.target_style if row.style_percentile >= 70 else "Style fit is not the reason he ranks",
                row.actual_value,
                note=f"#{int(row.rank)} · score {row.total_score:.0f} · value {row.value_percentile:.0f} · style {row.style_percentile:.0f} · form {row.form_percentile:.0f} · reliability {row.reliability_percentile:.0f}",
            )
            + flag_badges(row.flags)
        )
    show_cards(cards)


with striker:
    st.markdown("Penalty-box strikers, aged 27 or under on 1 January 2027, with 900 minutes in 2025-26.")
    draw("ST", "Striker score, split into its four parts")
with left_back:
    st.markdown("Transfermarkt left-backs, same age cut. The style part is fit to a defensive full-back.")
    draw("FB", "Left-back score, split into its four parts")

footer()
