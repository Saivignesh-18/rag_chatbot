"""Informal and romanized-Telugu ("Telgish") understanding.

Many users type English mixed with romanized Telugu, e.g. "resume lo skills
enti?". This module maps a small, curated set of romanized Telugu function/
question words to English KEYWORD HINTS that are appended to the *retrieval*
query only. It never rewrites the user's displayed message and never touches
document content.

The mapping is deliberately small and high-precision (common function words),
so it cannot corrupt ordinary English queries.
"""
from __future__ import annotations

import re

# token -> English hint. High-precision function / question words only.
TELUGU_TOKEN_HINTS: dict[str, str] = {
    "lo": "in",
    "loni": "in",
    "lopala": "inside",
    "meeda": "about",
    "gurinchi": "about",
    "gurinchii": "about",
    "nundi": "from",
    "enti": "what",
    "emiti": "what",
    "emi": "what",
    "enta": "how much",
    "entha": "how much",
    "ela": "how",
    "ekkada": "where",
    "eppudu": "when",
    "evaru": "who",
    "cheppu": "tell",
    "cheppandi": "tell",
    "chepu": "tell",
    "cheyyi": "do",
    "cheyi": "do",
    "cheyandi": "do",
    "chey": "do",
    "chudu": "show",
    "chudandi": "show",
    "kavali": "need",
    "ivvu": "give",
    "ivvandi": "give",
    "undi": "is",
    "unnayi": "are",
    "vivaralu": "details",
    "samacharam": "information",
}

# Romanized Telugu tokens PROTECTED from English spelling correction (so "enti"
# is never "corrected" to "anti"). Includes the function words above plus a few
# common romanized content words seen in document queries.
ROMANIZED_TELUGU_TOKENS: frozenset[str] = frozenset(TELUGU_TOKEN_HINTS) | frozenset(
    {
        "telugu", "telgish",
        "vidya", "chaduvu", "udyogam", "anubhavam", "pani",
        "prajektulu", "patralu",
    }
)

_WORD_RE = re.compile(r"[A-Za-z]+")


def has_telugu(text: str) -> bool:
    """True if ``text`` contains any recognised romanized-Telugu token."""
    if not text:
        return False
    return any(w.lower() in TELUGU_TOKEN_HINTS for w in _WORD_RE.findall(text))


def telugu_english_hints(text: str) -> list[str]:
    """Return de-duplicated English hint keywords for romanized-Telugu tokens.

    Order-preserving; only recognised tokens contribute. English words in the
    query are left for the caller to keep as-is.
    """
    if not text:
        return []
    hints: list[str] = []
    seen: set[str] = set()
    for word in _WORD_RE.findall(text):
        hint = TELUGU_TOKEN_HINTS.get(word.lower())
        if hint and hint not in seen:
            seen.add(hint)
            hints.append(hint)
    return hints
