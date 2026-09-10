# Source plugins

Source-specific acquisition is an extension of `swisstip-ingestion`. The shared
runner handles network policy, raw storage, resume checks and provenance. A plugin
recognizes source URLs, resolves them to document representations, and optionally
customizes local normalization. Fedlex is the first bundled implementation.

## Standard workflow

```shell
./.venv/Scripts/python.exe -m swisstip.builder.download_cli --catalogue config/catalogs/hackathon.sources.md --output .local/corpora/pilot-002
./.venv/Scripts/python.exe -m swisstip.builder.download_cli --catalogue config/catalogs/hackathon.sources.md --output .local/corpora/pilot-002 --download
./.venv/Scripts/python.exe -m swisstip.builder.concept_cli .local/corpora/pilot-002/fedlex-documents/pages/URL_HASH/attempt-001/response.html --dry-run
```

Replace `URL_HASH` with the document folder listed in the download summary. The
first command only writes a plan. The second snapshots exact catalogue URLs and
runs enabled source resolvers. The last command verifies and normalizes the saved
document without model calls. Omit `--dry-run` for configured concept extraction;
existing page, input and request budgets still apply. Large laws need explicit
budget planning. Acquisition never invokes a model or publishes to MCP.

`swisstip-download` is also registered as a console entry point when the builder
package is installed. The old `scripts/catalogs/download_hackathon.py` and
`download_fedlex.py` commands delegate to the shared implementation.

## Extension contract (API version 1)

Implement `SourcePlugin` from `swisstip.ingestion.source_plugins`:

| Member | Responsibility |
| --- | --- |
| `plugin_id`, `version`, `api_version` | Stable identity, implementation version and supported API. |
| `metadata_hosts`, `document_hosts` | Exact allowed host names for metadata and document requests. |
| `max_documents` | Maximum representations returned per source (default 8, maximum 100). |
| `matches(url)` | Recognize supported source URLs without network access. Multiple matches fail explicitly. |
| `resolve(request, fetch_json)` | Return `SourceDocument` values using the source URL and acquisition `as_of` date. |
| `normalize(path, provenance, **options)` | Optional local normalization returning `NormalizedPage`; defaults to the existing HTML/text normalizer. |

Example package implementation:

```python
from swisstip.ingestion.source_plugins import SourceDocument, SourcePlugin


class ExampleSource(SourcePlugin):
    plugin_id = "example"
    version = "1.0.0"
    metadata_hosts = ("example.gov",)
    document_hosts = ("example.gov",)
    max_documents = 1

    def matches(self, url):
        return url == "https://example.gov/permit"

    def resolve(self, request, fetch_json):
        data = fetch_json("https://example.gov/api/permit.json")
        return [SourceDocument(
            url=data["html_url"], media_type="text/html", language=data["language"],
            version_uri=data["version_uri"],
        )]
```

Register the class in that package's `pyproject.toml`:

```toml
[project.entry-points."swisstip.source_plugins"]
example = "example_source:ExampleSource"
```

Install the package into the repository `.venv`, then enable it explicitly with
`--source-plugin example`. Repeat `--source-plugin fedlex` to also enable Fedlex;
explicit selections replace the default. The same selection flag is available
on `concept_cli` for custom normalization. Python entry points load installed code;
plugins are trusted extensions, not sandboxed code. No packages are downloaded or
installed by the plugin loader. Programmatic callers can use `PluginRegistry`.

Plugins must use `fetch_json` instead of making their own network requests. The
runner permits four metadata fetches per source, with a 2 MB response limit and
the crawler's robots, public-network, redirect and time checks. Metadata responses
are cached with SHA-256 records. Document downloads use the same crawler and
25 MB cap as catalogue snapshots. Supported archival response types are HTML,
PDF, plain text, XML and binary data; adding a new text extractor is separate.

## Storage, resume and extraction

Each adapter writes `<plugin-id>-documents/plan.json`, `metadata/`, `pages/` and
`summary.json`. Manifests retain the original source page, resolved document URL,
language, version, plugin/API identity, retrieval time, raw hash and resolver
metadata references. HTML is preferred for extraction; PDFs are retained for
archival comparison. Resolution failures are recorded and cause a nonzero download
exit, even when all successfully resolved documents were saved.

Resume preserves successful snapshots after verifying their hashes. Failed
resolution/download attempts require `--retry-failed`. A changed catalogue or
plugin version requires a new output directory. A completed legacy Fedlex archive
can be reused unchanged; incomplete legacy archives require a new directory.

`normalize_source_snapshot` binds adjacent manifests to input files and checks
their raw hashes, review flags and plugin identity before calling normalization.
Plain files without manifests continue through generic normalization. Provenance
appears in standard concept reports and dry-run plans; empty provenance preserves
existing plain-page report and checkpoint behavior. These checks establish local
traceability, not legal validity or completeness of extracted evidence.

## Fedlex scope

The bundled plugin recognizes undated `/eli/cc/.../<language>` references. It uses
public JOLux metadata to select the latest dated consolidation at or before the
main acquisition plan's date, in the requested language. It saves public HTML
and PDF representations, checks work/version/language consistency, and reports
missing HTML explicitly. It does not switch languages or interpret consolidation
dates as proof that every provision is legally applicable.

Portal/search pages and unsupported URL forms retain ordinary snapshot behavior.
JavaScript shells cannot serve as extraction inputs. PDF text extraction and OCR
are not implemented by this plugin. Existing HTML normalization and concept
extraction are reused; this change does not tune legal extraction prompts.

## Validation (2026-09-10)

The ingestion and knowledge-builder suites pass 352 tests, including plugin
selection, host/size contracts, resume, metadata integrity, source provenance and
legacy checkpoint compatibility. Saved metadata for all seven corpus laws was
replayed through the Fedlex plugin, and all seven HTML files normalized with
verified hashes and source/version provenance.

A live standard download of GebV-AIG saved the landing page plus its dated HTML
and PDF. A subsequent standard extraction dry run retained the plugin identity
and version URI and sent zero model requests. Local evidence is under
`.local/corpora/plugin-fedlex-smoke-2026-09-10/run/`, including
`extraction-dry-run.json`; the corpus is excluded from Git.
