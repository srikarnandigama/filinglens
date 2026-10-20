"""M1 configuration does not require any LLM credentials."""

from datetime import date
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_RETRIEVAL_CORPUS = "corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = "postgresql://filinglens:filinglens@localhost:5432/filinglens"
    sec_user_agent: str
    snapshot_id: str = "2026-10-19-v1"
    ingestion_cutoff: date = date(2026, 10, 19)
    raw_dir: Path = ROOT / "data" / "raw"
    sec_requests_per_second: float = Field(default=8, gt=0, le=8)
    sec_max_attempts: int = Field(default=5, ge=1, le=10)
    retrieval_corpus: str = ACTIVE_RETRIEVAL_CORPUS

    @field_validator("retrieval_corpus", mode="before")
    @classmethod
    def active_corpus_when_unset(cls, value: str | None) -> str:
        return value if value and value.strip() else ACTIVE_RETRIEVAL_CORPUS

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
