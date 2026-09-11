-- Immutable acquisition runs, independent of serving releases and model jobs.
CREATE TABLE swisstip.corpora (
    corpus_id text PRIMARY KEY,
    title text NOT NULL,
    inventory_sha256 text NOT NULL CHECK (length(inventory_sha256) = 64),
    catalogue_sha256 text NOT NULL CHECK (length(catalogue_sha256) = 64),
    metadata jsonb NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE swisstip.corpus_files (
    corpus_id text NOT NULL REFERENCES swisstip.corpora,
    path text NOT NULL,
    sha256 text NOT NULL CHECK (length(sha256) = 64),
    original_bytes bytea NOT NULL,
    PRIMARY KEY (corpus_id, path)
);
ALTER TABLE swisstip.admin_assets
    ADD COLUMN corpus_id text REFERENCES swisstip.corpora,
    ADD COLUMN acquisition_metadata jsonb NOT NULL DEFAULT '{}',
    ADD COLUMN processing_eligible boolean NOT NULL DEFAULT true,
    ADD COLUMN processing_reason text NOT NULL DEFAULT '';
CREATE INDEX ON swisstip.admin_assets (corpus_id, created_at);
CREATE TRIGGER immutable_corpus BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.corpora
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
CREATE TRIGGER immutable_corpus_file BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.corpus_files
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
