CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS swisstip;
CREATE TABLE swisstip.releases (
    release_id text PRIMARY KEY,
    file_sha256 text NOT NULL CHECK (length(file_sha256) = 64),
    canonical_sha256 text NOT NULL CHECK (length(canonical_sha256) = 64),
    original_bytes bytea NOT NULL,
    payload jsonb NOT NULL,
    classification text NOT NULL CHECK (classification IN ('experimental', 'synthetic')),
    imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE swisstip.artifacts (
    release_id text NOT NULL REFERENCES swisstip.releases,
    kind text NOT NULL,
    artifact_id text NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (release_id, kind, artifact_id)
);
CREATE TABLE swisstip.evidence (
    release_id text NOT NULL REFERENCES swisstip.releases,
    evidence_id text NOT NULL,
    evidence_sha256 text NOT NULL,
    source_id text NOT NULL,
    language text NOT NULL,
    original_excerpt text NOT NULL,
    citation_url text NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (release_id, evidence_id)
);
CREATE TABLE swisstip.embeddings (
    release_id text NOT NULL,
    evidence_id text NOT NULL,
    evidence_sha256 text NOT NULL,
    index_sha256 text NOT NULL,
    model text NOT NULL,
    dimensions integer NOT NULL CHECK (dimensions > 0),
    embedding vector NOT NULL,
    PRIMARY KEY (release_id, evidence_id),
    FOREIGN KEY (release_id, evidence_id) REFERENCES swisstip.evidence,
    CHECK (vector_dims(embedding) = dimensions)
);
CREATE TABLE swisstip.attachments (
    release_id text NOT NULL REFERENCES swisstip.releases,
    path text NOT NULL,
    file_sha256 text NOT NULL CHECK (length(file_sha256) = 64),
    original_bytes bytea NOT NULL,
    PRIMARY KEY (release_id, path)
);
CREATE TABLE swisstip.active_release (
    slot text PRIMARY KEY,
    release_id text NOT NULL REFERENCES swisstip.releases
);
CREATE INDEX ON swisstip.evidence (release_id, source_id, language);
-- Exact vector scans initially. No approximate index changes candidate recall.
CREATE FUNCTION swisstip.reject_artifact_change() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION 'Stored release content is immutable; import a new release ID';
END $$;
CREATE TRIGGER immutable_release BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.releases
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
CREATE TRIGGER immutable_artifact BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.artifacts
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.evidence
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
CREATE TRIGGER immutable_embedding BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.embeddings
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
CREATE TRIGGER immutable_attachment BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.attachments
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
