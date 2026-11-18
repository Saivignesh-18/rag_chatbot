"""Query rewriting / expansion for retrieval ONLY.

Given the (spell-corrected, context-resolved) natural query plus detected
topics, produce an EXPANDED string that adds domain synonyms/keywords to improve
vector recall. This expanded string is used solely to embed + search: it is
never shown to the user, never persisted as the message, and never passed to the
LLM as the question (the LLM always receives the natural question). Expansion is
purely additive and deterministic, so it cannot change the query's meaning.
"""
from __future__ import annotations

from app.nlp.entities import EntityResult, extract_entities
from app.nlp.transliteration import telugu_english_hints

# topic -> extra retrieval keywords (synonyms / facets) appended to the query.
_TOPIC_EXPANSIONS: dict[str, str] = {
    "skills": (
        "technical and professional skills, technologies, tools, frameworks, "
        "programming languages"
    ),
    "education": (
        "education, qualifications, degree, university, college, institution, "
        "graduation year, GPA"
    ),
    "experience": (
        "work experience, companies, job roles, titles, responsibilities, "
        "duration, employment history"
    ),
    "projects": "projects, project names, technologies used, description, outcomes",
    "certifications": (
        "certifications, certificate names, issuing organization, credentials"
    ),
    "contact": "contact details, email, phone number, address, LinkedIn, GitHub",
    "summary": "summary, overview, profile, objective, highlights",
    "achievements": "achievements, awards, accomplishments, honors, recognition",
}


def expand_query(query: str, entities: EntityResult | None = None) -> str:
    """Return a retrieval-optimised expansion of ``query``.

    - Appends topic synonym keywords for any detected document topic.
    - Appends English hints for romanized-Telugu tokens (Telgish support).
    - Returns the ORIGINAL ``query`` UNCHANGED when there is nothing to add, so
      callers can detect "no expansion" via equality.
    """
    base = (query or "").strip()
    if not base:
        return base

    try:
        ent = entities if entities is not None else extract_entities(base)

        additions: list[str] = []
        for topic in ent.topics:
            extra = _TOPIC_EXPANSIONS.get(topic)
            if extra:
                additions.append(extra)

        hints = telugu_english_hints(base)
        if hints:
            additions.append(" ".join(hints))

        if not additions:
            return base
        return base + " " + " ".join(additions)
    except Exception:  # noqa: BLE001 - expansion must never break a request
        return base
