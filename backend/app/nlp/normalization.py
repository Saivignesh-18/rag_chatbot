"""Text normalization for user queries.

Cleans whitespace and excessive punctuation and expands a small, safe set of
conversational abbreviations WITHOUT altering case, technical expressions, or
meaningful punctuation.
"""
from __future__ import annotations

import re

# Small, safe conversational expansions. Deliberately EXCLUDES risky single
# letters (e.g. "u", "r", "c") that collide with technical usage (variables,
# the R / C languages, physics symbols). Extend this dict to add more.
_ABBREVIATIONS: dict[str, str] = {
    "pls": "please",
    "plz": "please",
    "thx": "thanks",
    "thnx": "thanks",
    "tnx": "thanks",
    "abt": "about",
    "asap": "as soon as possible",
    "btw": "by the way",
    "fyi": "for your information",
    "approx": "approximately",
}

_WHITESPACE_RE = re.compile(r"\s+")
_REPEATED_PUNCT_RE = re.compile(r"([?!.,;:])\1+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([?!.,;:])")
_WORD_RE = re.compile(r"[A-Za-z']+")


def _expand_abbreviations(text: str) -> str:
    if not _ABBREVIATIONS:
        return text

    def _repl(match: re.Match) -> str:
        word = match.group(0)
        return _ABBREVIATIONS.get(word.lower(), word)

    return _WORD_RE.sub(_repl, text)


def normalize_text(text: str) -> str:
    """Return a cleaned version of ``text``.

    - trims leading/trailing whitespace
    - collapses repeated whitespace to single spaces
    - collapses runs of the same punctuation mark (``"????"`` -> ``"?"``)
    - removes spaces that appear directly before punctuation
    - expands a few safe conversational abbreviations

    Case and technical expressions are preserved. Safe for empty/None input.
    """
    if not text:
        return ""
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = _REPEATED_PUNCT_RE.sub(r"\1", text)
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    text = _expand_abbreviations(text)
    # Abbreviation expansion can reintroduce double spaces; collapse once more.
    return _WHITESPACE_RE.sub(" ", text).strip()
