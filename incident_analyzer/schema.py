"""Canonical incident schema and CSV I/O helpers.

Every stage of the pipeline reads and writes incidents with these columns. The
``category`` column is only present once incidents have been classified.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

INCIDENT_NUMBER = "incident_number"
INCIDENT_ID = "incident_id"
TITLE = "title"
SUMMARY = "summary"
DETAILS = "details"
STATUS = "status"
SERVICE = "service"
CREATED_AT = "created_at"
UPDATED_AT = "updated_at"
CATEGORY = "category"

INCIDENT_COLUMNS: tuple[str, ...] = (
    INCIDENT_NUMBER,
    INCIDENT_ID,
    TITLE,
    SUMMARY,
    DETAILS,
    STATUS,
    SERVICE,
    CREATED_AT,
    UPDATED_AT,
)

STATUSES: tuple[str, ...] = ("triggered", "acknowledged", "resolved")


class SchemaError(ValueError):
    """Raised when a dataset does not match the expected incident schema."""


def require_columns(df: pd.DataFrame, columns: Iterable[str], *, source: str = "dataset") -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise SchemaError(f"{source} is missing required column(s): {', '.join(missing)}")


def normalize_incidents(df: pd.DataFrame, *, source: str = "dataset") -> pd.DataFrame:
    """Validate the schema and coerce column types.

    Timestamps are parsed as timezone-aware UTC, statuses are lower-cased and
    rows are ordered by creation time so downstream consumers can rely on it.
    """
    require_columns(df, INCIDENT_COLUMNS, source=source)
    out = df.copy()
    out[CREATED_AT] = pd.to_datetime(out[CREATED_AT], utc=True, errors="coerce")
    out[UPDATED_AT] = pd.to_datetime(out[UPDATED_AT], utc=True, errors="coerce")
    out = out.dropna(subset=[CREATED_AT, SERVICE])
    out[STATUS] = out[STATUS].astype("string").str.strip().str.lower()
    out[SERVICE] = out[SERVICE].astype("string").str.strip()
    out[DETAILS] = out[DETAILS].fillna("").astype("string")
    if CATEGORY in out.columns:
        out[CATEGORY] = out[CATEGORY].astype("string")
    return out.sort_values([CREATED_AT, INCIDENT_NUMBER], kind="stable").reset_index(drop=True)


def read_incidents(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Incident dataset not found: {path}")
    return normalize_incidents(pd.read_csv(path), source=str(path))


def write_csv(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n")
    return path
