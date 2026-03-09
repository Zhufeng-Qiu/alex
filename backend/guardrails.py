"""
Guardrails for AI agents (8_enterprise guide Section 4).
Input sanitization, output size limits, and validation helpers.
"""

import json
import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

# Patterns that may indicate prompt injection (case-insensitive)
DANGEROUS_PATTERNS = [
    "ignore previous instructions",
    "disregard all prior",
    "forget everything",
    "new instructions:",
    "system:",
    "assistant:",
]


def sanitize_user_input(text: str) -> str:
    """
    Remove potential prompt injection attempts from user-provided text.
    Use when passing user data into agent prompts.
    """
    if not text or not isinstance(text, str):
        return ""
    text_lower = text.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in text_lower:
            logger.warning(f"Potential prompt injection detected: {pattern!r}")
            return "[INVALID INPUT DETECTED]"
    return text


def truncate_response(text: str, max_length: int = 50000) -> str:
    """
    Ensure responses don't exceed reasonable size (guard against runaway token usage).
    """
    if not text or not isinstance(text, str):
        return text
    if len(text) <= max_length:
        return text
    logger.warning(f"Response truncated from {len(text)} to {max_length} characters")
    return text[:max_length] + "\n\n[Response truncated due to length]"
