"""Lightweight small-talk detection.

Greetings ("hi", "hello") and simple acknowledgements ("ok", "thanks") are not
document questions, so they should get a friendly reply instead of the
document-only refusal. This check runs BEFORE retrieval in
``rag_service.answer_question``.

It is intentionally conservative: only very short messages that are essentially
pure greetings/acknowledgements match, so a real question that merely begins
with "hi ..." is never intercepted and still goes through the RAG pipeline.
"""
from __future__ import annotations

import re

# Canonical friendly replies (kept short and on-brand for a document assistant).
GREETING_REPLY = "Hello! 👋 How can I help you today? Ask me anything about your selected documents."
THANKS_REPLY = "You're welcome! Feel free to ask me anything else about your documents."
ACK_REPLY = "Got it! Let me know what you'd like to ask about your documents."

_GREETINGS = {
    "hi", "hii", "hiii", "hiya", "hey", "hey", "heyy", "helo", "hello", "helloo",
    "hallo", "yo", "howdy", "greetings", "hi there", "hey there", "hello there",
    "good morning", "good afternoon", "good evening", "good day", "gm",
    "namaste", "hola",
}

_THANKS = {
    "thanks", "thank you", "thank u", "thankyou", "thx", "thnx", "ty", "tysm",
    "thanks a lot", "thank you so much", "many thanks", "much appreciated",
    "appreciate it", "cheers",
}

_ACKS = {
    "ok", "okay", "okey", "oki", "k", "kk", "cool", "great", "nice", "got it",
    "gotcha", "sounds good", "alright", "all right", "fine", "perfect", "good",
    "understood", "noted", "yes", "yep", "yup", "sure", "no", "nope",
}

_PUNCT_OR_EMOJI = re.compile(r"[^\w\s]", flags=re.UNICODE)
_MULTISPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation/emoji, and collapse whitespace."""
    text = (text or "").strip().lower()
    text = _PUNCT_OR_EMOJI.sub("", text)
    text = _MULTISPACE.sub(" ", text).strip()
    return text


def detect_smalltalk(question: str) -> str | None:
    """Return a canned reply if ``question`` is pure small talk, else ``None``.

    Only messages of up to three words are considered, so genuine document
    questions are never captured here.
    """
    norm = _normalize(question)
    if not norm or len(norm.split()) > 3:
        return None
    if norm in _GREETINGS:
        return GREETING_REPLY
    if norm in _THANKS:
        return THANKS_REPLY
    if norm in _ACKS:
        return ACK_REPLY
    return None
