"""Input validation & sanitization for coach chat.

Checks, in order: non-empty, message count, per-message and total length,
control-character stripping. It also screens for prompt-injection / jailbreak
patterns: rather than hard-blocking (which frustrates legitimate users), it
flags them so the agent can be told to ignore embedded instructions and the
event is logged. Hard limits raise GuardrailError -> HTTP 400.
"""
from __future__ import annotations

import re
import unicodedata

from ..config import get_settings
from ..models import CoachMessage

MAX_MESSAGES = 60
MIN_CHARS = 1

# Patterns that commonly precede prompt-injection / jailbreak attempts.
_INJECTION_PATTERNS = [
    r"ignore (all |the |your |previous |above )+(instructions|prompts?)",
    r"disregard (the |your |all |previous )+(instructions|rules)",
    r"\byou are now\b",
    r"\bsystem prompt\b",
    r"\bdeveloper mode\b",
    r"\bjailbreak\b",
    r"reveal (your |the )?(system )?(prompt|instructions|rules)",
    r"\bact as (an? )?(dan|unfiltered|unrestricted)\b",
    r"pretend (you are|to be) (an? )?(unrestricted|evil|uncensored)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


class GuardrailError(ValueError):
    """Raised for hard validation failures (caller maps to HTTP 400)."""


class ValidationResult:
    def __init__(self, messages: list[CoachMessage], flagged: bool, reason: str,
                 chars: int) -> None:
        self.messages = messages          # sanitized
        self.flagged = flagged            # possible injection (soft)
        self.reason = reason
        self.chars = chars

    def as_safety(self) -> dict:
        return {"flagged": self.flagged, "reason": self.reason}


def _sanitize(text: str) -> str:
    # drop control chars except newline/tab, normalize, collapse whitespace runs
    text = "".join(ch for ch in text
                   if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[ \t]{3,}", "  ", text).strip()


def validate_chat_messages(messages: list[CoachMessage]) -> ValidationResult:
    s = get_settings()
    if not messages:
        raise GuardrailError("messages required")
    if len(messages) > MAX_MESSAGES:
        raise GuardrailError(f"too many messages (max {MAX_MESSAGES})")

    cleaned: list[CoachMessage] = []
    total = 0
    flagged = False
    reasons: list[str] = []
    last_user_text = ""

    for m in messages:
        role = "assistant" if m.role == "assistant" else "user"
        text = _sanitize(m.content or "")
        if role == "user":
            last_user_text = text
        if len(text) > s.coach_max_input_chars:
            raise GuardrailError(
                f"message too long (max {s.coach_max_input_chars} chars)")
        total += len(text)
        if role == "user" and _INJECTION_RE.search(text):
            flagged = True
            reasons.append("possible prompt-injection phrasing")
        cleaned.append(CoachMessage(role=role, content=text))

    if total > s.coach_max_input_chars * 4:
        raise GuardrailError("conversation too large")
    if len(last_user_text) < MIN_CHARS:
        raise GuardrailError("empty message")

    return ValidationResult(cleaned, flagged, "; ".join(sorted(set(reasons))), total)
