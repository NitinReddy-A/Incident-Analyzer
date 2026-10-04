"""Supervised fine-tuning (SFT) corpus preparation for the incident classifier.

The corpus pairs incident descriptions with fine-grained root-cause labels
(``SQL Injection``, ``Certificate Expiry``, ``Database Connection Pool
Exhaustion`` ...) and renders each pair in an instruction format suitable for
causal-LM fine-tuning:

    ###Human:
    Categorize the incident: <description>

    ###Assistant:
    <label>

Hand-assembled corpora tend to contain CSV damage, where a label is truncated
or the next record has bled into the label field. :func:`clean_corpus` repairs
labels that are recognisable prefixes of a known label, drops the rest and
removes duplicate descriptions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

DESCRIPTION = "Incident Description"
LABEL = "Category"
TEXT = "text"

PROMPT_TEMPLATE = "###Human:\nCategorize the incident: {description}\n\n###Assistant:\n{label}"

# A label must appear at least this many times to be treated as a known class.
MIN_LABEL_SUPPORT = 3
# Fraction of a known label that a damaged label must reproduce to be repaired.
REPAIR_PREFIX_RATIO = 0.8


@dataclass(frozen=True)
class CorpusReport:
    input_rows: int
    repaired_labels: int
    dropped_labels: int
    duplicates_removed: int
    output_rows: int
    classes: int


def _clean_text(value: object) -> str:
    return " ".join(str(value).split()) if isinstance(value, str) else ""


def _common_prefix(a: str, b: str) -> int:
    return len(os.path.commonprefix([a, b]))


def repair_label(label: str, known: frozenset[str]) -> str | None:
    """Return the known label ``label`` was derived from, or ``None``."""
    if label in known:
        return label
    best, best_len = None, 0
    for candidate in known:
        n = _common_prefix(label, candidate)
        if n > best_len:
            best, best_len = candidate, n
    if best is not None and best_len >= REPAIR_PREFIX_RATIO * len(best):
        return best
    return None


def known_labels(*frames: pd.DataFrame) -> frozenset[str]:
    labels = pd.concat([f[LABEL].map(_clean_text) for f in frames])
    support = labels.value_counts()
    return frozenset(support[support >= MIN_LABEL_SUPPORT].index)


def clean_corpus(df: pd.DataFrame, labels: frozenset[str]) -> tuple[pd.DataFrame, CorpusReport]:
    missing = {DESCRIPTION, LABEL} - set(df.columns)
    if missing:
        raise ValueError(f"corpus is missing column(s): {', '.join(sorted(missing))}")

    out = pd.DataFrame({DESCRIPTION: df[DESCRIPTION].map(_clean_text), LABEL: df[LABEL].map(_clean_text)})
    out = out[out[DESCRIPTION] != ""]

    repaired = out[LABEL].map(lambda label: repair_label(label, labels))
    n_repaired = int(((repaired != out[LABEL]) & repaired.notna()).sum())
    n_dropped = int(repaired.isna().sum())
    out = out.assign(**{LABEL: repaired}).dropna(subset=[LABEL])

    before = len(out)
    out = out.drop_duplicates(DESCRIPTION, keep="first")
    n_dupes = before - len(out)

    out[TEXT] = [
        PROMPT_TEMPLATE.format(description=d, label=lbl) for d, lbl in zip(out[DESCRIPTION], out[LABEL], strict=True)
    ]
    out = out.reset_index(drop=True)
    report = CorpusReport(
        input_rows=len(df),
        repaired_labels=n_repaired,
        dropped_labels=n_dropped,
        duplicates_removed=n_dupes,
        output_rows=len(out),
        classes=out[LABEL].nunique(),
    )
    return out, report


def remove_leakage(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop test rows whose description also appears in the training split."""
    leaked = test[DESCRIPTION].isin(set(train[DESCRIPTION]))
    return test[~leaked].reset_index(drop=True), int(leaked.sum())
