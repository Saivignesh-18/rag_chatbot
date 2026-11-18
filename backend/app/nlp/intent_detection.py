"""Rule-based intent detection.

Classifies a query as:
  * a basic conversational intent that needs NO retrieval
      - GREETING, GRATITUDE, GOODBYE, HELP
      - POSITIVE_FEEDBACK                (context-gated: only with history)
  * a context-dependent intent that needs history + the RAG pipeline
      - NEGATIVE_FEEDBACK, FOLLOWUP, CLARIFICATION   (context-gated)
  * GENERAL - a real document question that goes straight to RAG.

Conservative by design:
  * Greeting/gratitude/goodbye/help require the WHOLE short message to match a
    known phrase, so a real question that merely contains "hi" is never a greeting.
  * Feedback / follow-up / clarification are only considered when
    ``has_history`` is True, i.e. the user is reacting to a previous answer.
    This is why a bare "good" is treated as feedback only mid-conversation.
"""
from __future__ import annotations

import re
from enum import Enum

from app.nlp.fuzzy import best_match


class Intent(str, Enum):
    GREETING = "greeting"
    GRATITUDE = "gratitude"
    GOODBYE = "goodbye"
    HELP = "help"
    POSITIVE_FEEDBACK = "positive_feedback"
    NEGATIVE_FEEDBACK = "negative_feedback"
    FOLLOWUP = "followup"
    CLARIFICATION = "clarification"
    GENERAL = "general"


# Whole-message canonical phrases that map to a basic conversational intent.
_INTENT_PHRASES: dict[Intent, frozenset[str]] = {
    Intent.GREETING: frozenset(
        {
            "hi", "hii", "hiii", "hey", "heyy", "heya", "hiya", "yo", "sup",
            "hello", "helloo", "helo", "hlo", "heloo", "hallo",
            "hi there", "hey there", "hello there",
            "good morning", "good afternoon", "good evening", "good day",
            "greetings", "howdy", "hola", "namaste",
        }
    ),
    Intent.GRATITUDE: frozenset(
        {
            "thanks", "thank you", "thank u", "thankyou", "thx", "thnx", "tnx",
            "thnks", "thanx", "thankz",
            "ty", "tysm", "thanks a lot", "thank you so much", "thanks so much",
            "many thanks", "much appreciated", "appreciate it", "cheers",
        }
    ),
    Intent.GOODBYE: frozenset(
        {
            "bye", "byee", "byeee", "goodbye", "good bye", "bye bye", "see you", "see ya",
            "see you later", "cya", "take care", "catch you later", "talk later",
        }
    ),
    Intent.HELP: frozenset(
        {
            "help", "help me", "what can you do", "what do you do",
            "what can you help with", "how can you help", "how do you work",
            "how does this work", "what is this", "who are you",
            "what can i ask", "what can i ask you",
        }
    ),
}

# Context-gated feedback phrases (only meaningful mid-conversation).
_POSITIVE_FEEDBACK = frozenset(
    {
        "good", "great", "awesome", "perfect", "nice", "excellent", "cool",
        "helpful", "very helpful", "that helps", "that helped", "well done",
        "amazing", "brilliant", "good job", "super", "fantastic", "wonderful",
        "good answer", "nice answer", "love it", "exactly", "thats helpful",
        "that is helpful", "ok good", "okay good", "great answer", "spot on",
    }
)
_NEGATIVE_FEEDBACK = frozenset(
    {
        "wrong", "incorrect", "unhelpful", "bad", "nope", "not right",
        "not correct", "wrong answer", "bad answer", "explain again",
        "explain it again", "try again", "that is wrong", "thats wrong",
        "this is wrong", "that's wrong",
    }
)
# Negative phrases detected as substrings (tolerates a few surrounding words).
_NEGATIVE_SUBSTR = (
    "not helpful", "not what i asked", "not what i meant", "does not help",
    "doesnt help", "not correct", "not right", "wrong answer",
)

# Continuation follow-ups that carry no new topic.
_FOLLOWUP_EXACT = frozenset(
    {
        "tell me more", "more", "more details", "more detail", "explain that",
        "explain it", "elaborate", "can you elaborate", "please elaborate",
        "go on", "continue", "say more", "in detail", "explain in detail",
        "more info", "more information", "expand", "expand on that", "details",
        "what did you mention earlier", "what you mentioned earlier",
        "what did you say earlier", "give me another example", "another example",
        "one more example", "again", "say it again", "once more",
    }
)
# New-topic follow-up prefixes: "what about X", "how about X", "and X", "also X".
_FOLLOWUP_PREFIX_RE = re.compile(
    r"^(what about|how about|what of|and|also|tell me more|then what about)\b",
    re.IGNORECASE,
)

# User asking the assistant to clarify.
_CLARIFICATION = frozenset(
    {
        "what do you mean", "what does that mean", "clarify", "can you clarify",
        "please clarify", "i dont understand", "didnt understand",
        "i didnt understand", "what", "huh", "come again", "i am confused",
        "im confused", "not clear", "confusing", "meaning",
    }
)

# Messages longer than this many words are always treated as real questions
# (for the static conversational sets).
_MAX_INTENT_WORDS = 5
# Feedback is very short by nature; cap to avoid matching inside long sentences.
_MAX_FEEDBACK_WORDS = 6

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_FEEDBACK_FUZZY_CUTOFF = 90.0


def _canonical(text: str) -> str:
    """Lowercase, strip punctuation/symbols, and collapse whitespace."""
    text = (text or "").lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _is_positive_feedback(canon: str, words: list[str]) -> bool:
    if canon in _POSITIVE_FEEDBACK:
        return True
    if len(words) <= 3:
        hit = best_match(canon, _POSITIVE_FEEDBACK, score_cutoff=_FEEDBACK_FUZZY_CUTOFF)
        if hit is not None:
            return True
    return False


def _is_negative_feedback(canon: str) -> bool:
    if canon in _NEGATIVE_FEEDBACK:
        return True
    return any(phrase in canon for phrase in _NEGATIVE_SUBSTR)


def _is_followup(canon: str) -> bool:
    if canon in _FOLLOWUP_EXACT:
        return True
    return bool(_FOLLOWUP_PREFIX_RE.match(canon))


def detect_intent(text: str, *, has_history: bool = False) -> Intent:
    """Return the detected :class:`Intent` for ``text``.

    ``has_history`` must be True only when there is a prior turn in the
    conversation; it gates feedback / follow-up / clarification so that short
    reactions like "good" are not misread as feedback on the first message.
    The one-argument call (``detect_intent(text)``) preserves the original
    greeting/gratitude/goodbye/help/general behaviour.
    """
    canon = _canonical(text)
    if not canon:
        return Intent.GENERAL
    words = canon.split()

    # 1) Static conversational intents (not history-gated): the whole short
    #    message must exactly match a known phrase.
    if len(words) <= _MAX_INTENT_WORDS:
        for intent, phrases in _INTENT_PHRASES.items():
            if canon in phrases:
                return intent

    # 2) Context-dependent intents: only when reacting to a previous answer.
    if has_history:
        if len(words) <= _MAX_FEEDBACK_WORDS:
            if _is_positive_feedback(canon, words):
                return Intent.POSITIVE_FEEDBACK
            if _is_negative_feedback(canon):
                return Intent.NEGATIVE_FEEDBACK
        if _is_followup(canon):
            return Intent.FOLLOWUP
        if canon in _CLARIFICATION:
            return Intent.CLARIFICATION

    return Intent.GENERAL
