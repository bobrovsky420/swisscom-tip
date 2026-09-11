"""Import complete local acquisition runs, without extraction or release creation."""
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re

from .postgres import connect, sha256


@dataclass
class CorpusImport:
    corpus_id: str
    title: str
    inventory_sha256: str
    catalogue_sha256: str
    files: dict[str, bytes]
    assets: list[dict]
    metadata: dict


def prepare_corpus(folder: Path, corpus_id: str, title: str) -> CorpusImport:
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}', corpus_id):
        raise ValueError('Use a corpus ID containing lowercase letters, numbers and hyphens')
    folder = folder.resolve()
    files = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink() or not path.resolve().is_relative_to(folder):
            raise ValueError('Corpus must contain ordinary local files, without links')
        if path.is_file():
            if path.stat().st_size > 30_000_000:
                raise ValueError(f'Corpus file exceeds 30 MB: {path.name}')
            files[path.relative_to(folder).as_posix()] = path.read_bytes()
    plan = json.loads(files['plan.json'])
    if sha256(files['catalogue.md']) != plan['catalogue_sha256']:
        raise ValueError('Catalogue bytes do not match the acquisition plan')
    assets, seen = [], set()
    for name, raw_manifest in files.items():
        manifest_path = PurePosixPath(name)
        if manifest_path.name != 'manifest.json' or not manifest_path.parent.name.startswith('attempt-'):
            continue
        manifest = json.loads(raw_manifest)
        # manifests live at [plugin-documents/]pages/URL/attempt-NNN/manifest.json.
        base = manifest_path.parents[3]
        for snapshot in manifest['snapshots']:
            relative = PurePosixPath(snapshot['relative_path'])
            if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative) or ':' in str(relative):
                raise ValueError('Unsafe snapshot path')
            key = (base / relative).as_posix()
            if key in seen:
                raise ValueError('Duplicate snapshot path')
            seen.add(key)
            raw = files[key]
            if sha256(raw) != snapshot['sha256'] or len(raw) != snapshot['bytes_downloaded']:
                raise ValueError(f'Snapshot hash or size mismatch: {key}')
            reasons = list(snapshot.get('review_flags', []))
            if relative.suffix.lower() not in {'.html', '.htm', '.txt', '.md', '.markdown'}:
                reasons.append('archived_format_without_text_extractor')
            if len(raw) > 2_000_000:
                reasons.append('exceeds_2mb_extraction_limit')
            if not reasons:
                try:
                    raw.decode('utf-8-sig')
                except UnicodeDecodeError:
                    reasons.append('requires_character_encoding_conversion')
            entries = manifest.get('registry_entries', [])
            source_id = (entries[0]['definition']['source_id'] if entries else
                         'catalogue-' + sha256(manifest.get('source_page_url', manifest['url']).encode())[:16])
            asset_id = sha256((corpus_id + '/' + key).encode())
            assets.append(dict(asset_id=asset_id, source_id=source_id,
                               filename=f'{corpus_id}-{asset_id[:16]}{relative.suffix}',
                               sha256=snapshot['sha256'], original_bytes=raw,
                               acquisition_metadata={**manifest, 'snapshots': [snapshot], 'corpus_path': key},
                               processing_eligible=not reasons, processing_reason=', '.join(reasons)))
    # Missing downloads remain recorded; a lost saved file must not silently disappear.
    for name, raw in files.items():
        if PurePosixPath(name).name == 'latest.json':
            latest = json.loads(raw)
            base = PurePosixPath(name).parents[2]
            for snapshot in latest.get('snapshots', []):
                key = (base / snapshot['relative_path']).as_posix()
                if key not in seen or sha256(files[key]) != snapshot['sha256']:
                    raise ValueError('Latest snapshot has no matching archived attempt')
    inventory = [{'path': name, 'sha256': sha256(raw)} for name, raw in sorted(files.items())]
    outcomes = []
    for name, raw in files.items():
        if PurePosixPath(name).name == 'latest.json':
            latest = json.loads(raw)
            if latest['status'] != 'saved':
                outcomes.append({'url': latest['url'], 'status': latest['status'], 'path': name})
    metadata = dict(source_directory=str(folder), acquisition_created_at=plan['created_at'],
                    file_count=len(files), file_bytes=sum(map(len, files.values())),
                    snapshot_count=len(assets), eligible_count=sum(a['processing_eligible'] for a in assets),
                    archive_only_count=sum(not a['processing_eligible'] for a in assets),
                    formats=dict(Counter(PurePosixPath(a['filename']).suffix for a in assets)),
                    unavailable=outcomes, model_calls=0, processing_status='NOT_PROCESSED')
    return CorpusImport(corpus_id, title, sha256(json.dumps(inventory, sort_keys=True).encode()),
                        plan['catalogue_sha256'], files, assets, metadata)


def import_corpus(dsn: str, corpus: CorpusImport) -> dict:
    from psycopg.types.json import Jsonb
    with connect(dsn) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(20260911)')
        existing = conn.execute('SELECT inventory_sha256,title FROM swisstip.corpora WHERE corpus_id=%s',
                                (corpus.corpus_id,)).fetchone()
        if existing:
            if existing != (corpus.inventory_sha256, corpus.title):
                raise ValueError('Corpus ID already contains different content; use a new corpus ID')
        else:
            conn.execute('INSERT INTO swisstip.corpora '
                         '(corpus_id,title,inventory_sha256,catalogue_sha256,metadata) VALUES (%s,%s,%s,%s,%s)',
                         (corpus.corpus_id, corpus.title, corpus.inventory_sha256,
                          corpus.catalogue_sha256, Jsonb(corpus.metadata)))
            with conn.cursor() as cur:
                cur.executemany('INSERT INTO swisstip.corpus_files VALUES (%s,%s,%s,%s)',
                                [(corpus.corpus_id, name, sha256(raw), raw) for name, raw in corpus.files.items()])
                cur.executemany('INSERT INTO swisstip.admin_assets '
                                '(asset_id,source_id,filename,sha256,original_bytes,origin,corpus_id,'
                                'acquisition_metadata,processing_eligible,processing_reason) '
                                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                                [(a['asset_id'], a['source_id'], a['filename'], a['sha256'], a['original_bytes'],
                                  corpus.title, corpus.corpus_id, Jsonb(a['acquisition_metadata']),
                                  a['processing_eligible'], a['processing_reason']) for a in corpus.assets])
        stored = conn.execute('SELECT path,sha256,original_bytes FROM swisstip.corpus_files WHERE corpus_id=%s',
                              (corpus.corpus_id,)).fetchall()
        if len(stored) != len(corpus.files) or any(
                name not in corpus.files or bytes(raw) != corpus.files[name] or sha256(bytes(raw)) != digest
                for name, digest, raw in stored):
            raise ValueError('Database corpus verification failed')
        assets = conn.execute('SELECT asset_id,sha256,original_bytes FROM swisstip.admin_assets WHERE corpus_id=%s',
                              (corpus.corpus_id,)).fetchall()
        if {row[0] for row in assets} != {a['asset_id'] for a in corpus.assets} or any(
                sha256(bytes(raw)) != digest for _, digest, raw in assets):
            raise ValueError('Database snapshot verification failed')
    return dict(corpus_id=corpus.corpus_id, created=existing is None,
                inventory_sha256=corpus.inventory_sha256, verified_files=len(stored), **corpus.metadata)
