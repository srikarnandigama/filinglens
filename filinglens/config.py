"""M1 configuration does not require any LLM credentials."""

from datetime import date
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = "postgresql://filinglens:filinglens@localhost:5432/filinglens"
    sec_user_agent: str
    snapshot_id: str = "2026-10-19-v1"
    ingestion_cutoff: date = date(2026, 10, 19)
    raw_dir: Path = ROOT / "data" / "raw"
    sec_requests_per_second: float = Field(default=8, gt=0, le=8)
    sec_max_attempts: int = Field(default=5, ge=1, le=10)

    @field_validator("sec_user_agent")
    @classmethod
    def descriptive_user_agent(cls, value: str) -> str:
        if "@" not in value or len(value.split()) < 2 or "your@email.com" in value.lower():
            raise ValueError(
                "SEC_USER_AGENT must identify the application and a real contact email"
            )
        return value

    @field_validator("snapshot_id")
    @classmethod
    def safe_snapshot_id(cls, value: str) -> str:
        if not value or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for c in value
        ):
            raise ValueError(
                "snapshot_id must contain only letters, digits, hyphens or underscores"
            )
        return value
