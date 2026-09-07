# BUILD-05 scoped hybrid retrieval integration

Date: 2026-09-07. This implements the runtime integration boundary over synthetic
serving releases. It does not complete POC-07's independently labelled Swiss
corpus experiment, certify projection fidelity or qualify a live semantic model.

Verification: 71 core, 83 ingestion, 135 builder, 54 runtime and three MCP tests
pass (346 total). The exported schema freshness and Git whitespace checks pass.

## Delivered behavior

- Sealed, release-pinned projections, reviewed terminology, vector index,
  provider/ranking configuration, evaluated fallback references and exact
  evidence-revision equivalence mappings.
- Independent term routes across five projection languages, scoped original and
  expanded lexical retrieval, concept associations, cosine vector retrieval,
  reciprocal rank fusion and semantic reranking.
- Scope, source filters, jurisdiction, dates and published applicability rules
  before providers, with exact membership validation before accepting outputs.
- Equivalent evidence occupies one slot and retains alternate references.
  Published fact hashes stay unchanged. Freshness and ranking precede German
  preference; partial translations, revision differences and conflicts cannot
  be hidden by grouping.
- Release-declared lexical/concept fallback with explicit omitted channels, or
  typed operational errors. Opt-in bounded Ollama adapters and MCP endpoint flags.
- A reusable release-bound gold-case evaluator with nonzero exit on failed gates.

## Controlled fixtures and gates

The fixture contains one synthetic supported requirement in five purported
equivalent language versions, parent/child/sibling concepts, a conditional work
rule and 30 in-scope distractors. Labels, terminology review, equivalence review,
model outputs and evaluation references are fabricated test inputs.

The term/source matrix uses six term profiles (`en`, `de`, `fr`, `it`, `rm`, `gsw`)
against five explicitly selected original-source languages. All 30 cases run in
three modes: hybrid, unavailable embedding provider, and failed ranking provider.
All 90 cases pass required-document recall at 20, required-fact/evidence support
at 5, precision of 1.0, original citation round-trips and zero scoped leakage. Fallback cases execute
only lexical/concept channels and name the declared fallback evaluation.

The fixture declares minimum precision 1.0, semantic score threshold 0.5 and
fallback lexical threshold 1.0 for optional excerpts. Its synthetic ranker assigns
1.0 to relevant evidence and 0.0 to distractors. These calibrated fixture thresholds
avoid filling spare slots with irrelevant evidence. A regression disables the
semantic threshold and requires the resulting precision gate to fail. Real profiles
need independently chosen thresholds and measured model behavior before qualification.

A separate ablation-style regression puts a zero-lexical-match target below 30
distractors with no published fact shortcut. The vector channel recovers it in
the top 20 and the semantic ranker selects it; the lexical/concept fallback misses
it. It remains excerpt-only and cannot create a supported fact. This demonstrates
independent channel contribution, not a model-quality gain on real data.

Additional regressions cover mixed terms, reviewed German aliases, optional terms,
exact/descendant scope, inactive rules, missing context, explicit English-only
filters, better non-German evidence, stale German evidence, unavailable German,
partial translations, incompatible dates, conflict visibility under a one-object
cap, malformed vectors/scores, invented candidate IDs, provider/model mismatch,
incomplete or tampered artifacts and actual MCP stdio alternate lookup. Loopback
HTTP tests verify the adapter protocol, non-streaming structured scoring, byte
limits, incomplete output, duplicate JSON fields and absence of retries/redirects.

## Reproduction and limits

From the repository root on Windows:

```shell
./.venv/Scripts/python.exe -m unittest discover -s packages/core/tests -v
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -v
./.venv/Scripts/python.exe -m unittest discover -s apps/mcp-server/tests -v
./.venv/Scripts/python.exe -m swisstip.core.schemas --output packages/core/schemas --check
./.venv/Scripts/python.exe -m swisstip.runtime.evaluation --synthetic --output .local/build05/evaluation.json
```

Use `./.venv/bin/python` on Unix. The report preserves case-label hashes, release
identities, per-case metrics, actual channels, response bytes and measured local
latency. Synthetic timings are not inference latency or an operational SLA.

No live source, embedding or ranking calls were made. The built-in Ollama adapter
is protocol-tested only. Apertus or another provider can implement the same
provider protocols, but switching provider IDs/models requires a new evaluated
release and matching index. BUILD-02/04 still own reviewed production evidence,
alignment and projections; BUILD-06 owns governed publication and qualification.
