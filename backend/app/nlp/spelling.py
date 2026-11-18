"""Conservative English spelling correction via symspellpy.

Design goals (per the integration brief):
- Correct only clear misspellings; never change meaning.
- Preserve acronyms (AI, ML, SQL), identifiers / camelCase, numbers, proper nouns,
  known English words, and a curated set of technical terms.
- Avoid correcting when confidence is insufficient (length-scaled edit distance).
- Load the frequency dictionary ONCE (thread-safe singleton); degrade to a no-op
  if symspellpy or the dictionary is unavailable.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.nlp.transliteration import ROMANIZED_TELUGU_TOKENS

logger = get_logger(__name__)

# Lowercase technical tokens that a general English dictionary may not contain;
# never "correct" these. Extend as needed.
_TECH_TERMS = frozenset(
    {
        "api", "apis", "sql", "nosql", "html", "css", "json", "xml", "yaml", "csv",
        "http", "https", "url", "uri", "sdk", "cli", "npm", "pip", "regex", "async",
        "await", "enum", "args", "kwargs", "cpu", "gpu", "ram", "ssd", "orm", "jwt",
        "oauth", "cors", "env", "backend", "frontend", "fullstack", "devops",
        "runtime", "middleware", "config", "repo", "llm", "rag", "nlp", "gpt",
        "embeddings", "embedding", "pgvector", "supabase", "fastapi", "react",
        "python", "javascript", "typescript", "nodejs", "uvicorn", "groq", "gemini",
        "chatbot", "dataset", "datasets",
        "pdf", "docx", "txt", "doc", "pptx", "xlsx", "rtf", "md", "odt",
    }
)

_WORD_RE = re.compile(r"[A-Za-z]+")


@dataclass
class CorrectionResult:
    corrected: str
    corrections: list[tuple[str, str]] = field(default_factory=list)
    changed: bool = False


class SpellingCorrector:
    """Thread-safe, lazily-loaded, conservative spelling corrector."""

    _DICT_NAME = "frequency_dictionary_en_82_765.txt"

    def __init__(self, max_edit_distance: int = 2, prefix_length: int = 7) -> None:
        self._max_edit = max_edit_distance
        self._prefix = prefix_length
        self._sym = None
        self._lock = threading.Lock()
        self._loaded = False
        self._failed = False

    # -- lifecycle -------------------------------------------------------
    def warmup(self) -> bool:
        """Load the dictionary once (call at app startup). Returns readiness."""
        self._ensure_loaded()
        return self._loaded

    def _ensure_loaded(self) -> None:
        if self._loaded or self._failed:
            return
        with self._lock:
            if self._loaded or self._failed:
                return
            try:
                import importlib.resources as ir

                from symspellpy import SymSpell

                sym = SymSpell(max_dictionary_edit_distance=self._max_edit, prefix_length=self._prefix)
                resource = ir.files("symspellpy").joinpath(self._DICT_NAME)
                with ir.as_file(resource) as path:
                    ok = sym.load_dictionary(str(path), term_index=0, count_index=1)
                if not ok:
                    raise RuntimeError("load_dictionary returned False")
                self._sym = sym
                self._loaded = True
                logger.info("Spelling dictionary loaded (symspellpy).")
            except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash
                self._failed = True
                logger.warning(
                    "Spelling correction unavailable (%s); queries pass through unchanged.", exc
                )

    @property
    def is_ready(self) -> bool:
        return self._loaded

    # -- correction ------------------------------------------------------
    def _correct_word(self, word: str) -> str | None:
        """Return a corrected spelling for ``word`` or ``None`` to keep it as-is."""
        from symspellpy import Verbosity

        # Only all-lowercase alphabetic tokens are candidates. This preserves
        # acronyms (AI), identifiers/camelCase (useState), and capitalized names.
        if (
            not word.islower()
            or len(word) < 3
            or word in _TECH_TERMS
            or word in ROMANIZED_TELUGU_TOKENS
        ):
            return None

        sym = self._sym
        # Already a valid English word? leave it untouched (distance-0 lookup).
        if sym.lookup(word, Verbosity.TOP, max_edit_distance=0, include_unknown=False):
            return None

        # Unknown token: scale the allowed edit distance by length to stay
        # conservative (short words must be very close to a real word).
        allowed = 1 if len(word) <= 6 else 2
        suggestions = sym.lookup(word, Verbosity.TOP, max_edit_distance=allowed, include_unknown=False)
        if not suggestions:
            return None
        best = suggestions[0]
        if best.term == word or best.distance == 0:
            return None
        return best.term

    def correct(self, text: str) -> CorrectionResult:
        """Return a :class:`CorrectionResult` for ``text``. Never raises."""
        if not text or not text.strip():
            return CorrectionResult(corrected=text or "")

        self._ensure_loaded()
        if not self._loaded:
            return CorrectionResult(corrected=text)  # graceful no-op

        corrections: list[tuple[str, str]] = []
        parts: list[str] = []
        last = 0
        try:
            for match in _WORD_RE.finditer(text):
                parts.append(text[last : match.start()])  # punctuation / spaces / digits
                word = match.group(0)
                fixed = self._correct_word(word)
                if fixed and fixed != word:
                    corrections.append((word, fixed))
                    parts.append(fixed)
                else:
                    parts.append(word)
                last = match.end()
            parts.append(text[last:])
        except Exception as exc:  # noqa: BLE001 - never break the request
            logger.warning("Spelling correction error; using original text (%s).", exc)
            return CorrectionResult(corrected=text)

        return CorrectionResult(
            corrected="".join(parts), corrections=corrections, changed=bool(corrections)
        )


# Module-level singleton: the dictionary is loaded once per process.
spelling_corrector = SpellingCorrector()
