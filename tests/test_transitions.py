from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest

from incident_analyzer.transitions import TABLE_COLUMNS, TransitionModel, extract_transitions
from tests.conftest import make_incidents


def _row(model: TransitionModel, service: str, src: str, dst: str) -> pd.Series:
    t = model.table
    match = t[(t["service"] == service) & (t["from_category"] == src) & (t["to_category"] == dst)]
    assert len(match) == 1, f"expected exactly one row for {service}: {src} -> {dst}"
    return match.iloc[0]


def test_pairs_are_formed_within_each_service_despite_interleaving(interleaved):
    pairs = extract_transitions(interleaved)
    # api: 4 incidents -> 3 pairs, db: 3 incidents -> 2 pairs. A naive scan of
    # globally adjacent rows would find none, because the services alternate.
    assert pairs.groupby("service").size().to_dict() == {"api": 3, "db": 2}
    db = pairs[pairs["service"] == "db"]
    assert list(zip(db["from_category"], db["to_category"], strict=True)) == [
        ("Disk Capacity Issue", "Disk Capacity Issue"),
        ("Disk Capacity Issue", "Data Corruption"),
    ]


def test_input_order_does_not_matter(interleaved):
    shuffled = interleaved.sample(frac=1, random_state=7)
    pd.testing.assert_frame_equal(TransitionModel.fit(interleaved).table, TransitionModel.fit(shuffled).table)


def test_probabilities_are_conditional_on_the_current_category(interleaved):
    model = TransitionModel.fit(interleaved)
    assert _row(model, "api", "Service Outage", "Configuration Error")["probability"] == pytest.approx(0.5)
    assert _row(model, "api", "Service Outage", "Service Outage")["probability"] == pytest.approx(0.5)
    assert _row(model, "api", "Configuration Error", "Service Outage")["probability"] == pytest.approx(1.0)
    sums = model.table.groupby(["service", "from_category"])["probability"].sum()
    assert sums.to_numpy() == pytest.approx(1.0)


def test_joint_probability_is_normalised_per_service(interleaved):
    model = TransitionModel.fit(interleaved)
    sums = model.table.groupby("service")["joint_probability"].sum()
    assert sums.to_numpy() == pytest.approx(1.0)


def test_delay_statistics(interleaved):
    model = TransitionModel.fit(interleaved)
    row = _row(model, "db", "Disk Capacity Issue", "Data Corruption")
    assert row["median_delay_s"] == pytest.approx(5 * 3600 - 70)
    assert row["count"] == 1


def test_max_gap_discards_distant_pairs(interleaved):
    model = TransitionModel.fit(interleaved, max_gap=timedelta(minutes=10))
    t = model.table
    assert t[(t["service"] == "db") & (t["to_category"] == "Data Corruption")].empty
    assert int(t["count"].sum()) == 4


def test_laplace_smoothing_assigns_mass_to_unseen_transitions(interleaved):
    model = TransitionModel.fit(interleaved, smoothing=1.0)
    # api vocabulary: {Service Outage, Configuration Error} -> K = 2.
    row = _row(model, "api", "Configuration Error", "Configuration Error")
    assert row["count"] == 0
    assert row["probability"] == pytest.approx((0 + 1) / (1 + 2))
    sums = model.table.groupby(["service", "from_category"])["probability"].sum()
    assert sums.to_numpy() == pytest.approx(1.0)


def test_labels_are_normalised_before_fitting():
    df = make_incidents(
        [
            ("svc", "2024-03-01T00:00:00Z", ".Service Outage"),
            ("svc", "2024-03-01T00:01:00Z", "service outage"),
        ]
    )
    model = TransitionModel.fit(df)
    assert model.table[["from_category", "to_category"]].iloc[0].tolist() == ["Service Outage", "Service Outage"]


def test_forecast_uses_latest_state(interleaved):
    model = TransitionModel.fit(interleaved)
    assert model.state("api").category == "Service Outage"
    forecast = model.forecast("api", top_k=5)
    assert [f.category for f in forecast] == ["Configuration Error", "Service Outage"]
    assert all(f.basis == "transition" for f in forecast)
    assert sum(f.probability for f in forecast) == pytest.approx(1.0)


def test_forecast_falls_back_to_priors_for_terminal_states(interleaved):
    model = TransitionModel.fit(interleaved)
    # Data Corruption is the last db incident and never transitions anywhere.
    forecast = model.forecast("db")
    assert {f.basis for f in forecast} == {"prior"}
    assert forecast[0].category == "Disk Capacity Issue"
    assert forecast[0].probability == pytest.approx(2 / 3)


def test_forecast_for_unknown_service_is_empty(interleaved):
    assert TransitionModel.fit(interleaved).forecast("unknown") == []


def test_matrix_rows_sum_to_one(interleaved):
    matrix = TransitionModel.fit(interleaved).matrix("api")
    assert list(matrix.index) == list(matrix.columns)
    assert matrix.sum(axis=1).to_numpy() == pytest.approx(1.0)


def test_single_incident_service_produces_no_transitions():
    model = TransitionModel.fit(make_incidents([("solo", "2024-03-01T00:00:00Z", "Software Bug")]))
    assert model.table.empty
    assert list(model.table.columns) == list(TABLE_COLUMNS)
    assert model.matrix("solo").empty
    assert model.forecast("solo")[0].basis == "prior"


@pytest.mark.parametrize("kwargs", [{"smoothing": -1}, {"max_gap": timedelta(0)}])
def test_invalid_parameters_are_rejected(interleaved, kwargs):
    with pytest.raises(ValueError):
        TransitionModel.fit(interleaved, **kwargs)


def test_sample_dataset_uses_every_within_service_pair(sample_categorized):
    model = TransitionModel.fit(sample_categorized)
    expected_pairs = len(sample_categorized) - sample_categorized["service"].nunique()
    assert int(model.table["count"].sum()) == expected_pairs
