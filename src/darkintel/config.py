"""Runtime configuration for the darkintel bridge.

All values come from environment variables (prefix ``DARKINTEL_``) or a
local ``.env`` file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DARKINTEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Dragon is opt-in only — no default model. Skipped (like any role whose
    # provider key is missing) until the user sets their own Claude model id,
    # e.g. "anthropic:claude-opus-4-...", plus ANTHROPIC_API_KEY.
    llm_dragon: str | None = None
    llm_temperature_dragon: float = 0.4

    data_dir: Path = Path("data")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
