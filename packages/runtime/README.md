# Structured knowledge runtime

BUILD-03 implements `KnowledgeService.get_coverage`, `resolve` and `get_evidence`
over explicitly loaded serving releases. The runtime depends only on core;
the [MCP application](../../apps/mcp-server/README.md) supplies the stdio adapter.
It never calls ingestion, extraction or a model provider.

Install and test from the repository root, using the local environment:

```shell
./.venv/Scripts/python.exe -m pip install -e packages/core -e packages/runtime
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -v
```

On Unix substitute `./.venv/bin/python`.

## Synthetic fixture

The fixture has fabricated English facts, a conditional work rule, parent/child
and sibling concepts, and invented evaluation references. It makes no claim about
Swiss legal coverage or real review. It does not consume or approve experimental
extractor candidates or the draft residence catalog.

```shell
./.venv/Scripts/python.exe -m swisstip.runtime.fixture --output .local/build03/fixture.json
```

```python
from pathlib import Path
from swisstip.runtime import KnowledgeService, ReleaseStore

store = ReleaseStore.from_files(
    [Path(".local/build03/fixture.json")], active_release_id="fixture-release-a"
)
service = KnowledgeService(store)
root = service.get_coverage({})
detail = service.get_coverage({
    "release_id": root.release_id, "parent_id": "fixture-topic", "limit": 1,
})
result = service.resolve({
    "schema_version": "structured-grounding/v1",
    "release_id": root.release_id,
    "knowledge_space_id": "fixture-space", "domain_id": "fixture-domain",
    "topic_id": "fixture-topic", "concept_ids": ["fixture-parent"],
    "intent": "requirements", "jurisdiction": {"country_code": "CH", "canton_code": "CH-ZH"},
    "context": {"population": "group-a", "purpose": "study"},
    "as_of": "2026-09-06", "scope_mode": "exact",
})
evidence = service.get_evidence({
    "release_id": result.release_id,
    "evidence_ids": [item.evidence_id for item in result.evidence],
})
```

Freshness uses the current UTC read time, independently of `as_of`. The fixture's
source timestamp is fixed at 2026-09-06; it becomes `STALE` after 30 days. Tests
inject a fixed clock. Source text and citations never change to hide aging.

## Serving release boundary

`ReleaseBundle` (`serving-release/v1`) contains a `KnowledgeRelease`, catalog,
language policy, resolution graph, normalized documents/sections, evidence,
published facts/rules and an external dependency reference registry. The graph
identity occupies the manifest's `concept_graph_ref`. Each approved coverage
profile has exactly one resolution plan; its required portions bind concepts to
unconditional fact IDs, conditional rule references and explicitly eligible
excerpt IDs. All these artifacts are covered by the existing manifest hashes.

Loading checks canonical hashes, exact references, approved profile/policy state,
selectable catalog entries, plan/profile relationships, declared rule fields and
values, complete fact/evidence references, and snapshot/document/source/section
chains. Original excerpts must match codepoint offsets in the retained normalized
text. Draft profiles and experimental bundles are rejected. Model instances and
returned results are copied across the store boundary; an ID cannot be replaced.

The external registry declares build-owned raw snapshots, evaluations, review,
configuration and other dependencies. The reader checks their exact identities;
it does not verify external bytes, attest reviewer authenticity or implement
reviewed promotion. Those remain BUILD-02/06 responsibilities. Loading a locally
authored bundle is not production publication. A failed store construction leaves
an already running service intact; the stdio process loads its configured files
once, before accepting requests.

## Resolution behavior

- Discovery returns available spaces, space roots or a selected parent's immediate
  children in ID order. Topic/concept records carry applicable profiles and full
  context schemas inline. Catalog limits control page size. HMAC cursors bind the
  release hash, selectors, page size and position. Child and continuation requests
  must pin the release. The default signing key lasts for one service instance;
  embedders can provide a persistent secret of at least 32 bytes across restarts.
- Requests reuse the core strict validator. Unknown fields/IDs and inconsistent
  selectors are errors; missing conditional facts return `NEEDS_CONTEXT` with
  schema/rule/evidence references. No term supplies context. Unavailable release
  IDs return `RELEASE_UNAVAILABLE` with active discovery information, without
  substitution. Retained releases remain independently readable.
- Exact concepts exclude children and siblings. Exact topic operations select
  directly attached profile concepts. Descendant selection uses the profile's
  depth/count limits. No candidate channel widens these boundaries.
- Rules use all-of scalar predicates to select pre-authored facts. Missing rule
  inputs also return machine-readable context requirements. Rules execute no code
  and generate no text. A failed predicate produces no rule output. Facts that
  depend on rules cannot be listed as unconditional support. Applicability prose
  is descriptive; authors must encode executable conditions in the context schema
  and rules before publication.
- Candidates come only from the operation's declared excerpts and applicable
  fact evidence. Source IDs/languages, date and concepts are hard constraints.
  Jurisdictions match exactly; a declared rule output may cite federal evidence
  for its profile's jurisdiction while preserving federal metadata. Ordinary
  lexical relevance cannot admit federal or another canton's material.
- The deterministic baseline counts shared case-folded word tokens in original
  excerpts and tagged terms; fact ID/evidence ID breaks ties. Complete fact support
  is selected within the evidence cap before spare excerpt slots are filled.
  Every required portion must have all applicable published facts represented for
  `SUPPORTED`. Missing support produces partial/insufficient outcomes; excerpts
  alone never establish `SUPPORTED`. Declared applicable conflicts are reported
  even if the evidence cap hides one side. Staleness prevents `SUPPORTED`.
- Results return original excerpts, exact citations, pre-authored facts, missing
  context, unresolved portions, freshness, trust and actual retrieval channels.
  `get_evidence` preserves request order and rejects unknown references atomically.

This is the BUILD-03 identifier/lexical contract baseline. Five-language projection
generation, verified translation equivalence, hybrid vector retrieval, semantic
ranking and evaluated provider fallback remain BUILD-04/05. Production publication,
durable retention and qualification with independent external clients remain
BUILD-06. The synthetic fixture does not complete those gates.
