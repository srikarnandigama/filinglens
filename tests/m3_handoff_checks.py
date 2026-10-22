"""Manual M3 test harness: raw stdio checks, timings, source sheet and preservation.

Not an application MCP client/runtime. Every received stdout line must be JSON-RPC.
Run from the project root: .venv/Scripts/python.exe -m tests.m3_handoff_checks
"""

import asyncio
import hashlib
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import Client

from filinglens.config import ROOT
from mcp_servers.edgar_mcp.server import create_server
from mcp_servers.quant_mcp.server import create_server as quant_server
from mcp_servers.runtime import ServerSettings, readonly_pool


class StdioProbe:
    """Legacy wire probe exclusively for tests; no LLM or orchestration."""

    def __init__(self, process):
        self.process = process
        self.sequence = 0
        self.stdout_messages = 0

    async def send(self, method: str, params=None, *, notification=False):
        self.sequence += 1
        message = {"jsonrpc": "2.0", "method": method}
        if not notification:
            message["id"] = self.sequence
        if params is not None:
            message["params"] = params
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        await self.process.stdin.drain()
        if notification:
            return None
        while True:
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout=180)
            assert line, "Server exited before replying; inspect captured stderr."
            reply = json.loads(line)  # Any non-protocol stdout is a test failure.
            assert reply["jsonrpc"] == "2.0"
            self.stdout_messages += 1
            if reply.get("id") == self.sequence:
                assert "error" not in reply, reply
                return reply["result"]


@asynccontextmanager
async def probe(module: str, settings: ServerSettings, mode: str, log_path: Path):
    env = os.environ.copy()
    env.update(
        DATABASE_URL=settings.database_url,
        RETRIEVAL_CORPUS=settings.retrieval_corpus,
        SNAPSHOT_ID=settings.snapshot_id,
        RETRIEVAL_MODE=mode,
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_PROGRESS_BARS="1",
        PYTHONPATH=str(ROOT),
    )
    started = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as log:
        process = await asyncio.create_subprocess_exec(
            str(ROOT / ".venv/Scripts/python.exe"),
            "-m",
            module,
            cwd=ROOT,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=log,
        )
        wire = StdioProbe(process)
        try:
            initialized = await wire.send(
                "initialize",
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "filinglens-m3-test-probe", "version": "1"},
                },
            )
            startup = time.perf_counter() - started
            await wire.send("notifications/initialized", notification=True)
            yield wire, startup, initialized
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), timeout=15)
            except TimeoutError:
                process.kill()
                await process.wait()
                raise AssertionError("Server did not stop cleanly after stdin closed.") from None
            for line in (await process.stdout.read()).splitlines():
                assert json.loads(line)["jsonrpc"] == "2.0"
            assert process.returncode == 0


async def benchmark(settings: ServerSettings) -> dict:
    from filinglens.ingest.embed import embedding_fingerprint
    from filinglens.ingest.identity import digest
    from filinglens.ingest.models import model_revision
    from filinglens.retrieval.service import RETRIEVAL_VERSION

    queries = [
        ("Explain share repurchase authorization.", "AAPL", 2025),
        ("How does Chevron describe acquisition accounting?", "CVX", 2024),
        ("What does Microsoft say about cloud competition?", "MSFT", 2025),
    ]
    records = []
    for mode in ["vector", "hybrid_rerank"]:
        async with probe(
            "mcp_servers.edgar_mcp.server", settings, mode, ROOT / f"data/m3-{mode}-stderr.log"
        ) as (wire, startup, initialized):
            record = {
                "mode": mode,
                "startup_to_initialize_s": startup,
                "protocol_version": initialized["protocolVersion"],
                "calls": [],
            }
            for query, ticker, year in queries:
                args = dict(query=query, ticker=ticker, fiscal_year=year, fiscal_period="FY", k=8)
                options = dict(
                    ticker=ticker, fiscal_year=year, fiscal_period="FY", items=None, mode=mode, k=8
                )
                key = digest(
                    [
                        RETRIEVAL_VERSION,
                        settings.retrieval_corpus,
                        query,
                        options,
                        embedding_fingerprint(),
                        model_revision("rerank"),
                    ]
                )
                path = ROOT / "data/retrieval_cache" / f"{key}.json"
                existed = path.exists()
                start = time.perf_counter()
                response = await wire.send(
                    "tools/call", {"name": "search_filings", "arguments": args}
                )
                elapsed = time.perf_counter() - start
                assert not response.get("isError"), response
                hits = response["structuredContent"]["data"]["hits"]
                record["calls"].append(
                    {
                        "query": query,
                        "ticker": ticker,
                        "fiscal_year": year,
                        "seconds": elapsed,
                        "cache_before": existed,
                        "results": len(hits),
                        "ranked_ids": [hit["chunk_id"] for hit in hits],
                    }
                )
            start = time.perf_counter()
            cached = await wire.send("tools/call", {"name": "search_filings", "arguments": args})
            record["cache_hit_s"] = time.perf_counter() - start
            assert [h["chunk_id"] for h in cached["structuredContent"]["data"]["hits"]] == record[
                "calls"
            ][-1]["ranked_ids"]
            record["valid_stdout_messages"] = wire.stdout_messages
            records.append(record)
            print(json.dumps(record), flush=True)
    async with probe(
        "mcp_servers.quant_mcp.server", settings, "vector", ROOT / "data/m3-quant-stderr.log"
    ) as (wire, startup, initialized):
        response = await wire.send(
            "tools/call", {"name": "evaluate", "arguments": {"expression": "1+1"}}
        )
        assert response["structuredContent"]["data"]["value"] == "2"
        records.append(
            {
                "server": "quant-mcp",
                "startup_to_initialize_s": startup,
                "protocol_version": initialized["protocolVersion"],
                "valid_stdout_messages": wire.stdout_messages,
            }
        )
    result = {
        "method": (
            "Fresh real stdio subprocess per mode, same three queries/filters/k=8. "
            "First call loads required models; later uncached calls retain models. "
            "Cache state recorded; no existing cache entries removed. Entire stdout validated "
            "as JSON-RPC, including cold model loads. Legacy initialization includes "
            "process/import/database time. CPU-only pinned models, four Torch threads."
        ),
        "measurements": records,
    }
    Path("docs/M3_PHASE_B_LATENCY.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


async def verification_sheet(settings: ServerSettings) -> None:
    # In-memory clients use the same protocol/handlers and actual stored inputs.
    async with Client(create_server(settings)) as edgar, Client(quant_server()) as quant:
        inventory = (
            await edgar.call_tool("list_available_metrics", {"ticker": "AAPL"})
        ).structured_content["data"]
        period = {
            k: inventory["latest_common_quarter"][k] for k in ["fiscal_year", "fiscal_period"]
        }
        facts = {}
        for metric in ["revenue", "gross_profit"]:
            response = await edgar.call_tool(
                "get_financial_metric", {"ticker": "AAPL", "metric": metric, "periods": [period]}
            )
            facts[metric] = response.structured_content["data"]["facts"][0]
        result = await quant.call_tool(
            "margin",
            {"numerator": facts["gross_profit"]["value"], "denominator": facts["revenue"]["value"]},
        )
        payload = {
            "snapshot": inventory["snapshot"],
            "period": period,
            "facts": facts,
            "quant_margin": result.structured_content["data"],
        }
        Path("docs/M3_APPLE_VERIFICATION.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        lines = [
            "# Apple gross-margin verification sheet",
            "",
            "Generated by EDGAR/quant MCP tools from the frozen snapshot; "
            "no expected financial values are hardcoded in tests.",
            "",
            f"Snapshot: {settings.snapshot_id}, cutoff {inventory['snapshot']['cutoff_date']}. "
            "Latest common available revenue/gross-profit quarter: "
            f"**FY{period['fiscal_year']} {period['fiscal_period']}**.",
            "",
            "This is the newest stored quarter shared by both metrics. An ended quarter "
            "without filed/stored facts is not available; no Q4 10-Q exists, and fiscal "
            "years use their ending calendar year. Today's date does not change this answer.",
            "",
            "| Metric | Fact ID | Raw USD | Period start | Period end | Observation filed "
            "| Source accession filed | Source accession |",
            "|---|---|---:|---|---|---|---|---|",
        ]
        for metric, fact in facts.items():
            lines.append(
                f"| {metric} | {fact['fact_id']} | {fact['value']} | {fact['period_start']} "
                f"| {fact['period_end']} | {fact['source_filed']} | {fact['source_filing_date']} "
                f"| {fact['source_accession']} |"
            )
        for metric, fact in facts.items():
            lines += ["", f"{metric} source: [SEC filing]({fact['source_url']}).", ""]
        lines += [
            f"Expected `quant-mcp.margin` result: **{payload['quant_margin']['value_pct']}%**, "
            "rounded to 12 fractional places using ROUND_HALF_EVEN. Inputs are the exact "
            "gross-profit and revenue strings above; do not mix raw USD with display millions.",
            "",
            "The student should open the source filing, locate both income-statement values "
            "for this three-month period, account for displayed units, and independently "
            "confirm the margin. Preserve both fact IDs and the computation as citations. "
            "See [machine-readable tool outputs](M3_APPLE_VERIFICATION.json).",
            "",
        ]
        Path("docs/M3_APPLE_VERIFICATION.md").write_text("\n".join(lines), encoding="utf-8")


async def preserve(settings: ServerSettings) -> None:
    before = json.loads(Path("docs/M3_PRESERVATION_BEFORE.json").read_text())
    after = {"tables": {}, "files": {}}
    async with readonly_pool(settings.database_url) as p, p.connection() as c:
        for table in before["tables"]:
            assert table.replace("_", "").isalnum()
            row = await (
                await c.execute(
                    f"SELECT count(*) AS n,md5(string_agg(md5(t::text),'' "
                    f"ORDER BY md5(t::text))) AS hash FROM {table} t"
                )
            ).fetchone()
            after["tables"][table] = {"count": row["n"], "content_md5": row["hash"]}
    after["files"] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before["files"]}
    assert after == before, "Protected data/files changed."
    Path("docs/M3_PRESERVATION_AFTER.json").write_text(
        json.dumps(after, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    settings = ServerSettings()
    with asyncio.Runner() as runner:
        runner.run(benchmark(settings))
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(verification_sheet(settings))
        runner.run(preserve(settings))
