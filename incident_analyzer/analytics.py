"""Descriptive incident analytics used by the dashboard and the CLI."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from incident_analyzer.schema import CATEGORY, CREATED_AT, SERVICE, STATUS, STATUSES
from incident_analyzer.transitions import FROM_CATEGORY, TO_CATEGORY, extract_transitions


@dataclass(frozen=True)
class Kpis:
    incidents: int
    services: int
    by_status: dict[str, int]
    recurrence_rate: float | None
    median_gap_s: float | None


def status_counts(incidents: pd.DataFrame) -> dict[str, int]:
    counts = incidents[STATUS].value_counts()
    return {status: int(counts.get(status, 0)) for status in STATUSES}


def compute_kpis(incidents: pd.DataFrame) -> Kpis:
    """Headline figures. ``recurrence_rate`` is the share of within-service
    transitions where the next incident has the same category as the current one."""
    recurrence = median_gap = None
    if CATEGORY in incidents.columns:
        pairs = extract_transitions(incidents)
        if not pairs.empty:
            recurrence = float((pairs[FROM_CATEGORY] == pairs[TO_CATEGORY]).mean())
            median_gap = float(pairs["delay_s"].median())
    return Kpis(
        incidents=len(incidents),
        services=int(incidents[SERVICE].nunique()),
        by_status=status_counts(incidents),
        recurrence_rate=recurrence,
        median_gap_s=median_gap,
    )


def volume_over_time(incidents: pd.DataFrame, freq: str = "h") -> pd.DataFrame:
    """Incident counts per time bucket and status (wide: one column per status)."""
    if incidents.empty:
        return pd.DataFrame(columns=[CREATED_AT, *STATUSES])
    table = (
        incidents.groupby([pd.Grouper(key=CREATED_AT, freq=freq), STATUS])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=list(STATUSES), fill_value=0)
    )
    full_range = pd.date_range(table.index.min(), table.index.max(), freq=freq)
    return table.reindex(full_range, fill_value=0).rename_axis(CREATED_AT).reset_index()


def category_distribution(incidents: pd.DataFrame) -> pd.Series:
    return incidents[CATEGORY].value_counts()


def service_category_matrix(incidents: pd.DataFrame) -> pd.DataFrame:
    """Incident counts with services as rows and categories as columns."""
    order = category_distribution(incidents).index
    matrix = incidents.groupby([SERVICE, CATEGORY]).size().unstack(fill_value=0)
    matrix = matrix.reindex(columns=order, fill_value=0)
    return matrix.loc[matrix.sum(axis=1).sort_values(ascending=False).index]


def format_duration(seconds: float | None) -> str:
    if seconds is None or pd.isna(seconds):
        return "n/a"
    seconds = float(seconds)
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 90 * 60:
        return f"{seconds / 60:.1f}m"
    if seconds < 48 * 3600:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"
