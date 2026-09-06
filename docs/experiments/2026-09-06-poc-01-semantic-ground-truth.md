# POC-01: semantic reference labels and reviewer value

Preparation date: 2026-09-06. Status: review preparation implemented; human labels and
reviewer comparisons have not been completed. No quality decision is claimed.

## Scope and review arrangement

Use the six frozen German zh.ch residence pages from the
[2026-09-05 experiment](2026-09-05-zhch-concept-extraction.md). The first BUILD-01
authoring scope is `swiss-public` / `immigration` / `residence`, Canton Zurich,
with `requirements` as the proposed first operation. These identifiers and this
operation do not establish reviewed source coverage.

The user volunteered to perform both review passes. Record the primary reviewer
as `user`; the second pass is a re-review by the same person. This is useful for
correction and curated authoring, but cannot measure independent reviewer
agreement. Independent adjudication of high-impact/disputed claims remains an
unmet evaluation criterion. No further reviewer is assumed or represented as
having approved content.

This historical corpus is a development fixture. Its outputs and known failures
have already been inspected and discussed. New source-first labels improve this
fixture; they do not turn it into an untouched holdout. Reserve independently
labelled, unseen natural examples before making a fresh generalization claim.

## Reproducible preparation

The [preparation script and instructions](../../scripts/test/poc01/README.md)
preserve the original source fixture, model artifacts and failed-run history
under `.local/experiments/poc-01/`. This ignored internal workspace keeps source
material and model responses out of version control. The original temporary
artifacts remain unchanged.

The preservation manifest identifies each archived file by a relative path,
byte count and SHA-256, and binds the source URLs to the verified raw pages.
Preparation records code/configuration and protocol identities. Historical
requested model identities and unverifiable observed identities remain as
recorded; they are not repaired by copying or hashing the old artifacts.

The separate reviewer workspace contains source-only views and blank annotation
rows. It exposes normalized sections for exact references and inert source HTML
for inspecting anything normalization might have omitted. It contains no model
proposals or assistant-authored gold claims. Normalized views are conveniences,
not a claim that normalization preserves every condition.

No live source fetch, inference call or provider comparison is part of packet
preparation. The current provider configuration is preserved as build context;
it is not attributed retroactively to the historical runs.

## Review sequence

1. Read the frozen sources and record expected concepts without inspecting the
   archived proposal reports. Begin with 10-15 high-impact concepts across the
   fixture, then extend to 5-10 expected concepts per page. Record necessary
   conditions, exceptions, evidence references, proposed operation/context and
   actual review time. Do not infer legal facts from illustrative contract tests.
2. Freeze the completed source labels before revealing model proposals. A freeze
   records the annotations and their hashes; it is not approval or publication.
3. Compare the fixed proposal set to those labels. Distinguish never proposed,
   rejected, represented elsewhere and truly missing. Record support, scope,
   completeness and validity of each proposed example question separately.
4. Perform the user's second pass, retaining changes and elapsed review time.
   Label this a same-person re-review. Keep unresolved material errors outside
   the accepted catalog subset.
5. Before running fresh reviewer comparisons, select the independent model-review
   configuration and set whole-run time/monetary limits. Freeze these choices and
   the common proposal set. Do not regenerate proposals for each reviewer arm.
6. Compare structural validation, same-model review, an independent configured
   model reviewer and structured condition/exception checking. Evaluate controlled
   mutations separately from held-out natural examples.

## Measurements and decision gates

Preserve the POC-01 gates in [TODO.md](../../TODO.md): every known critical mutation
must be caught and no unresolved material error may be promoted in the reviewed
acceptance set. Report raw numerators and denominators for material false
acceptance, valid-proposal false rejection and expected-concept recall, alongside
review minutes per usable concept. Same-person agreement cannot stand in for
independent reviewer disagreement.

Include missing conditions, changed population, permit/quota distinctions,
altered dates/numbers, misleading labels and unanswerable proposed questions in
the controlled comparison after source labels are frozen. Correct proposals are
required controls; a reviewer that rejects everything does not demonstrate value.
Freeze acceptable loss/cost criteria before comparing reviewers. The experiment
timebox is 0.5-1 focused engineer-day plus actual reviewer availability; it is not
a promise that all comparisons or the full P0 implementation fit that timebox.

The eventual decision is `CONFIRMED_FOR_TESTED_SLICE`, `REJECTED` or
`INCONCLUSIVE`. Until the measurements exist, POC-01 remains unchecked. The
reviewed 5-10-concept seed subset also remains pending; draft identifiers and
passing contract tests do not establish semantic approval.

## Implementation verification

The core contract suite passes 68 tests, ingestion passes 63 tests, and the builder
suite passes 96 tests including 13 POC-01 preparation tests and the PowerShell
workflow against loopback fake Ollama. The generated contract schema bundle also
matches its exporter. These are software checks, not semantic-quality results.

The broader run exposed tests that selected the operator's active model profile
while returning hard-coded HF 8B fake completions. Three test fixtures now select
that profile in temporary configuration copies; the operator's Ollama selection
and production identity validation remain unchanged.

The completed preparation preserved 87 historical files, including all six raw
source pages, and created 60 blank source-label rows. Preservation verification
passed. The active packet is `.local/experiments/poc-01/`; its manifest SHA-256 is
`7d6eca1a670a95a2fad963af32188bc0cf85fbc9ba46e091e09ef4bbe4964250`.
The input metadata includes the pre-result version of this report. The first
generated packet is retained separately as `poc-01-preparation-001` after the
source views were improved for readability; no human annotations were replaced.
There are zero completed human labels and zero new model-comparison calls.
