import pytest

from incident_analyzer.taxonomy import ALL_CATEGORIES, OTHER, normalize_category


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Service Outage", "Service Outage"),
        ("service outage", "Service Outage"),
        (".Service Outage", "Service Outage"),
        ("Performance Degradation.", "Performance Degradation"),
        ("Configuration  Error", "Configuration Error"),
        ("Authentication/ Access Issue", "Authentication/Access Issue"),
        ("uthentication/Access Issue", "Authentication/Access Issue"),
        ("Incident Category: Security Breach", "Security Breach"),
        ("Security Breach/Security Warning", "Security Breach"),
        ("Infrastructure Capacity Issue", "Disk Capacity Issue"),
        ("Sustainability Achievement", OTHER),
        ("No Category", OTHER),
        ("", OTHER),
        (None, OTHER),
        (float("nan"), OTHER),
    ],
)
def test_normalize_category(label, expected):
    assert normalize_category(label) == expected


def test_canonical_labels_are_fixed_points():
    for category in ALL_CATEGORIES:
        assert normalize_category(category) == category
