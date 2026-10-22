-- M4 agent runs and traces (D059). Additive; only runs and trace_events change.
ALTER TABLE runs
  ADD COLUMN finished_at TIMESTAMPTZ,
  ADD COLUMN error JSONB,
  ADD COLUMN total_cache_read_tokens INT NOT NULL DEFAULT 0,
  ADD COLUMN total_cache_write_tokens INT NOT NULL DEFAULT 0,
  ADD CONSTRAINT runs_status_check CHECK (status IN ('running', 'done', 'error'));

ALTER TABLE trace_events
  ADD CONSTRAINT trace_events_run_seq_key UNIQUE (run_id, seq);
