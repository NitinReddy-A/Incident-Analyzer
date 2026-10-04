"""Dash application: fleet overview plus per-service transition intelligence."""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, dcc, html

from incident_analyzer import __version__
from incident_analyzer.analytics import (
    category_distribution,
    compute_kpis,
    format_duration,
    service_category_matrix,
    status_counts,
    volume_over_time,
)
from incident_analyzer.config import load_settings
from incident_analyzer.dashboard import figures, theme
from incident_analyzer.schema import CATEGORY, CREATED_AT, SERVICE, read_incidents, require_columns
from incident_analyzer.taxonomy import normalize_category
from incident_analyzer.transitions import FROM_CATEGORY, TO_CATEGORY, TransitionModel

ASSETS_DIR = Path(__file__).parent / "assets"

MAX_GAP_OPTIONS = [
    {"label": "Any gap", "value": 0},
    {"label": "≤ 15 min", "value": 15},
    {"label": "≤ 1 hour", "value": 60},
    {"label": "≤ 6 hours", "value": 360},
    {"label": "≤ 24 hours", "value": 1440},
]
SMOOTHING_OPTIONS = [
    {"label": "None (MLE)", "value": 0.0},
    {"label": "α = 0.5", "value": 0.5},
    {"label": "α = 1 (Laplace)", "value": 1.0},
]
MAX_TABLE_ROWS = 25


def load_dashboard_data(path: str | Path) -> pd.DataFrame:
    incidents = read_incidents(path)
    require_columns(incidents, (CATEGORY,), source=str(path))
    incidents[CATEGORY] = incidents[CATEGORY].map(normalize_category)
    return incidents


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def _stat(label: str, value: str, *, tone: str | None = None, hint: str | None = None) -> html.Div:
    children = [
        html.Div(label, className="stat-label"),
        html.Div(
            [html.Span(className=f"status-dot status-{tone}") if tone else None, value],
            className="stat-value",
        ),
    ]
    if hint:
        children.append(html.Div(hint, className="stat-hint"))
    return html.Div(children, className="stat")


def _card(title: str, body, *, subtitle: str | None = None, class_name: str = "") -> html.Div:
    header = [html.H3(title, className="card-title")]
    if subtitle:
        header.append(html.P(subtitle, className="card-subtitle"))
    return html.Div([html.Div(header, className="card-header"), body], className=f"card {class_name}")


def _graph(graph_id: str, figure=None) -> dcc.Graph:
    return dcc.Graph(id=graph_id, figure=figure, config={"displaylogo": False, "displayModeBar": "hover"})


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def _forecast_panel(model: TransitionModel, service: str) -> html.Div:
    state = model.state(service)
    if state is None:
        return html.P("No incidents recorded for this service.", className="muted")

    forecasts = model.forecast(service)
    rows = []
    for rank, f in enumerate(forecasts, start=1):
        rows.append(
            html.Div(
                [
                    html.Div(f"{rank}", className="forecast-rank"),
                    html.Div(
                        [
                            html.Div(f.category, className="forecast-category"),
                            html.Div(
                                html.Div(className="forecast-bar-fill", style={"width": f"{f.probability:.0%}"}),
                                className="forecast-bar",
                            ),
                            html.Div(
                                f"{f.probability:.0%} · {f.support} observed"
                                + (
                                    f" · typically within {format_duration(f.median_delay_s)}"
                                    if f.median_delay_s is not None
                                    else ""
                                ),
                                className="forecast-meta",
                            ),
                        ],
                        className="forecast-body",
                    ),
                ],
                className="forecast-row",
            )
        )

    basis_note = (
        "Ranked by P(next | current) for this service."
        if forecasts and forecasts[0].basis == "transition"
        else "This state has no outgoing history yet; showing the service's base rates."
    )
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Current state", className="stat-label"),
                    html.Div(state.category, className="current-state"),
                    html.Span(f"last incident {state.observed_at:%d %b %Y, %H:%M} UTC", className="muted"),
                ],
                className="current",
            ),
            html.Div(rows, className="forecast-list"),
            html.P(basis_note, className="muted small"),
        ]
    )


def _transition_table(rows: pd.DataFrame) -> html.Div:
    observed = rows[rows["count"] > 0].sort_values(["count", "probability"], ascending=False)
    if observed.empty:
        return html.P("No transitions observed for this service.", className="muted")
    head = html.Thead(
        html.Tr([html.Th(c) for c in ("Current", "Next", "P(next | current)", "Count", "Median gap", "P90 gap")])
    )
    body = html.Tbody(
        [
            html.Tr(
                [
                    html.Td(r[FROM_CATEGORY]),
                    html.Td(r[TO_CATEGORY]),
                    html.Td(f"{r['probability']:.1%}", className="num"),
                    html.Td(f"{int(r['count'])}", className="num"),
                    html.Td(format_duration(r["median_delay_s"]), className="num"),
                    html.Td(format_duration(r["p90_delay_s"]), className="num"),
                ]
            )
            for _, r in observed.head(MAX_TABLE_ROWS).iterrows()
        ]
    )
    note = (
        html.P(f"Showing the {MAX_TABLE_ROWS} most frequent of {len(observed)} transitions.", className="muted small")
        if len(observed) > MAX_TABLE_ROWS
        else None
    )
    return html.Div([html.Table([head, body], className="data-table"), note], className="table-wrap")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(incidents: pd.DataFrame) -> Dash:
    """Build the dashboard for an already-categorised incident dataset."""
    require_columns(incidents, (SERVICE, CREATED_AT, CATEGORY), source="incidents")
    if incidents.empty:
        raise ValueError("Cannot build a dashboard from an empty dataset")

    services = sorted(incidents[SERVICE].unique())
    category_counts = category_distribution(incidents)
    colors = theme.category_colors(category_counts.index)
    kpis = compute_kpis(incidents)
    default_service = incidents[SERVICE].value_counts().idxmax()
    start, end = incidents[CREATED_AT].min(), incidents[CREATED_AT].max()

    @lru_cache(maxsize=32)
    def fitted_model(max_gap_minutes: int, smoothing: float) -> TransitionModel:
        max_gap = timedelta(minutes=max_gap_minutes) if max_gap_minutes else None
        return TransitionModel.fit(incidents, max_gap=max_gap, smoothing=smoothing, normalize_labels=False)

    app = Dash(
        __name__,
        title="Incident Analyzer",
        assets_folder=str(ASSETS_DIR),
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    )

    app.layout = html.Div(
        [
            html.Header(
                [
                    html.Div(
                        [
                            html.H1("Incident Analyzer"),
                            html.P("Transition intelligence for PagerDuty service fleets", className="tagline"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Span(f"{kpis.incidents} incidents · {kpis.services} services"),
                            html.Span(f"{start:%d %b %Y} – {end:%d %b %Y}"),
                        ],
                        className="dataset-meta",
                    ),
                ],
                className="topbar",
            ),
            html.Main(
                [
                    html.Section(
                        [
                            html.H2("Fleet overview"),
                            html.Div(
                                [
                                    _stat("Incidents", f"{kpis.incidents}"),
                                    _stat("Services", f"{kpis.services}"),
                                    _stat("Triggered", f"{kpis.by_status['triggered']}", tone="triggered"),
                                    _stat("Acknowledged", f"{kpis.by_status['acknowledged']}", tone="acknowledged"),
                                    _stat("Resolved", f"{kpis.by_status['resolved']}", tone="resolved"),
                                    _stat(
                                        "Recurrence rate",
                                        _percent(kpis.recurrence_rate),
                                        hint="next incident repeats the category",
                                    ),
                                    _stat(
                                        "Median gap",
                                        format_duration(kpis.median_gap_s),
                                        hint="between consecutive incidents",
                                    ),
                                ],
                                className="stat-row",
                            ),
                            html.Div(
                                [
                                    _card(
                                        "Incident volume",
                                        _graph("volume", figures.volume_figure(volume_over_time(incidents))),
                                        subtitle="Incidents created per hour, by current status",
                                        class_name="span-2",
                                    ),
                                    _card(
                                        "Category mix",
                                        _graph("categories", figures.category_bar_figure(category_counts, height=320)),
                                        subtitle="All services",
                                    ),
                                ],
                                className="grid grid-3",
                            ),
                            _card(
                                "Where incidents concentrate",
                                _graph(
                                    "service-heatmap",
                                    figures.service_category_heatmap(service_category_matrix(incidents)),
                                ),
                                subtitle="Incident count by service and category",
                            ),
                        ],
                        className="section",
                    ),
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H2("Service transition intelligence"),
                                            html.P(
                                                "A per-service Markov chain over incident categories: "
                                                "what tends to fail next, and how soon.",
                                                className="muted",
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Label(
                                                [
                                                    "Service",
                                                    dcc.Dropdown(
                                                        id="service",
                                                        options=services,
                                                        value=default_service,
                                                        clearable=False,
                                                    ),
                                                ],
                                                className="control control-wide",
                                            ),
                                            html.Label(
                                                [
                                                    "Max gap",
                                                    dcc.Dropdown(
                                                        id="max-gap",
                                                        options=MAX_GAP_OPTIONS,
                                                        value=0,
                                                        clearable=False,
                                                    ),
                                                ],
                                                className="control",
                                            ),
                                            html.Label(
                                                [
                                                    "Smoothing",
                                                    dcc.Dropdown(
                                                        id="smoothing",
                                                        options=SMOOTHING_OPTIONS,
                                                        value=0.0,
                                                        clearable=False,
                                                    ),
                                                ],
                                                className="control",
                                            ),
                                        ],
                                        className="controls",
                                    ),
                                ],
                                className="section-head",
                            ),
                            html.Div(id="service-stats", className="stat-row"),
                            html.Div(
                                [
                                    _card(
                                        "Next-incident outlook",
                                        html.Div(id="forecast"),
                                        subtitle="Given the latest incident",
                                    ),
                                    _card(
                                        "Transition flow",
                                        _graph("sankey"),
                                        subtitle="Current category → next category; width = observed transitions",
                                        class_name="span-2",
                                    ),
                                ],
                                className="grid grid-3",
                            ),
                            html.Div(
                                [
                                    _card(
                                        "Transition matrix",
                                        _graph("matrix"),
                                        subtitle="P(next | current); each row sums to 100%",
                                        class_name="span-2",
                                    ),
                                    _card("Category mix", _graph("service-categories"), subtitle="Selected service"),
                                ],
                                className="grid grid-3",
                            ),
                            _card(
                                "Transition table",
                                html.Div(id="transition-table"),
                                subtitle="Observed transitions with timing statistics",
                            ),
                        ],
                        className="section",
                    ),
                ],
            ),
            html.Footer(f"Incident Analyzer v{__version__}", className="footer"),
        ],
        className="page",
    )

    @app.callback(
        Output("service-stats", "children"),
        Output("forecast", "children"),
        Output("sankey", "figure"),
        Output("matrix", "figure"),
        Output("service-categories", "figure"),
        Output("transition-table", "children"),
        Input("service", "value"),
        Input("max-gap", "value"),
        Input("smoothing", "value"),
    )
    def update_service(service: str, max_gap_minutes: int, smoothing: float):
        model = fitted_model(int(max_gap_minutes or 0), float(smoothing or 0.0))
        subset = incidents[incidents[SERVICE] == service]
        counts = status_counts(subset)
        rows = model.for_service(service)
        observed = int(rows["count"].sum()) if not rows.empty else 0

        stats = [
            _stat("Incidents", f"{len(subset)}"),
            _stat("Triggered", f"{counts['triggered']}", tone="triggered"),
            _stat("Acknowledged", f"{counts['acknowledged']}", tone="acknowledged"),
            _stat("Resolved", f"{counts['resolved']}", tone="resolved"),
            _stat("Transitions", f"{observed}", hint="pairs used by the model"),
        ]
        return (
            stats,
            _forecast_panel(model, service),
            figures.transition_sankey(rows, colors),
            figures.transition_matrix_figure(model.matrix(service)),
            figures.category_bar_figure(category_distribution(subset)),
            _transition_table(rows),
        )

    return app


def create_server(data_path: str | None = None):
    """WSGI entry point, e.g. ``gunicorn "incident_analyzer.dashboard.app:create_server()"``."""
    settings = load_settings()
    path = Path(data_path) if data_path else settings.categorized_path
    return create_app(load_dashboard_data(path)).server
