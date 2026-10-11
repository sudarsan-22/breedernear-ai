from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    breedernear_backend: Literal["memory", "gcp"] = "memory"   # "gcp" = Firestore + Cloud Storage
    breedernear_model: str = "gemini-3.8-flash"
    breedernear_model_vision: str = ""      # photos and documents; empty = breedernear_model
    breedernear_model_agents: str = ""      # chat agents; empty = breedernear_model
    firebase_project: str = ""              # Firebase Authentication project for Google sign-in tokens
    breedernear_bucket: str = ""
    breedernear_region: str = "asia-south1"
    rate_limit_per_hour: int = 40          # AI calls per guest per hour
    rate_limit_per_ip_hour: int = 150      # AI calls per client IP per hour (shared networks)
    max_upload_mb: int = 5
    max_llm_calls_per_run: int = 20
    git_sha: str = "dev"
    # Browser origins allowed to call the API cross-origin: the Firebase Hosting site (static web app).
    cors_origins: list[str] = ["https://breedernear-ai-2026.web.app",
                               "https://breedernear-ai-2026.firebaseapp.com"]

    @field_validator("breedernear_model", "breedernear_model_vision", "breedernear_model_agents")
    @classmethod
    def reject_retiring_models(cls, value: str) -> str:
        # gemini-2.x retires on 20 Oct 2026, during judging (rule R2).
        if value.startswith("gemini-2") or value.startswith("gemini-1"):
            raise ValueError(f"{value} is retired or retiring; use a current Gemini Flash model")
        return value


def retry_options():
    """Retry Gemini calls that fail for capacity reasons (429 resource exhausted, 5xx), with backoff."""
    from google.genai import types

    return types.HttpRetryOptions(attempts=5, initial_delay=1.0, max_delay=16.0, exp_base=2.0,
                                  http_status_codes=[408, 429, 500, 502, 503, 504])


def vision_model() -> str:
    return get_settings().breedernear_model_vision or get_settings().breedernear_model


def agents_model() -> str:
    return get_settings().breedernear_model_agents or get_settings().breedernear_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
