# SwissTIP core contracts

BUILD-01 defines the versioned data contracts and validates structured requests
against an explicit catalog. It does not fetch sources, publish releases, retrieve
evidence or run an MCP server.

Install from the repository root:

```shell
./.venv/Scripts/python.exe -m pip install -e packages/core
./.venv/Scripts/python.exe -m unittest discover -s packages/core/tests -v
```

On Unix use `./.venv/bin/python` for the same commands. Python 3.11 or newer is
required. Pydantic 2 supplies strict boundary validation and JSON Schema export.

Export or verify the checked-in bundle:

```shell
./.venv/Scripts/python.exe -m swisstip.core.schemas --output packages/core/schemas
./.venv/Scripts/python.exe -m swisstip.core.schemas --output packages/core/schemas --check
```

The [schema bundle](schemas/contracts-v1.schema.json) shares definitions and maps
each root contract through `x-contracts`. It describes structural validation;
the Python models also enforce canonicalization and cross-field invariants, and
`swisstip.core.validation` enforces catalog-dependent boundaries. JSON Schema
validation alone does not establish catalog integrity or accepted coverage.

The `hackathon` authoring scope is residence in Switzerland, with federal sources,
all 26 cantonal entry points and deeper Zurich sources. The proposed seed catalog
contains only the space/domain/topic scaffold and no preselected concepts. Candidate entries and
proposed operations do not establish supported coverage. Human review must supply
the source-backed concepts, conditions, exceptions and evidence before curated
coverage can be declared.

The [seed files](../../config/catalogs/README.md) can be loaded without network
or model access:

```python
from pathlib import Path
from swisstip.core import KnowledgeCatalog, LanguagePolicy
from swisstip.core.validation import validate_catalog, validate_request

catalog = KnowledgeCatalog.model_validate_json(
    Path("config/catalogs/hackathon.seed.json").read_bytes()
)
policy = LanguagePolicy.model_validate_json(
    Path("config/catalogs/hackathon.language-policy.json").read_bytes()
)
assert not validate_catalog(catalog, policy)
# assessment = validate_request(request_dict, catalog, policy)
```

`validate_catalog` checks hashes, hierarchy, referenced inline schemas and policy
closure. Its optional `artifacts` registry checks exact external references;
existence and semantic verification of external source/rule/evidence content
remain build responsibilities. `validate_request` returns a `ValidationAssessment`
with typed issues, missing-context fields and bounded scope. `READY` is an
internal validation outcome for later execution, never a public factual result.
Invalid stored catalog data raises `CatalogIntegrityError` rather than becoming
a client coverage claim.

For contract artifacts, `swisstip.core.identity.seal_artifact` hashes canonical
JSON after model validation, including defaults. It excludes only the root self
hash and embedded catalog self-reference hashes. Other dependency hashes remain
bound. Raw source snapshot hashes continue to refer to original bytes. Sealing
neither approves content nor publishes a release.

The source-only review workflow is documented in
[POC-01 preparation](../../scripts/test/poc01/README.md). Original source pages,
model responses and human annotations stay in the ignored `.local/` workspace.

The public request is `structured-grounding/v1`. Its required envelope includes
the pinned release, Knowledge Space, domain, topic, finite intent, canonical
jurisdiction, typed context, applicability date and scope mode. Concept selectors
are required only by profiles that declare them necessary. The optional tagged
retrieval terms never fill in missing context or change explicit scope.

Request-shape errors, unknown fields/IDs and inconsistent selectors produce
`INVALID_ARGUMENT`. Missing conditional facts inside a valid context produce
`NEEDS_CONTEXT`. Known but unsupported combinations produce `OUT_OF_COVERAGE`.
An unavailable requested release produces `RELEASE_UNAVAILABLE`; validation never
substitutes the active release. A request ready for later processing does not by
itself have sufficient verified evidence or a `SUPPORTED` factual outcome.

Context schemas intentionally use a closed subset of scalar types, enums, bounds,
conditional requirements and consistency rules. They are not arbitrary executable
rules or unrestricted JSON Schema. The schema and validator reject unsupported
constructs. BUILD-03 adds closed published-rule, resolution-graph and normalized
document/section contracts. The [runtime](../runtime/README.md) binds them to
loaded releases and performs structured resolution; reviewed promotion remains
BUILD-02 work.

The `tip-language-catalog/v3` roles use `en`, `de`, `fr`, `it` and `rm` for
sources and projections, plus `gsw` for evaluated Swiss German term routes to
`de`. Jurisdiction, dialect and idiom coverage are declared separately. Raw
website/detector tags remain in provenance; the BCP 47 syntax parser preserves
their subtags. Public regional language profiles are unsupported. Existing v2
policies require migration and resealing before use with these validators.

All five metadata projection languages remain P0. This package defines language
and coverage boundaries; it does not establish source-language validation,
translation fidelity, multilingual retrieval or evaluated term routes.

Reviewed concept alignment may give official translations shared canonical
concept IDs and multilingual terms. Their document, snapshot and evidence
identities remain separate. The runtime applies scope, applicability,
authority, freshness and claim support before using German as a tie-breaker
between verified equivalent versions. Explicit source-language filters take
precedence; the caller chooses the answer language. BUILD-05 adds hash-bearing
retrieval projection, terminology, vector index, provider/ranking configuration
and revision-bound evidence-equivalence contracts. The runtime validates their
loaded dependency graph and performs grouping; authoring reviewed alignments and
evaluating actual projection fidelity remain BUILD-04 work.

When a selected equivalent represents a fact's original evidence, the returned
fact retains its immutable identity and original evidence IDs. The retrieval trace
names the mapping reference, representative, alternate IDs and supported fact IDs.
The result validator requires either direct evidence or that explicit per-fact
representation. Alternate IDs can be inspected with `get_evidence` in the same release.
