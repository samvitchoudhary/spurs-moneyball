"""Page presentation helpers. They format labels and do not refit models."""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from app.utils import (
    OUTCOME_ORDER,
    apply_euro_log_ticks,
    backtest_headlines,
    category_order,
    euro_tick,
    fully_missing_categories,
    highlight_category,
    humanize_feature_text,
    humanize_model_sentence,
    load_picks,
    load_signings,
    model_label,
    needs_bottom_to_top,
    pad_bar_value_axis,
    percent_point_label,
    style_sample_ready,
)


def test_feature_text_becomes_words_and_keeps_the_numbers():
    raw = "fouls_committed_per90 (+1.29), shots_per90 (-0.06)"
    assert humanize_feature_text(raw) == "Fouls (+1.29), Shots (-0.06)"
    assert humanize_feature_text(None) == ""


def test_model_names_are_readable_without_changing_the_sentence_numbers():
    assert model_label("hist_gradient_boosting") == "Histogram gradient boosting"
    assert model_label("ridge") == "Ridge"
    sentence = humanize_model_sentence(
        "We keep hist_gradient_boosting. On the 2025-26 season its median absolute error is 30.7% of the fee, against 33.2% for ridge."
    )
    assert "hist_gradient_boosting" not in sentence
    assert "30.7%" in sentence
    assert "33.2%" in sentence
    assert "Histogram gradient boosting" in sentence
    assert sentence.endswith("Ridge.")


def test_euro_ticks_name_the_stops_and_do_not_move_the_points():
    assert euro_tick(1e5) == "€100k"
    assert euro_tick(1e6) == "€1m"
    assert euro_tick(1e8) == "€100m"
    fig = go.Figure(go.Scatter(x=[2_000_000, 58_000_000], y=[1_500_000, 40_000_000]))
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    apply_euro_log_ticks(fig)
    assert list(fig.data[0].x) == [2_000_000, 58_000_000]
    assert "€1m" in list(fig.layout.xaxis.ticktext)
    assert "€10m" in list(fig.layout.yaxis.ticktext)


def test_goalkeeper_sized_sample_is_not_sent_to_a_map():
    assert style_sample_ready(0) is False
    assert style_sample_ready(1) is False
    assert style_sample_ready(2) is True


def test_zero_is_labeled_and_missing_is_not_turned_into_zero():
    assert percent_point_label(0) == "0%"
    assert percent_point_label(0.0) == "0%"
    assert percent_point_label(100) == ""
    assert percent_point_label(float("nan")) == ""
    assert percent_point_label(None) == ""
    summary = pd.DataFrame(
        {
            "Window": ["January 2024", "January 2026"],
            "Model picks": [0.0, math.nan],
            "Spurs signings": [0.0, math.nan],
            "Age-matched role": [-8.0, math.nan],
        }
    )
    assert fully_missing_categories(summary, "Window", ["Model picks", "Spurs signings", "Age-matched role"]) == ["January 2026"]


def test_backtest_headlines_match_the_published_results():
    headlines = backtest_headlines(load_picks(), load_signings())
    assert headlines["picks_median_pct"] == 0
    assert round(headlines["age_matched_pct"], 1) == -6.7
    assert round(headlines["beat_share"] * 100) == 47
    assert round(headlines["signings_median_pct"]) == 10


def test_selected_window_is_shaded_without_changing_the_bars():
    fig = go.Figure(go.Bar(x=["Summer 2023", "January 2026"], y=[36.9, None], name="Model picks"))
    highlight_category(fig, ["Summer 2023", "January 2026"], "January 2026")
    assert fig.layout.shapes[0].x0 == 0.5
    assert fig.layout.shapes[0].x1 == 1.5
    assert list(fig.data[0].y) == [36.9, None]


def test_outcome_order_puts_hits_before_misses_and_keeps_unknowns():
    assert category_order(OUTCOME_ORDER, ["miss", "too early", "hit", "mixed"]) == ["hit", "mixed", "too early", "miss"]
    assert category_order(OUTCOME_ORDER, ["miss", "other"]) == ["miss", "other"]


def test_need_rows_put_the_strongest_case_last_and_keep_the_scores():
    frame = pd.DataFrame({"role": ["Striker", "Centre-back"], "need_score": [0.79, -0.45]})
    ordered = needs_bottom_to_top(frame)
    assert ordered["role"].tolist() == ["Centre-back", "Striker"]
    assert ordered["need_score"].tolist() == [-0.45, 0.79]


def test_vertical_bars_get_headroom_without_changing_height():
    fig = go.Figure(go.Bar(x=["Summer 2024"], y=[100.0], name="Spurs signings"))
    pad_bar_value_axis(fig)
    low, high = fig.layout.yaxis.range
    assert low < 0 < 100 < high
    assert fig.data[0].y[0] == 100
