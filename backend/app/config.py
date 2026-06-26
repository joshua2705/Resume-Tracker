"""Central configuration, read once from the environment.

Extended with agentic-layer flags (agents, LangSmith, Gmail MCP, guardrails)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

try:  # load backend/.env if python-dotenv is installed (optional)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip())
    except (TypeError, ValueError):
        return default


class Settings:
    def __init__(self) -> None:
        self.user_name: str = os.getenv("USER_NAME", "Joshua").strip()
        # LlamaParse (LlamaCloud) for real PDF parsing
        self.llama_api_key: str = os.getenv("LLAMA_CLOUD_API_KEY", "").strip()
        # Gemini (Google) for scoring / question gen / coach chat
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
        self.frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip()
        self.data_file: Path = Path(__file__).resolve().parent / "data" / "store.json"

        # --- Agentic layer (LangGraph) ------------------------------------ #
        self.agents_enabled: bool = _flag("AGENTS_ENABLED", True)

        # LangSmith tracing
        self.langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "").strip()
        self.langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "resume-tracker").strip()

        # Gmail MCP
        self.gmail_mcp_enabled: bool = _flag("GMAIL_MCP_ENABLED", False)
        self.gmail_mcp_command: str = os.getenv("GMAIL_MCP_COMMAND", "npx").strip()
        self.gmail_mcp_args: list[str] = [
            a.strip() for a in os.getenv(
                "GMAIL_MCP_ARGS", "-y,@gongrzhe/server-gmail-autoauth-mcp"
            ).split(",") if a.strip()
        ]
        self.gmail_daily_scan: bool = _flag("GMAIL_DAILY_SCAN", False)
        self.gmail_scan_lookback_days: int = _int("GMAIL_SCAN_LOOKBACK_DAYS", 1)

        # Guardrails (chat)
        self.coach_max_input_chars: int = _int("COACH_MAX_INPUT_CHARS", 4000)
        self.coach_daily_token_budget: int = _int("COACH_DAILY_TOKEN_BUDGET", 200_000)
        self.coach_max_requests_per_min: int = _int("COACH_MAX_REQUESTS_PER_MIN", 12)

    @property
    def llama_enabled(self) -> bool:
        return bool(self.llama_api_key)

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def langsmith_enabled(self) -> bool:
        return bool(self.langsmith_api_key)

    @property
    def agents_active(self) -> bool:
        """Agents need the master switch AND a Gemini key (their LLM)."""
        return self.agents_enabled and self.gemini_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
