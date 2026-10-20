-- Approved M2 provenance: detect input drift independently of model revision.
ALTER TABLE chunks ADD COLUMN embedding_input_hash TEXT;
