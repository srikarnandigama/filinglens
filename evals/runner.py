"""Eval runner (SPEC §13.3; D090): TOML config, disk cache, resumability and a hard spend cap.

Every answer is written atomically to evals/cache/<system_config_hash>/<question_id>.json and is
the resume checkpoint: rerunning a config costs nothing for questions already answered. Each
invocation enforces its spend cap by reserving each in-flight question's maximum cost before
scheduling it; at the cap it schedules nothing new, lets in-flight work finish and marks the rest
skipped_spend_cap. --replay-only serves only cached records and never builds an SDK client.
"""

import argparse
import asyncio
import hashlib
import json
import os
import time
import tomllib
import uuid
from collections import Counter
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from evals.generate import (
    DRAFT_PATH,
    FROZEN_PATH,
    MANIFEST_PATH,
    SUBSET_PATH,
    ids_sha256,
    load_frozen,
    sha256_file,
)
from filinglens.config import ROOT

RUNNER_VERSION = "runner-v1"
CACHE_DIR = ROOT / "evals" / "cache"
RUNS_DIR = ROOT / "evals" / "results" / "runs"
HANDWRITTEN = ROOT / "evals" / "handwritten_v2.jsonl"
B2_META = ROOT / "evals" / "b2_contexts_v1.meta.jsonl"
RETRY_DELAYS = (2.0, 4.0, 8.0)
# Per-question reservations for the spend cap (D090); the system uses its max_cost_usd.
DEFAULT_RESERVE = {"b0": Decimal("0.10"), "b1": Decimal("0.40"), "b2": Decimal("0.20")}
# The frozen Option C test subset (D105): the 100-question sample plus 80 stratified questions.
SUBSET_180_SHA256 = "242fbea020b2570040d5af4dfc7512be4e152763e673bb693319492c23f16e76"


def subset_ids(path: Path | None = None, expected: str = SUBSET_180_SHA256) -> set[str]:
    data = json.loads((path or SUBSET_PATH).read_text(encoding="utf-8"))
    if ids_sha256(data["ids"]) != expected:
        raise ValueError("questions_v1.subset180.json does not match its frozen hash (D105)")
    return set(data["ids"])


class ReplayMiss(RuntimeError):
    pass


@dataclass
class SystemConfig:
    id: str
    kind: str  # system | b0 | b1 | b2
    model_env: str | None = None
    model_index: int | None = None  # for comma-separated env vars (BASELINE_MODELS)
    batch: bool = False
    max_uses: int = 5
    max_cost_usd: Decimal = Decimal("0.50")
    reserve_usd: Decimal | None = None
    flags: dict[str, Any] = field(default_factory=dict)  # RunConfig overrides (M6 ablations)

    def reserve(self) -> Decimal:
        if self.kind == "system":
            return self.max_cost_usd
        return self.reserve_usd if self.reserve_usd is not None else DEFAULT_RESERVE[self.kind]


@dataclass
class EvalConfig:
    name: str
    split: str  # dev | test | probe | handwritten
    sample: str  # "all" | "sample_100" | "subset_180" | an integer
    systems: list[SystemConfig]
    spend_cap_usd: Decimal
    seed: int = 20261109
    concurrency: int = 4
    questions: str = "frozen"  # frozen | draft (tests only)
    ids: list[str] = field(default_factory=list)  # explicit question list (smoke set)


def load_config(path: Path) -> EvalConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    systems = [
        SystemConfig(
            id=s["id"],
            kind=s["kind"],
            model_env=s.get("model_env"),
            model_index=s.get("model_index"),
            batch=bool(s.get("batch", False)),
            max_uses=int(s.get("max_uses", 5)),
            max_cost_usd=Decimal(str(s.get("max_cost_usd", "0.50"))),
            reserve_usd=Decimal(str(s["reserve_usd"])) if "reserve_usd" in s else None,
            flags=dict(s.get("flags", {})),
        )
        for s in data["systems"]
    ]
    for s in systems:
        if s.kind not in ("system", "b0", "b1", "b2"):
            raise ValueError(f"unknown system kind {s.kind}")
        if s.batch and s.kind not in ("b1", "b2"):
            raise ValueError("Batch API is approved for B1 and B2 only (D088/D089)")
    return EvalConfig(
        name=data["name"],
        split=data["split"],
        sample=str(data.get("sample", "all")),
        systems=systems,
        spend_cap_usd=Decimal(str(data["spend_cap_usd"])),
        seed=int(data.get("seed", 20261109)),
        concurrency=int(data.get("concurrency", 4)),
        questions=data.get("questions", "frozen"),
        ids=list(data.get("ids", [])),
    )


# ---------------------------------------------------------------- questions


def load_questions(cfg: EvalConfig) -> list[dict[str, Any]]:
    if cfg.split == "handwritten":
        rows = [json.loads(line) for line in HANDWRITTEN.read_text(encoding="utf-8").splitlines()]
        return [r | {"template": "handwritten", "split": "handwritten"} for r in rows]
    if cfg.questions == "frozen":
        records = load_frozen(FROZEN_PATH, MANIFEST_PATH)  # hash-checked (D084)
    else:
        records = [json.loads(line) for line in DRAFT_PATH.read_text(encoding="utf-8").splitlines()]
    chosen = [r for r in records if r["split"] == cfg.split]
    if cfg.ids:
        wanted = set(cfg.ids)
        chosen = [r for r in chosen if r["id"] in wanted]
        if len(chosen) != len(wanted):
            raise ValueError("config ids are not all in the requested split")
    elif cfg.sample == "sample_100":
        chosen = [r for r in chosen if r["sample_100"]]
    elif cfg.sample == "subset_180":
        wanted = subset_ids()
        chosen = [r for r in chosen if r["id"] in wanted]
        if len(chosen) != len(wanted):
            raise ValueError("subset_180 ids are not all in the requested split")
    elif cfg.sample != "all":
        chosen = stratified(chosen, int(cfg.sample), cfg.seed)
    return schedule(chosen, cfg.seed)


def _rank(seed: int, qid: str) -> str:
    return hashlib.sha256(f"{seed}|run|{qid}".encode()).hexdigest()


def stratified(records: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    """n questions stratified by template (largest remainder), seeded order within each."""
    by: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by.setdefault(r["template"], []).append(r)
    total = len(records)
    quotas = {t: Decimal(n * len(v)) / Decimal(total) for t, v in by.items()}
    alloc = {t: int(q) for t, q in quotas.items()}
    extra = n - sum(alloc.values())
    for t in sorted(quotas, key=lambda t: (-(quotas[t] - alloc[t]), t))[:extra]:
        alloc[t] += 1
    out = []
    for t, items in by.items():
        out += sorted(items, key=lambda r: _rank(seed, r["id"]))[: alloc[t]]
    return out


def schedule(records: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    """Seeded order, interleaved by template so a capped run covers a stratified prefix."""
    by: dict[str, list[dict[str, Any]]] = {}
    for r in sorted(records, key=lambda r: _rank(seed, r["id"])):
        by.setdefault(r["template"], []).append(r)
    out, i = [], 0
    while any(i < len(v) for v in by.values()):
        out += [v[i] for _, v in sorted(by.items()) if i < len(v)]
        i += 1
    return out


def question_sha(q: dict[str, Any]) -> str:
    return hashlib.sha256(q["question"].encode()).hexdigest()


# ---------------------------------------------------------------- cache (D090)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def config_hash(settings: dict[str, Any]) -> str:
    return hashlib.sha256(canonical({**settings, "runner": RUNNER_VERSION}).encode()).hexdigest()


class Cache:
    def __init__(self, root: Path = CACHE_DIR) -> None:
        self.root = root

    def path(self, system_hash: str, qid: str) -> Path:
        return self.root / system_hash / f"{qid}.json"

    def get(self, system_hash: str, q: dict[str, Any]) -> dict[str, Any] | None:
        path = self.path(system_hash, q["id"])
        if not path.exists():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("question_sha") != question_sha(q):
            return None  # the question text changed: a miss, never a silent reuse
        return record

    def put(self, system_hash: str, record: dict[str, Any]) -> None:
        path = self.path(system_hash, record["question_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(
            json.dumps(record, indent=1, sort_keys=True, default=str), encoding="utf-8"
        )
        os.replace(temporary, path)


# ---------------------------------------------------------------- spend cap


class SpendCap:
    """Hard cap per invocation: spent + reserved for in-flight work must stay within it."""

    def __init__(self, cap: Decimal) -> None:
        self.cap = cap
        self.spent = Decimal(0)
        self.reserved = Decimal(0)
        self.stopped = False

    def try_reserve(self, amount: Decimal) -> bool:
        if self.stopped or self.spent + self.reserved + amount > self.cap:
            self.stopped = True
            return False
        self.reserved += amount
        return True

    def settle(self, reserved: Decimal, actual: Decimal) -> None:
        self.reserved -= reserved
        self.spent += actual


# ---------------------------------------------------------------- runner


@dataclass
class Deps:
    """Everything with side effects, injectable for offline tests."""

    anthropic_client: Any = None  # AsyncAnthropic-like
    system_runner: Any = None  # async (question, system, handwritten) -> partial record
    b2_context: Any = None  # (question) -> (text, meta)
    prices: Any = None  # PriceTable
    web_search_per_1000: Decimal | None = None
    batch_multiplier: Decimal | None = None
    models: dict[str, str] = field(default_factory=dict)  # env var -> model id
    sleep: Any = asyncio.sleep
    system_settings: dict[str, Any] = field(default_factory=dict)  # for the system's hash
    # (system configs) -> async context manager holding shared resources (the system's MCP hub);
    # Runner.run enters it once, before any worker starts, and exits it in the same task (D103).
    lifespan: Any = None


def system_settings(system: SystemConfig, deps: Deps, cfg: EvalConfig) -> dict[str, Any]:
    from evals.baselines import BaselineSpec

    if system.kind == "system":
        return {
            "kind": "system",
            **deps.system_settings,
            "flags": system.flags,
            "max_cost_usd": str(system.max_cost_usd),
        }
    model = deps.models.get(model_key(system))
    if not model:  # the model ID is part of the cache key; never hash a blank (D090)
        raise ValueError(f"no model ID resolved for {system.id} ({model_key(system)})")
    spec = BaselineSpec(
        system.kind,
        model,
        max_uses=system.max_uses,
        batch=system.batch,
    )
    out = spec.settings() | {"batch": system.batch}
    if system.kind == "b2":
        out["b2_meta_sha256"] = sha256_file(B2_META) if B2_META.exists() else None
    return out


class Runner:
    def __init__(
        self, cfg: EvalConfig, deps: Deps, cache: Cache | None = None, replay_only: bool = False
    ) -> None:
        self.cfg = cfg
        self.deps = deps
        self.cache = cache or Cache()
        self.replay_only = replay_only
        self.cap = SpendCap(cfg.spend_cap_usd)
        self.summary: dict[str, Any] = {"counts": Counter(), "systems": {}}

    async def run(self) -> dict[str, Any]:
        """Opens shared resources once, in this task, before any worker starts, and closes them
        here on every exit path (completion, spend cap, error, Ctrl+C); the summary is always
        finalized, with its status (D103)."""
        self.summary |= {
            "name": self.cfg.name,
            "started": datetime.now(UTC).isoformat(),
            "status": "running",
        }
        try:
            async with AsyncExitStack() as stack:
                systems = [s for s in self.cfg.systems if s.kind == "system"]
                if systems and self.deps.lifespan is not None and not self.replay_only:
                    await stack.enter_async_context(self.deps.lifespan(systems))
                results = await self._run_systems()
            self.summary["status"] = "completed"
            return {"summary": self.summary, "records": results}
        except BaseException as exc:
            interrupted = isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError))
            self.summary["status"] = "interrupted" if interrupted else "error"
            self.summary["error"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
            raise
        finally:
            self.summary |= {
                "finished": datetime.now(UTC).isoformat(),
                "spent_usd": str(self.cap.spent),
                "spend_cap_usd": str(self.cap.cap),
                "stopped_by_cap": self.cap.stopped,
            }
            self.summary["counts"] = dict(self.summary["counts"])

    async def _run_systems(self) -> dict[str, list[dict[str, Any]]]:
        questions = load_questions(self.cfg)
        self.summary["questions"] = len(questions)
        results: dict[str, list[dict[str, Any]]] = {}
        for system in self.cfg.systems:
            settings = system_settings(system, self.deps, self.cfg)
            shash = config_hash(settings)
            self.summary["systems"][system.id] = {"config_hash": shash, "settings": settings}
            if system.batch and not self.replay_only:
                results[system.id] = await self._run_batch(system, shash, questions)
            else:
                results[system.id] = await self._run_realtime(system, shash, questions)
        return results

    def _base(self, system: SystemConfig, shash: str, q: dict[str, Any]) -> dict[str, Any]:
        return {
            "question_id": q["id"],
            "question_sha": question_sha(q),
            "system_id": system.id,
            "system_kind": system.kind,
            "system_config_hash": shash,
            "split": q["split"],
        }

    async def _run_realtime(self, system, shash, questions) -> list[dict[str, Any]]:
        semaphore = asyncio.Semaphore(self.cfg.concurrency)
        records: list[dict[str, Any] | None] = [None] * len(questions)

        async def one(i: int, q: dict[str, Any]) -> None:
            cached = self.cache.get(shash, q)
            if cached is not None:
                records[i] = cached | {"cached": True}
                self.summary["counts"][f"{system.id}:cached"] += 1
                return
            if self.replay_only:
                raise ReplayMiss(f"{system.id}: no cached record for {q['id']}")
            async with semaphore:  # FIFO: questions start, and reserve, in schedule order
                reserve = system.reserve()
                if not self.cap.try_reserve(reserve):
                    records[i] = self._base(system, shash, q) | {"status": "skipped_spend_cap"}
                    self.summary["counts"][f"{system.id}:skipped_spend_cap"] += 1
                    return
                record = await self._answer(system, shash, q)
            self.cap.settle(reserve, Decimal(record.get("cost_usd") or 0))
            self.cache.put(shash, record)
            records[i] = record | {"cached": False}
            self.summary["counts"][f"{system.id}:{record['status']}"] += 1

        tasks = [asyncio.create_task(one(i, q)) for i, q in enumerate(questions)]
        try:
            await asyncio.gather(*tasks)
        except BaseException:  # stop the other workers before shared resources close
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        return [r for r in records if r is not None]

    async def _answer(self, system: SystemConfig, shash: str, q: dict[str, Any]) -> dict[str, Any]:
        base = self._base(system, shash, q)
        handwritten = q["template"] == "handwritten"
        started = datetime.now(UTC).isoformat()
        if system.kind == "system":
            try:
                out = await self.deps.system_runner(q, system, handwritten)
                status = "done" if out.get("run_status") == "done" else "error"
            except Exception as exc:  # recorded, never silently dropped
                out, status = (
                    {
                        "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
                        "cost_usd": "0",
                    },
                    "error",
                )
            return (
                base
                | out
                | {
                    "status": status,
                    "attempts": 1,
                    "started_at": started,
                    "finished_at": datetime.now(UTC).isoformat(),
                }
            )
        return (
            base
            | await self._baseline_realtime(system, q, handwritten)
            | {"started_at": started, "finished_at": datetime.now(UTC).isoformat()}
        )

    def _params(self, system: SystemConfig, q: dict[str, Any], handwritten: bool):
        from evals.baselines import BaselineSpec, build_params

        spec = BaselineSpec(
            system.kind, self.deps.models[model_key(system)], system.max_uses, system.batch
        )
        context, meta = (None, None)
        if system.kind == "b2":
            context, meta = self.deps.b2_context(q)
        return spec, build_params(spec, q, context, handwritten=handwritten), meta

    def _cost(self, model: str, usage: dict[str, int], batched: bool) -> Decimal:
        from evals.baselines import cost_usd

        return cost_usd(
            usage,
            self.deps.prices.prices[model],
            self.deps.web_search_per_1000,
            self.deps.batch_multiplier if batched else None,
        )

    async def _baseline_realtime(self, system, q, handwritten) -> dict[str, Any]:
        from evals.baselines import call_realtime, prediction_of

        spec, params, meta = self._params(system, q, handwritten)
        error, result, attempt = None, None, 0
        while result is None and error is None:
            attempt += 1
            try:
                result = await call_realtime(self.deps.anthropic_client, params)
            except Exception as exc:  # retry only transient API errors
                if attempt > len(RETRY_DELAYS) or not retryable(exc):
                    error = {"type": type(exc).__name__, "message": str(exc)[:500]}
                else:
                    await self.deps.sleep(RETRY_DELAYS[attempt - 1])
        if result is None:
            return {"status": "error", "error": error, "cost_usd": "0", "attempts": attempt}
        return {
            "status": "done",
            "prediction": prediction_of(result, handwritten),
            "raw_output": result.text,
            "stop_reason": result.stop_reason,
            "usage": result.usage,
            "cost_usd": str(self._cost(spec.model, result.usage, batched=False)),
            "latency_ms": result.latency_ms,
            "latency_note": None,
            "request_ids": result.request_ids,
            "b2_context": meta,
            "attempts": attempt,
        }

    async def _run_batch(self, system, shash, questions) -> list[dict[str, Any]]:
        from evals.baselines import prediction_of, run_batch

        records: dict[str, dict[str, Any]] = {}
        todo: list[tuple[dict[str, Any], Any, dict[str, Any], Any]] = []
        reserve = system.reserve()
        for q in questions:
            cached = self.cache.get(shash, q)
            if cached is not None:
                records[q["id"]] = cached | {"cached": True}
                self.summary["counts"][f"{system.id}:cached"] += 1
            elif self.cap.try_reserve(reserve):
                spec, params, meta = self._params(system, q, q["template"] == "handwritten")
                todo.append((q, spec, params, meta))
            else:
                records[q["id"]] = self._base(system, shash, q) | {"status": "skipped_spend_cap"}
                self.summary["counts"][f"{system.id}:skipped_spend_cap"] += 1
        if todo:
            started = datetime.now(UTC).isoformat()
            results = await run_batch(
                self.deps.anthropic_client,
                {q["id"]: params for q, _, params, _ in todo},
                sleep=self.deps.sleep,
            )
            for q, spec, _params, meta in todo:
                result = results[q["id"]]
                handwritten = q["template"] == "handwritten"
                ok = result.stop_reason is not None and not result.stop_reason.startswith("batch_")
                cost = (
                    self._cost(spec.model, result.usage, batched=True)
                    if result.usage
                    else Decimal(0)
                )
                record = self._base(system, shash, q) | {
                    "status": "done" if ok else "error",
                    "error": None if ok else {"type": result.stop_reason},
                    "prediction": prediction_of(result, handwritten) if ok else None,
                    "raw_output": result.text,
                    "stop_reason": result.stop_reason,
                    "usage": result.usage,
                    "cost_usd": str(cost),
                    "latency_ms": None,
                    "latency_note": "batch, not comparable",
                    "b2_context": meta,
                    "started_at": started,
                    "finished_at": datetime.now(UTC).isoformat(),
                    "attempts": 1,
                }
                self.cap.settle(reserve, cost)
                self.cache.put(shash, record)
                records[q["id"]] = record | {"cached": False}
                self.summary["counts"][f"{system.id}:{record['status']}"] += 1
        return [records[q["id"]] for q in questions if q["id"] in records]


def model_key(system: SystemConfig) -> str:
    return (
        f"{system.model_env}[{system.model_index}]"
        if system.model_index is not None
        else (system.model_env or "")
    )


def resolve_model(system: SystemConfig, settings: Any) -> str:
    """A model ID only from the runtime Settings (env vars or .env), e.g. BASELINE_MODELS index 0
    (D087)."""
    value = getattr(settings, (system.model_env or "").lower(), None)
    if not value:
        raise ValueError(f"Set {system.model_env} in .env (model IDs come only from env vars).")
    if system.model_index is not None:
        parts = [m.strip() for m in value.split(",") if m.strip()]
        if system.model_index >= len(parts):
            raise ValueError(f"{system.model_env} has no entry {system.model_index}")
        return parts[system.model_index]
    return value.strip()


def retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status in (408, 409, 429) or status >= 500
    return type(exc).__name__ in ("APIConnectionError", "APITimeoutError")


# ---------------------------------------------------------------- live wiring and CLI


def live_deps(cfg: EvalConfig) -> Deps:
    """Real clients and prices (Phase C/D only); fails before any call if a price is missing."""
    import anthropic

    from evals import b2_context
    from filinglens.agents.settings import RuntimeSettings
    from filinglens.llm.pricing import PRICING_PATH, PriceTable

    settings = RuntimeSettings()
    prices = PriceTable.load()
    extra = tomllib.loads(PRICING_PATH.read_text(encoding="utf-8"))
    models = {model_key(s): resolve_model(s, settings) for s in cfg.systems if s.model_env}
    needed = {m for m in models.values() if m}
    prices.require(needed)
    if any(s.kind == "b1" for s in cfg.systems) and "web_search" not in extra.get("tools", {}):
        raise ValueError("pricing.toml needs [tools.web_search] usd_per_1000 for B1")
    if any(s.batch for s in cfg.systems) and "batch_multiplier" not in extra.get("eval", {}):
        raise ValueError("pricing.toml needs [eval] batch_multiplier for batched systems")
    deps = Deps(
        anthropic_client=anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(), max_retries=4, timeout=300.0
        ),
        prices=prices,
        web_search_per_1000=_price(extra, "tools", "web_search", "usd_per_1000"),
        batch_multiplier=_price(extra, "eval", "batch_multiplier"),
        models=models,
    )
    if any(s.kind == "b2" for s in cfg.systems):
        deps.b2_context = b2_context.frozen_context_loader(settings)
    if any(s.kind == "system" for s in cfg.systems):
        deps.system_runner, deps.system_settings, deps.lifespan = system_runner(settings, prices)
    return deps


def preflight(
    cfg: EvalConfig,
    settings: Any = None,
    deps: Deps | None = None,
    retrieve: Any = None,
    count_facts: Any = None,
) -> dict[str, Any]:
    """Phase C checks before any spend: the API key is set, the question set matches its
    manifest, every model resolves from Settings, has prices and is accessible (models.retrieve
    generates nothing), and the database holds the snapshot. Reports key names, never values."""
    if settings is None:
        from filinglens.agents.settings import RuntimeSettings

        settings = RuntimeSettings()
    if settings.anthropic_api_key is None:
        raise ValueError("Set ANTHROPIC_API_KEY in .env")
    questions = load_questions(cfg)
    deps = deps or live_deps(cfg)
    models = set(deps.models.values()) | set(deps.system_settings.get("models", {}).values())
    if deps.prices is not None:
        deps.prices.require(models)
    if retrieve is None:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
        retrieve = lambda model: client.models.retrieve(model).id  # noqa: E731
    accessible = {m: retrieve(m) == m for m in sorted(models)}
    if not all(accessible.values()):
        raise ValueError(f"model access failed: {accessible}")
    facts = (count_facts or _count_facts)(settings)
    if not facts:
        raise ValueError(f"no financial_facts for snapshot {settings.snapshot_id}")
    return {
        "config": cfg.name,
        "questions": len(questions),
        "question_set": (
            "handwritten_v2 (frozen M2 labels)"
            if cfg.split == "handwritten"
            else "frozen, manifest hash ok"
            if cfg.questions == "frozen"
            else cfg.questions
        ),
        "models": deps.models | deps.system_settings.get("models", {}),
        "accessible": accessible,
        "priced": sorted(models),
        "web_search_per_1000": deps.web_search_per_1000,
        "batch_multiplier": deps.batch_multiplier,
        "snapshot_facts": facts,
        "spend_cap_usd": cfg.spend_cap_usd,
    }


def _count_facts(settings: Any) -> int:
    import psycopg

    from filinglens.db import connection_options

    url = settings.database_url
    with psycopg.connect(url, **connection_options(url)) as conn:
        row = conn.execute(
            "SELECT count(*) FROM financial_facts WHERE snapshot_id = %s", (settings.snapshot_id,)
        ).fetchone()
    return int(row[0]) if row else 0


def _price(data: dict[str, Any], *keys: str) -> Decimal | None:
    """An optional decimal-string price from pricing.toml's eval tables; None when absent."""
    node: Any = data
    for key in keys:
        node = node.get(key, {}) if isinstance(node, dict) else {}
    return Decimal(node) if isinstance(node, str) and node.strip() else None


def system_keyed(settings: Any) -> dict[str, Any]:
    """The system settings that key its cache: resolved model IDs, prompt hashes, snapshot,
    corpus and token budget. Needs no client, MCP server or database."""
    from filinglens.agents.orchestrator import RunConfig, load_prompts, resolve_models

    base = RunConfig(max_run_tokens=settings.max_run_tokens)
    return {
        "models": resolve_models(base, settings),
        "prompts": {name: sha for name, (_, sha) in load_prompts().items()},
        "snapshot_id": settings.snapshot_id,
        "corpus_id": settings.retrieval_corpus,
        "max_run_tokens": settings.max_run_tokens,
    }


def replay_deps(cfg: EvalConfig, settings: Any = None) -> Deps:
    """Only what keys the cache, so a replay hits the live run's records: model IDs from
    Settings and the system's keyed settings. No SDK client, MCP server or database (D103)."""
    if settings is None:
        from filinglens.agents.settings import RuntimeSettings

        settings = RuntimeSettings()
    deps = Deps(
        models={model_key(s): resolve_model(s, settings) for s in cfg.systems if s.model_env}
    )
    if any(s.kind == "system" for s in cfg.systems):
        deps.system_settings = system_keyed(settings)
    return deps


def system_runner(settings: Any, prices: Any):
    """A runner sharing one MCP hub across questions, the settings that key its cache, and the
    lifespan that opens that hub once per invocation and closes it (D103)."""
    from evals import system_adapter
    from filinglens.agents import mcp_client
    from filinglens.agents.orchestrator import RunConfig

    hubs: dict[str, Any] = {}  # retrieval mode -> open hub, only inside the lifespan
    keyed = system_keyed(settings)

    @asynccontextmanager
    async def lifespan(systems: list[SystemConfig]):
        """One hub per retrieval mode in use (normally one), opened before any worker starts."""
        modes = sorted({RunConfig(**s.flags).retrieval_mode for s in systems})
        try:
            async with AsyncExitStack() as stack:
                for mode in modes:
                    hubs[mode] = await stack.enter_async_context(
                        mcp_client.McpHub(
                            settings, retrieval_mode=mode, log_dir=ROOT / "data" / "runs" / "eval"
                        )
                    )
                yield hubs
        finally:
            hubs.clear()

    async def run(question, system, handwritten):
        cfg = RunConfig(
            max_run_tokens=settings.max_run_tokens, max_cost_usd=system.max_cost_usd, **system.flags
        )
        hub = hubs.get(cfg.retrieval_mode)
        if hub is None:
            raise RuntimeError("MCP hub is not open; Runner.run opens it once per invocation")
        return await system_adapter.run_system(question, cfg, settings, hub, prices, handwritten)

    return run, keyed, lifespan


def write_summary(out: dict[str, Any], runs_dir: Path | None = None) -> Path:
    runs_dir = runs_dir or RUNS_DIR
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{out['summary']['name']}-{int(time.time())}.json"
    path.write_text(
        json.dumps(out["summary"], indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an eval config (D090).")
    parser.add_argument("config", type=Path)
    parser.add_argument(
        "--replay-only",
        action="store_true",
        help="serve cached records only; no SDK client, no keys, no database",
    )
    parser.add_argument(
        "--preflight", action="store_true", help="check keys, prices, models and data; no LLM call"
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    if args.preflight:
        print(json.dumps(preflight(cfg), indent=2, default=str))
        return 0
    deps = replay_deps(cfg) if args.replay_only else live_deps(cfg)
    runner = Runner(cfg, deps, replay_only=args.replay_only)
    try:
        asyncio.run(runner.run())
    except ReplayMiss as exc:
        print(f"replay miss: {exc}")
        return 2
    finally:  # written on completion, spend-cap stop, error and Ctrl+C alike (D103)
        path = write_summary({"summary": runner.summary})
        print(json.dumps(runner.summary, indent=2, default=str))
        print(f"summary: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
