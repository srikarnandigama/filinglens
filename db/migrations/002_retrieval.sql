-- M2 was explicitly approved after M1. Refuse to discard pre-existing passages.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM chunks) OR EXISTS (SELECT 1 FROM sections) THEN
    RAISE EXCEPTION 'M2 identity migration requires empty sections/chunks';
  END IF;
END $$;
ALTER TABLE chunks DROP CONSTRAINT chunks_section_id_fkey;
ALTER TABLE sections ALTER COLUMN id DROP DEFAULT;
ALTER TABLE chunks ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sections ALTER COLUMN id TYPE TEXT USING id::text;
ALTER TABLE chunks ALTER COLUMN id TYPE TEXT USING id::text;
ALTER TABLE chunks ALTER COLUMN section_id TYPE TEXT USING section_id::text;
ALTER TABLE chunks ADD FOREIGN KEY (section_id) REFERENCES sections(id);

CREATE TABLE document_processing (
  snapshot_id TEXT NOT NULL REFERENCES ingestion_snapshots(id),
  accession TEXT NOT NULL REFERENCES filings(accession),
  fingerprint TEXT NOT NULL,
  stage TEXT NOT NULL CHECK (stage IN ('filings','parse','embed')),
  status TEXT NOT NULL CHECK (status IN ('complete','error')),
  details JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (snapshot_id, accession, fingerprint, stage)
);
CREATE TABLE retrieval_corpora (
  id TEXT PRIMARY KEY,
  snapshot_id TEXT NOT NULL REFERENCES ingestion_snapshots(id),
  configuration JSONB NOT NULL,
  frozen BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE corpus_documents (
  corpus_id TEXT NOT NULL REFERENCES retrieval_corpora(id),
  accession TEXT NOT NULL REFERENCES filings(accession),
  source_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('complete','error')),
  details JSONB NOT NULL DEFAULT '{}',
  PRIMARY KEY (corpus_id, accession)
);
ALTER TABLE sections ADD COLUMN source_hash TEXT NOT NULL;
ALTER TABLE sections ADD COLUMN fingerprint TEXT NOT NULL;
ALTER TABLE sections ADD COLUMN occurrence INT NOT NULL;
ALTER TABLE sections ADD COLUMN blocks JSONB NOT NULL;
ALTER TABLE sections ADD UNIQUE (accession, source_hash, fingerprint, item, occurrence);
ALTER TABLE chunks ADD COLUMN source_hash TEXT NOT NULL;
ALTER TABLE chunks ADD COLUMN fingerprint TEXT NOT NULL;
ALTER TABLE chunks ADD COLUMN context_header TEXT NOT NULL;
ALTER TABLE chunks ADD COLUMN source_start INT NOT NULL;
ALTER TABLE chunks ADD COLUMN source_end INT NOT NULL;
ALTER TABLE chunks ADD COLUMN oversized_row BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE chunks ADD COLUMN embedding_fingerprint TEXT;
ALTER TABLE chunks ADD UNIQUE (section_id, ordinal);
CREATE TABLE corpus_chunks (
  corpus_id TEXT NOT NULL REFERENCES retrieval_corpora(id),
  chunk_id TEXT NOT NULL REFERENCES chunks(id),
  PRIMARY KEY (corpus_id, chunk_id)
);
