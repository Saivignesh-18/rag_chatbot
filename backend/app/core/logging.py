"""Centralised logging configuration.

Provides a helper to configure structured, readable logging. Secrets (API keys,
passwords, tokens) must NEVER be passed to the logger.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers on reload.
    root.handlers.clear()
    root.addHandler(handler)

    # Reduce noise from third-party libraries.
    for noisy in ("httpx", "httpcore", "urllib3", "python_multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
