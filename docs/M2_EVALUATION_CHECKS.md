# M2 evaluation checks and command record

The original pre-fix command record is preserved below. The keyword correctness
fix, post-fix rerun and follow-up analysis commands/results are recorded at the end.

Run from the project root in Windows PowerShell using the existing virtual environment.
The read-only pre-run validation was reported before computing metrics. The student
had corrected JNJ to FY2024/FY and approved six cross-year searches; validation
confirmed exactly those six. The label SHA-256 is
`d7b364662b9aa97f5c8616079297ff81322a7179583e2cb663c3614640896f04`.

## Evaluation and validation commands

```powershell
.venv/Scripts/python.exe -m evals.retrieval_eval --validate-only
.venv/Scripts/python.exe -m evals.retrieval_eval > data/m2_retrieval_eval.log 2>&1
```

The evaluation ran all 120 combinations with k=30 and saved filters unchanged:
60 valid D026 cache hits and 60 fresh runs. `evals/results/retrieval.json`
(ignored local evidence) records the validation, ranked IDs, filters, source/cache
path for every search, per-question metrics and full 730-slot coverage inventory.
`evals/results/retrieval.md` is the tracked report. Report-only rendering afterward
used these original rankings, scores and cache-source counts; it did not rerun search.

Read-only validation before and after the run, and again after the tests, confirmed
the same corpus fingerprint and chunk metadata/text/vector digest
`c86236eab76aee9189cc3fb5d8ab1c3272a8d69b2299e12c4af03ffaf9bb4ca2`.
All reranked ID sets equal the corresponding entire hybrid candidate pools.
The validator performs SELECTs in read-only transactions; it never calls the
labeling CLI's write-based freeze helper. No production schema or corpus changed.

The report-only render command (after adding interpretation and pool checks) was:

```powershell
@'
import asyncio,json
from pathlib import Path
from evals.retrieval_eval import report,check_reranker_pool
from evals.retrieval_audit import validate
from filinglens.db import pool_for
from filinglens.config import Settings
async def main():
 output=Path('evals/results/retrieval.md')
 payload=json.loads(output.with_suffix('.json').read_text(encoding='utf-8'))
 async with pool_for(Settings().database_url) as pool:
  records,current=await validate(pool,Path('evals/handwritten.jsonl'))
 if json.loads(json.dumps(current))!=payload['validation']: raise ValueError('Labels or corpus changed')
 check_reranker_pool(payload['details'])
 output.write_text(report(records,current,payload['details'],payload['coverage']),encoding='utf-8')
 print('Original evidence rendered; labels, corpus and full reranker pools verified unchanged.')
with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner: runner.run(main())
'@ | .venv/Scripts/python.exe -
```

JSON round-trip normalization is needed for the gold-size histogram's integer
dictionary keys when comparing in-memory validation against saved JSON keys.
An initial report-render comparison omitted that normalization and stopped;
the corrected comparison confirmed no label or corpus changes.

## Tests and formatting

```powershell
.venv/Scripts/python.exe -m ruff check evals/retrieval_eval.py evals/retrieval_audit.py tests/test_labeling_retrieval.py --fix
.venv/Scripts/python.exe -m ruff format evals/retrieval_eval.py evals/retrieval_audit.py tests/test_labeling_retrieval.py
.venv/Scripts/python.exe -m pytest tests/test_labeling_retrieval.py -q -p no:cacheprovider --basetemp=data/m2_eval_metric_tests
$env:FILINGLENS_TEST_DB = '1'
$env:FILINGLENS_TEST_CORPUS_REPLAY = '0'
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=data/m2_eval_full_tests > data/m2_eval_pytest.log 2>&1
.venv/Scripts/python.exe -m ruff check
.venv/Scripts/python.exe -m ruff format --check
git diff --check
.venv/Scripts/python.exe -m pytest tests/test_labeling_retrieval.py -q -p no:cacheprovider --basetemp=data/m2_eval_final_metric_tests
```

The initial focused run passed 8 tests; a further test verifies first-gold ranks
and that the reranker scores all 30 candidates, including promoting candidate 30
to first place. The full suite passed **58 tests, 1 skipped in 57.07 seconds**.
The skip is the explicitly gated production-corpus replay: it was not run because
the corpus is frozen. Integration checks include the filtered-HNSW exact fallback
and real section fixtures. Rebuild/resume tests use isolated test schemas and
fixture/mocked inputs, never reparsing or embedding the frozen production corpus.
Ruff lint and formatting pass after corrections to new report-code formatting.
The final focused metric/reranker run passed all 9 tests in 0.21 seconds;
`git diff --check` passed as well.
No dependencies or migration files were added or changed.

## Repo search for the incomplete non-December list

```powershell
rg -n --hidden -g '!data/**' -g '!.git/**' -g '!.venv/**' -g '!.tools/**' -g '!.uv/**' 'AAPL, MSFT, NVDA, COST|NKE, DIS, WMT|non.December' .
```

The incomplete list occurs at SPEC.md:199 and SPEC.md:645. There is no runtime
hard-coded copy of that list. New evaluation notes/decisions explain the omission;
they do not add a runtime exception list. PG uses actual report dates per D006.

## Changes and acceptance

- `evals/retrieval_eval.py`: seven metrics, subgroup/paired comparisons, rank and
  cache evidence, full reranker-pool guard, complete report generation, validate-only mode.
- `evals/retrieval_audit.py`: strict read-only label/corpus validation and complete
  annual/quarterly expected-item coverage inventory, including zero-chunk slots.
- `evals/retrieval_notes.md`: methodology, labeling edits, coverage interpretation,
  future parser proposal and deferred period-resolution notes included in the report.
- `tests/test_labeling_retrieval.py`: hand-made metric boundary and full-depth reranker tests.
- `docs/DECISIONS.md`: D027–D030 amend D022 and record metric choice, label provenance,
  temporal ambiguity, PG and frozen coverage policy.
- `docs/M2_STATUS.md`, this command record and `evals/results/retrieval.md`: handoff.

`evals/handwritten.jsonl` remains the student's unchanged, currently untracked file.
Local ignored artifacts include the detailed result JSON, execution/test logs and
read-only coverage inventory. No question, filter, gold label or reference answer
was edited. No M3 work began; wait for explicit M2 acceptance.

## Keyword defect correction and follow-up analyses

D031 selected one OR-over-English-lexemes correction before the rerun, with
ts_rank_cd, metadata filters and RRF 60 unchanged. The implementation version
changed to `retrieval-v2-keyword-or`. All 120 post-fix searches ran fresh;
the old cache cannot serve these keys. Vector rankings remained unchanged,
while hybrid now differs from vector on all 30 questions.

The baseline was archived once, **before** changing results (do not repeat these
copies after a post-fix run):

```powershell
Copy-Item -LiteralPath evals/results/retrieval.md -Destination evals/results/retrieval_pre_fix.md
Copy-Item -LiteralPath evals/results/retrieval.json -Destination evals/results/retrieval_pre_fix.json
```

The archived JSON SHA-256 is
`8714437e6d1c9a80d05a05df15323ccd25950aafd198257d8eb4176ba0cd2ae9`.

```powershell
.venv/Scripts/python.exe -m evals.retrieval_eval --validate-only
.venv/Scripts/python.exe -m ruff format filinglens/retrieval/service.py tests/test_retrieval_database.py
$env:FILINGLENS_TEST_DB='1'
.venv/Scripts/python.exe -m pytest tests/test_retrieval_database.py -q -p no:cacheprovider --basetemp=data/m2_keyword_fix_tests
.venv/Scripts/python.exe -m ruff format evals/retrieval_eval.py tests/test_retrieval_database.py
.venv/Scripts/python.exe -m evals.retrieval_eval > data/m2_keyword_or_eval.log 2>&1
.venv/Scripts/python.exe -m ruff format evals/retrieval_followup.py tests/test_retrieval_analyses.py
.venv/Scripts/python.exe -m pytest tests/test_retrieval_analyses.py -q -p no:cacheprovider --basetemp=data/m2_followup_unit_tests
$env:FILINGLENS_TEST_DB='1'
$env:FILINGLENS_TEST_CORPUS_REPLAY='0'
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=data/m2_keyword_or_full_tests > data/m2_keyword_or_pytest.log 2>&1
.venv/Scripts/python.exe -m evals.retrieval_followup > data/m2_keyword_or_analyses.log 2>&1
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=data/m2_keyword_or_final_tests > data/m2_keyword_or_final_pytest.log 2>&1
.venv/Scripts/python.exe -m ruff check
.venv/Scripts/python.exe -m ruff format --check
git diff --check
```

Focused keyword DB tests: **2 passed**. New analysis/cache-invalidation tests:
**3 passed**. Initial full suite: **62 passed, 1 skipped in 46.04 seconds**;
the final full rerun passed **62 tests, 1 skipped in 34.21 seconds**. The only skip
is the frozen production corpus replay. Lint, format and whitespace checks pass.
All corpus and label fingerprints still match the original validation evidence.

`evals/retrieval_followup.py` replays all 120 v1 caches through the original
four-mode depth-30 pooling definition, checks the union against the archived
rankings, computes per-question/overall outside-pool and unjudged rates, and
audits all six cross-year questions with the fixed D032 shingle rule. It also
reads the 22 cached JNJ/XOM quarterly HTML bodies and verifies their hashes;
the DOM inspection is read-only and invokes no ingestion parser or network client.
Each has one annual Item 1A reference and no quarterly risk section.

The three result JSONs (`retrieval_pre_fix.json`, `retrieval.json`,
`retrieval_analyses.json`) are now explicitly retained by `.gitignore` as
reproducible evidence instead of discarded local artifacts. The analyses include
reconstructed pool IDs, unjudged IDs, every audited top-10 result, overlap scores,
matching gold IDs, and cached-source paths/hashes/excerpts. Historical logs and
the extra pre-fix Markdown copy remain ignored; pre-fix tables are preserved in
the main report. No human labels or frozen corpus content were changed.

Additional changes: keyword/version fix in `filinglens/retrieval/service.py`,
the new `evals/retrieval_followup.py` and `tests/test_retrieval_analyses.py`, the
database keyword regression in `tests/test_retrieval_database.py`, evaluator
pre/post reporting, D031/D032, coverage priority and label-migration notes in
`evals/retrieval_notes.md` and `docs/M2_STATUS.md`, this command record and the
generated report/evidence. M2 remains pending explicit student acceptance;
corpus repair is required after that acceptance and before M4. No M3 work began.
