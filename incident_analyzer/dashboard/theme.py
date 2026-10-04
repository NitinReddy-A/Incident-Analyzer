"""Visual tokens shared by the dashboard figures and stylesheet.

The categorical palette is validated for colour-vision deficiency in this
order; colours are bound to categories once (by global frequency) and never
re-assigned when a filter changes, so a category keeps its hue everywhere.
"""

from __future__ import annotations

from collections.abc import Iterable

import plotly.graph_objects as go

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#8a8984"
GRID = "#e6e5e0"
NEUTRAL = "#b4b2aa"

CATEGORICAL = (
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
)

# Single-hue sequential ramp (near-zero recedes toward the surface).
SEQUENTIAL = (
    (0.0, "#f3f7fd"),
    (0.15, "#cde2fb"),
    (0.35, "#86b6ef"),
    (0.55, "#3987e5"),
    (0.75, "#256abf"),
    (1.0, "#0d366b"),
)

# Reserved for incident state only; never used for a data series.
STATUS_COLORS = {
    "triggered": "#d03b3b",
    "acknowledged": "#fab219",
    "resolved": "#0ca30c",
}

FONT_FAMILY = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"


def category_colors(categories_by_frequency: Iterable[str]) -> dict[str, str]:
    """Bind the most frequent categories to palette slots; the tail is neutral."""
    colors: dict[str, str] = {}
    slots = iter(CATEGORICAL)
    for category in categories_by_frequency:
        if category == "Other":
            colors[category] = NEUTRAL
            continue
        colors[category] = next(slots, NEUTRAL)
    return colors


def apply_layout(fig: go.Figure, *, height: int = 360, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, size=12, color=TEXT_SECONDARY),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=GRID, font=dict(family=FONT_FAMILY, color=TEXT_PRIMARY)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, zeroline=False, tickfont=dict(color=TEXT_MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, zeroline=False, tickfont=dict(color=TEXT_MUTED))
    return fig


def empty_figure(message: str, *, height: int = 360) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        font=dict(color=TEXT_MUTED, size=13),
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return apply_layout(fig, height=height, legend=False)
