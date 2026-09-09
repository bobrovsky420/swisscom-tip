# Structured knowledge runtime

BUILD-03 implements `KnowledgeService.get_coverage`, `resolve` and `get_evidence`
over explicitly loaded serving releases. The runtime depends only on core;
the [MCP application](../../apps/mcp-server/README.md) supplies the stdio adapter.
It does not call ingestion or extraction. BUILD-05 adds optional runtime embedding
and ranking providers, selected through the loaded release configuration.

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

## Hybrid retrieval (BUILD-05)

Hybrid bundles additionally load sealed `RetrievalProjection`, `ReviewedTerminology`,
`EvidenceEquivalence`, `RetrievalIndex`, `RetrievalProviders` and
`RetrievalConfiguration` artifacts. The manifest pins all assets: ranking configuration
binds equivalence mappings and coverage evaluations; the index binds the embedding
model and projection revisions. A missing projection, stale evidence reference,
wrong vector dimension, undeclared fallback profile or incomplete asset set fails
loading. Hybrid profiles require complete `en`, `de`, `fr`, `it` and `rm` projections.
Generating and reviewing those assets remains a builder responsibility.

Each term independently selects its published projection and reviewed terminology.
Original/expanded lexical matches, concept associations (including applicable
published fact support), and cosine similarity of multilingual vectors contribute
through reciprocal rank fusion. Zero-score lexical/vector entries do not suppress
other channels. Pools contain at most the configured 20-100 evidence groups;
the default is 20. A semantic provider ranks the admitted originals and routed
projections. Providers see only eligible evidence and cannot add IDs or facts.
Provider/model identities, dimensions, finite scores and complete candidate
membership must match. The final assembler selects complete published support
within the existing five-object cap, then fills spare slots with ranked excerpts
meeting the release's optional `minimum_semantic_score`. Fallback profiles can
separately pin `minimum_lexical_score`. These thresholds govern optional excerpts;
they cannot remove a published fact's required support or create support from a
score. Thresholds default to unset and require profile-specific evaluation.

Exact revision-bound equivalence mappings are required for grouping. Scope,
temporal coverage, authority and per-fact support must be compatible. Conflicting
facts and joint supporting spans cannot be collapsed. Fresh equivalents precede
stale equivalents, then semantic suitability precedes a German language tie-breaker
and stable evidence identity. Materially different versions stay separate.
Original facts retain their hashes and evidence IDs; trace `selections` provides
the per-fact representative/alternate mapping. Only the representative consumes
a slot. Alternate IDs remain available through `get_evidence`; references to
filtered languages are metadata and are not returned as selected evidence.

`KnowledgeService` accepts `embedding_provider` and `ranking_provider` implementations
of the protocols in [retrieval.py](src/swisstip/runtime/retrieval.py). Each adapter
declares `provider_id`; the release pins that ID and requested model. The optional
[Ollama adapter](src/swisstip/runtime/providers.py) implements the documented
[embedding](https://docs.ollama.com/api/embed) and [chat](https://docs.ollama.com/api/chat)
APIs. Its identity is `ollama-retrieval/v1`, including a fixed scoring instruction
and generation options. It limits request/response bytes, uses bounded HTTP I/O,
and performs one attempt per stage, with no redirects or retries. Applications
must supply endpoints explicitly; no model is downloaded or called on startup.

The `groq-ranking/v1` adapter scores evidence through Groq's chat API using
[strict structured outputs](https://console.groq.com/docs/structured-outputs),
the same fixed relevance instruction, temperature zero and low reasoning effort.
It shares the bounded transport and validates complete responses before the
retriever checks model identity and exact score membership.

Model identities and provider connections are shared with extraction in
[config/model-profiles.toml](../../config/model-profiles.toml). Named retrieval profiles live in
[config/retrieval-models.toml](../../config/retrieval-models.toml). As in the
semantic-model configuration, each role selects a `[profiles.<name>]` table:

```toml
schema_version = "swisstip.retrieval-model-profiles/v1"
model_profiles_file = "model-profiles.toml"

[embedding]
active_profile = "qwen_embedding_0_6b"

[ranking]
active_profile = "apertus_ranking_8b"
```

Change only the corresponding `active_profile` to select another defined model.
The included choices cover local embeddings, hosted ranking and fully local
ranking; they are independent, so any embedding profile can pair with any ranking
profile. Model alternatives are configuration options, not live qualifications.

| Profile | Role | Model |
| --- | --- | --- |
| `qwen_embedding_0_6b` (default) | Embedding | `qwen3-embedding:0.6b` |
| `qwen_embedding_4b` | Embedding | `qwen3-embedding:4b` |
| `qwen_embedding_8b` | Embedding | `qwen3-embedding:8b` |
| `apertus_ranking_8b` (default) | Ranking | `MichelRosselli/apertus:8b-instruct-2509-q4_k_m` |
| `groq_gpt_oss_20b` | Ranking | `openai/gpt-oss-20b` |
| `groq_gpt_oss_120b` | Ranking | `openai/gpt-oss-120b` |
| `qwen_ranking_9b` | Ranking | `qwen3.5:9b` |
| `deepseek_v4_pro` | Ranking | `deepseek-v4-pro` |

Each profile declares `model_profile`, `role`, `timeout_seconds` and any scoring
contract. `model_profile` refers to the shared catalog, which owns `adapter`,
`model`, `base_url` and, for hosted adapters, `token_env`. Legacy inline definitions still
load. See the [shared configuration guide](../../config/README.md) for examples
and relative path rules. Add more profiles using the supported adapters;
Ollama supports embedding and ranking roles, while Groq supports ranking with
the two GPT-OSS models accepted by this adapter. DeepSeek supports V4 Pro ranking.
Unknown names, role mismatches,
unsupported adapters and invalid settings (including inactive profiles) fail
configuration loading. Profile names are deployment labels, not release model IDs.
There is no automatic switch to another profile on failure.

The default selections resolve to:

| Role | Service | Model | Release adapter ID |
| --- | --- | --- | --- |
| Embedding | Local Ollama | `qwen3-embedding:0.6b` | `ollama-retrieval/v1` |
| Evidence ranking | Local Ollama | `MichelRosselli/apertus:8b-instruct-2509-q4_k_m` | `ollama-retrieval/v1` |

The default pair uses local Ollama without provider credentials. Install/start
Ollama and pull `qwen3-embedding:0.6b` and
`MichelRosselli/apertus:8b-instruct-2509-q4_k_m`. The Apertus model is the same
unofficial community package available in the builder's local profile. Ollama
serves embeddings at `http://127.0.0.1:11434/api/embed` and ranking at `/api/chat`.

For a Groq ranking profile, set `GROQ_API_KEY` in the environment inherited by the
MCP server or evaluation process. The config stores only the environment variable
name; it does not load `.env` files. Groq ranking uses
`https://api.groq.com/openai/v1/chat/completions`.

For DeepSeek V4 Pro ranking, set `DEEPSEEK_API_KEY` and select `deepseek_v4_pro`.
The direct API uses JSON-object output with thinking disabled; the adapter checks
completion/model identity, duplicate keys, exact candidate IDs and finite scores.
It uses the existing relevance instruction and a distinct `deepseek-ranking/v1`
release adapter identity. See [DeepSeek setup](../../config/README.md#deepseek-v4-pro).
Adding this profile does not change the active defaults or qualify model quality.

Both CLI applications accept `--provider-config config/retrieval-models.toml`.
Do not combine it with legacy provider URL/timeout flags. Configured models are
allowlists checked against the models requested by the sealed release; editing
this TOML cannot replace its pinned models, adapter IDs or stored vectors. Build
and evaluate a new matching release/index before using these models for hybrid
retrieval. The BUILD-03 fixture remains lexical and makes no provider calls.

OpenCode's independent caller uses `opencode/ling-3.0-flash-fin-free`, the
[Ling 3.0 Flash Fin Free model](https://dev.opencode.ai/docs/zen/).
The local `.local/opencode.json` pins it, supplies the retrieval config path to
the MCP process and gives MCP calls a 120-second timeout. Restart OpenCode using
that config after setting the environment. Builder extraction profiles remain
in `config/semantic-models.toml`.

Provider errors restart only a release-declared, evaluated lexical/concept fallback
for the selected coverage profile. Trace metadata identifies omitted channels and
the fallback evaluation. Without that path, `resolve` returns `OPERATIONAL_ERROR`.
A failed provider never becomes a knowledge-coverage claim. Legacy BUILD-03 bundles
with no retrieval assets retain their explicitly labelled identifier/lexical baseline.

Generate the synthetic multilingual bundle or reproduce its integration gates:

```shell
./.venv/Scripts/python.exe -m swisstip.runtime.hybrid_fixture --output .local/build05/fixture.json
./.venv/Scripts/python.exe -m swisstip.runtime.evaluation --synthetic --output .local/build05/evaluation.json
```

For an in-process hybrid demo, call `hybrid_fixture()` and inject
`SyntheticSemanticProvider()` for both providers. Its `synthetic/v1` adapter and
two-dimensional vectors are fabricated and cannot qualify a real provider. Without
those adapters the demo uses its declared synthetic fallback, including over MCP.
Do not point this fixture at live models; an actual model needs a newly built index,
pinned configuration and evaluation for its profile.

The evaluation CLI also accepts `--release`, `--cases`, `--output`, and optional
`--provider-config` (or legacy Ollama `--embedding-url` and `--ranking-url`).
Cases use `RetrievalGoldCase` in
[evaluation.py](src/swisstip/runtime/evaluation.py): exact release identity, typed
request, required evidence groups/facts, eligible/relevant IDs and a declared
minimum precision. Every case must pass top-20 recall, top-5 fact/evidence support,
original citation round-trips, zero leakage and the specified relevance threshold.
An empty suite fails. Reports retain label hashes, release refs, channels, recall,
precision, latency and response size; a failing suite exits nonzero.

The [evaluation record](../../docs/experiments/2026-09-07-build05-retrieval.md)
states the synthetic gates and limits. Production multilingual fidelity and live
model qualification remain POC-06/07/10/11; reviewed publication and retention
remain BUILD-02/04/06. Loading fabricated review/evaluation references does not
attest their authenticity or promote the draft residence catalogue.
