-- Mutable operational jobs are separate from immutable serving releases.
CREATE TABLE swisstip.admin_assets (
    asset_id text PRIMARY KEY,
    source_id text NOT NULL,
    filename text NOT NULL,
    sha256 text NOT NULL,
    original_bytes bytea NOT NULL,
    origin text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, filename, sha256)
);
CREATE TABLE swisstip.admin_jobs (
    job_id text PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('crawl', 'plan', 'extract')),
    status text NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'needs_attention', 'failed', 'cancelled', 'interrupted')),
    request jsonb NOT NULL,
    config_text text NOT NULL,
    log text NOT NULL DEFAULT '',
    result jsonb,
    error text,
    cancel_requested boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz
);
CREATE TABLE swisstip.admin_reviews (
    review_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id text NOT NULL REFERENCES swisstip.admin_jobs,
    result_sha256 text NOT NULL,
    candidate_id text NOT NULL,
    reviewer text NOT NULL,
    decision text NOT NULL CHECK (decision IN ('accept_draft', 'reject', 'needs_changes')),
    notes text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON swisstip.admin_jobs (created_at);
CREATE TRIGGER immutable_admin_asset BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.admin_assets
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
CREATE TRIGGER immutable_admin_review BEFORE UPDATE OR DELETE OR TRUNCATE ON swisstip.admin_reviews
FOR EACH STATEMENT EXECUTE FUNCTION swisstip.reject_artifact_change();
