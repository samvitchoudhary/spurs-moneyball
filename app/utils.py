"""Shared loading, formatting, and player cards for the dashboard."""

from __future__ import annotations

import inspect
import re
import sys
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA = ROOT / "app_data"
NAVY = "#132257"
FOOTER = (
    "Stats: FBref (basic stats). Market values: Transfermarkt via transfermarkt-datasets "
    "(June 2026 snapshot). Personal student project, not affiliated with Tottenham Hotspur."
)
ROLE = {
    "CB": "Centre-back",
    "FB": "Full-back",
    "CM": "Central midfield",
    "AM_W": "Wide attacker",
    "ST": "Striker",
    "GK": "Goalkeeper",
}
POSITION_COLORS = {
    "CB": "#132257",
    "FB": "#1F7A4D",
    "CM": "#C45C26",
    "AM_W": "#6B4C9A",
    "ST": "#B03A2E",
    "GK": "#5C6B73",
}
FEATURE_LABELS = {
    "goals_per90": "Goals",
    "non_penalty_goals_per90": "Non-penalty goals",
    "assists_per90": "Assists",
    "shots_per90": "Shots",
    "shots_on_target_per90": "Shots on target",
    "crosses_per90": "Crosses",
    "tackles_won_per90": "Tackles won",
    "interceptions_per90": "Interceptions",
    "fouls_committed_per90": "Fouls",
    "fouls_drawn_per90": "Fouls won",
    "offsides_per90": "Offsides",
    "shot_accuracy": "Shot accuracy",
    "goals_per_shot": "Goals per shot",
}
# Football codes that are not already ISO alpha-2.
FIFA_TO_ISO = {
    "ENG": "GB",
    "SCO": "GB",
    "WAL": "GB",
    "NIR": "GB",
    "GER": "DE",
    "SUI": "CH",
    "CRO": "HR",
    "POR": "PT",
    "DEN": "DK",
    "NED": "NL",
    "GRE": "GR",
    "CZE": "CZ",
    "URU": "UY",
    "RSA": "ZA",
    "CHI": "CL",
    "PAR": "PY",
    "KSA": "SA",
    "UAE": "AE",
    "CRC": "CR",
    "IRL": "IE",
    "ALG": "DZ",
    "MAR": "MA",
    "SEN": "SN",
    "CIV": "CI",
    "NGA": "NG",
    "GHA": "GH",
    "MLI": "ML",
    "CMR": "CM",
    "GUI": "GN",
    "BIH": "BA",
    "SRB": "RS",
    "UKR": "UA",
    "TUR": "TR",
    "ALB": "AL",
    "JPN": "JP",
    "KOR": "KR",
    "USA": "US",
    "COL": "CO",
    "ARG": "AR",
    "BRA": "BR",
    "ESP": "ES",
    "FRA": "FR",
    "ITA": "IT",
    "BEL": "BE",
    "AUT": "AT",
    "POL": "PL",
    "SWE": "SE",
    "NOR": "NO",
    "HUN": "HU",
    "ROU": "RO",
    "SVK": "SK",
    "SVN": "SI",
    "FIN": "FI",
    "ISL": "IS",
    "EGY": "EG",
    "TUN": "TN",
    "AUS": "AU",
    "CAN": "CA",
    "MEX": "MX",
    "ECU": "EC",
    "PER": "PE",
    "JAM": "JM",
    "CHN": "CN",
    "RUS": "RU",
    "GEO": "GE",
    "ARM": "AM",
    "ISR": "IL",
    "CPV": "CV",
    "EQG": "GQ",
    "CGO": "CG",
    "COD": "CD",
    "TOG": "TG",
    "BFA": "BF",
    "GAM": "GM",
    "ZAM": "ZM",
    "ZIM": "ZW",
    "MOZ": "MZ",
    "ANG": "AO",
    "MTN": "MR",
    "SLE": "SL",
    "LBR": "LR",
    "HAI": "HT",
    "HON": "HN",
    "PAN": "PA",
    "VEN": "VE",
    "BOL": "BO",
    "TRI": "TT",
    "GUY": "GY",
    "SUR": "SR",
    "NZL": "NZ",
    "IND": "IN",
    "IDN": "ID",
    "THA": "TH",
    "VIE": "VN",
    "MAS": "MY",
    "PHI": "PH",
    "IRN": "IR",
    "IRQ": "IQ",
    "KAZ": "KZ",
    "UZB": "UZ",
    "AZE": "AZ",
    "MKD": "MK",
    "MNE": "ME",
    "LUX": "LU",
    "MLT": "MT",
    "CYP": "CY",
    "EST": "EE",
    "LAT": "LV",
    "LTU": "LT",
    "BLR": "BY",
    "MDA": "MD",
    "BUL": "BG",
    "AND": "AD",
    "FRO": "FO",
    "LIE": "LI",
    "KOS": "XK",
}
SUBDIVISION_FLAGS = {
    "ENG": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "SCO": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
    "WAL": "\U0001F3F4\U000E0067\U000E0062\U000E0077\U000E006C\U000E0073\U000E007F",
}


def prepare_page(title: str) -> None:
    _install_chart_display()
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.25rem; padding-bottom: 4rem; max-width: 1180px;}
        [data-testid="stHeading"] h1 {
            color: #132257 !important;
            font-size: 2.05rem !important;
            line-height: 1.15 !important;
            font-weight: 650 !important;
            letter-spacing: -0.02em;
        }
        [data-testid="stHeading"] h2,
        [data-testid="stHeading"] h3 {
            color: #132257 !important;
            letter-spacing: -0.015em;
        }
        [data-testid="stHeading"] h2 {font-size: 1.45rem !important;}
        [data-testid="stHeading"] h3 {font-size: 1.2rem !important;}
        .ppdp-chart-title {
            color: #132257;
            font-size: 1.05rem;
            font-weight: 650;
            line-height: 1.3;
            margin: 0.85rem 0 0.1rem 0;
        }
        @media (max-width: 800px) {
            [data-testid="stHeading"] h1 {
                font-size: 1.65rem !important;
                line-height: 1.2 !important;
            }
            [data-testid="stHeading"] h2 {font-size: 1.28rem !important;}
        }
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p {
            color: #3A4256 !important;
        }
        div[data-testid="stMetric"] {
            background: #F4F5F7;
            border: 1px solid #E6E8EE;
            border-radius: 12px;
            padding: 12px 16px;
        }
        [data-testid="stMetricValue"] {
            color: #132257;
            font-weight: 650;
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] p {
            color: #3A4256 !important;
        }
        a[data-testid="stSidebarNavLink"][aria-current="page"] {
            background: #E4E9F5 !important;
            border-radius: 8px;
            box-shadow: inset 3px 0 0 #132257;
        }
        a[data-testid="stSidebarNavLink"][aria-current="page"] p {
            color: #132257 !important;
            font-weight: 650 !important;
        }
        a[data-testid="stSidebarNavLink"]:focus-visible,
        button:focus-visible,
        input:focus-visible,
        [role="tab"]:focus-visible {
            outline: 2px solid #132257 !important;
            outline-offset: 2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title(title)


def footer() -> None:
    st.divider()
    st.caption(FOOTER)


def money(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    sign = "−" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000:
        return f"{sign}€{number / 1_000_000:.1f}m"
    if number >= 1_000:
        return f"{sign}€{number / 1_000:.0f}k"
    return f"{sign}€{number:.0f}"


def season_label(season) -> str:
    text = str(int(season))
    return f"20{text[:2]}-{text[2:]}"


def percent_change(log_change) -> str:
    if log_change is None or pd.isna(log_change):
        return "—"
    return f"{(np.exp(float(log_change)) - 1) * 100:+.0f}%"


def flag_emoji(nationality) -> str:
    if nationality is None or pd.isna(nationality):
        return ""
    code = str(nationality).strip().upper()
    if code in SUBDIVISION_FLAGS:
        return SUBDIVISION_FLAGS[code]
    iso = FIFA_TO_ISO.get(code, code if len(code) == 2 and code.isalpha() else "")
    if len(iso) != 2 or not iso.isalpha() or any(ord(character) > 127 for character in iso):
        return ""
    return "".join(chr(0x1F1E6 + ord(character) - ord("A")) for character in iso)


def initials(name: str) -> str:
    parts = [part for part in str(name).replace("-", " ").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def player_card(
    name: str,
    club: str = "",
    age=None,
    nationality: str = "",
    position: str = "",
    style: str = "",
    market_value=None,
    note: str = "",
    figure: str = "",
    badges: str = "",
) -> str:
    color = POSITION_COLORS.get(str(position), NAVY)
    age_text = f"{int(round(float(age)))}" if age is not None and not pd.isna(age) else "—"
    role = ROLE.get(str(position), str(position) or "—")
    style_text = str(style) if style is not None and not pd.isna(style) and str(style) else "Style unknown"
    flag = flag_emoji(nationality)
    note_html = f"<div style='margin-top:6px;color:#132257;font-weight:600'>{escape(note)}</div>" if note else ""
    figure_html = (
        f"<div style='margin-left:auto;text-align:right;flex:0 0 auto;'>"
        f"<div style='font-weight:700;color:#132257;font-size:1.45rem;line-height:1;'>{escape(figure)}</div>"
        f"</div>"
        if figure
        else ""
    )
    badge_html = f"<div style='margin-top:8px'>{badges}</div>" if badges else ""
    return f"""
    <div style="display:flex;gap:12px;align-items:flex-start;border:1px solid #E6E8EE;border-radius:14px;padding:12px 14px;background:#fff;margin-bottom:10px;min-height:92px;">
      <div style="flex:0 0 52px;width:52px;height:52px;border-radius:50%;background:{color};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;letter-spacing:0.03em;">{escape(initials(name))}</div>
      <div style="min-width:0;flex:1">
        <div style="font-weight:700;color:#132257;font-size:1.02rem;">{escape(str(name))} {flag}</div>
        <div style="color:#5c6578;font-size:0.9rem;">{escape(str(club or '—'))} · {age_text}</div>
        <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
          <span style="background:{color};color:#fff;border-radius:999px;padding:2px 8px;font-size:0.75rem;">{escape(role)}</span>
          <span style="background:#F4F5F7;color:#132257;border-radius:999px;padding:2px 8px;font-size:0.75rem;">{escape(style_text)}</span>
          <span style="color:#132257;font-weight:650;font-size:0.9rem;">{escape(money(market_value))}</span>
        </div>
        {note_html}
        {badge_html}
      </div>
      {figure_html}
    </div>
    """


def show_cards(cards: list[str], per_row: int = 2) -> None:
    if not cards:
        st.info("No players match these filters.")
        return
    for start in range(0, len(cards), per_row):
        columns = st.columns(per_row)
        for column, card in zip(columns, cards[start : start + per_row]):
            column.markdown(card, unsafe_allow_html=True)


def readable_flag_text(text) -> str:
    """Add the space after a comma when the stored flag text omitted one."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    return re.sub(r",(?=\S)", ", ", str(text))


def same_side_applies(position_group: str) -> bool:
    """The flank filter only changes full-back and wide-attacker results."""
    return str(position_group) in {"FB", "AM_W"}


def similarity_empty_message(max_age: float, max_value_m: float, leagues: list[str], same_side: bool) -> str:
    parts = [f"aged {int(max_age)} or under"]
    if max_value_m:
        parts.append(f"valued at €{max_value_m:.0f}m or less")
    if same_side:
        parts.append("on the same side")
    league_text = ", ".join(leagues) if leagues else "no selected league"
    return f"No player in {league_text} is {', '.join(parts)}."


def flag_badges(text) -> str:
    text = readable_flag_text(text)
    if not str(text).strip():
        return "<span style='color:#5c6578'>No flags</span>"
    colors = {
        "Hard to buy": ("#FDECEC", "#8C2F2F"),
        "Cheaper now": ("#E7F6EE", "#1F7A4D"),
        "No adaptation": ("#E8EEF8", "#132257"),
    }
    pieces = []
    for sentence in str(text).split(". "):
        sentence = sentence.strip().rstrip(".")
        if not sentence:
            continue
        background, color = ("#F4F5F7", "#132257")
        for key, palette in colors.items():
            if sentence.startswith(key):
                background, color = palette
        pieces.append(
            f"<span style='display:inline-block;background:{background};color:{color};border-radius:999px;padding:3px 8px;margin:2px 4px 2px 0;font-size:0.8rem;'>{escape(sentence)}</span>"
        )
    return "".join(pieces)


# Streamlit's Plotly theme paints series with placeholder colors (#000001…).
# The browser swaps those for its default blue/red palette unless the figure
# already uses real colors. These are the dashboard series colors.
CHART_COLORS = ["#132257", "#C45C26", "#1F7A4D", "#6B4C9A", "#B03A2E", "#5C6B73"]
_PLACEHOLDER_COLORS = {f"#{index:06d}": CHART_COLORS[(index - 1) % len(CHART_COLORS)] for index in range(1, 11)}
_OURS = {color.lower() for color in CHART_COLORS}
# High values (more need) are terracotta. Low values are navy. Same direction as RdBu_r.
DIVERGING_SCALE = [
    [0.0, "#132257"],
    [0.2, "#5C73A8"],
    [0.4, "#C5CEE3"],
    [0.5, "#F7F6F4"],
    [0.6, "#F3D2C2"],
    [0.8, "#D4784A"],
    [1.0, "#C45C26"],
]
_CODE_LABEL = re.compile(r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+")


def _solid_color(value) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _recolor(container, mapping: dict[str, str]) -> None:
    if container is None:
        return
    current = _solid_color(getattr(container, "color", None))
    if current is None or current.lower() in _OURS:
        return
    mapped = mapping.get(current.lower())
    if mapped:
        container.color = mapped


def _apply_series_palette(fig: go.Figure) -> None:
    """Replace Streamlit placeholder series colors, leaving explicit ones."""
    for trace in fig.data:
        _recolor(getattr(trace, "marker", None), _PLACEHOLDER_COLORS)
        _recolor(getattr(trace, "line", None), _PLACEHOLDER_COLORS)


def _apply_diverging_scale(fig: go.Figure) -> None:
    # Plotly expands a named scale such as RdBu_r into RGB stops before we see it,
    # so the shared layout owns the diverging palette for every heatmap.
    for trace in fig.data:
        if getattr(trace, "type", None) == "heatmap":
            trace.colorscale = DIVERGING_SCALE


def _readable_axis_title(text: str) -> str:
    cleaned = str(text).strip()
    if cleaned in {"x", "y"}:
        return ""
    if cleaned in FEATURE_LABELS or _CODE_LABEL.fullmatch(cleaned):
        return feature_label(cleaned)
    return cleaned


def _humanize_labels(fig: go.Figure) -> None:
    for axis_name in ("xaxis", "yaxis"):
        axis = getattr(fig.layout, axis_name, None)
        title = getattr(axis, "title", None) if axis is not None else None
        text = getattr(title, "text", None) if title is not None else None
        if text:
            axis.title.text = _readable_axis_title(str(text))
    for trace in fig.data:
        name = getattr(trace, "name", None)
        if isinstance(name, str) and (_CODE_LABEL.fullmatch(name) or name in FEATURE_LABELS):
            trace.name = feature_label(name)


def _room_for_outside_bar_labels(fig: go.Figure) -> None:
    values: list[float] = []
    for trace in fig.data:
        if getattr(trace, "type", None) != "bar" or getattr(trace, "orientation", None) != "h":
            continue
        if getattr(trace, "textposition", None) not in {"outside", "auto"}:
            continue
        trace.cliponaxis = False
        raw = getattr(trace, "x", None)
        if raw is None:
            continue
        for value in list(raw):
            if isinstance(value, (int, float)) and value == value:
                values.append(float(value))
    if not values or fig.layout.xaxis.range is not None:
        return
    low, high = min(values), max(values)
    span = max(high - low, abs(high), abs(low), 1.0)
    # Outside labels on a negative bar extend toward the category names.
    fig.update_xaxes(range=[low - span * 0.42, high + span * 0.28])


def chart_layout(fig: go.Figure, title: str) -> go.Figure:
    """Shared chart chrome: palette, readable labels, and room for the legend."""
    _apply_series_palette(fig)
    _apply_diverging_scale(fig)
    _humanize_labels(fig)
    _room_for_outside_bar_labels(fig)
    named = [trace.name for trace in fig.data if getattr(trace, "name", None) and trace.showlegend is not False]
    # Phone width fits about two legend items per row. Leave that room up front
    # so a wrapped legend does not sit on the axis title.
    legend_rows = 0 if not named else max(1, (len(named) + 1) // 2)
    category_count = _string_category_count(fig)
    # Vertical category labels need their own band, under the legend.
    # A shallow angle stacks "Summer 2023" on the next window at phone width.
    bottom = 56 + legend_rows * 22 + (88 if category_count >= 5 else 0)
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=NAVY, size=17, family="Source Sans, Arial, sans-serif"),
            x=0,
            xanchor="left",
            xref="paper",
            yref="container",
            y=1,
            yanchor="top",
            pad=dict(t=2, b=6, l=0, r=0),
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#1C2333", family="Source Sans, Arial, sans-serif", size=13),
        colorway=CHART_COLORS,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.42 if category_count >= 5 else -0.16,
            x=0,
            xanchor="left",
            title_text="",
            font=dict(size=12, color="#1C2333"),
            bgcolor="rgba(0,0,0,0)",
            tracegroupgap=8,
        ),
        margin=dict(l=56, r=28, t=52, b=bottom),
        hoverlabel=dict(bgcolor="white", font_size=13, font_color="#1C2333"),
    )
    axis = dict(showgrid=True, gridcolor="#E6E8EE", zeroline=False, automargin=True, title_standoff=10)
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    if category_count >= 5:
        fig.update_xaxes(tickangle=-90)
    return fig


def _string_category_count(fig: go.Figure) -> int:
    """How many x labels are words, not a numeric series."""
    if not fig.data:
        return 0
    raw = getattr(fig.data[0], "x", None)
    if raw is None:
        return 0
    try:
        values = list(raw)
    except TypeError:
        return 0
    if values and all(isinstance(value, str) for value in values):
        return len(values)
    return 0


def _figure_title(figure) -> str:
    title = getattr(getattr(figure, "layout", None), "title", None)
    text = getattr(title, "text", None) if title is not None else None
    return str(text or "").strip()


# Room above the plotting area for zoom and pan. The title itself is drawn
# outside the canvas, so this lane is only for the toolbar.
TOOLBAR_LANE = 36


def lift_chart_title(fig: go.Figure) -> str:
    """Move the title off the canvas and leave a lane for the toolbar."""
    title = _figure_title(fig)
    if not title:
        return ""
    fig.update_layout(title_text="", margin_t=TOOLBAR_LANE)
    return title


def chart_interaction_config(existing: dict | None = None) -> dict:
    """Keep zoom and pan on the chart.

    The toolbar stays visible. A hover-only bar is not something a phone can
    discover, and hiding the bar removed pan and zoom entirely. Titles are
    rendered above the canvas, so the bar sits in the top lane instead of on
    the title. A caller that already chose a mode keeps it.
    """
    config = dict(existing or {})
    config.setdefault("displayModeBar", True)
    return config


def _install_chart_display() -> None:
    """Show the chart title above the canvas and keep the Plotly toolbar.

    Called from prepare_page so every page picks it up. The wrap survives reruns.
    """
    current = st.plotly_chart
    if getattr(current, "_ppdp_wrapped", False):
        return
    accepted = set(inspect.signature(current).parameters)

    def show(figure_or_data, *args, **kwargs):
        title = ""
        if hasattr(figure_or_data, "update_layout"):
            title = lift_chart_title(figure_or_data)
        if title:
            st.markdown(f"<p class='ppdp-chart-title'>{escape(title)}</p>", unsafe_allow_html=True)
        kwargs["config"] = chart_interaction_config(kwargs.get("config"))
        if "alt" in accepted and not kwargs.get("alt") and title:
            kwargs["alt"] = title
        return current(figure_or_data, *args, **kwargs)

    show._ppdp_wrapped = True
    st.plotly_chart = show


def feature_label(name: str) -> str:
    return FEATURE_LABELS.get(str(name), str(name).replace("_", " "))


_FEATURE_TOKEN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
MODEL_LABELS = {
    "hist_gradient_boosting": "Histogram gradient boosting",
    "ridge": "Ridge",
}
EURO_LOG_STOPS = (1e5, 1e6, 1e7, 1e8, 2e8)
OUTCOME_ORDER = ("hit", "mixed", "too early", "miss")


def humanize_feature_text(text) -> str:
    """Turn stored feature codes into words. The numbers in the text stay put."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    return _FEATURE_TOKEN.sub(lambda match: feature_label(match.group(0)), str(text))


def model_label(name: str) -> str:
    key = str(name)
    return MODEL_LABELS.get(key, key.replace("_", " "))


def humanize_model_sentence(text: str) -> str:
    sentence = str(text)
    for key, label in MODEL_LABELS.items():
        sentence = sentence.replace(key, label)
    return sentence


def euro_tick(value: float) -> str:
    number = float(value)
    if number >= 1_000_000:
        millions = number / 1_000_000
        text = f"{millions:.0f}" if abs(millions - round(millions)) < 1e-9 else f"{millions:.1f}"
        return f"€{text}m"
    if number >= 1_000:
        return f"€{number / 1_000:.0f}k"
    return f"€{number:.0f}"


def apply_euro_log_ticks(fig: go.Figure) -> None:
    """Label a log fee axis in euros. The plotted values are unchanged."""
    labels = [euro_tick(stop) for stop in EURO_LOG_STOPS]
    fig.update_xaxes(tickmode="array", tickvals=list(EURO_LOG_STOPS), ticktext=labels)
    fig.update_yaxes(tickmode="array", tickvals=list(EURO_LOG_STOPS), ticktext=labels)


def style_sample_ready(row_count: int) -> bool:
    """A two-axis map needs at least two players. Fewer than that is empty data."""
    return int(row_count) >= 2


def percent_point_label(value) -> str:
    """Label a measured zero. Leave other values to the bar, and missing values blank."""
    if value is None or pd.isna(value):
        return ""
    if float(value) == 0.0:
        return "0%"
    return ""


def fully_missing_categories(frame: pd.DataFrame, category: str, columns: list[str]) -> list[str]:
    missing = []
    for name, group in frame.groupby(category, sort=False):
        if group[columns].isna().all().all():
            missing.append(str(name))
    return missing


def backtest_headlines(picks: pd.DataFrame, signings: pd.DataFrame) -> dict[str, float]:
    """The four headline figures already published for the backtest.

    Medians use the log change, then convert to a percent. The beat rate is the
    share of picks with a follow-up value above their own age-matched benchmark.
    """
    role = picks.drop_duplicates(["window", "position_group"])
    compared = picks.loc[picks["log_value_change"].notna()]
    return {
        "picks_median_pct": float((np.exp(picks["log_value_change"].median()) - 1) * 100),
        "age_matched_pct": float((np.exp(role["age_matched_median_log_change"].median()) - 1) * 100),
        "beat_share": float((compared["log_value_change"] > compared["age_matched_median_log_change"]).mean()),
        "signings_median_pct": float((np.exp(signings["log_value_change"].median()) - 1) * 100),
    }


def needs_bottom_to_top(frame: pd.DataFrame) -> pd.DataFrame:
    """Lowest need score first, which Plotly draws at the bottom."""
    return frame.sort_values("need_score", ascending=True)


def category_order(preferred: tuple[str, ...] | list[str], present: list[str]) -> list[str]:
    seen = []
    for item in present:
        text = str(item)
        if text not in seen:
            seen.append(text)
    ordered = [item for item in preferred if item in seen]
    ordered.extend(item for item in seen if item not in preferred)
    return ordered


def highlight_category(fig: go.Figure, categories: list[str], selected: str) -> go.Figure:
    """Shade one category. The bar values are not changed."""
    index = list(categories).index(selected)
    fig.add_vrect(
        x0=index - 0.5,
        x1=index + 0.5,
        fillcolor="rgba(19, 34, 87, 0.08)",
        line_width=0,
        layer="below",
    )
    return fig


def pad_bar_value_axis(fig: go.Figure, lower: float = 8, upper: float = 18) -> None:
    """Leave room above and below vertical bars so an end label is not clipped."""
    values: list[float] = []
    for trace in fig.data:
        if getattr(trace, "type", None) != "bar" or getattr(trace, "orientation", None) == "h":
            continue
        raw = getattr(trace, "y", None)
        if raw is None:
            continue
        for value in list(raw):
            if isinstance(value, (int, float)) and value == value:
                values.append(float(value))
    if not values:
        return
    low, high = min(values), max(values)
    fig.update_yaxes(range=[min(low, 0) - lower, max(high, 0) + upper])


@st.cache_data
def load_vectors() -> pd.DataFrame:
    frame = pd.read_parquet(DATA / "player_vectors.parquet")
    frame["season"] = frame["season"].astype(int)
    return frame


@st.cache_data
def load_clusters() -> pd.DataFrame:
    return pd.read_parquet(DATA / "player_clusters.parquet")


@st.cache_data
def load_cluster_names() -> pd.DataFrame:
    return pd.read_parquet(DATA / "cluster_names.parquet")


@st.cache_data
def load_predictions() -> pd.DataFrame:
    frame = pd.read_parquet(DATA / "value_predictions.parquet")
    frame["season"] = frame["season"].astype(int)
    return frame


@st.cache_data
def load_metrics() -> pd.DataFrame:
    return pd.read_parquet(DATA / "model_metrics.parquet")


@st.cache_data
def load_signings() -> pd.DataFrame:
    return pd.read_parquet(DATA / "backtest_signings.parquet")


@st.cache_data
def load_picks() -> pd.DataFrame:
    return pd.read_parquet(DATA / "backtest_model_picks.parquet")


@st.cache_data
def load_needs() -> pd.DataFrame:
    return pd.read_parquet(DATA / "spurs_needs.parquet")


@st.cache_data
def load_shortlist() -> pd.DataFrame:
    return pd.read_parquet(DATA / "shortlist.parquet")
