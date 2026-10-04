"""LLM-assisted incident classification.

The classifier is constrained to the closed taxonomy in
:mod:`incident_analyzer.taxonomy`, runs deterministically (temperature 0) and
every response is passed through :func:`normalize_category`, so the output is
always a valid state for the transition model regardless of model drift.

Any OpenAI-compatible chat model works, including a model fine-tuned on the
corpus produced by :mod:`incident_analyzer.finetune`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

import pandas as pd

from incident_analyzer.schema import CATEGORY, DETAILS, TITLE
from incident_analyzer.taxonomy import CATEGORIES, OTHER, normalize_category

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""\
You are an incident-response analyst for a private cloud platform. Classify each
incident into exactly one of these categories:

{chr(10).join(f"- {c}" for c in CATEGORIES)}
- {OTHER}

Rules:
- Answer with the category name only, spelled exactly as listed.
- Use "{OTHER}" when the incident does not describe an operational failure or
  does not fit any listed category.

Example
Incident: Users are experiencing intermittent login failures and are denied access.
Answer: Authentication/Access Issue
"""


class Classifier(Protocol):
    def __call__(self, text: str) -> str: ...


class OpenAIClassifier:
    """Zero-shot classifier backed by an OpenAI-compatible chat completion API."""

    def __init__(self, api_key: str, model: str, *, max_retries: int = 5) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ImportError(
                "LLM classification requires the 'llm' extra: pip install 'incident-analyzer[llm]'"
            ) from exc
        self._client = OpenAI(api_key=api_key, max_retries=max_retries)
        self._model = model

    def __call__(self, text: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            max_tokens=16,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Incident: {text}\nAnswer:"},
            ],
        )
        return response.choices[0].message.content or ""


def incident_text(row: pd.Series) -> str:
    title = str(row.get(TITLE) or "").strip()
    details = str(row.get(DETAILS) or "").strip()
    return f"{title}. {details}" if title and details else title or details


def classify_incidents(
    incidents: pd.DataFrame,
    classifier: Classifier,
    *,
    checkpoint: Callable[[pd.DataFrame], None] | None = None,
    checkpoint_every: int = 25,
) -> pd.DataFrame:
    """Return a copy of ``incidents`` with a normalised ``category`` column.

    Rows that already carry a category are skipped, so an interrupted run can
    be resumed by passing its partial output back in. ``checkpoint`` is called
    periodically with the partial result.
    """
    out = incidents.copy()
    if CATEGORY not in out.columns:
        out[CATEGORY] = pd.NA
    out[CATEGORY] = out[CATEGORY].astype("object")

    pending = out.index[out[CATEGORY].isna()]
    log.info("Classifying %d of %d incidents", len(pending), len(out))
    for done, idx in enumerate(pending, start=1):
        out.at[idx, CATEGORY] = normalize_category(classifier(incident_text(out.loc[idx])))
        if checkpoint and done % checkpoint_every == 0:
            checkpoint(out)
            log.info("Classified %d/%d", done, len(pending))
    if checkpoint and len(pending):
        checkpoint(out)
    return out
