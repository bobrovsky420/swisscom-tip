# Hackathon MVP knowledge space - residence permit in Switzerland

The residence-permit MCP pilot is the hackathon MVP. Its curated source plan,
nationwide inventory and acquisition gaps live in [the source catalogue](hackathon.sources.md).
The `hackathon` Knowledge Space remains source-only pending an operator-triggered
build. Its machine-readable scan registry currently contains **59 official source references**:
24 federal references, 34 cantonal references covering all 26 cantons, and one
municipal reference for the City of Zurich. Zurich has additional topic pages;
the other cantons initially have one migration/residence entry point each.

- [Browse the source catalogue](hackathon.sources.md).
- [Machine-readable sources, scope, scan sets and budgets](hackathon.sources.json).
- [Draft KnowledgeCatalog contract](hackathon.seed.json).
- [Draft language policy](hackathon.language-policy.json).

The sources include SEM/admin.ch, Fedlex, BAG, BAZG, BSV, BWO, ESTV, ch.ch, zh.ch and
official cantonal sites. Discovery references and dates are recorded per source.
These files contain URLs and planning metadata only. No source pages, extracts,
quotations, legal rules, facts or model-generated concepts are included.

## Scope and status

Fourteen planning groups cover entry/visas, permits, work for EU/EFTA and
third-country nationals, family reunification, study/non-working residence,
settlement/renewal, registration/moving, integration/language, health insurance,
housing, tax/social insurance, legal bases and competent authorities.

These groups are operator hints for selecting sources. They are not extracted
topics, gold labels or a reviewed concept taxonomy, and the extraction command
does not receive them as expected answers. The draft contract has only the
`hackathon` space, `immigration` domain and broad `residence` topic, all
`CANDIDATE`. It contains no concepts, context schemas or coverage profiles.
`hackathon-draft-001` is an authoring identifier, not a published release.

`ready` means eligible for a later crawler test, not that content, live
availability or robots access has been verified. Three access issues (AI, NW,
TG) are recorded as `needs_access_review` and excluded from automatic runs.
The three Fedlex ELI references are `manual_adapter_required`: the current HTML
crawler sees a JavaScript shell, so a later document/data adapter is needed.
The HTML brochure/directive indexes can be tested, but their linked PDFs also
need a later PDF acquisition and normalization step.

Each seed has an exact host allowlist and path scope. Department-only hosts may
use `/`; shared cantonal portals use specific paths. A shallow scan of an
authority portal can yield navigation only. Inspect its discovered links and
add relevant sibling paths deliberately before expanding the scan. The City
of Zurich source has an explicit municipality; its procedures must not become
canton-wide claims. All 26 cantons being listed does not establish complete
cantonal or municipal coverage.

German is preferred when selecting one version of a page for a limited MVP run.
Federal topic seeds use verified
German URLs, including SEM, BAG, BAZG and ch.ch. First-pillar planning uses BSV's
German AHV overview. The bilingual Fribourg and Valais sources also use their
German entry points. French and Italian cantonal seeds remain where a German
equivalent has not been verified.

The catalogue retains SEM's German, French, Italian and English residence
overviews in the `multilingual`, `federal` and `all` sets. Every selected version
is kept, with German seeds scheduled first; an explicit English-only selection
stays English-only. The five-source `smoke` set deliberately chooses the German
SEM overview. Per-source budgets never remove other selected language versions.

`parallel_page_groups` records the four SEM entry points as one candidate group
with alignment status `NOT_EVALUATED`. This is a discovery relationship for later
comparison, not proof of equivalent content or synchronized revisions. Group
hints apply only to those entry pages, not every page crawled beneath them.
The catalogue is not an exhaustive inventory of every translation on every site;
later language discovery must report missing, excluded and unresolved variants.

Language hints support later discovery. URL patterns do not establish
parallel equivalence or availability of Romansh. The builder must later record
declared/detected languages and compare independently versioned parallel pages.
The five metadata projection targets are `en`, `de`, `fr`, `it` and `rm`.
Language identifiers carry no location; jurisdiction and reviewed dialect/idiom
coverage are separate metadata. Raw website tags are retained as provenance and
require reviewed mappings to enabled language-only source tags. These targets
remain planned; the language policy enables no evaluated routes.

## Concepts, multilingual metadata and answer evidence

The intended build separates these identities and language choices:

| Layer | Planned behavior |
| --- | --- |
| Canonical concept | One stable, language-neutral ID for a reviewed scoped concept, with reviewed multilingual labels and aliases. A page can discuss several concepts. |
| Source document and evidence | Separate document, snapshot, section and evidence identities for each version, retaining URL, source language, authority, jurisdiction, dates and byte hash. |
| Retrieval metadata | The same field schema and five target languages can apply to each eligible section. Values and provenance remain section-specific; shared terms or concept IDs do not prove equal claims. |
| Answer language | Chosen by the calling LLM independently of source language, with citations to the selected original evidence. |

The planned evidence-selection policy is recorded in the registry as
`PLANNED_NOT_IMPLEMENTED`. It first enforces explicit scope, applicability date,
jurisdiction and any `source_languages` filter, then ranks authoritative, current
evidence supporting the requested claim. German is a final tie-breaker only
between verified equivalent, equally suitable official versions. English terms
or an English answer do not implicitly filter evidence to English. An explicit
English-only source filter must be honored, including an insufficient-evidence or
coverage outcome when appropriate.

When equivalent translations of the same source revision support the same claim,
the future retriever should select a representative and retain alternate
references. They must not crowd the evidence limit or count as independent
corroboration. Different conditions, newer revisions or conflicts remain visible;
language preference cannot resolve them. Metadata projections help locate the
original evidence and cannot themselves support factual claims.

For example, reviewed German and English sections can share a concept ID and
English retrieval terms while retaining different evidence IDs and URLs. If both
support the claim equally, German can supply the citation even when the caller
writes an English answer. If only the English section supports it, the German
preference cannot displace that evidence. No cross-language concept alignment,
projection generation or answer-evidence selection runs during catalogue planning
or the current extraction CLI.

## Validate and inspect without downloading

Run from the repository root. The commands below use the Windows repository
Python; on Unix substitute `./.venv/bin/python`.

```shell
./.venv/Scripts/python.exe -m swisstip.builder.source_cli --dry-run
./.venv/Scripts/python.exe -m swisstip.builder.source_cli --set all --dry-run
./.venv/Scripts/python.exe scripts/catalogs/refresh_hackathon.py --check
```

Omitting `--dry-run` still produces an offline plan. Validation checks unique
source IDs/URLs, jurisdictions, source scope, selectors, planning references
and explicit numeric budgets. It performs no DNS, HTTP, source download or
model calls. Plans include selection/order policy, candidate parallel groups,
exclusions and aggregate crawler budgets. The `all` set retains all 59 catalogue
references, of which 53 are eligible for a test and six retain their access/adapter
exclusions. Crawling does not automatically switch languages after a failure.

Available scan sets are `smoke` (default), `multilingual`, `zurich`, `federal`,
`cantons` and `all`. Use repeatable `--source SOURCE_ID` instead of a set for precise selection.
The default `smoke` set selects SEM German, Zurich German, Vaud French, Ticino
Italian and Graubunden German.

A four-language SEM comparison plan is available without making requests. Its
default profile permits four HTML pages and 20 requests in total. Use explicit
source selectors to narrow that comparison:

```shell
./.venv/Scripts/python.exe -m swisstip.builder.source_cli --set multilingual --dry-run
./.venv/Scripts/python.exe -m swisstip.builder.source_cli --source ch-sem-residence-de --source ch-sem-residence-en --dry-run
```

| Profile | Depth | Pages per source | Requests per source | Bytes per source | Crawler time per source |
| --- | --- | --- | --- | --- | --- |
| `smoke` (default) | 0 | 1 | 5 | 3 MB | 60 seconds |
| `sample` | 1 | 5 | 10 | 10 MB | 120 seconds |

Both profiles cap individual responses at 2 MB, use a 2-second minimum delay
and honor stricter robots delays. Requests include robots and redirects.
Aggregate ceilings are the sum of per-source crawler budgets; inter-source
delays and local file I/O add wall-clock time. Runs are sequential. Broad sets
are deliberate opt-ins; the default five-source smoke run allows at most five
HTML pages and 25 HTTP requests.

## Run a test crawl later

Only `--crawl` together with `--output` makes requests and saves HTML. The output
directory must not already exist. Use a new run name for each experiment:

```shell
./.venv/Scripts/python.exe -m swisstip.builder.source_cli --crawl --output .local/crawls/residence-smoke-001
```

For one source and a slightly deeper scan:

```shell
./.venv/Scripts/python.exe -m swisstip.builder.source_cli --source zh-overview --profile sample --crawl --output .local/crawls/residence-zh-001
```

The runner uses `SafeCrawler` with its robots, redirect, scope, public-network
and traffic checks. It saves the exact accepted HTML response bytes from the
same requests, without a separate download. Non-HTML responses are not saved
as extraction inputs. `plan.json`, each source's `manifest.json`, and `scan.json`
record the source catalogue hash, source metadata, requested/final URLs,
retrieval times, content types, byte hashes, crawl outcomes and exclusions.
Entry-page snapshots also retain `candidate_parallel_page_group_id` when
configured. Identical bytes do not merge snapshots from different source entries;
fetched child pages receive no inherited parallel-page assertion.
An eligible source that yields no HTML or encounters failures produces an
`incomplete` result and a nonzero CLI exit. A saved page can still be a navigation
page or application shell; inspect content before inference.

## Extract concepts later

The existing extractor accepts the saved directories recursively and ignores
the JSON manifests. Select the model profile in `config/semantic-models.toml`
and follow the [provider setup](../../apps/knowledge-builder/README.md).
The checked-in profile's ten-page limit accommodates the five-page smoke run:

```shell
./.venv/Scripts/python.exe -m swisstip.builder.concept_cli .local/crawls/residence-smoke-001 --config config/semantic-models.toml --checkpoint-dir .local/checkpoints/residence-smoke-001 > .local/crawls/residence-smoke-001/concept-proposals.json
```

This later command may call a configured model. Larger scans must be split
into batches within the configured page/request budgets. Reports retain local
input paths: join them to snapshot `relative_path` entries to recover official
URLs and source provenance. Automatic manifest binding into normalized evidence
and release contracts is still a later build stage.

Extraction proposes evidence-backed candidate concepts. Its current batch groups
depend on language and extracted content; they are not stable public concept IDs
and do not automatically merge translations. Cross-language concept alignment,
cross-document topic clustering, human review, stable concept IDs, applicability,
operations and publication remain later stages. Review source-only annotations before model
proposals or planning groups. The historical
[POC-01 review](../../scripts/test/poc01/README.md) and zh.ch experiment remain
available independently of this catalogue.

## Maintain the catalogue

Edit `hackathon.sources.json`, including discovery references, reviewed URLs,
allowlists and scan status. When choosing a single version, prefer a verified
German URL and update its language hint and path allowlist together. Retain all
selected versions in multilingual sets. Use `parallel_page_groups` for candidate
translations with distinct language hints and matching authority/jurisdiction;
each seed can belong to one group, whose alignment remains `NOT_EVALUATED`.
The former `preferred_source_id` substitution field is rejected by validation.
Verify actual source links before changing translated URL
slugs. Edit the curated MVP plan in `hackathon.sources.md` directly; the refresh
helper preserves that text and only replaces the marked generated registry section.
Keep both registry markers intact. Then regenerate the registered seed index and reseal the
draft language policy/catalog and their source-reference hash:

```shell
./.venv/Scripts/python.exe scripts/catalogs/refresh_hackathon.py
./.venv/Scripts/python.exe scripts/catalogs/refresh_hackathon.py --check
```

The refresh helper needs the editable `packages/core` installation as well as
the builder and ingestion packages. Sealing records content identity; it never
approves sources, promotes concepts or publishes coverage. The former
Zurich-only draft catalogue has been replaced by these `hackathon.*` files.
