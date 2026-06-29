"""Guardrails for the chat surface: input validation + token rate limiting.

These run in the coach router BEFORE the agent, so a bad or abusive request
never reaches the model. Pure-Python and dependency-free.
"""
from .input_validation import (GuardrailError, ValidationResult,
                               validate_chat_messages)
from .rate_limit import RateLimitError, coach_rate_limiter

__all__ = [
    "GuardrailError", "ValidationResult", "validate_chat_messages",
    "RateLimitError", "coach_rate_limiter",
]
