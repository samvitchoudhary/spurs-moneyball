"""Shared chart chrome stays readable without changing the numbers."""

from __future__ import annotations

import plotly.graph_objects as go

from app.utils import CHART_COLORS, DIVERGING_SCALE, chart_layout, lift_chart_title


def test_placeholder_colors_share_a_series_and_explicit_colors_stay():
    fig = go.Figure()
    fig.add_bar(name="one", x=["A"], y=[1], marker_color="#000001")
    fig.add_bar(name="same", x=["A"], y=[2], marker_color="#000001")
    fig.add_bar(name="two", x=["A"], y=[3], marker_color="#000002")
    fig.add_bar(name="kept", x=["A"], y=[4], marker_color="#132257")
    chart_layout(fig, "Series")
    assert fig.data[0].marker.color == fig.data[1].marker.color == CHART_COLORS[0]
    assert fig.data[2].marker.color == CHART_COLORS[1]
    assert fig.data[3].marker.color == "#132257"
    assert [value for value in fig.data[0].y] == [1]


def test_legend_sits_below_the_title_and_code_labels_are_readable():
    fig = go.Figure()
    fig.add_bar(name="goals_per90", x=["A"], y=[1])
    fig.update_xaxes(title="x")
    fig.update_yaxes(title="shots_per90")
    fig.update_layout(legend_title_text="cluster_name, squad")
    chart_layout(fig, "Where the profiles differ")
    assert fig.layout.title.text == "Where the profiles differ"
    assert fig.layout.legend.y < 0
    assert fig.layout.legend.title.text in ("", None)
    assert fig.layout.xaxis.title.text in ("", None)
    assert fig.layout.yaxis.title.text == "Shots"
    assert fig.data[0].name == "Goals"
    assert fig.layout.margin.t >= 48
    assert fig.layout.margin.b >= 56
    assert fig.layout.xaxis.automargin is True


def test_horizontal_bar_labels_get_room_past_the_last_value():
    import numpy as np

    fig = go.Figure(
        go.Bar(
            y=["Striker"],
            x=np.array([0.79]),
            orientation="h",
            text=["0.79"],
            textposition="outside",
            marker_color=["#132257"],
        )
    )
    chart_layout(fig, "Need")
    low, high = fig.layout.xaxis.range
    assert low < 0.79 < high
    assert high > 0.79
    assert fig.data[0].x[0] == 0.79
    assert fig.data[0].cliponaxis is False


def test_long_category_labels_stand_upright_and_scatter_axes_do_not():
    windows = go.Figure(go.Bar(
        x=["Summer 2023", "January 2024", "Summer 2024", "January 2025", "Summer 2025", "January 2026"],
        y=[36.9, 0, 100, 4, -28, None],
        name="Model picks",
    ))
    chart_layout(windows, "Did the picks gain value?")
    assert windows.layout.xaxis.tickangle == -90
    assert list(windows.data[0].y)[:5] == [36.9, 0, 100, 4, -28]

    scatter = go.Figure(go.Scatter(x=[-1.2, 0.4, 3.1], y=[0.2, -0.5, 1.4], mode="markers"))
    chart_layout(scatter, "Centre-back styles in 2025-26")
    assert scatter.layout.xaxis.tickangle in (None, 0)
    assert list(scatter.data[0].x) == [-1.2, 0.4, 3.1]


def test_title_can_be_lifted_off_the_canvas_without_changing_the_series():
    fig = go.Figure(go.Bar(x=["Summer 2023"], y=[36.9], name="Model picks"))
    chart_layout(fig, "Did the picks gain value?")
    bottom = fig.layout.margin.b
    assert lift_chart_title(fig) == "Did the picks gain value?"
    assert fig.layout.title.text in ("", None)
    assert fig.layout.margin.b == bottom
    assert list(fig.data[0].y) == [36.9]


def test_diverging_heatmap_keeps_values_and_uses_navy_to_terracotta():
    fig = go.Figure(go.Heatmap(z=[[-1.2, 0.4], [1.5, -0.2]], colorscale="RdBu_r", zmid=0))
    chart_layout(fig, "Drivers")
    rows = [list(row) for row in fig.data[0].z]
    assert rows == [[-1.2, 0.4], [1.5, -0.2]]
    scale = list(fig.data[0].colorscale)
    assert scale[0][1].lower() == DIVERGING_SCALE[0][1].lower()
    assert scale[-1][1].lower() == DIVERGING_SCALE[-1][1].lower()
    assert fig.data[0].zmid == 0
