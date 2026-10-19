"""Transactional numbered migrations; run from any working directory."""

import hashlib
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from filinglens.config import Settings  # noqa: E402
from filinglens.db import connection_options  # noqa: E402


def migrate(url: str, directory: Path | None = None) -> None:
    directory = directory or Path(__file__).parent / "migrations"
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(619263701)")
        conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            name TEXT PRIMARY KEY, checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
        for path in sorted(directory.glob("[0-9]*.sql")):
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            previous = conn.execute(
                "SELECT checksum FROM schema_migrations WHERE name=%s", (path.name,)
            ).fetchone()
            if previous:
                if previous[0] != checksum:
                    raise RuntimeError(f"Applied migration changed: {path.name}")
                continue
            conn.execute(sql)
            conn.execute(
                "INSERT INTO schema_migrations(name, checksum) VALUES (%s,%s)",
                (path.name, checksum),
            )
            print(f"Applied {path.name}")


if __name__ == "__main__":
    migrate(Settings().database_url)
