"""Orchestrates the NLP preprocessing flow for a single user query.

    raw query
      -> normalize (whitespace / punctuation / safe abbreviations)
      -> spelling correction (conservative)
      -> intent detection (history-aware)
      -> decision:
           * basic conversational intent  -> canned response (no RAG)
           * follow-up / clarification     -> resolve from history (or ask to clarify)
           * document question             -> entity extraction + query expansion
      -> retrieval-ready query + the natural question for the LLM

This function NEVER raises: any sub-step failure degrades to the original text
so the existing RAG pipeline always keeps working.

Key outputs:
    corrected        - spell-corrected natural text (drives the UI "searched as" hint)
    prompt_question  - the natural question handed to the LLM (resolved for follow-ups)
    expanded_query   - retrieval-only string (synonyms + Telgish hints); never shown
    retrieval_query  - == expanded_query (what the embedder should search with)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.nlp.basic_responses import (
    CLARIFICATION_PROMPT,
    NEGATIVE_FEEDBACK_PROMPT,
    get_basic_response,
    is_basic_intent,
)
from app.nlp.conversation import resolve_followup
from app.nlp.entities import extract_entities
from app.nlp.intent_detection import Intent, detect_intent
from app.nlp.normalization import normalize_text
from app.nlp.query_expansion import expand_query
from app.nlp.spelling import CorrectionResult, spelling_corrector
from app.nlp.transliteration import has_telugu

logger = get_logger(__name__)

RESPONSE_SOURCE_NLP = "nlp"
RESPONSE_SOURCE_RAG = "rag"

# Intents that are resolved against conversation history before retrieval.
_CONTEXT_INTENTS = (Intent.FOLLOWUP, Intent.CLARIFICATION, Intent.NEGATIVE_FEEDBACK)


@dataclass
class PreprocessResult:
    original: str
    normalized: str
    corrected: str
    retrieval_query: str
    corrections: list[tuple[str, str]] = field(default_factory=list)
    intent: str = Intent.GENERAL.value
    is_basic: bool = False
    basic_response: str | None = None
    preprocessing_applied: bool = False
    response_source: str = RESPONSE_SOURCE_RAG
    # --- additive context/expansion metadata (safe defaults) ---
    prompt_question: str = ""
    expanded_query: str = ""
    entities_topics: list[str] = field(default_factory=list)
    is_followup: bool = False
    elaborate: bool = False
    used_context: bool = False
    informal: bool = False


def _basic_result(
    *,
    original: str,
    normalized: str,
    corrected: str,
    correction: CorrectionResult,
    intent: Intent,
    response: str,
) -> PreprocessResult:
    """Build a short-circuit (no-RAG) result for a conversational/clarify reply."""
    return PreprocessResult(
        original=original,
        normalized=normalized,
        corrected=corrected,
        retrieval_query=corrected,
        corrections=correction.corrections,
        intent=intent.value,
        is_basic=True,
        basic_response=response,
        preprocessing_applied=(normalized != original.strip()) or correction.changed,
        response_source=RESPONSE_SOURCE_NLP,
        prompt_question=corrected,
        expanded_query=corrected,
    )


def preprocess_query(
    raw_query: str,
    *,
    history: list[tuple[str, str]] | None = None,
) -> PreprocessResult:
    """Run normalization, spelling, intent detection and (optional) context
    resolution + query expansion on a query.

    ``history`` is an optional chronological list of ``(role, content)`` prior
    turns; when provided it enables feedback / follow-up / clarification handling.
    Omitting it preserves the original single-argument behaviour.
    """
    original = raw_query or ""
    history = history or []
    has_history = any((role or "").lower() == "user" and (content or "").strip() for role, content in history)

    # 1) Normalization (safe).
    try:
        normalized = normalize_text(original)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Normalization failed; using trimmed original (%s).", exc)
        normalized = original.strip()

    # 2) Spelling correction (conservative, graceful).
    try:
        correction = spelling_corrector.correct(normalized)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Spelling correction failed; using normalized text (%s).", exc)
        correction = CorrectionResult(corrected=normalized)
    corrected = correction.corrected

    # 3) Intent detection. Check the NORMALIZED (pre-correction) text first so a
    #    conversational typo that the spell-corrector would turn into an unrelated
    #    real word is still recognised (e.g. "byee" -> goodbye, even though
    #    correction maps it to the word "byte"). Fall back to the corrected text
    #    (e.g. "thnks" -> "thanks" -> gratitude; "helo" -> "help").
    try:
        intent = detect_intent(normalized, has_history=has_history)
        if intent is Intent.GENERAL:
            intent = detect_intent(corrected, has_history=has_history)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Intent detection failed; treating as general (%s).", exc)
        intent = Intent.GENERAL

    # 4a) Basic conversational intents -> canned reply, no retrieval/LLM.
    if is_basic_intent(intent):
        response = get_basic_response(intent) or ""
        return _basic_result(
            original=original,
            normalized=normalized,
            corrected=corrected,
            correction=correction,
            intent=intent,
            response=response,
        )

    # 4b) Context-dependent intents -> resolve from history, else ask to clarify.
    prompt_question = corrected
    elaborate = False
    used_context = False
    is_followup = False
    if intent in _CONTEXT_INTENTS:
        resolution = None
        try:
            resolution = resolve_followup(corrected, history)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Follow-up resolution failed (%s).", exc)
            resolution = None
        if resolution is None:
            prompt_text = (
                NEGATIVE_FEEDBACK_PROMPT
                if intent is Intent.NEGATIVE_FEEDBACK
                else CLARIFICATION_PROMPT
            )
            return _basic_result(
                original=original,
                normalized=normalized,
                corrected=corrected,
                correction=correction,
                intent=intent,
                response=prompt_text,
            )
        prompt_question = resolution.resolved_query or corrected
        elaborate = resolution.elaborate
        used_context = resolution.used_context
        is_followup = True

    # 5) Entity extraction + query expansion (retrieval only).
    try:
        entities = extract_entities(prompt_question)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Entity extraction failed (%s).", exc)
        from app.nlp.entities import EntityResult

        entities = EntityResult()
    try:
        expanded = expand_query(prompt_question, entities)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Query expansion failed (%s).", exc)
        expanded = prompt_question

    informal = has_telugu(original) or has_telugu(corrected)
    retrieval_query = expanded if expanded.strip() else (prompt_question or corrected or original)

    preprocessing_applied = (
        (normalized != original.strip())
        or correction.changed
        or is_followup
        or (expanded != prompt_question)
        or informal
    )

    return PreprocessResult(
        original=original,
        normalized=normalized,
        corrected=corrected,
        retrieval_query=retrieval_query,
        corrections=correction.corrections,
        intent=intent.value,
        is_basic=False,
        basic_response=None,
        preprocessing_applied=preprocessing_applied,
        response_source=RESPONSE_SOURCE_RAG,
        prompt_question=prompt_question,
        expanded_query=expanded,
        entities_topics=entities.topics,
        is_followup=is_followup,
        elaborate=elaborate,
        used_context=used_context,
        informal=informal,
    )
