"""Lightweight, rule-based entity & keyword extraction for document queries.

No heavyweight NER model (keeps the service light and avoids model downloads).
Instead we use curated keyword "gazetteers" for the document topics this product
cares about (resumes, reports, specs): skills, education, experience, projects,
certifications, plus generic contact / summary / achievements. Fuzzy matching
(RapidFuzz/difflib) makes detection robust to minor residual typos.

Detected topics drive QUERY EXPANSION for retrieval; they are NEVER treated as
facts about a document (we only *retrieve* with them, then let the grounded LLM
decide whether the information is actually present).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.nlp.fuzzy import ratio

# topic -> trigger terms indicating the user is asking about that topic.
_TOPIC_TRIGGERS: dict[str, tuple[str, ...]] = {
    "skills": (
        "skill", "skills", "skillset", "technologies", "technology", "tech stack",
        "tools", "expertise", "proficiency", "programming languages", "languages",
        "stack", "competencies",
    ),
    "education": (
        "education", "qualification", "qualifications", "degree", "degrees",
        "academics", "academic", "study", "studies", "university", "college",
        "school", "graduation", "cgpa", "gpa", "major",
    ),
    "experience": (
        "experience", "employment", "job", "jobs", "career", "company", "companies",
        "role", "roles", "position", "positions", "responsibilities", "tenure",
        "designation", "worked",
    ),
    "projects": (
        "project", "projects", "portfolio", "work samples", "case study",
        "case studies",
    ),
    "certifications": (
        "certification", "certifications", "certificate", "certificates",
        "certified", "credential", "credentials", "licenses", "license",
    ),
    "contact": (
        "contact", "email", "phone", "mobile", "address", "linkedin", "github",
        "website", "portfolio link",
    ),
    "summary": (
        "summary", "summarise", "summarize", "overview", "objective", "profile",
        "tldr", "gist", "highlights", "brief",
    ),
    "achievements": (
        "achievement", "achievements", "awards", "accomplishments", "honors",
        "honours", "recognition",
    ),
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z+#.]*")
_FUZZY_CUTOFF = 88.0

# Common query words that are not useful as retrieval keywords.
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "of", "in", "on", "to", "is", "are", "was", "were", "what",
        "which", "who", "whom", "whose", "where", "when", "why", "how", "do", "does",
        "did", "list", "show", "give", "tell", "me", "my", "your", "this", "that",
        "these", "those", "about", "from", "and", "or", "for", "with", "please",
        "can", "could", "you", "i", "it", "its", "there", "here", "any", "all",
        "some", "find", "inside", "document", "documents", "doc", "docs", "pdf",
        "file", "files", "mentioned", "have", "has",
    }
)


@dataclass
class EntityResult:
    topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    @property
    def has_topic(self) -> bool:
        return bool(self.topics)


def _detect_topics(text_lower: str, tokens_lower: list[str]) -> list[str]:
    topics: list[str] = []
    token_set = set(tokens_lower)
    for topic, triggers in _TOPIC_TRIGGERS.items():
        matched = False
        for trig in triggers:
            if " " in trig:
                if trig in text_lower:
                    matched = True
                    break
            elif trig in token_set:
                matched = True
                break
            else:
                # fuzzy for single tokens (handles minor residual typos)
                for tok in tokens_lower:
                    if len(tok) >= 4 and ratio(tok, trig) >= _FUZZY_CUTOFF:
                        matched = True
                        break
                if matched:
                    break
        if matched:
            topics.append(topic)
    return topics


def _extract_keywords(tokens: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        low = tok.lower()
        if low in _STOPWORDS or len(low) < 3 or low in seen:
            continue
        seen.add(low)
        out.append(tok)
    return out


def extract_entities(text: str) -> EntityResult:
    """Return detected document topics and salient keywords for ``text``."""
    if not text or not text.strip():
        return EntityResult()
    try:
        text_lower = text.lower()
        tokens = _WORD_RE.findall(text)
        tokens_lower = [t.lower() for t in tokens]
        topics = _detect_topics(text_lower, tokens_lower)
        keywords = _extract_keywords(tokens)
        return EntityResult(topics=topics, keywords=keywords)
    except Exception:  # noqa: BLE001 - extraction must never break a request
        return EntityResult()
