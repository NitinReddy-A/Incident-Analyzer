"""PagerDuty incident ingestion (REST API v2)."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator, Mapping
from typing import Any

import pandas as pd
import requests

from incident_analyzer.schema import INCIDENT_COLUMNS

log = logging.getLogger(__name__)

PAGE_SIZE = 100
# PagerDuty's classic offset pagination stops at 10,000 records.
MAX_OFFSET = 10_000


class PagerDutyError(RuntimeError):
    pass


class PagerDutyClient:
    """Minimal read-only client for the PagerDuty incidents endpoint."""

    def __init__(
        self,
        api_token: str,
        *,
        base_url: str = "https://api.pagerduty.com",
        session: requests.Session | None = None,
        timeout: float = 30.0,
        max_retries: int = 5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/vnd.pagerduty+json;version=2",
                "Authorization": f"Token token={api_token}",
                "Content-Type": "application/json",
            }
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> PagerDutyClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(self, path: str, params: Mapping[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        for attempt in range(1, self._max_retries + 1):
            response = self._session.get(url, params=params, timeout=self._timeout)
            if response.status_code == 429 or response.status_code >= 500:
                delay = float(response.headers.get("Retry-After", 2**attempt))
                log.warning("PagerDuty returned %s, retrying in %.0fs", response.status_code, delay)
                time.sleep(delay)
                continue
            if not response.ok:
                raise PagerDutyError(f"GET {path} failed with {response.status_code}: {response.text[:500]}")
            return response.json()
        raise PagerDutyError(f"GET {path} failed after {self._max_retries} attempts")

    def iter_incidents(
        self,
        *,
        since: str | None = None,
        until: str | None = None,
        service_ids: list[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield raw incident objects, oldest first, following pagination."""
        params: dict[str, Any] = {
            "limit": PAGE_SIZE,
            "offset": 0,
            "sort_by": "created_at:asc",
            "include[]": "body",
        }
        if since or until:
            if since:
                params["since"] = since
            if until:
                params["until"] = until
        else:
            params["date_range"] = "all"
        if service_ids:
            params["service_ids[]"] = service_ids

        while True:
            page = self._get("/incidents", params)
            incidents = page.get("incidents", [])
            yield from incidents
            params["offset"] += len(incidents)
            if not page.get("more") or not incidents:
                return
            if params["offset"] >= MAX_OFFSET:
                log.warning(
                    "Reached PagerDuty's %d-record pagination limit; narrow the window "
                    "with --since/--until to fetch the remainder.",
                    MAX_OFFSET,
                )
                return


def _details_text(body: Mapping[str, Any] | None) -> str:
    details = (body or {}).get("details")
    if details is None:
        return ""
    if isinstance(details, str):
        return details.strip()
    return json.dumps(details, sort_keys=True) if details else ""


def flatten_incident(incident: Mapping[str, Any]) -> dict[str, Any]:
    service = incident.get("service") or {}
    return {
        "incident_number": incident.get("incident_number"),
        "incident_id": incident.get("id"),
        "title": incident.get("title"),
        "summary": incident.get("summary"),
        "details": _details_text(incident.get("body")),
        "status": incident.get("status"),
        "service": service.get("summary"),
        "created_at": incident.get("created_at"),
        "updated_at": incident.get("updated_at"),
    }


def fetch_incidents(client: PagerDutyClient, **filters: Any) -> pd.DataFrame:
    rows = [flatten_incident(i) for i in client.iter_incidents(**filters)]
    return pd.DataFrame(rows, columns=list(INCIDENT_COLUMNS))
