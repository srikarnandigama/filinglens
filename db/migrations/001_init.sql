CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE ingestion_snapshots (
  id TEXT PRIMARY KEY,
  cutoff_date DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  manifest JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE companies (
  cik              TEXT PRIMARY KEY,          -- 10-digit zero-padded
  ticker           TEXT UNIQUE NOT NULL,
  name             TEXT NOT NULL,
  fiscal_year_end  TEXT NOT NULL              -- 'MMDD'
);

CREATE TABLE filings (
  accession        TEXT PRIMARY KEY,          -- with dashes
  cik              TEXT NOT NULL REFERENCES companies(cik),
  form             TEXT NOT NULL,             -- '10-K' | '10-Q'
  filing_date      DATE NOT NULL,
  report_date      DATE NOT NULL,             -- period end
  fiscal_year      INT  NOT NULL,
  fiscal_period    TEXT NOT NULL,             -- 'Q1'|'Q2'|'Q3'|'FY'
  url              TEXT NOT NULL
);

CREATE TABLE sections (
  id               BIGSERIAL PRIMARY KEY,
  accession        TEXT NOT NULL REFERENCES filings(accession),
  item             TEXT NOT NULL,             -- e.g. '1A', '7', 'P1-2'
  title            TEXT NOT NULL,             -- e.g. 'Risk Factors'
  text             TEXT NOT NULL
);

CREATE TABLE chunks (
  id               BIGSERIAL PRIMARY KEY,
  section_id       BIGINT NOT NULL REFERENCES sections(id),
  accession        TEXT NOT NULL,
  cik              TEXT NOT NULL,
  form             TEXT NOT NULL,
  fiscal_year      INT  NOT NULL,
  fiscal_period    TEXT NOT NULL,
  item             TEXT NOT NULL,
  ordinal          INT  NOT NULL,             -- position within section
  text             TEXT NOT NULL,
  token_count      INT  NOT NULL,
  embedding        vector(384),
  tsv              tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
);
CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_tsv_gin ON chunks USING gin (tsv);
CREATE INDEX chunks_filter_idx ON chunks (cik, fiscal_year, fiscal_period, item);

CREATE TABLE financial_facts (
  id               BIGSERIAL PRIMARY KEY,
  cik              TEXT NOT NULL REFERENCES companies(cik),
  metric           TEXT NOT NULL,             -- normalized name, e.g. 'revenue'
  concept          TEXT NOT NULL,             -- source XBRL concept
  period_type      TEXT NOT NULL,             -- 'quarter'|'annual'|'instant'
  start_date       DATE,                      -- null for instant
  end_date         DATE NOT NULL,
  fiscal_year      INT  NOT NULL,             -- derived from dates, NOT from XBRL 'fy'
  fiscal_period    TEXT NOT NULL,             -- 'Q1'..'Q4'|'FY'
  value            NUMERIC NOT NULL,
  unit             TEXT NOT NULL,
  derived          BOOLEAN NOT NULL DEFAULT FALSE,  -- true for computed Q4
  source_accession TEXT,
  source_filed DATE NOT NULL,
  snapshot_id TEXT NOT NULL REFERENCES ingestion_snapshots(id),
  derivation_inputs JSONB NOT NULL DEFAULT '[]',
  CHECK (period_type IN ('quarter','annual','instant')),
  CHECK ((period_type = 'instant') = (start_date IS NULL)),
  CHECK (NOT derived OR jsonb_array_length(derivation_inputs) >= 2),
  UNIQUE NULLS NOT DISTINCT
    (snapshot_id, cik, metric, period_type, start_date, end_date, unit)
);

CREATE INDEX facts_period_idx ON financial_facts
  (snapshot_id, cik, metric, fiscal_year, fiscal_period);

CREATE TABLE metric_availability (
  snapshot_id TEXT NOT NULL REFERENCES ingestion_snapshots(id),
  cik TEXT NOT NULL REFERENCES companies(cik),
  metric TEXT NOT NULL,
  fiscal_year INT NOT NULL,
  fiscal_period TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('available','unavailable','not_applicable')),
  reason TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, cik, metric, fiscal_year, fiscal_period)
);

CREATE TABLE runs (
  id               UUID PRIMARY KEY,
  question         TEXT NOT NULL,
  config           JSONB NOT NULL,
  status           TEXT NOT NULL,             -- running|done|error
  answer           JSONB,
  total_input_tokens  INT DEFAULT 0,
  total_output_tokens INT DEFAULT 0,
  cost_usd         NUMERIC DEFAULT 0,
  latency_ms       INT,
  created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE trace_events (
  id               BIGSERIAL PRIMARY KEY,
  run_id           UUID NOT NULL REFERENCES runs(id),
  seq              INT NOT NULL,
  agent            TEXT NOT NULL,             -- planner|data|filings|analyst|verifier
  event_type       TEXT NOT NULL,             -- llm_call|tool_call|tool_result|plan|claim|verification|final|error
  payload          JSONB NOT NULL,
  input_tokens     INT DEFAULT 0,
  output_tokens    INT DEFAULT 0,
  latency_ms       INT,
  created_at       TIMESTAMPTZ DEFAULT now()
);
