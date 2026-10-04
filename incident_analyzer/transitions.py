"""Service-scoped incident transition model.

Each service is modelled as an independent first-order Markov chain over the
incident taxonomy. For a service ``s`` with time-ordered incidents
``x_1, x_2, ..., x_n`` every consecutive pair ``(x_t, x_{t+1})`` is one
observed transition, and the model estimates

    P(next = j | current = i, service = s) = (n_sij + a) / (n_si + a * K_s)

where ``n_sij`` counts ``i -> j`` transitions inside ``s``, ``n_si`` is the
number of transitions leaving ``i``, ``K_s`` is the number of categories seen
in ``s`` and ``a`` is an optional additive (Laplace) smoothing constant.

Every transition also carries its inter-arrival delay, so the model answers two
questions at once: *what* is most likely to fail next in this service, and
*how soon* it has historically followed. An optional ``max_gap`` discards
pairs that are too far apart in time to plausibly be related.

Transitions are always computed inside a service. Pairing incidents across
services, or pairing rows that merely happen to be adjacent in a global export,
would mix unrelated failure streams.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

import pandas as pd

from incident_analyzer.schema import CATEGORY, CREATED_AT, SERVICE, require_columns
from incident_analyzer.taxonomy import ALL_CATEGORIES, normalize_category

FROM_CATEGORY = "from_category"
TO_CATEGORY = "to_category"
DELAY_S = "delay_s"

TABLE_COLUMNS: tuple[str, ...] = (
    SERVICE,
    FROM_CATEGORY,
    TO_CATEGORY,
    "count",
    "probability",
    "joint_probability",
    "mean_delay_s",
    "median_delay_s",
    "p90_delay_s",
)

_CATEGORY_ORDER = {name: rank for rank, name in enumerate(ALL_CATEGORIES)}


def _category_rank(category: str) -> tuple[int, str]:
    """Order categories by taxonomy position, unknown labels last."""
    return (_CATEGORY_ORDER.get(category, len(_CATEGORY_ORDER)), category)


def extract_transitions(incidents: pd.DataFrame, *, max_gap: timedelta | None = None) -> pd.DataFrame:
    """Return one row per consecutive incident pair within each service.

    Columns: ``service``, ``from_category``, ``to_category``, ``delay_s``.
    """
    require_columns(incidents, (SERVICE, CREATED_AT, CATEGORY), source="incidents")
    df = incidents[[SERVICE, CREATED_AT, CATEGORY]].copy()
    df[CREATED_AT] = pd.to_datetime(df[CREATED_AT], utc=True, errors="coerce")
    df = df.dropna().sort_values([SERVICE, CREATED_AT], kind="stable")

    by_service = df.groupby(SERVICE, sort=False)
    pairs = pd.DataFrame(
        {
            SERVICE: df[SERVICE],
            FROM_CATEGORY: df[CATEGORY],
            TO_CATEGORY: by_service[CATEGORY].shift(-1),
            DELAY_S: (by_service[CREATED_AT].shift(-1) - df[CREATED_AT]).dt.total_seconds(),
        }
    ).dropna(subset=[TO_CATEGORY])

    if max_gap is not None:
        pairs = pairs[pairs[DELAY_S] <= max_gap.total_seconds()]
    return pairs.reset_index(drop=True)


@dataclass(frozen=True)
class Forecast:
    """One candidate for the next incident in a service."""

    category: str
    probability: float
    support: int
    median_delay_s: float | None
    basis: Literal["transition", "prior"]


@dataclass(frozen=True)
class ServiceState:
    """The most recent observed incident category of a service."""

    category: str
    observed_at: pd.Timestamp


class TransitionModel:
    """Fitted per-service transition statistics. Build with :meth:`fit`."""

    def __init__(
        self,
        table: pd.DataFrame,
        priors: pd.DataFrame,
        states: dict[str, ServiceState],
        *,
        max_gap: timedelta | None,
        smoothing: float,
    ) -> None:
        self._table = table
        self._priors = priors
        self._states = states
        self.max_gap = max_gap
        self.smoothing = smoothing

    @classmethod
    def fit(
        cls,
        incidents: pd.DataFrame,
        *,
        max_gap: timedelta | None = None,
        smoothing: float = 0.0,
        normalize_labels: bool = True,
    ) -> TransitionModel:
        if smoothing < 0:
            raise ValueError("smoothing must be non-negative")
        if max_gap is not None and max_gap <= timedelta(0):
            raise ValueError("max_gap must be a positive duration")
        require_columns(incidents, (SERVICE, CREATED_AT, CATEGORY), source="incidents")

        df = incidents[[SERVICE, CREATED_AT, CATEGORY]].copy()
        df[CREATED_AT] = pd.to_datetime(df[CREATED_AT], utc=True, errors="coerce")
        if normalize_labels:
            df[CATEGORY] = df[CATEGORY].map(normalize_category)
        df = df.dropna().sort_values([SERVICE, CREATED_AT], kind="stable")

        pairs = extract_transitions(df, max_gap=max_gap)
        table = _build_table(pairs, df, smoothing)
        priors = _build_priors(df)
        last = df.groupby(SERVICE, sort=True).tail(1)
        states = {row[SERVICE]: ServiceState(row[CATEGORY], row[CREATED_AT]) for _, row in last.iterrows()}
        return cls(table, priors, states, max_gap=max_gap, smoothing=smoothing)

    @property
    def table(self) -> pd.DataFrame:
        """All transitions as a tidy table (see :data:`TABLE_COLUMNS`)."""
        return self._table.copy()

    @property
    def services(self) -> list[str]:
        return sorted(self._states)

    def for_service(self, service: str) -> pd.DataFrame:
        return self._table[self._table[SERVICE] == service].reset_index(drop=True)

    def matrix(self, service: str) -> pd.DataFrame:
        """Conditional transition matrix (rows: current, columns: next)."""
        rows = self.for_service(service)
        if rows.empty:
            return pd.DataFrame(dtype=float)
        matrix = rows.pivot_table(
            index=FROM_CATEGORY,
            columns=TO_CATEGORY,
            values="probability",
            aggfunc="sum",
            fill_value=0.0,
        )
        labels = sorted(set(matrix.index) | set(matrix.columns), key=_category_rank)
        return matrix.reindex(index=labels, columns=labels, fill_value=0.0)

    def state(self, service: str) -> ServiceState | None:
        return self._states.get(service)

    def forecast(self, service: str, current: str | None = None, *, top_k: int = 3) -> list[Forecast]:
        """Rank the most likely next incident categories for ``service``.

        ``current`` defaults to the category of the service's latest incident.
        If that state was never observed as the source of a transition the
        service's marginal category distribution is returned instead, flagged
        with ``basis="prior"``.
        """
        if current is None:
            state = self.state(service)
            if state is None:
                return []
            current = state.category
        else:
            current = normalize_category(current)

        rows = self.for_service(service)
        rows = rows[rows[FROM_CATEGORY] == current]
        if not rows.empty:
            ranked = rows.sort_values(["probability", "count"], ascending=False).head(top_k)
            return [
                Forecast(
                    category=r[TO_CATEGORY],
                    probability=float(r["probability"]),
                    support=int(r["count"]),
                    median_delay_s=None if pd.isna(r["median_delay_s"]) else float(r["median_delay_s"]),
                    basis="transition",
                )
                for _, r in ranked.iterrows()
            ]

        priors = self._priors[self._priors[SERVICE] == service]
        ranked = priors.sort_values(["probability", "count"], ascending=False).head(top_k)
        return [
            Forecast(
                category=r[CATEGORY],
                probability=float(r["probability"]),
                support=int(r["count"]),
                median_delay_s=None,
                basis="prior",
            )
            for _, r in ranked.iterrows()
        ]


def _build_table(pairs: pd.DataFrame, incidents: pd.DataFrame, smoothing: float) -> pd.DataFrame:
    if pairs.empty:
        return pd.DataFrame(columns=list(TABLE_COLUMNS))

    keys = [SERVICE, FROM_CATEGORY, TO_CATEGORY]
    stats = (
        pairs.groupby(keys)[DELAY_S]
        .agg(
            count="size",
            mean_delay_s="mean",
            median_delay_s="median",
            p90_delay_s=lambda s: s.quantile(0.9),
        )
        .reset_index()
    )

    vocab = incidents.groupby(SERVICE)[CATEGORY].unique()
    if smoothing > 0:
        # Expand every observed source state to the full vocabulary of its
        # service so unseen transitions receive non-zero mass.
        grid = [
            (service, src, dst)
            for service, src in stats[[SERVICE, FROM_CATEGORY]].drop_duplicates().itertuples(index=False)
            for dst in vocab[service]
        ]
        stats = stats.set_index(keys).reindex(pd.MultiIndex.from_tuples(grid, names=keys)).reset_index()
        stats["count"] = stats["count"].fillna(0).astype(int)

    k = stats[SERVICE].map(vocab.map(len))
    out_total = stats.groupby([SERVICE, FROM_CATEGORY])["count"].transform("sum")
    service_total = stats.groupby(SERVICE)["count"].transform("sum")
    stats["probability"] = (stats["count"] + smoothing) / (out_total + smoothing * k)
    stats["joint_probability"] = stats["count"] / service_total

    stats = stats.sort_values(
        [SERVICE, FROM_CATEGORY, "probability", TO_CATEGORY],
        ascending=[True, True, False, True],
        kind="stable",
    )
    return stats[list(TABLE_COLUMNS)].reset_index(drop=True)


def _build_priors(incidents: pd.DataFrame) -> pd.DataFrame:
    counts = incidents.groupby([SERVICE, CATEGORY]).size().rename("count").reset_index()
    counts["probability"] = counts["count"] / counts.groupby(SERVICE)["count"].transform("sum")
    return counts
