# Extract local sources into intermediate JSON

This standalone script reads saved source files directly. It does not import or
invoke the SwissTIP application, connect to the database, fetch URLs, or call a
model. It uses lxml for HTML and pypdf for embedded PDF text.

```shell
./.venv/Scripts/python.exe -m pip install -r scripts/corpora/requirements.txt
./.venv/Scripts/python.exe scripts/corpora/extract_intermediate.py --corpus .local/corpora/hackathon-residence-2026-09-10 --output .local/intermediate/hackathon-residence-2026-09-11-v1
./.venv/Scripts/python.exe -m unittest discover -s scripts/corpora -p test_extract_intermediate.py
```

Output must be a new directory outside the immutable downloaded corpus. The
extractor uses the latest saved attempt per URL, verifies snapshot hashes/sizes
and the catalogue hash, and records missing downloads separately. Original
downloads and the database remain unchanged.

## Output

| File | Contents |
| --- | --- |
| `README.md` | Human-readable index linking to individual JSON records |
| `index.json` | Titles, URLs, statuses, language hints and representation relationships |
| `documents.jsonl` | One complete record per downloaded response |
| `documents/doc-*.json` | The same records, formatted individually for review |
| `summary.json` | Counts, dependencies, script hash, verified source hashes and execution metadata |
| `unavailable.json` | Failed download URLs and their acquisition reports |

Records use `swisstip.source-intermediate/v1`. Each retains the official source
and document URLs, acquisition hash/path/time, manifest hash, registry metadata,
catalogue references and available version URI. Declared HTML language and
catalogue/URL language hints are separate fields; no language is inferred by a
model. `title` prefers the HTML title, falling back to the catalogue label for
Fedlex's generic `input-*` titles. Original titles and main headings are retained.

`blocks` contain headings, paragraphs, lists, definitions, tables and PDF pages.
HTML blocks retain DOM paths, anchors, article IDs, heading paths, list positions,
footnote markers, explicit visibility attributes and links. Table cells retain
headers and row/column spans. Nested tables are flattened within their parent
cell and counted. PDF pages retain embedded text and page numbers, plus form-field
metadata where present; reading order and table layout are not reconstructed.

`content_text` joins blocks using two newlines. Block `start`/`end` offsets refer
to that Unicode string, not to raw HTML bytes. Each block and the full text have
SHA-256 hashes. HTML `text_integrity` compares the DOM and extracted text sequences
after whitespace removal and the documented nontext exclusions. This checks text
retention, not whether the page is useful evidence or whether layout was understood.

Navigation, footer, contact and explicitly hidden text remain labelled for later
review. Scripts, styles, noscript fallbacks, SVG, canvas and templates are omitted.
Maintenance pages and flagged application shells remain represented with
`eligible_for_processing=false`. PDF pages without embedded text are reported;
the script performs no OCR. Identical raw snapshots are linked without merging
their source identities. Fedlex PDF records link to available HTML counterparts;
HTML is preferred for processing without asserting equivalence of representations.

This is an intermediate source-text dataset. It does not infer eligibility rules,
deadlines, costs, legal applicability or reviewed knowledge claims.

## 2026-09-11 corpus result

The output at `.local/intermediate/hackathon-residence-2026-09-11-v1/` contains
121 records, 26,179 blocks and 2,814,419 text characters. There are 111 extracted
responses and 10 excluded responses (8 application shells and 2 maintenance
pages). All 8 PDFs produced text on every page (414 pages total); the Nidwalden
application form also yielded 60 native form fields. Seven PDF records link to
Fedlex HTML counterparts, giving 104 preferred records before content deduplication.
Eight unavailable acquisition URLs are recorded separately.

`validation.json` records successful raw/normalized hash and block-offset checks,
equality between the JSONL and individual JSON files, and preserved text sequences
for all 113 HTML responses (including the two mislabelled text responses).
Six standalone tests passed. No application, database or model was invoked.
These intermediate files are Git ignored, like the underlying corpus.

## Semantic MVP release

`residence_mvp_curated.py` contains assistant-authored claims, applicability notes
and selected evidence ranges, based on reading the saved official sources.
`build_residence_mvp.py` packages these selections directly into `serving-release/v1`.
It uses only local contract, hashing and validation libraries. It does not run the
application, call providers or models, fetch sources, or access the database.

```shell
./.venv/Scripts/python.exe scripts/corpora/build_residence_mvp.py
```

The default output is `.local/mvp/residence-semantic-2026-09-11-v1/`. Choose a new
directory with `--output` for another build; existing directories are not overwritten.
The curated block coordinates are pinned to the reviewed intermediate export hash.
Changes to source text require another semantic review and updated selections.

The pack includes 81 facts with exact cited excerpts, 19 population-routing rules,
34 concepts and 59 coverage profiles. It covers selected federal requirements,
Zurich procedures and migration contacts for all 26 cantons, using 11 official
documents. `source-disposition.json` explicitly accounts for the remaining corpus.
This is bounded MCP test coverage, not exhaustive semantic extraction of every page.

Use `release.json` as the app-ingestible artifact; `mcp-client.json` contains a
ready local server configuration, and `mcp-requests.json` contains 59 positive
examples and four negative scope/context cases. These pass the existing pure
validators; the server is not launched. Exact concept selection uses the existing
deterministic baseline without embeddings, ranking models or free-text retrieval.

The release ID `hackathon-residence-semantic-2026-09-11-v1` distinguishes this pack
from earlier attempts. No database import or activation is performed. The contract
approval flags enable an **experimental test fixture** and do not assert independent
human/legal review. The September 10-11 temporal window is frozen test scope, not
statutory validity. See the generated README and validation report for details.

## Nationwide source and language expansion

The current requested scope is every available residence-permit source and every
published language. The original 81-fact pack is retained as an earlier fixture;
it does not satisfy that scope. No step below calls SwissTIP's extraction app,
an external LLM, or an embedding provider. This is an offline data-preparation
workflow, except for explicitly requested public-source acquisition.

Install these standalone dependencies into the repository environment:

```shell
./.venv/Scripts/python.exe -m pip install -r scripts/corpora/requirements.txt
```

Acquisition is resumable. The audit follows published hreflang links, language
anchors, federal Nuxt language/slug metadata, relevant page links, attachments
and government document subdomains. It preserves the referring page and reason
for discovery. It does not invent translated URLs. Generic language menus,
identical content and HTTP 200 responses are not proof of a working translation.

```shell
./.venv/Scripts/python.exe scripts/corpora/audit_source_languages.py --download --batch-size 10000 --workers 12 --until-idle
./.venv/Scripts/python.exe scripts/corpora/audit_fedlex_languages.py
./.venv/Scripts/python.exe scripts/corpora/audit_source_languages.py --download --batch-size 10000 --workers 12 --until-idle
```

Run the Fedlex metadata audit again when discovery identifies additional laws.
It selects the latest available HTML/PDF publication separately for each language
as of the frozen date, retaining older translation dates. It does not assert that
all languages have the same consolidation date or that every historical version
has been downloaded. `download_supplement.py --seeds FILE` accepts manually
verified public links for cases such as Basel-Landschaft's published document
host. It retains those links in `additional-seeds.json` for the next audit pass.

The raw corpus is `.local/corpora/hackathon-residence-all-languages-2026-09-11/`.
`audit-state.json` contains the complete discovery graph; the checked-in
`config/catalogs/hackathon.sources.expanded.json` is a compact URL inventory.
The legacy application scan registry remains a separate artifact.

Extract native text after acquisition. Four independent shards reduce local I/O
and decoding latency; run each index 0 through 3 with the same shard count:

```shell
./.venv/Scripts/python.exe scripts/corpora/extract_expanded.py --shard-index 0 --shard-count 4
./.venv/Scripts/python.exe scripts/corpora/extract_expanded.py --shard-index 1 --shard-count 4
./.venv/Scripts/python.exe scripts/corpora/extract_expanded.py --shard-index 2 --shard-count 4
./.venv/Scripts/python.exe scripts/corpora/extract_expanded.py --shard-index 3 --shard-count 4
./.venv/Scripts/python.exe scripts/corpora/prepare_ocr.py
```

The destination is `.local/intermediate/hackathon-residence-all-languages-2026-09-11/`.
The extractor preserves text, block locations and hashes for HTML, PDF, DOC/DOT,
DOCX, XLSX and RTF. PDF layout, visual tables, revision visibility and scanned content
are not silently reported as understood. Office macros and formulas are never
executed. HTML maintenance pages, soft 404s and empty app shells are excluded.

On Windows, `Invoke-LocalOcr.ps1 -Jobs FILE` processes the rendered OCR job file
under `.local/ocr/hackathon-residence-all-languages-2026-09-11/`. It uses installed
Windows OCR recognizers and records language fallback, word boxes and unreviewed
recognition status. OCR text remains separate from verified native quotations.
Image-only HTML information and other unsupported media still require review.

After all extraction shards finish:

```shell
./.venv/Scripts/python.exe scripts/corpora/finalize_expanded.py
./.venv/Scripts/python.exe scripts/corpora/extract_source_assertions.py
./.venv/Scripts/python.exe scripts/corpora/build_expanded_pack.py
```

The finalizer validates every normalized hash and block span and writes detailed
source, language-version, failure, deferred-link and OCR ledgers. An empty crawl
frontier is not proof of exhaustive government-site coverage. The report retains
that distinction and accounts for saved responses not yet decoded.

The semantic intermediate is
`.local/semantic/hackathon-residence-all-languages-2026-09-11/assertions.jsonl`.
It contains attributed original-language source sections, headings, citations,
exact spans, topic annotations, permit mentions, numeric/date mentions and literal
condition/exception sentences. High-accuracy local Lingua language identification
is a statistical classifier, not an LLM. Source declarations and classifier
results remain separate. Published language metadata takes precedence; classifier
disagreements and language assignments inferred without metadata require review.
This is not verification of translation equivalence or every mixed-language span.
The annotations do not normalize logical eligibility conditions. These are
automatically derived source assertions, not independently curated legal rules.

The serving output is `.local/mvp/residence-all-languages-2026-09-11-v1/`.
`collection.json` lists every app-ingestible `serving-release/v1` part. Actual
contract cardinality limits determine partitioning; no tail of the corpus is
silently dropped. The MCP server loads a listed release explicitly and does not
implicitly combine parts. Exact duplicate normalized documents have a source
alias ledger. The root `mcp-client.json` loads all listed parts in one server;
requests pin the appropriate release ID from `collection.json`. Unresolved languages
and unreviewed OCR are reported separately.
Sections with dense unexpected control characters from broken native font mappings
are retained in the semantic JSONL and excluded from serving, with explicit reasons
in `unresolved-assertions.json`. Other layout and font-quality warnings remain in
the provenance and text-quality ledgers; contract validity is not a quality review.
Facts retain every character of the original assertion across bounded fragments,
with the complete section as evidence. They support reading source statements,
not a claim that all legal eligibility rules have been interpreted.

Additional source languages use the opt-in `tip-language-catalog/v4` policy and
`evidence-object/v2` contract. Existing v3/v1 releases retain their closed five-
language validation. This does not enable multilingual term retrieval or create
translations. Pure release and request validation runs without starting a server,
importing a database, calling providers or activating a release. Test-fixture
approval flags do not assert human review or production approval.

For larger corpora, assertion extraction also supports the same four-way
partitioning. Run indexes 0 through 3 with `--shard-count 4`, then run
`extract_source_assertions.py --merge --shard-count 4` before packaging. The merge
checks each completed shard hash and exact coverage of the current document index.
Profiles group at most 50 independently selectable document concepts so discovery
metadata stays inside the MCP contract's limits. Original statements are never
combined across those document selections.

`download_rendered_sources.py --url URL` can capture public JavaScript content with
an isolated headless Edge profile. It does not use existing browser sessions,
credentials or form submissions. These snapshots are labelled rendered DOM,
separately from HTTP response bodies. Language/source links from the rendering are
retained for the next audit pass. `extract_expanded.py --retry-failures` retries
only failed records in the selected shard; it does not discard successful records.
`--refresh-rtf` reprocesses rich-text records previously decoded as plain text.
`extract_source_assertions.py --reuse-detection` reuses cached statistical results
while rebuilding spans, annotations and publisher-first language assignments.
Changed RTF text is classified afresh. Run the finalizer again after packaging
to include the completed serving collection and latest OCR dispositions.

## Paced retry of failed downloads

`retry_failed_downloads.py` retries targets whose last attempt failed for a
recoverable reason: rate limits, timeouts, refused connections, server errors,
redirects that the host rules now allow, and a single fresh attempt for 404, 403,
DNS and certificate failures. It processes one host at a time with `--host-delay`
seconds between requests, backs off after HTTP 429 and pauses a host after
repeated 429 responses. Mailto redirects, the defunct `bfm.admin.ch` host and
documents over the size cap are listed as skipped unless `--oversized-limit`
allows them. Certificate verification is never disabled.

```shell
./.venv/Scripts/python.exe scripts/corpora/retry_failed_downloads.py --dry-run
./.venv/Scripts/python.exe scripts/corpora/retry_failed_downloads.py --host-delay 2 --backoff 45 --workers 6
./.venv/Scripts/python.exe -m unittest discover -s scripts/corpora -p test_retry_failed_downloads.py
```

Recovered responses are new attempt folders under the same raw corpus; the
audit state, plan and checked-in inventory are updated through the crawler's
functions, and `<label>-results.json` records every outcome, remaining error and
skipped target. Links discovered on recovered pages become pending targets for
the next audit pass. Recovered raw responses are not yet in any intermediate,
semantic or serving artifact: rebuild those as a new version before changing any
published statistic.

## Live MCP check

`live_mcp_check.py` starts the server from a completed collection's
`mcp-client.json` over MCP stdio and records real `get_coverage`, `resolve` and
`get_evidence` outcomes, citations, limits and timings. It reads each part's
`mcp-requests.json` as input only and leaves the release, the fixtures and their
`executed` flags unchanged. It makes no extraction application, LLM, provider,
database or network call. Pure validation and this live check remain separate
records.

```shell
./.venv/Scripts/python.exe scripts/corpora/live_mcp_check.py --output .local/evaluations/residence-all-languages-2026-09-11-v1-live-mcp-check
./.venv/Scripts/python.exe -m unittest discover -s scripts/corpora -p test_live_mcp_check.py
```

The output directory must not exist. `calls.jsonl` keeps every request and full
response, `summary.json` the aggregates and `README.md` a readable digest. The
check walks the catalog of every listed part, resolves a jurisdiction-balanced
sample of fixture requests (one per canton or federal scope by default, plus a
seeded random tail, within `--time-budget` seconds), reads the returned evidence
back for parity, fetches one further batch of the remaining fixture evidence
IDs, and records explicit negative and boundary cases. The script expects the
expanded collection layout with `source_url` and `evidence_ids` per request; the
earlier 81-fact pack uses a different fixture layout. Sample outcomes describe
served fixtures only, not corpus completeness or semantic review.
