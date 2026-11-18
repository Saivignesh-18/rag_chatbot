"""Lightweight fuzzy string matching.

Prefers RapidFuzz (fast, C-backed) when installed and degrades to the stdlib
``difflib`` otherwise, so the NLP layer has NO hard dependency on RapidFuzz. All
scores are normalised to the 0-100 range regardless of the active backend.
"""
from __future__ import annotations

from collections.abc import Iterable

try:  # pragma: no cover - depends on which backend is installed
    from rapidfuzz import fuzz as _rf_fuzz
    from rapidfuzz import process as _rf_process

    _HAS_RAPIDFUZZ = True
except Exception:  # noqa: BLE001 - optional dependency
    import difflib

    _HAS_RAPIDFUZZ = False


def is_ready() -> bool:
    """True when the (faster) RapidFuzz backend is available."""
    return _HAS_RAPIDFUZZ


def ratio(a: str, b: str) -> float:
    """Return a 0-100 similarity score between two strings. Never raises."""
    a = a or ""
    b = b or ""
    try:
        if _HAS_RAPIDFUZZ:
            return float(_rf_fuzz.ratio(a, b))
        return difflib.SequenceMatcher(None, a, b).ratio() * 100.0
    except Exception:  # noqa: BLE001
        return 0.0


def best_match(
    query: str, choices: Iterable[str], *, score_cutoff: float = 85.0
) -> tuple[str, float] | None:
    """Return ``(choice, score)`` for the closest choice at/above ``score_cutoff``.

    Returns ``None`` when nothing clears the cutoff. Never raises.
    """
    query = query or ""
    choice_list = [c for c in choices if c]
    if not query or not choice_list:
        return None
    try:
        if _HAS_RAPIDFUZZ:
            hit = _rf_process.extractOne(
                query, choice_list, scorer=_rf_fuzz.ratio, score_cutoff=score_cutoff
            )
            return (hit[0], float(hit[1])) if hit is not None else None
        best_choice: str | None = None
        best_score = 0.0
        for choice in choice_list:
            score = ratio(query, choice)
            if score > best_score:
                best_choice, best_score = choice, score
        if best_choice is not None and best_score >= score_cutoff:
            return best_choice, best_score
        return None
    except Exception:  # noqa: BLE001
        return None
