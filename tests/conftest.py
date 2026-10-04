from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"


def make_incidents(rows: list[tuple[str, str, str]], *, status: str = "triggered") -> pd.DataFrame:
    """Build a categorised incident frame from ``(service, created_at, category)`` tuples."""
    return pd.DataFrame(
        [
            {
                "incident_number": i,
                "incident_id": f"Q{i:04d}",
                "title": f"incident {i}",
                "summary": f"[#{i}] incident {i}",
                "details": "payload",
                "status": status,
                "service": service,
                "created_at": created_at,
                "updated_at": created_at,
                "category": category,
            }
            for i, (service, created_at, category) in enumerate(rows, start=1)
        ]
    )


@pytest.fixture
def interleaved() -> pd.DataFrame:
    """Two services whose incidents interleave in the global stream."""
    return make_incidents(
        [
            ("api", "2024-03-01T00:00:00Z", "Service Outage"),
            ("db", "2024-03-01T00:00:10Z", "Disk Capacity Issue"),
            ("api", "2024-03-01T00:01:00Z", "Configuration Error"),
            ("db", "2024-03-01T00:01:10Z", "Disk Capacity Issue"),
            ("api", "2024-03-01T00:03:00Z", "Service Outage"),
            ("api", "2024-03-01T00:04:00Z", "Service Outage"),
            ("db", "2024-03-01T05:00:00Z", "Data Corruption"),
        ]
    )


@pytest.fixture
def sample_categorized() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_DIR / "incidents_categorized.csv")
