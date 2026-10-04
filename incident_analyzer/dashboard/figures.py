"""Plotly figure builders. Pure functions of their inputs, no Dash state."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from incident_analyzer.analytics import format_duration
from incident_analyzer.dashboard import theme
from incident_analyzer.schema import CREATED_AT, STATUSES
from incident_analyzer.transitions import FROM_CATEGORY, TO_CATEGORY


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def volume_figure(volume: pd.DataFrame) -> go.Figure:
    if volume.empty:
        return theme.empty_figure("No incidents in range")
    fig = go.Figure()
    for status in STATUSES:
        if not volume[status].any():
            continue
        fig.add_trace(
            go.Scatter(
                x=volume[CREATED_AT],
                y=volume[status],
                name=status.capitalize(),
                mode="lines",
                line=dict(color=theme.STATUS_COLORS[status], width=2, shape="spline", smoothing=0.4),
                hovertemplate="%{y} " + status + "<extra></extra>",
            )
        )
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title=None, rangemode="tozero")
    return theme.apply_layout(fig, height=320)


def category_bar_figure(counts: pd.Series, *, height: int = 360) -> go.Figure:
    if counts.empty:
        return theme.empty_figure("No categorised incidents")
    counts = counts.sort_values()
    fig = go.Figure(
        go.Bar(
            x=counts.values,
            y=counts.index,
            orientation="h",
            marker=dict(color=theme.CATEGORICAL[0], cornerradius=4),
            hovertemplate="%{y}: %{x} incidents<extra></extra>",
        )
    )
    fig.update_layout(bargap=0.35)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, showgrid=False, tickfont=dict(color=theme.TEXT_SECONDARY))
    return theme.apply_layout(fig, height=height, legend=False)


def service_category_heatmap(matrix: pd.DataFrame) -> go.Figure:
    if matrix.empty:
        return theme.empty_figure("No categorised incidents")
    fig = go.Figure(
        go.Heatmap(
            z=matrix.values,
            x=list(matrix.columns),
            y=list(matrix.index),
            colorscale=theme.SEQUENTIAL,
            xgap=2,
            ygap=2,
            hovertemplate="%{y}<br>%{x}: %{z} incidents<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=theme.TEXT_MUTED)),
        )
    )
    fig.update_xaxes(showgrid=False, tickangle=-35)
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color=theme.TEXT_SECONDARY))
    return theme.apply_layout(fig, height=420, legend=False)


def transition_sankey(transitions: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    """Bipartite flow from the current category (left) to the next one (right).

    Link width is the observed transition count, so each link's share of its
    source node is exactly P(next | current).
    """
    observed = transitions[transitions["count"] > 0]
    if observed.empty:
        return theme.empty_figure("Not enough history to estimate transitions", height=440)

    sources = list(dict.fromkeys(observed[FROM_CATEGORY]))
    targets = list(dict.fromkeys(observed[TO_CATEGORY]))
    left = {name: i for i, name in enumerate(sources)}
    right = {name: len(sources) + i for i, name in enumerate(targets)}
    labels = sources + targets
    node_colors = [colors.get(name, theme.NEUTRAL) for name in labels]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=labels,
                color=node_colors,
                pad=14,
                thickness=14,
                line=dict(color=theme.SURFACE, width=2),
                hovertemplate="%{label}<br>%{value} transitions<extra></extra>",
            ),
            link=dict(
                source=[left[s] for s in observed[FROM_CATEGORY]],
                target=[right[t] for t in observed[TO_CATEGORY]],
                value=observed["count"].tolist(),
                color=[_rgba(colors.get(s, theme.NEUTRAL), 0.35) for s in observed[FROM_CATEGORY]],
                customdata=list(
                    zip(observed["probability"], observed["median_delay_s"].map(format_duration), strict=True)
                ),
                hovertemplate=(
                    "%{source.label} → %{target.label}<br>"
                    "P(next | current) = %{customdata[0]:.0%}<br>"
                    "Observed %{value}×, median gap %{customdata[1]}<extra></extra>"
                ),
            ),
        )
    )
    fig.update_layout(font=dict(size=12, color=theme.TEXT_PRIMARY))
    return theme.apply_layout(fig, height=440, legend=False)


def transition_matrix_figure(matrix: pd.DataFrame) -> go.Figure:
    if matrix.empty:
        return theme.empty_figure("Not enough history to estimate transitions", height=440)
    text = matrix.map(lambda p: f"{p:.0%}" if p >= 0.005 else "")
    fig = go.Figure(
        go.Heatmap(
            z=matrix.values,
            x=list(matrix.columns),
            y=list(matrix.index),
            zmin=0,
            zmax=1,
            colorscale=theme.SEQUENTIAL,
            text=text.values,
            texttemplate="%{text}",
            xgap=2,
            ygap=2,
            hovertemplate="Current: %{y}<br>Next: %{x}<br>P = %{z:.1%}<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickformat=".0%", tickfont=dict(color=theme.TEXT_MUTED)),
        )
    )
    fig.update_xaxes(title="Next incident", showgrid=False, tickangle=-35, side="bottom")
    fig.update_yaxes(
        title="Current incident", showgrid=False, autorange="reversed", tickfont=dict(color=theme.TEXT_SECONDARY)
    )
    return theme.apply_layout(fig, height=440, legend=False)
