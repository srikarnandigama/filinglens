# M3 status: accepted

The student explicitly accepted M3 on 2026-10-22 after Inspector and all five
Claude Desktop checks passed, including launch from outside the project with
explicit Inspector `-e` environment flags. The Apple values were independently
confirmed in the source 10-Q. Manual acceptance results:

1. Apple latest gross margin: FY2026 Q3, displayed as 50.06%, via
   list_available_metrics -> get_financial_metric twice -> quant margin; matches
   the source sheet.
2. JPM FY2024 gross margin: evidence-backed not_applicable, without an invented
   value or ratio.
3. Apple FY2025 repurchase authorization: grounded search/get_passage answer;
   correctly declined to state a remaining authorization it could not find.
4. Microsoft cross-year: initial search missed the FY2025 10-K and returned
   FY2026/FY2024 hits; narrowing to FY2025 produced an answer only from that filing.
5. Apple FY2024-to-FY2025 revenue growth: metric lookups, growth_rate and evaluate;
   no model arithmetic.

Phase A was approved with four amendments, all implemented: official MCP v2
(MCPServer 2.3.0), vector by default, JSON int/float quant inputs via Decimal(str(x)),
and concise 60-150-word descriptions. D039-D048 record the amended decisions.

Both stdio servers are implemented with typed contracts, structured errors,
read-only snapshot/corpus access, pinned bank applicability evidence and the filing
resource. Quant uses bounded Decimal computations and a non-executable parser.
No corpus, labels, M1 facts, schema, retrieval algorithm or model revision changed.

- Ruff lint/format pass. Full pytest: **167 passed, 1 skipped** (117.70 s), with
  database integration enabled; the existing opt-in production corpus replay was
  skipped to preserve frozen data.
- Four-mode tool parity with M2 retrieval passed; source absence, reference stubs,
  provenance, precision, all-tool protocol/errors, stdio and cancellation checks pass.
- Actual stdio startup to legacy initialize: EDGAR ~1.21 s, quant ~1.10 s.
  Vector search: 8.49 s cold, 0.084-0.112 s warm uncached. Reranked comparison:
  25.34 s cold, 12.69-12.76 s warm uncached. Cache hits ~0.05 s.
- Production content/file preservation checks match before/after. Only MCP and its
  required dependencies were installed; no models were downloaded.

Review [Phase B report](M3_PHASE_B.md) for final deployed docstrings, schemas,
latencies, tests, commands and file inventory. Follow [M3_HANDOFF.md](M3_HANDOFF.md)
for exact Inspector/Desktop steps and [Apple source sheet](M3_APPLE_VERIFICATION.md)
for independent verification: FY2026 Q3, fact IDs 18/54, quant margin
50.056206987945% from stored raw USD values.

## Known limitations and deferred candidates

- CVX FY2024 Item 7's resolved boundary is slightly late: its span includes
  "Quarterly Results" (unaudited) and "Management's Responsibility for Financial
  Statements", which belong to Item 8. Nothing is missing or duplicated. Corpus
  v2 is frozen; this is a documented limitation, not a parser or corpus fix.
- The Apple repurchase check retrieved a relevant chunk beginning mid-sentence
  without its predecessor, which may contain the remaining-authorization figure;
  that location is not confirmed. Tools currently offer the whole-section resource
  but no adjacent-chunk navigation. Returning previous/next chunk IDs from
  get_passage is an M4/M6 candidate only; nothing is implemented now.
- Cross-year unfiltered search can miss the explicitly requested filing. M4's
  planner must resolve explicit fiscal periods into filters before searching,
  rather than depending on an unfiltered top-k list to select the correct year.

The corrected [handoff](M3_HANDOFF.md) documents explicit Inspector environment
flags, the tested outside-project launch, and this machine's MSIX Desktop config
path with a backed-up UTF-8-without-BOM merge preserving preferences. Desktop
itself does not read `.env`; the example supplies settings explicitly.

**M3 is accepted. No M4 work has started; wait for the student's separate task.**
