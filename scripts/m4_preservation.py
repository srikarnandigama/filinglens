"""Read-only M4 preservation check for frozen data, labels, retrieval and M3 server code.

Usage (project root):
  .venv/Scripts/python.exe scripts/m4_preservation.py before
  .venv/Scripts/python.exe scripts/m4_preservation.py after   # compares with before
"""

import hashlib
import json
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filinglens.config import Settings  # noqa: E402
from filinglens.db import connection_options  # noqa: E402

TABLES = [
    "companies",
    "filings",
    "financial_facts",
    "metric_availability",
    "ingestion_snapshots",
    "retrieval_corpora",
    "corpus_documents",
    "corpus_chunks",
    "sections",
    "chunks",
]
FILE_GLOBS = [
    "evals/handwritten.jsonl",
    "evals/handwritten_v2.jsonl",
    "evals/corpus_v2_migration.json",
    "evals/results/retrieval*.json",
    "evals/results/retrieval*.md",
    "filinglens/retrieval/*.py",
    "filinglens/ingest/*.py",
    "mcp_servers/**/*.py",
    "mcp_servers/edgar_mcp/applicability.json",
    "db/migrations/00[123]_*.sql",
    "data/models/revisions.json",
    "tests/fixtures/*.json",
]


def snapshot() -> dict:
    files = sorted({p for g in FILE_GLOBS for p in ROOT.glob(g) if p.is_file()})
    result: dict = {"tables": {}, "migrations": {}, "files": {}}
    url = Settings().database_url
    with psycopg.connect(url, **connection_options(url)) as conn:
        conn.execute("SET default_transaction_read_only = on")
        for table in TABLES:
            n, digest = conn.execute(
                f"SELECT count(*), md5(string_agg(md5(t::text), '' ORDER BY md5(t::text))) "
                f"FROM {table} t"
            ).fetchone()
            result["tables"][table] = {"count": n, "content_md5": digest}
        for name, checksum in conn.execute(
            "SELECT name, checksum FROM schema_migrations WHERE name < '004' ORDER BY name"
        ):
            result["migrations"][name] = checksum
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        result["files"][rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> None:
    stage = sys.argv[1]
    current = snapshot()
    out = ROOT / "docs" / f"M4_PRESERVATION_{stage.upper()}.json"
    out.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    if stage == "after":
        before = json.loads((ROOT / "docs" / "M4_PRESERVATION_BEFORE.json").read_text())
        if current != before:
            changed = [
                f"{kind}:{key}"
                for kind in before
                for key in set(before[kind]) | set(current[kind])
                if before[kind].get(key) != current[kind].get(key)
            ]
            raise SystemExit(f"Protected content changed: {sorted(changed)}")
        print(f"Preserved: {len(TABLES)} tables, {len(current['files'])} files, migrations 001-003")
    else:
        print(f"Recorded {len(TABLES)} tables and {len(current['files'])} files")


if __name__ == "__main__":
    main()
