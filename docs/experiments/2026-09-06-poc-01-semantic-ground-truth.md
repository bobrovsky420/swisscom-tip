# POC-01: semantic reference labels and reviewer value

Experiment date: 2026-09-06. Status: 30 reference concepts frozen; assistant draft
comparison prepared; the user's second pass and controlled reviewer evaluation
remain pending. Current reviewer-value/model-selection decision: `INCONCLUSIVE`.

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

The reviewer workspace initially contained source-only views and blank annotation
rows, without model proposals or prefilled claims. It exposes normalized sections
for exact references and inert source HTML for checking normalization. The user
subsequently supplied questions, quotations, risks, uncertainty and actual time;
the assistant structured the authoring fields and documented scope corrections
and confirmation boundaries. These annotations are human-led, assistant-assisted
development references, not independently adjudicated gold. Normalized views do
not establish that every condition or logical relationship has been preserved.

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

## Frozen reference and draft comparison

The full-gold snapshot contains 30 concepts, five per source, with 101 reported
primary-review minutes and 41 validated evidence spans. It is preserved under
`.local/experiments/poc-01/review-freezes/20260906T133038-b99b9023/`.
Its `gold.csv` SHA-256 is
`80c3cc45359f0e9d47cfc6e3c0af4d2640c724b903d9f3dbf1040d15b7fea37a`.
The original ten-concept initial-batch snapshot is also preserved. Freezing checked
completeness of annotation fields and exact spans; it did not approve semantics.

The comparison lives outside the fixed packet inventory at
`.local/experiments/poc-01-comparisons/20260906-full-gold-01/`.
Its `input-manifest.json` SHA-256 is
`0551d26a19efb465bc4df99801a58640e07602dab5e44fc29a8238c1f56ad142`.
The manifest binds unchanged copies of the gold snapshot and both final reports,
plus a common proposal inventory that preserves every retained/rejected proposal:

| Historical run | Proposed | Retained | Rejected |
|---|---:|---:|---:|
| `8b-v3-02` | 59 | 47 | 12 |
| `70b-v3-05` | 57 | 55 | 2 |

There are 60 assistant draft alignments, one per gold concept and run. The
inventory includes 305 example questions: 183 have assistant draft assessments
against linked concepts and 122 remain unassessed. Every human second-review
decision and timing cell is blank. These counts are preparation bookkeeping, not
accuracy, reviewer agreement or an independently measured recall result.

The retained-output representation counts are:

| Draft representation against 30 reference concepts | 8B | 70B |
|---|---:|---:|
| Full claim content represented in retained output | 7 | 9 |
| Partially represented in retained output | 12 | 12 |
| No retained representation | 11 | 9 |

The 8B gaps include four concepts found only in rejected proposals and seven with
no identified proposal; the nine 70B gaps have no identified proposal. Searching
the whole selected run distinguishes representation elsewhere from absence.
Internal all-linked content counts also include rejected proposals: their nine
complete 8B matches must not be reported as nine retained complete matches.
Full content representation can coexist with citation, scope or example-question
problems. No retained proposal is promoted by these draft classifications.

The principal draft findings are:

- Missing material conditions in close-relative, family-reunification and
  medical-treatment concepts, including separate procedure branches.
- Changes to population, logical prerequisites and time windows; a quota or
  card/registration exemption is sometimes described as permit-free employment.
- Missing municipal-registration obligations and the construction-sector
  exception. Both runs also omit the selected skilled-worker restriction.
- Three contact concepts are excluded before model extraction. This is a
  mismatch between reviewed coverage expectations and historical filtering.
  The historical runs had no frozen policy declaring these later reference
  contacts required; this does not establish that the models failed to read
  content they were never given or violated such a historical coverage policy.
- Infobox headings split continued condition lists, and a general procedure
  inherits a misleading heading. Normalized text presence alone does not prove
  preserved logical applicability. Blanket primary-section evidence restrictions
  also reject relevant multi-section content without establishing its invalidity.
- Some example questions ask for an individual outcome, proof requirements or
  details beyond the candidate's saved evidence. Source ambiguities, including an
  unassigned exact-age boundary, remain unresolved in the reference notes.

These observations motivate [Product Specification V20](../product/product-functional-specification.md)
and [Technical Specification V11](../architecture/technical-specification.md):
separate claim/question assessments, logical source blocks and bounded supporting
evidence, versioned content policy and gap accounting, and finite semantic
acceptance fixtures. [BUILD-02 and POC-01/03/05](../../TODO.md) track implementation
and validation. Updating the requirements does not implement the controls or
qualify the existing extractor for automatic promotion.

Next, complete the user's same-person second pass and preserve any corrections
in new snapshots. Confirm failures before using them as regression truth; retain
correct controls and independently label unseen natural cases for later quality
claims. Controlled reviewer arms, valid-content-loss/cost criteria, provider
configuration and whole-run budgets must be fixed before fresh reviewer runs.
The 101 minutes measure primary reference work, not total engineering effort or
minutes per usable published concept. No model-size winner is established.

## Artifact verification

The comparison's `verification.json` records checked input/output hashes, local
links, 60 comparison rows, 30 empty second-review rows, 116 proposals and 305
questions. The offline browser view was rendered and its initial one-concept
selection verified. The original packet still passes preservation verification
for all six sources and 87 historical files; gold and source snapshots are unchanged.
No new configured extraction/reviewer inference calls or live source fetches were
run for this comparison. Assistant draft analysis is recorded as such.

Recheck packet preservation with the repository environment:

```shell
./.venv/bin/python scripts/test/poc01/prepare_packet.py verify
```

On Windows, substitute `./.venv/Scripts/python.exe`. Internal comparison inputs,
worksheets and generation instructions remain in the ignored directory; source
text and individual annotations are not copied into this tracked report.

## Implementation verification

The preparation implementation recorded 68 passing core tests, 63 ingestion
tests and 96 builder tests including 13 POC-01 preparation tests and the PowerShell
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
At that initial preparation point there were zero completed human labels. The
subsequent frozen reference and draft-comparison progress is recorded above;
the original preparation metadata remains unchanged.
