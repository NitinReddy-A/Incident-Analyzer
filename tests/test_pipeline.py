from __future__ import annotations

import pandas as pd
import pytest

from incident_analyzer.classify import classify_incidents
from incident_analyzer.curation import curate
from incident_analyzer.finetune import clean_corpus, known_labels, remove_leakage, repair_label
from incident_analyzer.ingest import PagerDutyClient, fetch_incidents, flatten_incident
from tests.conftest import SAMPLE_DIR, make_incidents

# -- curation ---------------------------------------------------------------


def test_curate_drops_empty_payloads_and_duplicates():
    df = make_incidents(
        [
            ("svc", "2024-03-01T00:00:00Z", "x"),
            ("svc", "2024-03-01T00:01:00Z", "x"),
            ("svc", "2024-03-01T00:02:00Z", "x"),
        ]
    ).drop(columns="category")
    df.loc[1, "details"] = "{}"
    duplicate = df.iloc[[2]].assign(updated_at="2024-03-01T01:00:00Z", status="resolved")
    curated, report = curate(pd.concat([df, duplicate]))

    assert report.input_rows == 4
    assert report.duplicates_removed == 1
    assert report.empty_payloads_removed == 1
    assert len(curated) == report.output_rows == 2
    assert curated.loc[curated["incident_id"] == "Q0003", "status"].item() == "resolved"


def test_curate_sample_export():
    curated, report = curate(pd.read_csv(SAMPLE_DIR / "incidents_raw.csv"))
    assert report.empty_payloads_removed > 0
    assert not curated["details"].isin(["", "{}"]).any()


# -- classification -----------------------------------------------------------


def test_classify_normalises_and_resumes():
    df = make_incidents([("svc", f"2024-03-01T00:0{i}:00Z", "x") for i in range(3)])
    df.loc[0, "category"] = "Hardware Failure"
    df.loc[1:, "category"] = pd.NA
    calls: list[str] = []

    def fake(text: str) -> str:
        calls.append(text)
        return "  service outage. "

    out = classify_incidents(df, fake)
    assert len(calls) == 2
    assert out["category"].tolist() == ["Hardware Failure", "Service Outage", "Service Outage"]


# -- ingestion ----------------------------------------------------------------


class _Response:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.headers, self.text = payload, status, {}, ""

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._payload


class _Session:
    def __init__(self, pages):
        self.headers, self.calls, self._pages = {}, [], list(pages)

    def get(self, url, params, timeout):
        self.calls.append(dict(params))
        return self._pages.pop(0)

    def close(self):
        pass


def _incident(n, details):
    return {
        "id": f"P{n}",
        "incident_number": n,
        "title": "t",
        "summary": "s",
        "status": "triggered",
        "service": {"summary": "api"},
        "created_at": "2024-03-01T00:00:00Z",
        "updated_at": "2024-03-01T00:00:00Z",
        "body": {"details": details},
    }


def test_fetch_follows_pagination():
    session = _Session(
        [
            _Response({"incidents": [_incident(1, "disk full")], "more": True}),
            _Response({"incidents": [_incident(2, {})], "more": False}),
        ]
    )
    df = fetch_incidents(PagerDutyClient("token", session=session))
    assert df["incident_id"].tolist() == ["P1", "P2"]
    assert df["details"].tolist() == ["disk full", ""]
    assert [c["offset"] for c in session.calls] == [0, 1]
    assert session.headers["Authorization"] == "Token token=token"


def test_flatten_serialises_structured_details():
    row = flatten_incident(_incident(3, {"b": 1, "a": 2}))
    assert row["details"] == '{"a": 2, "b": 1}'


# -- fine-tuning corpus ---------------------------------------------------------


def test_repair_label():
    known = frozenset({"DNS Resolution Issues", "Certificate Expiry"})
    assert repair_label("DNS Resolution IssuAn incident occurred where", known) == "DNS Resolution Issues"
    assert repair_label("Certificate Expiry", known) == "Certificate Expiry"
    assert repair_label(" leading to rate limiting", known) is None


def test_clean_corpus_formats_prompts():
    df = pd.DataFrame(
        {
            "Incident Description": ["a  b\r\n c", "d", "a b c", "e"],
            "Category": ["SQL Injection"] * 3 + [" fragment of the previous row"],
        }
    )
    out, report = clean_corpus(df, known_labels(df))
    assert report.duplicates_removed == 1
    assert report.dropped_labels == 1
    assert out["text"].iloc[0] == "###Human:\nCategorize the incident: a b c\n\n###Assistant:\nSQL Injection"


def test_remove_leakage():
    train = pd.DataFrame({"Incident Description": ["x", "y"]})
    test = pd.DataFrame({"Incident Description": ["y", "z"]})
    cleaned, leaked = remove_leakage(train, test)
    assert leaked == 1
    assert cleaned["Incident Description"].tolist() == ["z"]


@pytest.mark.parametrize("split", ["train", "test"])
def test_shipped_corpus_is_clean(split):
    df = pd.read_csv(SAMPLE_DIR.parent / "finetune" / f"{split}.csv")
    assert not df["Incident Description"].duplicated().any()
    assert df["text"].str.startswith("###Human:\nCategorize the incident: ").all()
    assert (df["Category"].value_counts() >= 1).all()
