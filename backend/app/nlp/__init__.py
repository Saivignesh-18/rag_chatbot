"""Lightweight NLP preprocessing layer for the RAG chat pipeline.

Modules:
    normalization    - whitespace / punctuation cleanup, safe abbreviation expansion
    spelling         - conservative English spelling correction (symspellpy)
    intent_detection - rule-based basic-intent classifier
    basic_responses  - canned responses for basic intents (no LLM)
    preprocessing    - orchestrates the above into a single PreprocessResult

The public entry point is :func:`preprocess_query`.
"""
from app.nlp.preprocessing import PreprocessResult, preprocess_query

__all__ = ["PreprocessResult", "preprocess_query"]
