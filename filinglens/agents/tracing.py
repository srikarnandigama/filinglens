"""Trace recording to runs/trace_events with synchronous Psycopg in a worker thread (D053/D059)."""

import asyncio
import json
import threading
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from filinglens.db import connection_options


class TraceEvent(BaseModel):
    seq: int
    agent: str
    event_type: str
    payload: dict[str, Any]
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int | None = None


class RunTotals(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: Decimal = Decimal(0)
    latency_ms: int = 0


class TraceStore(Protocol):
    def create_run(self, run_id: UUID, question: str, config: dict) -> None: ...
    def append(self, run_id: UUID, event: TraceEvent) -> None: ...
    def finish(
        self, run_id: UUID, status: str, answer: dict | None, totals: RunTotals, error: dict | None
    ) -> None: ...


class MemoryTraceStore:
    """Used by replay and unit tests; keeps everything in memory."""

    def __init__(self) -> None:
        self.runs: dict[UUID, dict] = {}
        self.events: dict[UUID, list[TraceEvent]] = {}

    def create_run(self, run_id: UUID, question: str, config: dict) -> None:
        self.runs[run_id] = {"question": question, "config": config, "status": "running"}
        self.events[run_id] = []

    def append(self, run_id: UUID, event: TraceEvent) -> None:
        self.events[run_id].append(event)

    def finish(self, run_id, status, answer, totals, error) -> None:
        self.runs[run_id].update(status=status, answer=answer, totals=totals, error=error)


class PostgresTraceStore:
    """One synchronous connection per run; autocommit so traces survive a crashed run."""

    def __init__(self, database_url: str) -> None:
        self.conn = psycopg.connect(
            database_url, autocommit=True, **connection_options(database_url)
        )
        self.lock = threading.Lock()

    def close(self) -> None:
        self.conn.close()

    def create_run(self, run_id: UUID, question: str, config: dict) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO runs (id, question, config, status) VALUES (%s, %s, %s, 'running')",
                (run_id, question, Jsonb(config)),
            )

    def append(self, run_id: UUID, event: TraceEvent) -> None:
        with self.lock:
            self.conn.execute(
                """INSERT INTO trace_events (run_id, seq, agent, event_type, payload,
                input_tokens, output_tokens, latency_ms) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    run_id,
                    event.seq,
                    event.agent,
                    event.event_type,
                    Jsonb(event.payload),
                    event.input_tokens,
                    event.output_tokens,
                    event.latency_ms,
                ),
            )

    def finish(self, run_id, status, answer, totals: RunTotals, error) -> None:
        with self.lock:
            self.conn.execute(
                """UPDATE runs SET status=%s, answer=%s, total_input_tokens=%s,
                total_output_tokens=%s, total_cache_read_tokens=%s, total_cache_write_tokens=%s,
                cost_usd=%s, latency_ms=%s, error=%s, finished_at=%s WHERE id=%s""",
                (
                    status,
                    Jsonb(answer) if answer is not None else None,
                    totals.input_tokens,
                    totals.output_tokens,
                    totals.cache_read_tokens,
                    totals.cache_write_tokens,
                    totals.cost_usd,
                    totals.latency_ms,
                    Jsonb(error) if error is not None else None,
                    datetime.now(UTC),
                    run_id,
                ),
            )


def load_run(database_url: str, run_id: UUID) -> tuple[dict, list[TraceEvent]]:
    with psycopg.connect(database_url, **connection_options(database_url)) as conn:
        conn.execute("SET default_transaction_read_only = on")
        row = conn.execute(
            "SELECT question, config, status, answer, error FROM runs WHERE id=%s", (run_id,)
        ).fetchone()
        if row is None:
            raise LookupError(f"No run {run_id}")
        events = [
            TraceEvent(
                seq=r[0],
                agent=r[1],
                event_type=r[2],
                payload=r[3],
                input_tokens=r[4],
                output_tokens=r[5],
                latency_ms=r[6],
            )
            for r in conn.execute(
                """SELECT seq, agent, event_type, payload, input_tokens, output_tokens, latency_ms
                FROM trace_events WHERE run_id=%s ORDER BY seq""",
                (run_id,),
            )
        ]
    question, config, status, answer, error = row
    return {
        "question": question,
        "config": config,
        "status": status,
        "answer": answer,
        "error": error,
    }, events


class Recorder:
    """Assigns sequence numbers and forwards events to a store off the event loop."""

    def __init__(self, store: TraceStore, run_id: UUID) -> None:
        self.store = store
        self.run_id = run_id
        self.events: list[TraceEvent] = []
        self._seq = 0
        self._lock = asyncio.Lock()

    async def emit(
        self,
        agent: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int | None = None,
    ) -> TraceEvent:
        async with self._lock:
            self._seq += 1
            event = TraceEvent(
                seq=self._seq,
                agent=agent,
                event_type=event_type,
                payload=json.loads(json.dumps(payload, default=str)),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )
            self.events.append(event)
            await asyncio.to_thread(self.store.append, self.run_id, event)
            return event
