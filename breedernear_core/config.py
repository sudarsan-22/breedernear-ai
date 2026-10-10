from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    breedernear_backend: Literal["memory", "gcp"] = "memory"   # "gcp" = Firestore + Cloud Storage
    breedernear_model: str = "gemini-3.8-flash"
    breedernear_bucket: str = ""
    breedernear_region: str = "asia-south1"
    rate_limit_per_hour: int = 40          # AI calls per guest per hour
    rate_limit_per_ip_hour: int = 150      # AI calls per client IP per hour (shared networks)
    max_upload_mb: int = 5
    max_llm_calls_per_run: int = 20
    git_sha: str = "dev"

    @field_validator("breedernear_model")
    @classmethod
    def reject_retiring_models(cls, value: str) -> str:
        # gemini-2.x retires on 20 Oct 2026, during judging (rule R2).
        if value.startswith("gemini-2") or value.startswith("gemini-1"):
            raise ValueError(f"{value} is retired or retiring; use a current Gemini Flash model")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
