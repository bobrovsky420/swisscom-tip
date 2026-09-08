from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ActionRequest(StrictModel):
    pass


class Source(BaseModel):
    source_id: str
    title: str
    language: str
    url: str
    scan_status: str
    selected: bool


class Profile(BaseModel):
    name: str
    adapter: str
    model: str
    credential_ready: bool
    selected: bool


class Catalog(BaseModel):
    sources: list[Source]
    profiles: list[Profile]
    crawl_profiles: list[str]
    max_pages: int
    max_requests: int


class Asset(BaseModel):
    asset_id: str
    source_id: str
    filename: str
    sha256: str
    origin: str
    size: int
    created_at: datetime


class JobRequest(StrictModel):
    kind: Literal['crawl', 'plan', 'extract']
    source_ids: list[str] = Field(default_factory=list, max_length=10)
    asset_ids: list[str] = Field(default_factory=list, max_length=10)
    profile: str = 'ollama_local'
    crawl_profile: Literal['smoke'] = 'smoke'


class Job(BaseModel):
    job_id: str
    kind: str
    status: str
    request: dict[str, Any]
    log: str
    result: dict[str, Any] | None
    result_sha256: str | None = None
    error: str | None
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ReviewRequest(StrictModel):
    result_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    candidate_id: str = Field(min_length=1, max_length=200)
    reviewer: str = Field(min_length=1, max_length=100)
    decision: Literal['accept_draft', 'reject', 'needs_changes']
    notes: str = Field(default='', max_length=4000)


class UploadRequest(StrictModel):
    source_id: str = Field(min_length=1, max_length=100)
    filename: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=2_000_000)


class Release(BaseModel):
    release_id: str
    classification: str
    evidence_count: int
    imported_at: datetime


class Evidence(BaseModel):
    evidence_id: str
    source_id: str
    language: str
    original_excerpt: str
    citation_url: str


class Section(BaseModel):
    section_id: str
    text: str


class Preview(BaseModel):
    title: str
    language: str | None
    sections: list[Section]
    characters: int
    excluded_sections: int


class Message(BaseModel):
    message: str
