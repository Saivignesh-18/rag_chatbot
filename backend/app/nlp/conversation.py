"""Conversation-context resolution for follow-up questions.

Turns a context-dependent follow-up ("what about projects?", "tell me more")
into a standalone retrieval question using RECENT HISTORY. Key safety property:
resolution anchors on the user's PREVIOUS QUESTION(S) only - never on the
assistant's previous answer - so we never carry invented facts forward. The
selected-document scope is preserved by the caller (rag_service); this module
only rewrites the query text.

Rule-based and LLM-free by design (cheap, deterministic, predictable).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

ROLE_USER = "user"

# Continuation follow-ups that carry NO new topic: re-ask the previous question
# and let the answer layer elaborate.
_ELABORATE = frozenset(
    {
        "tell me more", "more", "more details", "more detail", "explain that",
        "explain it", "explain", "elaborate", "can you elaborate", "please elaborate",
        "go on", "continue", "say more", "in detail", "explain in detail",
        "more info", "more information", "expand", "expand on that", "details",
        "what did you mention earlier", "what you mentioned earlier",
        "what did you say earlier", "give me another example", "another example",
        "one more example", "explain again", "explain it again", "again",
        "try again", "say it again", "once more",
    }
)

# New-topic follow-ups: "what about X", "how about X", "and X?", "also X".
_NEW_TOPIC_RE = re.compile(
    r"^(?:and|also|ok(?:ay)?\s+and|what\s+about|how\s+about|what\s+of|then\s+what\s+about)\s+(.*?)[\s?.!]*$",
    re.IGNORECASE,
)

# Trailing prepositional phrase that names the "domain" of a question, e.g.
# "...in my resume", "...of the report". Used to carry context onto a new topic.
_DOMAIN_RE = re.compile(r"\b(in|of|from|within|on|about)\b\s+(.+)$", re.IGNORECASE)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class FollowupResolution:
    resolved_query: str
    used_context: bool = True
    elaborate: bool = False


def _canon(text: str) -> str:
    text = (text or "").lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def last_user_question(history: list[tuple[str, str]] | None) -> str | None:
    """Return the most recent prior USER message content, or ``None``."""
    if not history:
        return None
    for role, content in reversed(history):
        if (role or "").lower() == ROLE_USER and content and content.strip():
            return content.strip()
    return None


def _carry_domain(anchor: str | None) -> str:
    """Extract a trailing 'in my resume' / 'of the report' style domain phrase."""
    if not anchor:
        return ""
    match = _DOMAIN_RE.search(anchor.strip())
    if not match:
        return ""
    return f"{match.group(1)} {match.group(2)}".strip().rstrip("?.! ")


def resolve_followup(
    current: str, history: list[tuple[str, str]] | None
) -> FollowupResolution | None:
    """Resolve a follow-up ``current`` against ``history``.

    Returns a :class:`FollowupResolution` with a standalone query, or ``None``
    when it cannot be resolved (the caller should then ask for clarification).
    """
    anchor = last_user_question(history)
    canon = _canon(current)
    if not canon:
        return None

    # 1) Continuation ("tell me more", "explain again") -> re-ask the anchor.
    if canon in _ELABORATE:
        if not anchor:
            return None
        return FollowupResolution(resolved_query=anchor, used_context=True, elaborate=True)

    # 2) New topic ("what about projects?") -> topic + carried domain.
    match = _NEW_TOPIC_RE.match((current or "").strip())
    if match:
        topic = _WHITESPACE_RE.sub(" ", match.group(1)).strip().rstrip("?.! ")
        # Only treat SHORT tails as follow-up topics; a long tail is a complete
        # question in its own right and should be used as-is.
        if topic and len(topic.split()) <= 4:
            domain = _carry_domain(anchor)
            resolved = f"{topic} {domain}".strip() if domain else topic
            return FollowupResolution(resolved_query=resolved, used_context=bool(domain))

    # 3) Not a resolvable follow-up (e.g. "what do you mean").
    return None
