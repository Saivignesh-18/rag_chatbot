"""Canned responses for basic conversational intents (no LLM involved).

``BASIC_RESPONSES`` holds the intents that ALWAYS short-circuit the RAG pipeline
with a fixed reply. POSITIVE_FEEDBACK is included: it is context-gated in
``intent_detection`` (only classified mid-conversation), so if it reaches here it
is safe to answer directly.

CLARIFICATION_PROMPT / NEGATIVE_FEEDBACK_PROMPT are used by the preprocessing
orchestrator when a follow-up/clarification cannot be resolved from history -
we ask the user for a bit more detail instead of guessing.
"""
from __future__ import annotations

from app.nlp.intent_detection import Intent

BASIC_RESPONSES: dict[Intent, str] = {
    Intent.GREETING: "Hello! How can I help you today?",
    Intent.GRATITUDE: "You're welcome! Happy to help.",
    Intent.GOODBYE: "Goodbye! Have a great day.",
    Intent.HELP: (
        "I'm a document assistant. Upload your documents (PDF, DOCX, or TXT), "
        "choose which ones to chat with, and ask questions about them. I answer "
        "using only your selected documents and show the sources I used. I don't "
        "rely on outside knowledge, so if an answer isn't in those documents I'll "
        "tell you."
    ),
    Intent.POSITIVE_FEEDBACK: (
        "Glad that was helpful! Ask me anything else about your documents."
    ),
}

# Shown when a follow-up/clarification cannot be resolved from the conversation.
CLARIFICATION_PROMPT = (
    "Could you add a little more detail about what you'd like to know - for "
    "example, the topic or section of the document you're interested in?"
)

# Shown on negative feedback when there is no previous question to re-answer.
NEGATIVE_FEEDBACK_PROMPT = (
    "Sorry that wasn't quite right. Could you rephrase or tell me what to focus "
    "on, and I'll try again using your documents?"
)


def is_basic_intent(intent: Intent) -> bool:
    """True if ``intent`` has a direct canned response (no RAG needed)."""
    return intent in BASIC_RESPONSES


def get_basic_response(intent: Intent) -> str | None:
    """Return the canned response for ``intent`` or ``None`` if it needs RAG."""
    return BASIC_RESPONSES.get(intent)
