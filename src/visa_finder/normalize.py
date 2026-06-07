"""Company-name normalization and stable id generation.

Cross-source name matching is the main error source, so normalization is shared
by every source adapter and the dedupe pass to keep them consistent.
"""

from __future__ import annotations

import hashlib
import re

# Common legal suffixes / corporate noise removed before fuzzy matching.
_SUFFIXES = [
    "incorporated", "inc", "corporation", "corp", "company", "co",
    "limited liability company", "limited liability co", "llc", "l l c",
    "limited partnership", "lp", "l p", "llp", "l l p", "pllc",
    "limited", "ltd", "the",
]

_SUFFIX_RE = re.compile(
    r"\b(" + "|".join(sorted((re.escape(s) for s in _SUFFIXES), key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation and legal suffixes, collapse whitespace."""
    s = name.lower().strip()
    s = s.replace("&", " and ")
    s = _NON_ALNUM.sub(" ", s)
    s = _SUFFIX_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def company_id(normalized_name: str, state: str | None) -> str:
    """Stable id from normalized name + state, so the same company collapses to
    one record across quarterly refreshes."""
    key = f"{normalized_name}|{(state or '').upper()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
