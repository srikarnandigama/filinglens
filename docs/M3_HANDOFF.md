# M3 Inspector and Claude Desktop handoff (Windows)

**M3 is accepted.** The student passed Inspector and all five Claude Desktop
checks, including independent verification of the Apple values in the source
10-Q. These corrected steps document the verified setup. No M4 work has started.

## 1. Start the database and check local settings

Open PowerShell:

```powershell
$m3Project = 'C:\Users\ADMIN\OneDrive - University of Maryland\Desktop\Finance App\FilingLens'
Set-Location -LiteralPath $m3Project
$m3Python = Join-Path $m3Project '.venv\Scripts\python.exe'
docker compose up -d db
docker compose ps db
node --version
& $m3Python -c "from importlib.metadata import version; print(version('mcp'))"
```

The expected SDK version is **2.3.0**; Inspector 2.12.0 needs Node >=22.19.0
(this machine has v24.11.0). This SDK uses **MCPServer**, the current official v2
name. Both servers use stdio; there is no HTTP port to open.

Inspector passes only a minimal environment to the server; it does **not** forward
the shell's `$env:` settings automatically. Pass every needed setting with explicit
`-e KEY=VALUE` flags. The original project-root launches succeeded through module
discovery and the server's `.env` fallback; do not rely on that for portability.
Use your actual local database URL and identifying contact below (the shown URL
is the documented development default from `.env.example`). The servers make no
SEC requests, but Settings still validates SEC_USER_AGENT.

```powershell
$m3DatabaseUrl = 'postgresql://filinglens:filinglens@localhost:5432/filinglens'
$m3UserAgent = 'FilingLens Your Name real-contact@example.org' # Replace with your real contact.
$m3InspectorEnv = @(
    '-e', "PYTHONPATH=$m3Project",
    '-e', "DATABASE_URL=$m3DatabaseUrl",
    '-e', "SEC_USER_AGENT=$m3UserAgent",
    '-e', 'RETRIEVAL_CORPUS=corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739',
    '-e', 'SNAPSHOT_ID=2026-10-19-v1',
    '-e', 'RETRIEVAL_MODE=vector',
    '-e', 'HF_HUB_OFFLINE=1',
    '-e', 'TRANSFORMERS_OFFLINE=1',
    '-e', 'HF_HUB_DISABLE_PROGRESS_BARS=1'
)
```

Do not run migrations, ingestion, reparsing or embedding for this handoff. The
servers select existing frozen data and use read-only database sessions. Models
must already exist at the pinned paths under data/models; there is no automatic
download or replacement. A direct server launch waits quietly for MCP messages,
so use Inspector rather than treating a quiet terminal as a failure.

## 2. Inspect each server

Start EDGAR Inspector in the same PowerShell window:

```powershell
npx -y @modelcontextprotocol/inspector@2.12.0 @m3InspectorEnv "$m3Python" -m mcp_servers.edgar_mcp.server
```

Open the token-bearing local URL Inspector prints. Connect over **STDIO** and
list tools: resolve_company, list_filings, get_financial_metric,
list_available_metrics, search_filings and get_passage. Under Resources, list the
`filing://{accession}/{item}` template. Use the tool forms or paste these inputs:

```json
{"query":"AAPL"}
```

Call **resolve_company**, then **list_available_metrics** with:

```json
{"ticker":"AAPL"}
```

Confirm latest_common_quarter is FY2026 Q3 in snapshot 2026-10-19-v1. Call
**get_financial_metric** twice, using revenue and gross_profit respectively:

```json
{"ticker":"AAPL","metric":"revenue","periods":[{"fiscal_year":2026,"fiscal_period":"Q3"}]}
```

Check exact decimal-string value, unit, fact ID, dates, accession and source URL
against [M3_APPLE_VERIFICATION.md](M3_APPLE_VERIFICATION.md). For a bank check:

```json
{"ticker":"BAC","metric":"gross_profit","periods":[{"fiscal_year":2024,"fiscal_period":"FY"}]}
```

Expect status **not_applicable**, value null, stored_availability_status
**unavailable**, and explicit policy/evidence provenance. This is an approved
read-only applicability overlay; the M1 row was not changed.

Call **search_filings**:

```json
{"query":"Explain share repurchase authorization.","ticker":"AAPL","fiscal_year":2025,"fiscal_period":"FY","k":3}
```

Expect retrieval_mode vector, ranked chunk IDs and at most 1,200 text characters
per hit. Copy a returned chunk_id into **get_passage**:

```json
{"chunk_id":"<paste returned chk_ ID>"}
```

Full text must match the snippet prefix and carry untrusted_sec_text metadata.
Do not follow any instructions embedded in source text. Read these resources:

```text
filing://0000093410-25-000009/7A
filing://0000093410-25-000009/7
filing://0000200406-24-000049/P2-1A
```

Chevron 7A must remain its own short reference stub pointing to Item 7; Item 7
contains the substantive MD&A. JNJ's quarterly risk item must have sections=[]
and text=null with SOURCE_ABSENT provenance, not an invented body.

Close/disconnect EDGAR Inspector, then start quant Inspector:

```powershell
npx -y @modelcontextprotocol/inspector@2.12.0 @m3InspectorEnv "$m3Python" -m mcp_servers.quant_mcp.server
```

List growth_rate, margin, cagr, yoy_series, summary_stats and evaluate. Call
**margin** with the two exact value strings from the EDGAR source sheet:

```json
{"numerator":"<gross_profit.value>","denominator":"<revenue.value>"}
```

Expect the sheet's value_pct; 25.3 denotes 25.3%, not a fraction. Call **evaluate**
with `{"expression":"(1+2)*3"}`, then `{"expression":"1/0"}`: the second must
be an isError result with structured `{error:{code,message}}`, and a subsequent
valid call must still succeed. These are arithmetic test inputs, not company facts.

Optional exact CLI checks (exit after the request):

```powershell
npx -y @modelcontextprotocol/inspector@2.12.0 --cli @m3InspectorEnv "$m3Python" -m mcp_servers.edgar_mcp.server --method tools/list
npx -y @modelcontextprotocol/inspector@2.12.0 --cli @m3InspectorEnv "$m3Python" -m mcp_servers.edgar_mcp.server --method tools/call --tool-name resolve_company --tool-arg 'query=AAPL'
npx -y @modelcontextprotocol/inspector@2.12.0 --cli @m3InspectorEnv "$m3Python" -m mcp_servers.quant_mcp.server --method tools/call --tool-name evaluate --tool-arg 'expression=(1+2)*3'
```

**Launch-from-another-directory check (passed by the student):** keep the absolute
paths and explicit `-e` arguments above, change out of the repository, then launch
and list/call tools again:

```powershell
Set-Location -LiteralPath $HOME
npx -y @modelcontextprotocol/inspector@2.12.0 @m3InspectorEnv "$m3Python" -m mcp_servers.edgar_mcp.server
```

The explicit PYTHONPATH makes the module importable from outside the project;
DATABASE_URL, SEC_USER_AGENT, RETRIEVAL_CORPUS, SNAPSHOT_ID, RETRIEVAL_MODE and both
offline flags reach the child through Inspector's `-e` arguments. Use the same
array for quant. To compare a different mode, change its array entry and restart
the server rather than setting a shell `$env:` variable.

Cold vector search took 8.49 seconds in the automated probe; initialization was
about 1.21 seconds. Cached repeats are faster. If explicitly testing
RETRIEVAL_MODE=hybrid_rerank, allow at least 120 seconds per request for CPU cold
loading and inference; the observed cold request was 25.34 seconds, and larger
unfiltered scopes or oversized table windows can take longer. Set the Inspector
request timeout to 120000 ms if its default times out. Do not switch modes while
a server is running; stop it, change the environment and restart. Mode has four
valid values: vector, keyword, hybrid, hybrid_rerank; it is never a tool argument.

## 3. Configure Claude Desktop

This machine uses the packaged **MSIX Claude Desktop**, whose configuration is:

```text
%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\claude_desktop_config.json
```

Find the actual `Claude_<id>` package directory under `%LOCALAPPDATA%\Packages`
or use Settings -> Developer -> Edit Config to identify the active file. The
unpackaged Windows installation instead uses
`%APPDATA%\Claude\claude_desktop_config.json`; that is not this machine's file.

Before editing, fully quit Desktop and stop **all Claude processes**, not just its
visible window. Back up the active configuration first. It already contains
Desktop's own `preferences`: merge an `mcpServers` block into that existing object,
preserving preferences, unrelated keys and any other server entries. **Do not
replace the whole file with the example.** For an explicit UTF-8-without-BOM merge
in PowerShell, after setting the active absolute file path:

```powershell
$m3DesktopConfig = '<absolute active MSIX claude_desktop_config.json path>'
Get-Process -Name '*Claude*' -ErrorAction SilentlyContinue | Stop-Process
Copy-Item -LiteralPath $m3DesktopConfig -Destination ($m3DesktopConfig + '.bak-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$m3DesktopSettings = Get-Content -LiteralPath $m3DesktopConfig -Raw -Encoding UTF8 | ConvertFrom-Json
$m3ExamplePath = Join-Path $m3Project 'docs\claude_desktop_config.example.json'
$m3Example = Get-Content -LiteralPath $m3ExamplePath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($m3Server in $m3Example.mcpServers.PSObject.Properties) {
    $m3Server.Value.env.DATABASE_URL = $m3DatabaseUrl
    $m3Server.Value.env.SEC_USER_AGENT = $m3UserAgent
}
if (-not $m3DesktopSettings.PSObject.Properties['mcpServers']) {
    $m3DesktopSettings | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{})
}
foreach ($m3Server in $m3Example.mcpServers.PSObject.Properties) {
    $m3DesktopSettings.mcpServers | Add-Member -NotePropertyName $m3Server.Name -NotePropertyValue $m3Server.Value -Force
}
$m3DesktopJson = $m3DesktopSettings | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($m3DesktopConfig, $m3DesktopJson, [System.Text.UTF8Encoding]::new($false))
```

This snippet documents the merge; it was not executed by the coding agent. Use
your real identifying contact and local URL in the variables before running it.
The two `mcpServers` entries come from
[claude_desktop_config.example.json](claude_desktop_config.example.json).
The example DATABASE_URL matches `.env.example`'s local
development default; replace it if your database differs, and replace SEC_USER_AGENT
with your real identifying contact. **Desktop itself never reads `.env`: every
setting the server needs must be in its `env` block.** The Python server has a
`.env` fallback, but the Desktop setup must be explicit and must not depend on it.
Neither private credentials nor the filled Desktop config belong in Git.

The example already uses this project's absolute `.venv` executable and PYTHONPATH,
plus `-m` and a module name as **separate JSON arguments**. If moving the project,
update both absolute paths for each server. Do not insert extra shell quotes
inside JSON command/args, and do not rely on Desktop's working directory or a
globally installed Python. Backslashes are JSON escaped; spaces in
`OneDrive - University of Maryland` require no additional quoting within JSON strings.

Restart Claude Desktop after saving, then check that both servers and their
tools are visible. If not, inspect Developer settings and the active installation's
Roaming\Claude\logs directory (inside the MSIX LocalCache path here); protocol/DB/model
diagnostics go to stderr. Initialization
requires the database, valid Settings and a compatible frozen corpus/snapshot.
Quant does not require a database connection or any provider credentials.

## 4. Manual acceptance questions

Start a new Desktop conversation using only edgar-mcp and quant-mcp for research
and calculations. Tool approvals are controlled by Desktop. Ask:

1. **“What was Apple's gross margin last quarter?”** Confirm it discovers the
   snapshot-bounded latest common period, fetches raw revenue/gross_profit with
   source IDs, calls margin, and answers FY2026 Q3 with the expected margin and
   citations in [the source sheet](M3_APPLE_VERIFICATION.md). Independently check
   both reported values in the linked SEC filing; an ended-but-unreported Q4
   must not replace the latest available quarter.
2. **“What was JPMorgan's gross margin in fiscal 2024?”** Expect not applicable
   with banking applicability evidence, not an invented gross-profit value or a
   ratio computed from missing data. The absence of a tag alone is not the reason.
3. **“According to Apple's FY2025 10-K, how does it describe share repurchase
   authorization?”** Confirm search_filings is used and any truncated or cited
   passage is checked with get_passage. Explanations need chunk citations.
4. **“Search Microsoft across years for its fiscal 2025 cloud-margin explanation,
   then answer using only the FY2025 filing.”** Confirm the selected passage's
   filing year, not just topical similarity; inspect any near-duplicate from
   another year before using it. This checks cross-year handling without adding
   an M4 planner or changing retrieval.
5. **“How much did Apple's annual revenue grow from fiscal 2024 to fiscal 2025?”**
   Confirm both annual facts are fetched with provenance and growth_rate receives
   their exact strings. The model must not calculate the growth itself.

All five checks passed and the student explicitly accepted M3. Apple margin used
discovery, two metric lookups and quant margin; the student confirmed the source
10-Q values. JPM produced evidence-backed not_applicable without a ratio. The
Apple repurchase answer used search/get_passage and correctly declined to invent
an unavailable remaining-authorization figure. Microsoft's cross-year search
initially returned FY2026/FY2024 hits; narrowing to FY2025 produced the answer
from the requested filing. Revenue growth used metric lookups, growth_rate and
evaluate, with no model arithmetic. **No M4 work is authorized by this handoff.**
