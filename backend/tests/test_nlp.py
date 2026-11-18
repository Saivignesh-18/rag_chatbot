"""Unit tests for the NLP preprocessing layer (``app.nlp``).

These are PURE-FUNCTION tests: they do NOT touch the database, embeddings, Groq
or Gemini. Run them either way:

    python tests/test_nlp.py        # standalone (no DB, no conftest) - used in CI/dev
    pytest tests/test_nlp.py        # under pytest (needs a LOCAL test DB; see note)

NOTE: tests/conftest.py truncates the database before every test and now refuses
to run against a non-local DATABASE_URL (e.g. Supabase). So under pytest against
a remote DB these will skip; run them standalone instead.
"""
from __future__ import annotations

import os
import sys

# Allow running as a standalone script (`python tests/test_nlp.py`) by putting
# the backend/ directory on sys.path. Harmless under pytest.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.nlp import preprocess_query  # noqa: E402
from app.nlp.basic_responses import BASIC_RESPONSES, get_basic_response, is_basic_intent  # noqa: E402
from app.nlp.conversation import resolve_followup  # noqa: E402
from app.nlp.entities import extract_entities  # noqa: E402
from app.nlp.intent_detection import Intent, detect_intent  # noqa: E402
from app.nlp.normalization import normalize_text  # noqa: E402
from app.nlp.query_expansion import expand_query  # noqa: E402
from app.nlp.spelling import spelling_corrector  # noqa: E402
from app.nlp.transliteration import has_telugu, telugu_english_hints  # noqa: E402

# Load the frequency dictionary once for the spelling tests.
spelling_corrector.warmup()

# A short prior conversation used to exercise context-dependent intents.
_HIST = [
    ("user", "What are the technical skills in my resume?"),
    ("assistant", "Your resume lists Python, SQL and React."),
]


# ---- A. Normalization -----------------------------------------------------
def test_normalize_whitespace_and_punctuation():
    assert normalize_text("  WHAT   IS AI???? ") == "WHAT IS AI?"


def test_normalize_empty_and_none():
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""
    assert normalize_text(None) == ""  # type: ignore[arg-type]


def test_normalize_collapses_repeated_whitespace():
    assert normalize_text("hello\t\n   world") == "hello world"


def test_normalize_excessive_punctuation():
    assert normalize_text("stop!!!") == "stop!"
    assert normalize_text("really???") == "really?"


def test_normalize_safe_abbreviations():
    assert normalize_text("pls help") == "please help"


def test_normalize_preserves_technical_expression():
    assert normalize_text("what is 2+2?") == "what is 2+2?"


# ---- B. Spelling correction ----------------------------------------------
def test_spelling_keeps_correct_words():
    r = spelling_corrector.correct("hello")
    assert r.corrected == "hello"
    assert r.changed is False


def test_spelling_fixes_misspelled_phrases():
    assert (
        spelling_corrector.correct("wht is artifical inteligence").corrected
        == "what is artificial intelligence"
    )
    assert spelling_corrector.correct("machne lerning").corrected == "machine learning"


def test_spelling_empty_input_is_safe():
    assert spelling_corrector.correct("").corrected == ""
    assert spelling_corrector.correct("   ").corrected == "   "
    assert spelling_corrector.correct("   ").changed is False


def test_spelling_corrects_single_typo():
    r = spelling_corrector.correct("helo")
    assert r.changed is True
    assert r.corrected != "helo"  # -> a real dictionary word (help/hello)


def test_spelling_preserves_technical_terms_and_identifiers():
    assert spelling_corrector.correct("AI").corrected == "AI"
    assert spelling_corrector.correct("ML").corrected == "ML"
    assert spelling_corrector.correct("useState").corrected == "useState"
    assert spelling_corrector.correct("PostgreSQL").corrected == "PostgreSQL"
    assert spelling_corrector.correct("api").corrected == "api"
    assert spelling_corrector.correct("openai").corrected == "openai"


def test_spelling_preserves_short_tokens_and_names():
    assert spelling_corrector.correct("ai").corrected == "ai"  # len < 3 -> skipped
    assert spelling_corrector.correct("booja").corrected == "booja"  # unknown name kept


# ---- C. Intent detection (basic + context-gated) --------------------------
def test_intent_greeting():
    for t in ["hi", "hello", "hey", "good morning", "hi there"]:
        assert detect_intent(t) is Intent.GREETING


def test_intent_gratitude():
    for t in ["thanks", "thank you", "thank u", "thx"]:
        assert detect_intent(t) is Intent.GRATITUDE


def test_intent_goodbye():
    for t in ["bye", "goodbye", "see you"]:
        assert detect_intent(t) is Intent.GOODBYE


def test_intent_help():
    for t in ["help", "what can you do", "how do you work"]:
        assert detect_intent(t) is Intent.HELP


def test_intent_general_for_real_questions():
    assert detect_intent("what is machine learning") is Intent.GENERAL
    assert detect_intent("tell me about the retirement age") is Intent.GENERAL


def test_intent_does_not_misclassify_document_question():
    # A real question that merely starts with "hi" must NOT be a greeting.
    assert detect_intent("hi, what is in my document?") is Intent.GENERAL


def test_intent_is_punctuation_insensitive():
    assert detect_intent("Hello!!!") is Intent.GREETING
    assert detect_intent("thanks a lot!") is Intent.GRATITUDE


def test_intent_feedback_requires_history():
    # Without history, short reactions are NOT feedback (they go to RAG).
    assert detect_intent("good") is Intent.GENERAL
    assert detect_intent("great") is Intent.GENERAL
    # With history, they are positive feedback.
    assert detect_intent("good", has_history=True) is Intent.POSITIVE_FEEDBACK
    assert detect_intent("perfect", has_history=True) is Intent.POSITIVE_FEEDBACK


def test_intent_negative_feedback_context_gated():
    assert detect_intent("not helpful") is Intent.GENERAL
    assert detect_intent("not helpful", has_history=True) is Intent.NEGATIVE_FEEDBACK
    assert detect_intent("wrong answer", has_history=True) is Intent.NEGATIVE_FEEDBACK


def test_intent_followup_context_gated():
    assert detect_intent("what about projects?") is Intent.GENERAL
    assert detect_intent("what about projects?", has_history=True) is Intent.FOLLOWUP
    assert detect_intent("tell me more", has_history=True) is Intent.FOLLOWUP


def test_intent_clarification_context_gated():
    assert detect_intent("what do you mean", has_history=True) is Intent.CLARIFICATION


def test_intent_greeting_not_history_gated():
    assert detect_intent("hello") is Intent.GREETING
    assert detect_intent("hello", has_history=True) is Intent.GREETING


def test_intent_document_question_wins_even_with_history():
    # Real document questions must still route to RAG mid-conversation.
    assert detect_intent("what is the retirement age", has_history=True) is Intent.GENERAL
    assert detect_intent("skills inside document?", has_history=True) is Intent.GENERAL


# ---- D. Basic responses ---------------------------------------------------
def test_basic_responses_mapping():
    assert get_basic_response(Intent.GREETING) == "Hello! How can I help you today?"
    assert get_basic_response(Intent.GRATITUDE) == "You're welcome! Happy to help."
    assert get_basic_response(Intent.GOODBYE) == "Goodbye! Have a great day."
    assert get_basic_response(Intent.HELP) is not None
    assert get_basic_response(Intent.POSITIVE_FEEDBACK) is not None
    assert get_basic_response(Intent.GENERAL) is None


def test_basic_intent_flags():
    assert is_basic_intent(Intent.GREETING) is True
    assert is_basic_intent(Intent.POSITIVE_FEEDBACK) is True
    assert is_basic_intent(Intent.GENERAL) is False
    assert is_basic_intent(Intent.FOLLOWUP) is False
    assert set(BASIC_RESPONSES) == {
        Intent.GREETING,
        Intent.GRATITUDE,
        Intent.GOODBYE,
        Intent.HELP,
        Intent.POSITIVE_FEEDBACK,
    }


# ---- E. Conversation / follow-up resolution -------------------------------
def test_resolve_followup_new_topic_carries_domain():
    r = resolve_followup("what about projects?", _HIST)
    assert r is not None
    assert "projects" in r.resolved_query.lower()
    assert "resume" in r.resolved_query.lower()  # domain carried from prior Q
    assert r.elaborate is False


def test_resolve_followup_elaborate_reuses_previous_question():
    r = resolve_followup("tell me more", _HIST)
    assert r is not None
    assert r.elaborate is True
    assert r.resolved_query == "What are the technical skills in my resume?"


def test_resolve_followup_unresolvable_returns_none():
    assert resolve_followup("what do you mean", _HIST) is None
    assert resolve_followup("tell me more", []) is None  # no history to anchor on


# ---- F. Entity / keyword extraction ---------------------------------------
def test_entity_topics_detection():
    assert "skills" in extract_entities("skills inside document?").topics
    assert "education" in extract_entities("education history?").topics
    assert "projects" in extract_entities("tell me about the projects").topics
    assert "certifications" in extract_entities("list my certifications").topics


def test_entity_no_topic_for_generic_question():
    assert extract_entities("what is the capital city").topics == []


# ---- G. Query expansion (retrieval only) ----------------------------------
def test_expand_query_adds_topic_keywords():
    out = expand_query("skills inside document?")
    assert out != "skills inside document?"
    assert "programming languages" in out.lower()


def test_expand_query_noop_when_no_topic():
    # No detectable topic -> returned unchanged (so retrieval_query is unaffected).
    assert expand_query("what is machine learning") == "what is machine learning"


# ---- H. Telgish (romanized Telugu) / informal -----------------------------
def test_telgish_detection_and_hints():
    assert has_telugu("resume lo skills enti?") is True
    hints = telugu_english_hints("resume lo skills enti?")
    assert "in" in hints and "what" in hints


def test_telgish_tokens_not_spell_corrected():
    # Romanized Telugu function words must survive spelling correction.
    assert spelling_corrector.correct("enti").corrected == "enti"
    assert spelling_corrector.correct("gurinchi").corrected == "gurinchi"


def test_expand_query_adds_telugu_hints_and_topic():
    out = expand_query("resume lo skills enti?").lower()
    assert "in" in out  # from 'lo'
    assert "programming languages" in out  # skills topic expansion


# ---- I. Preprocessing orchestrator (pipeline contract) --------------------
def test_preprocess_basic_intent_short_circuits():
    r = preprocess_query("hi")
    assert r.is_basic is True
    assert r.basic_response == "Hello! How can I help you today?"
    assert r.response_source == "nlp"
    assert r.intent == "greeting"


def test_preprocess_document_question_routes_to_rag():
    r = preprocess_query("what is machine learning")
    assert r.is_basic is False
    assert r.response_source == "rag"
    assert r.retrieval_query == "what is machine learning"


def test_preprocess_corrects_then_routes_to_rag():
    r = preprocess_query("machne lerning")
    assert r.corrected == "machine learning"
    assert r.corrections  # non-empty
    assert r.is_basic is False
    assert r.response_source == "rag"
    assert r.retrieval_query == "machine learning"


def test_preprocess_applies_normalization():
    r = preprocess_query("  WHAT   IS AI???? ")
    assert r.corrected == "WHAT IS AI?"
    assert r.preprocessing_applied is True


def test_preprocess_empty_is_safe():
    r = preprocess_query("")
    assert r.is_basic is False
    assert r.response_source == "rag"
    assert r.basic_response is None


def test_basic_intents_need_no_retrieval_but_questions_do():
    # Contract guaranteeing rag_service skips embeddings/LLM for basic intents.
    assert preprocess_query("thanks").basic_response is not None
    assert preprocess_query("what are the main requirements").basic_response is None


def test_preprocess_followup_resolves_and_routes_to_rag():
    r = preprocess_query("what about projects?", history=_HIST)
    assert r.is_basic is False
    assert r.response_source == "rag"
    assert r.is_followup is True
    assert "projects" in r.prompt_question.lower()
    assert "projects" in r.retrieval_query.lower()


def test_preprocess_positive_feedback_short_circuits_with_history():
    r = preprocess_query("good", history=_HIST)
    assert r.is_basic is True
    assert r.response_source == "nlp"
    assert r.intent == "positive_feedback"


def test_preprocess_clarification_when_unresolvable():
    r = preprocess_query("what do you mean", history=_HIST)
    assert r.is_basic is True
    assert r.response_source == "nlp"
    assert r.basic_response  # a clarification prompt


def test_preprocess_telgish_routes_to_rag_with_hints():
    r = preprocess_query("resume lo skills enti?")
    assert r.is_basic is False
    assert r.informal is True
    assert "programming languages" in r.retrieval_query.lower()


def test_preprocess_backward_compatible_single_arg():
    # No history: a bare feedback word must NOT short-circuit.
    r = preprocess_query("good")
    assert r.is_basic is False
    assert r.response_source == "rag"


# ---- Standalone runner (no pytest / no conftest / no DB) ------------------
if __name__ == "__main__":
    import traceback

    cases = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for name, fn in cases:
        try:
            fn()
            print(f"PASS  {name}")
            passed += 1
        except Exception:  # noqa: BLE001
            print(f"FAIL  {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed (of {len(cases)})")
    sys.exit(1 if failed else 0)
