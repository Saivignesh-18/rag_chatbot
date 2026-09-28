"""Prompt construction for the document-grounded assistant.

Defines the strict system prompt and builds the context block from retrieved
chunks. The retrieval threshold gate (in rag_service) is the primary defence
against out-of-context answers; this prompt is the secondary defence.
"""
from __future__ import annotations

from collections.abc import Sequence

from app.services.retrieval_service import RetrievedChunk

# The exact phrase the assistant must use when the answer is not in the documents.
REFUSAL_MESSAGE = "I couldn't find this information in the selected documents."

SYSTEM_PROMPT = """You are a document-grounded AI assistant.

Your job is to answer questions ONLY using the document context provided to you.

Rules:

1. Never use external knowledge.
2. Never use your general model knowledge.
3. Never guess.
4. Never invent facts.
5. Never fabricate citations.
6. Never assume information that is not present.
7. Only make claims that are supported by the retrieved context.
8. If the answer cannot be found in the supplied context, say:

   "I couldn't find this information in the provided documents."

9. If the question is unrelated to the uploaded documents, do not answer it using general knowledge.
10. When possible, cite the document and page number.
"""


def build_context(chunks: Sequence[RetrievedChunk]) -> str:
    """Render retrieved chunks into a numbered, source-labelled context block."""
    blocks: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        location = f", page {chunk.page_number}" if chunk.page_number else ""
        header = f"[Source {i}: {chunk.document_name}{location}]"
        blocks.append(f"{header}\n{chunk.content}")
    return "\n\n---\n\n".join(blocks)


def build_user_prompt(question: str, context: str) -> str:
    """Assemble the final user prompt with the context and grounding instructions."""
    return (
        "Use ONLY the following document context to answer the question. "
        "If the answer is not contained in the context, respond EXACTLY with:\n"
        f'"{REFUSAL_MESSAGE}"\n\n'
        "Formatting rules for your answer:\n"
        "- Write in clear prose or markdown (headings, bullet points, bold) as appropriate.\n"
        "- Do NOT emit special citation markup or bracketed source tags such as "
        "\u3010...\u3011 or [oai_citation]. Sources are shown separately to the user.\n"
        "- If you reference a source, do so naturally, e.g. (SRS.pdf, page 2).\n\n"
        "Document context:\n"
        '"""\n'
        f"{context}\n"
        '"""\n\n'
        f"Question: {question}\n\n"
        "Answer (grounded only in the context above):"
    )


import re as _re

# Full-width citation brackets and zero/narrow-width spaces sometimes emitted by
# reasoning models. Removing them keeps answers clean; real citations are provided
# via the structured sources list.
_CITATION_TAG = _re.compile(r"\u3010[^\u3011]*\u3011")


def sanitize_answer(text: str) -> str:
    """Strip citation-markup artifacts and normalise unusual whitespace."""
    if not text:
        return ""
    text = text.replace("\u202f", " ").replace("\u200b", "").replace("\ufeff", "")
    text = _CITATION_TAG.sub("", text)
    text = _re.sub(r"[ \t]{2,}", " ", text)
    text = _re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()
