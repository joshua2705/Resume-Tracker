"""Central configuration, read once from the environment."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

try:  # load backend/.env if python-dotenv is installed (optional)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


class Settings:
    def __init__(self) -> None:
        self.user_name: str = os.getenv("USER_NAME", "Joshua").strip()
        # LlamaParse (LlamaCloud) for real PDF parsing
        self.llama_api_key: str = os.getenv("LLAMA_CLOUD_API_KEY", "llx-hI0NsWqftPRVkCPoMQLvLV90H3StNcmlTqIMY0bYO5jTp9w0").strip()
        # Gemini (Google) for scoring / question gen / coach chat
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
        self.frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip()
        self.data_file: Path = Path(__file__).resolve().parent / "data" / "store.json"

    @property
    def llama_enabled(self) -> bool:
        return bool(self.llama_api_key)

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
