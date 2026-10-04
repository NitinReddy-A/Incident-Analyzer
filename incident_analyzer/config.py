"""Runtime configuration.

All configuration is read from environment variables (optionally loaded from a
``.env`` file in the working directory). Secrets are never given defaults and
are only required by the stage that needs them, so the dashboard and the
transition engine run without any credentials at all.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Relative to the working directory, like any CLI tool; override with
# INCIDENT_ANALYZER_DATA_DIR.
DEFAULT_DATA_DIR = Path("data") / "sample"

RAW_FILENAME = "incidents_raw.csv"
CURATED_FILENAME = "incidents_curated.csv"
CATEGORIZED_FILENAME = "incidents_categorized.csv"
TRANSITIONS_FILENAME = "transition_model.csv"


class ConfigurationError(RuntimeError):
    """Raised when a required setting is missing or malformed."""


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    pagerduty_api_token: str | None
    pagerduty_base_url: str
    openai_api_key: str | None
    llm_model: str
    dashboard_host: str
    dashboard_port: int

    @property
    def raw_path(self) -> Path:
        return self.data_dir / RAW_FILENAME

    @property
    def curated_path(self) -> Path:
        return self.data_dir / CURATED_FILENAME

    @property
    def categorized_path(self) -> Path:
        return self.data_dir / CATEGORIZED_FILENAME

    @property
    def transitions_path(self) -> Path:
        return self.data_dir / TRANSITIONS_FILENAME

    def require_pagerduty_token(self) -> str:
        if not self.pagerduty_api_token:
            raise ConfigurationError(
                "PAGERDUTY_API_TOKEN is not set. Create a read-only REST API key in "
                "PagerDuty and export it (or add it to .env)."
            )
        return self.pagerduty_api_token

    def require_openai_key(self) -> str:
        if not self.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY is not set. It is required for LLM classification only.")
        return self.openai_api_key


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {value!r}") from exc


def load_settings() -> Settings:
    # Only the working directory's .env is honoured; real environment
    # variables always take precedence over it.
    env_file = Path.cwd() / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)
    data_dir = Path(os.getenv("INCIDENT_ANALYZER_DATA_DIR") or DEFAULT_DATA_DIR)
    return Settings(
        data_dir=data_dir.expanduser().resolve(),
        pagerduty_api_token=os.getenv("PAGERDUTY_API_TOKEN") or None,
        pagerduty_base_url=os.getenv("PAGERDUTY_BASE_URL") or "https://api.pagerduty.com",
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        llm_model=os.getenv("INCIDENT_ANALYZER_LLM_MODEL") or "gpt-4o-mini",
        dashboard_host=os.getenv("INCIDENT_ANALYZER_HOST") or "127.0.0.1",
        dashboard_port=_int_env("INCIDENT_ANALYZER_PORT", 8050),
    )
