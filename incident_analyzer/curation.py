"""Noise reduction for raw incident exports.

PagerDuty exports contain a large share of incidents that carry no payload
(test pages, heartbeat alerts, manually opened placeholders). They add volume
but no signal, and they would dominate transition statistics, so they are
removed before classification.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from incident_analyzer.schema import DETAILS, INCIDENT_ID, UPDATED_AT, normalize_incidents

_EMPTY_PAYLOADS = frozenset({"", "{}", "[]", "none", "null", "nan"})


@dataclass(frozen=True)
class CurationReport:
    input_rows: int
    duplicates_removed: int
    empty_payloads_removed: int

    @property
    def output_rows(self) -> int:
        return self.input_rows - self.duplicates_removed - self.empty_payloads_removed


def has_payload(details: pd.Series) -> pd.Series:
    normalized = details.fillna("").astype("string").str.strip().str.lower()
    return ~normalized.isin(_EMPTY_PAYLOADS)


def curate(raw: pd.DataFrame) -> tuple[pd.DataFrame, CurationReport]:
    """Return the curated incidents together with a summary of what was dropped."""
    df = normalize_incidents(raw, source="raw incidents")
    input_rows = len(df)

    # Keep the most recent snapshot of each incident.
    deduped = df.sort_values(UPDATED_AT, kind="stable").drop_duplicates(INCIDENT_ID, keep="last")
    duplicates = input_rows - len(deduped)

    curated = deduped[has_payload(deduped[DETAILS])]
    empty = len(deduped) - len(curated)

    report = CurationReport(input_rows, duplicates, empty)
    return normalize_incidents(curated), report
