"""Operational incident taxonomy and label normalisation.

LLM classifiers drift: the same class comes back as ``"Service outage"``,
``".Service Outage"``, ``"Incident Category: Service Outage"`` or with a
truncated first letter. Transition statistics are only meaningful over a closed
state space, so every label is snapped onto :data:`CATEGORIES` before it is
used. Anything that cannot be matched confidently becomes :data:`OTHER`.
"""

from __future__ import annotations

import difflib
import re

CATEGORIES: tuple[str, ...] = (
    "Authentication/Access Issue",
    "Configuration Error",
    "Service Outage",
    "Security Breach",
    "Performance Degradation",
    "Hardware Failure",
    "Software Bug",
    "Network Connectivity Problem",
    "Disk Capacity Issue",
    "Data Corruption",
)
OTHER = "Other"
ALL_CATEGORIES: tuple[str, ...] = (*CATEGORIES, OTHER)

# Labels the classifier is known to emit that are semantically one of the
# canonical classes but too far away for fuzzy matching to pick up safely.
ALIASES: dict[str, str] = {
    "system capacity issue": "Disk Capacity Issue",
    "infrastructure capacity issue": "Disk Capacity Issue",
    "storage capacity issue": "Disk Capacity Issue",
    "email service outage": "Service Outage",
    "service outage/event": "Service Outage",
    "e-commerce site configuration error": "Configuration Error",
    "software integration issue": "Software Bug",
    "security breach/security warning": "Security Breach",
    "access issue": "Authentication/Access Issue",
    "authentication issue": "Authentication/Access Issue",
    "network issue": "Network Connectivity Problem",
    "performance issue": "Performance Degradation",
}

_PREFIX = re.compile(r"^(incident\s+)?category\s*:\s*", re.IGNORECASE)
_EDGE_PUNCT = re.compile(r"^[\s\.\-\*\"'`:]+|[\s\.\-\*\"'`:]+$")
_WS = re.compile(r"\s+")
_SLASH = re.compile(r"\s*/\s*")

_FUZZY_CUTOFF = 0.88


def _canonical_key(label: str) -> str:
    text = _PREFIX.sub("", label.strip())
    text = _EDGE_PUNCT.sub("", text)
    text = _SLASH.sub("/", text)
    return _WS.sub(" ", text).lower()


_LOOKUP: dict[str, str] = {_canonical_key(c): c for c in ALL_CATEGORIES}
_LOOKUP.update({_canonical_key(k): v for k, v in ALIASES.items()})


def normalize_category(label: object) -> str:
    """Map a free-form classifier label onto the canonical taxonomy."""
    if not isinstance(label, str) or not label.strip():
        return OTHER
    key = _canonical_key(label)
    if key in _LOOKUP:
        return _LOOKUP[key]
    match = difflib.get_close_matches(key, _LOOKUP.keys(), n=1, cutoff=_FUZZY_CUTOFF)
    return _LOOKUP[match[0]] if match else OTHER
