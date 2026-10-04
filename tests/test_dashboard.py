from __future__ import annotations

import pytest

pytest.importorskip("dash")

from incident_analyzer.cli import build_parser, parse_duration  # noqa: E402
from incident_analyzer.dashboard import create_app, load_dashboard_data  # noqa: E402
from tests.conftest import SAMPLE_DIR  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return create_app(load_dashboard_data(SAMPLE_DIR / "incidents_categorized.csv"))


def _callback(app):
    (entry,) = [cb for key, cb in app.callback_map.items() if "service-stats.children" in key]
    return entry["callback"].__wrapped__


@pytest.mark.parametrize("max_gap", [0, 15])
@pytest.mark.parametrize("smoothing", [0.0, 1.0])
def test_service_callback_renders_every_service(app, max_gap, smoothing):
    update = _callback(app)
    for service in load_dashboard_data(SAMPLE_DIR / "incidents_categorized.csv")["service"].unique():
        stats, forecast, sankey, matrix, mix, table = update(service, max_gap, smoothing)
        assert len(stats) == 5
        assert sankey.to_dict()["data"] is not None
        assert matrix.to_dict()["layout"] is not None
        assert mix is not None and forecast is not None and table is not None


def test_layout_serialises(app):
    import json

    import plotly

    json.dumps(app.layout.to_plotly_json(), cls=plotly.utils.PlotlyJSONEncoder)


def test_cli_parses_durations():
    assert parse_duration("15m").total_seconds() == 900
    assert parse_duration("1.5h").total_seconds() == 5400
    args = build_parser().parse_args(["transitions", "--max-gap", "6h", "--smoothing", "0.5"])
    assert args.max_gap.total_seconds() == 6 * 3600
    assert args.smoothing == 0.5
