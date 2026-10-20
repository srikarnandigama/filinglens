# Corpus-v2 Phase C checks and acceptance handoff

Phase C is complete and awaits explicit student acceptance. M3 has not started.
All work ran from the project root with `.venv/Scripts/python.exe` on Windows.
No network requests, dependencies, model downloads, production schema migrations,
production parsing, chunking, corpus embedding or financial-data changes were performed.

## Validation and preservation

Pre-run validation was reported before computing metrics. All 30 question IDs
and texts are unique. All 64 gold labels belong to frozen v2, match its corpus
fingerprint and satisfy the saved filters. All question/filter/reference fields
match the original fields copied by migration; the manifest supplies the original
61 mapped gold IDs. No gold was removed. Only the two approved JPM additions and
one approved Chevron/Hess addition are present. Attribution groups are 28 (a)
and 2 (b), fixed by the student before the run.

- Corpus ID: `corpus_3f3c2a9affddcc6a29eca9e768c65bcbd3e2f131fb69595b24b9b92005738739`.
- Corpus fingerprint: `d6e2dd9856cdf645873078c0505a690615b680346a95d4d591adcf0b3a18809a`.
- Frozen v2 content/metadata/vector hash: `2a877e4ef2ee5cadbcb812f0f592aebd9b3f9ec8f52555a9ffbe5bc74d4670e8`.
- Reviewed v2 labels SHA-256: `6d120892242bb97e9131a0ee4cc2316793f06b837d6149fc5a06a622baea9233`.
- V1 labels SHA-256: `d7b364662b9aa97f5c8616079297ff81322a7179583e2cb663c3614640896f04`.
- V1 chunk-row hash: `b9081fa4d2fe10a0eddd1d65837ad19de13644e3166cf8e8b380dd69e7d694a7`.
- M1 financial-fact hash: `6b3f44b03efc7d3054c3e3597bd66a81885dbea8b7f2f3ceddb577c1d105c13f` (2715 rows).

The result's `validation` and `unchanged_after` objects are identical. Another
read-only validation after tests and documentation has exactly the same object,
including labels, full stored vectors, document details, sections and membership.
The Phase B baseline comparison still verifies v1 labels, historical reports,
corpus/document/chunk rows, facts, companies, filings, availability and the shared
snapshot manifest. Only the living `docs/M2_STATUS.md` is exempted because the
student explicitly authorized its Phase C update; the saved baseline JSON itself
was not rewritten. No Phase B reports or migration manifest were overwritten.

## Evaluation and pool evidence

Every question ran in vector, keyword, hybrid and hybrid_rerank at depth 30,
with original filters, D031 keyword logic and RRF 60. All reranked candidate sets
match their entire hybrid top-30 sets. Apple FY2025 Q3 has 15 eligible chunks;
its shorter output is not filtered-HNSW underfill. D026 supplied 24 cached searches;
96 searches ran fresh. Gold changes do not invalidate ranking caches.

The pre-evaluation inventory records complete four-mode caches for six reviewed
questions, and none for the other 24. The exposure proxy migrates historical
labeling pools by unique exact text and adds only those pre-existing review pools
plus known golds. The separate reconstructed current v2 pooling definition has
zero unjudged slots by construction; evaluation-created caches are not treated
as evidence of student exposure. All per-question pools, exclusions, rates and
bridge scores are saved with the new results.

## Checks

- Ruff lint: passed.
- Ruff format check: passed.
- Full pytest: **101 passed, 1 skipped**, 62.02 seconds.
- The skipped test is the opt-in legacy production corpus replay. It remains
  disabled because both corpora are frozen; no reparse ran in Phase C.
- Real DB tests use isolated schemas, including the M1 cache replay. New tests
  cover exact approved additions, rejection of changed fields or labels,
  fixed-ranking attribution, unique/nonunique candidate migration, prevention of
  evaluation-pool leakage, complete pre-evaluation review pools and active-v2
  defaults with historical overrides. Existing metric tests cover gold sets
  larger than k, missing hits, capped/standard recall, hit rates and MRR@30.
- Configured/default active corpus was checked and equals v2. No `.env` was edited.

## Commands

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.venv/Scripts/python.exe -m evals.retrieval_v2 --validate-only
.venv/Scripts/python.exe -u -m evals.retrieval_v2
.venv/Scripts/python.exe -m evals.retrieval_v2_report
$env:FILINGLENS_TEST_DB='1'
$env:FILINGLENS_TEST_CORPUS_REPLAY='0'
.venv/Scripts/python.exe -m ruff check
.venv/Scripts/python.exe -m ruff format --check
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=data/pytest-corpus-v2-phase-c
.venv/Scripts/python.exe -m evals.retrieval_v2 --validate-only
.venv/Scripts/python.exe -c "from filinglens.config import Settings; print(Settings().retrieval_corpus)"
```

The report command was run again after the narrative/formatting edits; cached
rankings and metrics were not rerun or tuned. Additional read-only Python checks
compared all validation objects and label hashes, and inspected archived v1
metrics, attribution bridges, pool rates and rank changes. Logs are under ignored
`data/corpus_v2_phase_c_*.log`.

## Files created or changed in Phase C

- New `evals/retrieval_v2.py`: strict read-only validation, pre-run inventory,
  depth-30 evaluation and preservation checks.
- New `evals/retrieval_v2_report.py`: comparisons, attribution, exposure/overlap
  evidence and the report; no labels written.
- New `tests/test_retrieval_v2.py`: validation/attribution/pool/config tests.
- `filinglens/config.py`, `.env.example`: active v2 default; historical overrides.
- `evals/corpus_v2.py`: only the authorized living-status baseline exemption.
- `.gitignore`: retain the four new v2 report/evidence files.
- `docs/DECISIONS.md`: D036-D038; `docs/M2_STATUS.md` and `README.md`: current v2
  selection, measured results, limitations and the explicit acceptance gate.
- New `docs/CORPUS_V2_PHASE_C_VALIDATION.json` and this checks document.
- New `evals/results/retrieval_v2.md`, `retrieval_v2.json`,
  `retrieval_v2_analyses.json`, `retrieval_v2_pool_inventory.json`.

Existing unrelated working-tree changes were preserved. Student label files,
v1 results, Phase B artifacts, ingestion/parser/chunker/model code and retrieval
algorithms were not edited in Phase C. Await acceptance; do not implement M3.
