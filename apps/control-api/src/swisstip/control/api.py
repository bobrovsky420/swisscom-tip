"""Loopback-only operator API. Start with scripts/admin/run.py."""
from pathlib import Path
import os
import tempfile
import tomllib
import tomli_w
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from psycopg.types.json import Jsonb
from swisstip.builder.source_catalog import load_source_catalog, build_plan
from swisstip.core.model_profiles import load_model_config
from swisstip.ingestion.concepts import normalize_downloaded_page, CandidateConceptExtractor, STRUCTURED_PROMPT_PROFILE
from swisstip.ingestion.structured_extraction import StructuredExtraction
from swisstip.runtime.postgres import connect, sha256
from .models import (ActionRequest, Asset, Catalog, Evidence, Job, JobRequest, Message, Preview,
                     Release, ReviewRequest, UploadRequest)
from .store import ROOT, add_asset, database_url, jobs, result_hash, rows, save_job

app = FastAPI(title='SwissTIP local control API', version='0.1.0')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost'])
DEFAULT_SOURCES = {'ch-sem-residence-de', 'ch-sem-residence-en', 'zh-eu-efta'}


@app.middleware('http')
async def local_requests(request: Request, call_next):
    if request.method not in {'GET', 'HEAD'}:
        origin = request.headers.get('origin')
        if request.headers.get('x-swisstip-local') != '1' or origin not in {
            None, 'http://127.0.0.1:8000', 'http://localhost:8000',
            'http://127.0.0.1:5173', 'http://localhost:5173'
        }:
            return JSONResponse({'detail': 'Use the local operator console'}, status_code=403)
        try:
            size = int(request.headers.get('content-length', '0'))
        except ValueError:
            return JSONResponse({'detail': 'Invalid content length'}, status_code=400)
        if not 0 < size <= 2_100_000:
            return JSONResponse({'detail': 'Request must be at most 2.1 MB'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


def catalog_data():
    return load_source_catalog(ROOT / 'config/catalogs/hackathon.sources.json')


def config_text(profile):
    path = ROOT / 'config/semantic-models.toml'
    data = load_model_config(path)
    if profile not in data['profiles']:
        raise HTTPException(422, 'Unknown semantic-model profile')
    # Freeze resolved model definitions so queued jobs do not depend on later
    # catalog edits. Prompt paths still refer to the original config directory.
    data['semantic_model']['active_profile'] = profile
    for key in ('extraction_prompt_file', 'review_prompt_file'):
        if value := data['extraction'].get(key):
            data['extraction'][key] = str((path.parent / value).resolve())
    # GUI jobs never silently retry requests. Repairs remain a separate configured
    # extraction operation and are included in the displayed request ceiling.
    data.setdefault('recovery', {})['max_retries'] = 0
    return tomli_w.dumps(data)


def find_job(identifier):
    found = jobs(identifier)
    if not found:
        raise HTTPException(404, 'Job not found')
    return found[0]


@app.get('/api/catalog', response_model=Catalog, operation_id='getCatalog')
def catalog():
    data = catalog_data()
    config = load_model_config(ROOT / 'config/semantic-models.toml')
    return dict(sources=[dict(source_id=s['definition']['source_id'], title=s.get('title', s['definition']['source_id']),
                             language=s['definition']['language'], url=s['definition']['start_url'],
                             scan_status=s['scan_status'], selected=s['definition']['source_id'] in DEFAULT_SOURCES)
                         for s in data['sources']],
                profiles=[dict(name=name, adapter=p['adapter'], model=p['model'],
                               credential_ready=not p.get('token_env') or bool(os.environ.get(p['token_env'])),
                               selected=name == config['semantic_model']['active_profile'])
                          for name, p in config['profiles'].items()],
                crawl_profiles=['smoke'], max_pages=config['extraction']['max_pages_per_run'],
                max_requests=config['extraction']['max_model_requests_per_run'])


@app.get('/api/assets', response_model=list[Asset], operation_id='getAssets')
def assets():
    return rows('SELECT asset_id,source_id,filename,sha256,origin,octet_length(original_bytes) AS size,created_at '
                'FROM swisstip.admin_assets ORDER BY created_at DESC LIMIT 500')


@app.post('/api/assets/pilot', response_model=Message, operation_id='loadPilotAssets')
def load_pilot(body: ActionRequest):
    archived = rows("SELECT DISTINCT ON (path) path,original_bytes,file_sha256 FROM swisstip.attachments "
                    "WHERE path LIKE %s ORDER BY path", ('crawl/%/pages/%.html',))
    for row in archived:
        raw = bytes(row['original_bytes'])
        if sha256(raw) != row['file_sha256']:
            raise HTTPException(409, 'Archived page hash mismatch')
        path = Path(row['path'])
        add_asset(path.parts[1], path.name, raw, 'Archived pilot crawl')
    return {'message': f'{len(archived)} saved pilot pages available. No network requests sent.'}


@app.post('/api/assets', response_model=Message, operation_id='uploadAsset')
def upload_asset(body: UploadRequest):
    if body.source_id not in {s['definition']['source_id'] for s in catalog_data()['sources']}:
        raise HTTPException(422, 'Choose a source from the catalog')
    if Path(body.filename).name != body.filename or '/' in body.filename or '\\' in body.filename:
        raise HTTPException(422, 'Filename must not contain a path')
    if Path(body.filename).suffix.lower() not in {'.html', '.htm', '.txt', '.md', '.markdown'}:
        raise HTTPException(422, 'Upload HTML, text or Markdown')
    try:
        add_asset(body.source_id, body.filename, body.text.encode('utf-8'), 'Operator upload; source identity declared')
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {'message': 'Saved a new immutable page snapshot.'}


@app.get('/api/assets/{identifier}/preview', response_model=Preview, operation_id='previewAsset')
def preview(identifier: str):
    found = rows('SELECT filename,original_bytes,sha256 FROM swisstip.admin_assets WHERE asset_id=%s', (identifier,))
    if not found:
        raise HTTPException(404, 'Page not found')
    raw = bytes(found[0]['original_bytes'])
    if sha256(raw) != found[0]['sha256']:
        raise HTTPException(409, 'Snapshot hash mismatch')
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / ('page' + Path(found[0]['filename']).suffix)
        path.write_bytes(raw)
        try:
            page = normalize_downloaded_page(path, logical_blocks=True)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    _, inventory = StructuredExtraction(CandidateConceptExtractor(None, active_profile='preview',
                                        prompt_profile=STRUCTURED_PROMPT_PROFILE)).plan(page)
    visible = [s for s in inventory if s['status'] != 'excluded_policy']
    return dict(title=page.title, language=page.language,
                sections=[dict(section_id=s['section_id'], text=s['evidence_text']) for s in visible],
                characters=sum(len(s['evidence_text']) for s in visible),
                excluded_sections=len(inventory) - len(visible))


@app.get('/api/jobs', response_model=list[Job], operation_id='getJobs')
def list_jobs():
    return jobs()


@app.post('/api/jobs', response_model=Job, status_code=202, operation_id='createJob')
def create_job(body: JobRequest):
    config = config_text(body.profile)
    if body.kind == 'crawl':
        if not body.source_ids or body.asset_ids:
            raise HTTPException(422, 'Select 1-10 sources for crawling')
        try:
            plan = build_plan(catalog_data(), source_ids=body.source_ids, profile=body.crawl_profile)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if any(s['scan_status'] != 'ready' for s in plan['sources']):
            raise HTTPException(422, 'Selection includes a source that needs access review')
    else:
        if not body.asset_ids or body.source_ids or len(set(body.asset_ids)) != len(body.asset_ids):
            raise HTTPException(422, 'Select 1-10 distinct saved pages')
        found = rows('SELECT asset_id FROM swisstip.admin_assets WHERE asset_id=ANY(%s)', (body.asset_ids,))
        if len(found) != len(body.asset_ids):
            raise HTTPException(422, 'Some selected pages are unavailable')
        if body.kind == 'extract':
            profile = tomllib.loads(config)['profiles'][body.profile]
            if profile.get('token_env') and not os.environ.get(profile['token_env']):
                raise HTTPException(422, f"Set {profile['token_env']} before starting the console")
    if body.kind == 'crawl':
        import json
        config = json.dumps(catalog_data(), ensure_ascii=False)
    return save_job(body, config)


@app.get('/api/jobs/{identifier}', response_model=Job, operation_id='getJob')
def get_job(identifier: str):
    return find_job(identifier)


@app.post('/api/jobs/{identifier}/cancel', response_model=Message, operation_id='cancelJob')
def cancel_job(identifier: str, body: ActionRequest):
    find_job(identifier)
    with connect(database_url()) as conn:
        conn.execute("UPDATE swisstip.admin_jobs SET cancel_requested=true, "
                     "status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END, "
                     "finished_at=CASE WHEN status='queued' THEN now() ELSE finished_at END "
                     "WHERE job_id=%s AND status IN ('queued','running')", (identifier,))
    return {'message': 'Cancellation requested. Completed artifacts are retained.'}


@app.get('/api/jobs/{identifier}/reviews', operation_id='getReviews')
def reviews(identifier: str) -> list[dict]:
    find_job(identifier)
    return rows('SELECT candidate_id,reviewer,decision,notes,created_at,result_sha256 FROM swisstip.admin_reviews '
                'WHERE job_id=%s ORDER BY review_id', (identifier,))


@app.post('/api/jobs/{identifier}/reviews', response_model=Message, operation_id='addReview')
def review(identifier: str, body: ReviewRequest):
    job = find_job(identifier)
    if job['result_sha256'] != body.result_sha256 or job['result'] is None:
        raise HTTPException(409, 'Review is for a different result revision')
    candidates = [c for report in job['result'].get('reports', []) for c in report.get('candidates', [])]
    if not any(c['candidate_id'] == body.candidate_id for c in candidates):
        raise HTTPException(422, 'Candidate is not in this result')
    if not body.reviewer.strip():
        raise HTTPException(422, 'Reviewer name is required')
    with connect(database_url()) as conn:
        conn.execute('INSERT INTO swisstip.admin_reviews (job_id,result_sha256,candidate_id,reviewer,decision,notes) '
                     'VALUES (%s,%s,%s,%s,%s,%s)',
                     (identifier, body.result_sha256, body.candidate_id, body.reviewer.strip(), body.decision, body.notes))
    return {'message': 'Draft review recorded. Publication is a separate workflow.'}


@app.get('/api/releases', response_model=list[Release], operation_id='getReleases')
def releases():
    return rows('SELECT r.release_id,r.classification,r.imported_at,count(e.evidence_id)::int AS evidence_count '
                'FROM swisstip.releases r LEFT JOIN swisstip.evidence e USING (release_id) '
                'GROUP BY r.release_id ORDER BY r.imported_at DESC')


@app.get('/api/releases/{identifier}/evidence', response_model=list[Evidence], operation_id='getReleaseEvidence')
def evidence(identifier: str):
    return rows('SELECT evidence_id,source_id,language,original_excerpt,citation_url FROM swisstip.evidence '
                'WHERE release_id=%s ORDER BY evidence_id', (identifier,))


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    # Database connection strings and provider credentials must not reach a browser.
    return JSONResponse({'detail': f'Control service unavailable ({type(exc).__name__}). Check the local service logs.'}, status_code=503)


dist = ROOT / 'apps/admin-console/dist'
if dist.is_dir():
    app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='static-assets')


@app.get('/', include_in_schema=False)
def index():
    if not (dist / 'index.html').is_file():
        raise HTTPException(503, 'Build apps/admin-console first; see its README')
    return FileResponse(dist / 'index.html')
