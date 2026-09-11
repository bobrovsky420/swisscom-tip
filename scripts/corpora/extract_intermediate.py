"""Local source-text extraction. No SwissTIP application imports, network or models."""
import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
from importlib.metadata import version
import io
import json
from pathlib import Path
import re
from urllib.parse import urljoin

from lxml import html
from pypdf import PdfReader

FORMAT = 'swisstip.source-intermediate/v1'
EXTRACTOR_VERSION = '1.1.0'
IGNORED = {'script', 'style', 'noscript', 'svg', 'canvas', 'template', 'head'}
STRUCTURAL = {'address', 'article', 'aside', 'blockquote', 'button', 'caption', 'dd', 'details',
              'div', 'dl', 'dt', 'fieldset', 'figcaption', 'figure', 'footer', 'form', 'header',
              'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'li', 'main', 'nav', 'ol', 'p', 'pre',
              'section', 'summary', 'table', 'ul'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def clean(text):
    return re.sub(r'\s+', ' ', text).strip()


def tag(node):
    return node.tag.lower() if isinstance(node.tag, str) else ''


def inline_text(node):
    if not tag(node) or tag(node) in IGNORED:
        return ''
    if tag(node) == 'br':
        return '\n'
    return (node.text or '') + ''.join(('\n' if tag(child) in STRUCTURAL else '') +
                                      inline_text(child) + ('\n' if tag(child) in STRUCTURAL else '') +
                                      (child.tail or '') for child in node)


def encoding(raw):
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return 'utf-16'
    try:
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        match = re.search(br'charset\s*=\s*[\"\x27]?([a-zA-Z0-9_-]+)', raw[:8192])
        if match:
            candidate = match[1].decode('ascii')
            raw.decode(candidate)  # Never silently replace invalid source characters.
            return candidate
        raw.decode('windows-1252')
        return 'windows-1252'


class HtmlBlocks:
    def __init__(self, raw, url):
        self.encoding = encoding(raw)
        self.root = html.fromstring(raw.decode(self.encoding), parser=html.HTMLParser(no_network=True))
        self.tree = self.root.getroottree()
        base = self.root.xpath('//base/@href')
        self.url = urljoin(url, base[0]) if base else url
        self.blocks, self.headings = [], []
        self.ignored = Counter(tag(n) for n in self.root.iter() if tag(n) in IGNORED)

    def links(self, node):
        links = []
        for anchor in node.iter():
            if tag(anchor) == 'a' and anchor.get('href'):
                links.append(dict(text=clean(inline_text(anchor)), href=anchor.get('href'),
                                  resolved_url=urljoin(self.url, anchor.get('href'))))
        return links

    def context(self, node):
        ancestors = [node, *node.iterancestors()]
        region = next((tag(n) for n in ancestors if tag(n) in {'nav', 'header', 'footer', 'aside', 'form', 'main'}), 'body')
        roles = [n.get('role') for n in ancestors if n.get('role')]
        anchor = next((n.get('id') for n in ancestors if n.get('id')), None)
        article_id = next((n.get('id') for n in ancestors if tag(n) == 'article' and n.get('id')), None)
        footnote = any('footnote' in n.get('class', '').lower() or n.get('id', '').startswith('fn-') for n in ancestors)
        lists = []
        for n in reversed(ancestors):
            if tag(n) == 'li':
                parent = n.getparent()
                lists.append(dict(ordered=tag(parent) == 'ol', item_position=len(n.xpath('preceding-sibling::li')) + 1,
                                  start=parent.get('start'), value=n.get('value')))
        return dict(dom_path=self.tree.getpath(node), anchor=anchor, article_id=article_id,
                    region=region, aria_roles=roles, in_main=any(tag(n) == 'main' or n.get('role') == 'main' for n in ancestors),
                    explicit_hidden=any('hidden' in n.attrib or n.get('aria-hidden') == 'true' or
                                        re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', n.get('style', ''))
                                        for n in ancestors),
                    is_footnote=footnote, list_context=lists)

    def emit(self, node, text, kind=None, links=None, **extra):
        if not text.strip():
            return
        kind = kind or {'p': 'paragraph', 'li': 'list_item', 'dt': 'definition_term', 'dd': 'definition',
                        'pre': 'preformatted', 'blockquote': 'quotation', 'summary': 'disclosure_title',
                        'button': 'control', 'figcaption': 'caption'}.get(tag(node), 'text')
        links = list(links or [])
        for ancestor in node.iterancestors():
            if tag(ancestor) == 'a' and ancestor.get('href'):
                links.append(dict(text=clean(inline_text(ancestor)), href=ancestor.get('href'),
                                  resolved_url=urljoin(self.url, ancestor.get('href'))))
        self.blocks.append(dict(kind=kind, text=text, heading_path=[h[1] for h in self.headings],
                                source_locator=self.context(node), links=links, **extra))

    def walk(self, node):
        name = tag(node)
        if not name or name in IGNORED:
            return
        if name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            text = clean(inline_text(node))
            level = int(name[1])
            self.headings = [h for h in self.headings if h[0] < level]
            if text:
                self.headings.append((level, text))
                self.emit(node, text, 'heading', self.links(node), level=level)
            return
        if name == 'table':
            rows = []
            for row in node.xpath('.//tr'):
                if row.xpath('ancestor::table[1]')[0] is not node:
                    continue
                cells = [dict(text=clean(inline_text(cell)), header=tag(cell) == 'th',
                              rowspan=cell.get('rowspan', '1'), colspan=cell.get('colspan', '1'),
                              dom_path=self.tree.getpath(cell)) for cell in row if tag(cell) in {'td', 'th'}]
                if cells:
                    rows.append(cells)
            caption = clean(' '.join(inline_text(c) for c in node.xpath('./caption')))
            text = '\n'.join(([caption] if caption else []) + ['\t'.join(c['text'] for c in row) for row in rows])
            self.emit(node, text, 'table', self.links(node), rows=rows, caption=caption,
                      nested_table_count=len(node.xpath('.//table')))
            return
        pieces, links = [node.text or ''], []

        def flush():
            value = ''.join(pieces)
            self.emit(node, value.strip() if name == 'pre' else clean(value), links=list(links))
            pieces.clear()
            links.clear()

        for child in node:
            child_tag = tag(child)
            if child_tag in IGNORED or not child_tag:
                pass
            elif child_tag in STRUCTURAL or any(tag(n) in STRUCTURAL for n in child.iterdescendants()):
                flush()
                self.walk(child)
            else:
                pieces.append(inline_text(child))
                links.extend(self.links(child))
            pieces.append(child.tail or '')
        flush()

    def extract(self):
        bodies = self.root.xpath('//body')
        self.walk(bodies[0] if bodies else self.root)
        return self.blocks


def extract_html(raw, url):
    parser = HtmlBlocks(raw, url)
    blocks = parser.extract()
    document_title = clean(parser.root.xpath('string(//title)'))
    headings = [b['text'] for b in blocks if b['kind'] == 'heading' and b['level'] == 1]
    page_kind = 'ordinary_page'
    if document_title.lower() == 'fedlex' or parser.root.xpath('//*[local-name()="fedlex-app" or local-name()="app-root"]'):
        page_kind = 'application_shell'
    if b'window.CONTENT_ID' in raw and b'window.IS_FRONTEND' in raw and sum(len(b['text']) for b in blocks)<300:
        page_kind = 'application_shell'
    if re.search(r'wartungsarbeiten|maintenance|lavurs da mantegniment|lavori di manutenzione', document_title, re.I):
        page_kind = 'maintenance_page'
    error_titles = [document_title, *headings]
    if any(re.fullmatch(r'\s*(?:Error Page\s*\(404\)|404(?:\s*[-:]?\s*(?:Not Found|Page not found))?|'
                        r'Page not found|Not Found|Seite nicht gefunden|Page introuvable|Pagina non trovata|'
                        r'Access Denied|Forbidden)\s*', title, re.I) for title in error_titles):
        page_kind = 'error_page'
    bodies = parser.root.xpath('//body')
    source_sequence = re.sub(r'\s+', '', inline_text(bodies[0] if bodies else parser.root))
    extracted_sequence = re.sub(r'\s+', '', ''.join(b['text'] for b in blocks))
    warnings = ['character_encoding_fallback'] if parser.encoding == 'windows-1252' else []
    if source_sequence != extracted_sequence:
        warnings.append('html_text_sequence_differs_review_required')
    return dict(blocks=blocks, html_title=document_title, main_headings=headings,
                language_declared=parser.root.get('lang') or parser.root.get('{http://www.w3.org/XML/1998/namespace}lang'),
                decoding=parser.encoding, page_kind=page_kind, ignored_nontext_elements=dict(parser.ignored),
                warnings=warnings,
                text_integrity=dict(method='DOM text sequence excluding nontext elements and whitespace',
                    sequence_preserved=source_sequence == extracted_sequence,
                    source_sequence_sha256=digest(source_sequence.encode('utf-8')),
                    extracted_sequence_sha256=digest(extracted_sequence.encode('utf-8'))))


def extract_pdf(raw):
    reader = PdfReader(io.BytesIO(raw))
    blocks, blank = [], []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ''
        if not text.strip():
            blank.append(number)
        else:
            blocks.append(dict(kind='pdf_page', text=text.strip(), heading_path=[],
                               source_locator={'page_number': number}, links=[]))
    fields = []
    for name, field in (reader.get_fields() or {}).items():
        fields.append(dict(name=name, field_type=str(field.get('/FT', '')),
                           label=str(field.get('/TU', '')), value=str(field.get('/V', '')),
                           options=[str(option) for option in field.get('/Opt', [])]))
    return dict(blocks=blocks, pdf_page_count=len(reader.pages), pages_without_text=blank, form_fields=fields,
                html_title=None, main_headings=[], language_declared=None, page_kind='pdf_document',
                decoding='PDF embedded text', warnings=['pdf_layout_and_reading_order_unverified'] +
                (['some_pdf_pages_have_no_text_no_ocr_performed'] if blank else []))


def attach_offsets(document):
    position, texts = 0, []
    for index, block in enumerate(document['blocks'], 1):
        block['block_id'] = f"{document['document_id']}:b{index:05d}"
        block['start'] = position
        block['end'] = position + len(block['text'])
        block['text_sha256'] = digest(block['text'].encode('utf-8'))
        texts.append(block['text'])
        position = block['end'] + 2
    document['content_text'] = '\n\n'.join(texts)
    document['content_sha256'] = digest(document['content_text'].encode('utf-8'))
    for block in document['blocks']:
        assert document['content_text'][block['start']:block['end']] == block['text']


def run(corpus, output):
    corpus, output = corpus.resolve(), output.resolve()
    if output.is_relative_to(corpus):
        raise ValueError('Output must be outside the immutable acquisition corpus')
    plan = json.loads((corpus / 'plan.json').read_text(encoding='utf-8'))
    if digest((corpus / 'catalogue.md').read_bytes()) != plan['catalogue_sha256']:
        raise ValueError('Acquisition catalogue hash mismatch')
    documents, missing, verified = [], [], []
    for pointer in sorted(corpus.rglob('latest.json')):
        manifest_raw = pointer.read_bytes()
        manifest = json.loads(manifest_raw)
        if not manifest.get('snapshots'):
            missing.append(dict(source_url=manifest['url'], status=manifest['status'],
                                manifest_path=pointer.relative_to(corpus).as_posix(),
                                report=manifest.get('report'), error=manifest.get('error')))
            continue
        for snapshot in manifest['snapshots']:
            path = (pointer.parents[2] / snapshot['relative_path']).resolve()
            if not path.is_relative_to(corpus):
                raise ValueError('Snapshot escapes corpus')
            raw = path.read_bytes()
            if digest(raw) != snapshot['sha256'] or len(raw) != snapshot['bytes_downloaded']:
                raise ValueError(f'Acquisition hash/size mismatch: {path}')
            relative = path.relative_to(corpus).as_posix()
            verified.append(dict(path=relative, sha256=digest(raw)))
            source_url = manifest.get('source_page_url', manifest['url'])
            document = dict(schema_version=FORMAT, document_id='doc-' + digest(relative.encode())[:20],
                corpus_id=corpus.name, source_url=source_url, document_url=snapshot['final_url'],
                version_uri=manifest.get('version_uri'), source_registry=manifest.get('registry_entries', []),
                catalogue_references=manifest.get('references', []),
                acquisition=dict(path=relative, manifest_path=pointer.relative_to(corpus).as_posix(),
                    manifest_sha256=digest(manifest_raw), raw_sha256=digest(raw), bytes=len(raw),
                    retrieved_at=snapshot['retrieved_at'], requested_url=snapshot['requested_url'],
                    declared_content_type=snapshot['content_type'], review_flags=snapshot.get('review_flags', [])),
                extractor_version=EXTRACTOR_VERSION, representation_group='source-' + digest(source_url.encode())[:20])
            try:
                if raw.startswith(b'%PDF-'):
                    document.update(extract_pdf(raw), representation='pdf')
                elif re.search(br'<(?:!doctype\s+html|html|head|body)\b', raw[:8192], re.I) or path.suffix.lower() in {'.html', '.htm'}:
                    document.update(extract_html(raw, snapshot['final_url']), representation='html')
                else:
                    codec = encoding(raw)
                    document.update(blocks=[dict(kind='plain_text', text=raw.decode(codec), heading_path=[],
                                                source_locator={'file': relative}, links=[])],
                                    representation='text', decoding=codec, warnings=[], page_kind='text_document',
                                    html_title=None, main_headings=[], language_declared=None)
                flags = snapshot.get('review_flags', [])
                excluded = document['page_kind'] in {'application_shell', 'maintenance_page', 'error_page'} or bool(flags)
                document['eligible_for_processing'] = bool(document['blocks']) and not excluded
                document['status'] = ('excluded_source_response' if excluded else
                                      'extracted' if document['blocks'] else 'no_extractable_text')
                document['exclusion_reasons'] = ([document['page_kind']] if excluded else []) + flags
            except Exception as exc:
                document.update(blocks=[], representation='unknown', warnings=[f'{type(exc).__name__}: {exc}'],
                                status='extraction_failed', eligible_for_processing=False,
                                html_title=None, main_headings=[], language_declared=None)
            hints = [s['definition'].get('language') for s in document['source_registry']]
            url_language = re.search(r'/eli/cc/.+/(de|fr|it|en|rm)$', source_url)
            document['language_hint'] = manifest.get('language') or next((h for h in hints if h), None) or (
                url_language[1] if url_language else None)
            refs = document['catalogue_references']
            title = document['html_title']
            document['title'] = title if title and not title.startswith('input-') else (
                refs[0]['label'] if refs else next(iter(document['main_headings']), source_url))
            attach_offsets(document)
            documents.append(document)
    groups, hashes = defaultdict(list), defaultdict(list)
    for doc in documents:
        groups[doc['representation_group']].append(doc)
        hashes[doc['acquisition']['raw_sha256']].append(doc['document_id'])
    for doc in documents:
        html_ids = [d['document_id'] for d in groups[doc['representation_group']]
                    if d['representation'] == 'html' and d['eligible_for_processing']]
        doc['preferred_representation'] = doc['eligible_for_processing'] and (doc['representation'] != 'pdf' or not html_ids)
        doc['html_counterparts'] = html_ids if doc['representation'] == 'pdf' else []
        doc['identical_raw_snapshots'] = [i for i in hashes[doc['acquisition']['raw_sha256']] if i != doc['document_id']]
    output.mkdir(parents=True, exist_ok=False)
    (output / 'documents').mkdir()
    with (output / 'documents.jsonl').open('w', encoding='utf-8') as stream:
        for doc in documents:
            stream.write(json.dumps(doc, ensure_ascii=False) + '\n')
            (output / 'documents' / (doc['document_id'] + '.json')).write_text(
                json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    index = [{k: d.get(k) for k in ('document_id', 'title', 'source_url', 'document_url', 'representation',
                                   'status', 'eligible_for_processing', 'preferred_representation', 'html_counterparts',
                                   'language_declared', 'language_hint', 'version_uri', 'exclusion_reasons')}
             | {'block_count': len(d['blocks']), 'text_characters': len(d['content_text']),
                'file': 'documents/' + d['document_id'] + '.json'} for d in documents]
    summary = dict(schema_version=FORMAT, corpus_id=corpus.name, generated_at=datetime.now(UTC).isoformat(),
                   extractor_version=EXTRACTOR_VERSION, script_sha256=digest(Path(__file__).read_bytes()),
                   dependencies={name: version(name) for name in ('lxml', 'pypdf')},
                   catalogue_sha256=plan['catalogue_sha256'], document_count=len(documents),
                   status_counts=dict(Counter(d['status'] for d in documents)),
                   representations=dict(Counter(d['representation'] for d in documents)),
                   eligible_count=sum(d['eligible_for_processing'] for d in documents),
                   preferred_count=sum(d['preferred_representation'] for d in documents),
                   block_count=sum(len(d['blocks']) for d in documents),
                   text_characters=sum(len(d['content_text']) for d in documents),
                   unavailable_count=len(missing), model_calls=0, network_requests=0, application_invoked=False,
                   pdf_ocr_performed=False, verified_snapshots=verified)
    for filename, value in [('index.json', index), ('summary.json', summary), ('unavailable.json', missing)]:
        (output / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Intermediate source extraction', '',
             f"Corpus: `{corpus.name}`. {len(documents)} downloaded responses; {len(missing)} unavailable URLs.",
             f"Statuses: {summary['status_counts']}. Preferred representations: {summary['preferred_count']}.", '',
             'Start with `index.json`; `documents.jsonl` contains all records and `documents/` contains readable JSON files.',
             'No application, network requests, model calls, database writes or OCR were used during extraction.',
             'Source text and DOM/PDF structure are retained. These are not interpreted or reviewed legal rules.',
             'Text offsets address content_text after whitespace normalization, not raw HTML byte offsets.',
             'Navigation, footer text and hidden HTML are retained with source-region/visibility labels.',
             'Scripts, styles, noscript fallbacks, SVG, canvas and templates are omitted from text.',
             'Excluded maintenance/shell responses remain in the output with eligible_for_processing=false.',
             'PDF reading order is unverified. Fedlex PDFs link to their preferred HTML counterparts; no equivalence is inferred.',
             'Identical raw snapshots remain distinct source records and are linked for later deduplication.', '',
             '| Source | Status | Blocks | JSON |', '| --- | --- | ---: | --- |']
    for d in index:
        lines.append(f"| {d['title'].replace('|', '/')} | {d['status']} | {d['block_count']} | [{d['document_id']}]({d['file']}) |")
    (output / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'verified_snapshots'}, indent=2))
    return int(any(d['status'] == 'extraction_failed' for d in documents))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.corpus, args.output))
