# V4 extraction comparison: Apertus 70B, GPT-OSS 120B and DeepSeek V4 Pro

For the subsequent nine-run comparison using the updated review prompt and
nesting correction, see the [comparison rerun](2026-09-09-v4-model-comparison-rerun.md).
The historical measurements below remain unchanged.

DeepSeek V4 Pro produced the most reliable extraction/review result on the saved
English SEM Residence page: all three runs retained a source-complete candidate.
GPT-OSS and Apertus retained no candidates in their three respective runs.
This is evidence for this page and these provider configurations, not a general
model ranking. Existing model selections and the paused GUI training workflow
were not changed.

## Reproduction and experiment design

Run [the local comparison script](../../scripts/test/model_comparison/README.md)
from the repository root:

```shell
./.venv/Scripts/python.exe scripts/test/model_comparison/run.py --repeats 3
```

It uses current process credentials, then `.env.dev` for missing `HF_TOKEN`,
`GROQ_API_KEY` and `DEEPSEEK_API_KEY`. Keys and authorization headers are not
included in artifacts. The default input is the previously saved GUI page;
`--input` selects another saved HTML page. No new crawl or publication occurs.

Each model used `concept_extraction_v4` for extraction and model-assisted review,
temperature 0, a nominal 4096-token output ceiling, a 180-second request timeout,
one repair revision and zero provider retries. The source requires at most four
model requests per run: extraction, review, repair, final review. An invalid
extraction skips its review. Three runs were attempted per model with local
checkpoint reuse disabled. Each model reviewed its own extraction.

| Model profile | Connection | Output contract |
| --- | --- | --- |
| `apertus_70b` | HF router, PublicAI, `swiss-ai/Apertus-70B-Instruct-2509` | JSON schema |
| `groq_gpt_oss_120b` | Groq, `openai/gpt-oss-120b` | Strict JSON schema, low reasoning effort |
| `deepseek_v4_pro` | Direct DeepSeek, `deepseek-v4-pro` | JSON object, schema in prompt, thinking disabled |

Groq's [strict structured output contract](https://console.groq.com/docs/structured-outputs)
enforces JSON shape, while DeepSeek's
[JSON mode](https://api-docs.deepseek.com/guides/json_mode/) requires local schema
validation. All three retain the same local evidence, logic, scope and coverage
checks. GPT-OSS reasoning consumes part of its output allowance. This compares
configured pipelines, not model weights with identical decoding contracts.

The frozen source has 24 normalized sections, six eligible blocks and one
substantive paragraph (`section-0008`). Five remaining blocks are brochure/link,
modification metadata and footer material. The
[predeclared rubric](../../scripts/test/model_comparison/README.md#source-review-rubric-fixed-before-the-comparison)
checks six atomic source assertions: work requires a permit; a stay longer than
three months requires one, with OR and a strict boundary; cantonal offices issue
permits; short-term permits last less than a year; annual permits are limited;
permanent permits are unlimited. It also checks exact condition quotations,
scope roles, supported questions and exclusion of unrelated footer claims.

- Source SHA-256: `4e24815fa1ac301c1d0e3c4cd7c4f63eec1802e3af00529526774c7515d578bb`.
- Normalized input hash: `74c14fccf0d86be51f344940c347ccf6edb32ee8d1879b9ac7507ca0cc17c015`.
- Extraction prompt SHA-256: `4b870022420a0be39e16b8d993a8b1a44ee122375088807835d3d1c4efc5290e`.
- Review prompt SHA-256: `19412842e494e320b666a084c9c97da89d0204dd60e64465ac67ff14762ce284`.

All nine primary runs had identical initial user payloads, normalized input
hashes and effective extraction/review prompt hashes. Code snapshots preserve
the client versions used in each cohort.

## Measured results

| Model | Initial source assertions represented | Runs retaining a candidate | Runs needing repair | Mean API time per run | Mean wall time per run |
| --- | --- | --- | --- | --- | --- |
| DeepSeek V4 Pro | 6/6 in all three runs | 3/3 | 2/3 | 39.3 s | 39.4 s |
| GPT-OSS 120B, Groq | 6/6 in all three paced runs | 0/3 | 3/3 | 12.6 s | 181.5 s |
| Apertus 70B, PublicAI | 3/6 in the two matching-identity runs | 0/3 | 2/3; one identity failure | Not comparable | Not comparable |

Assertion coverage here is inspection of the initial draft, not a claim that all
its fields are correct. In particular, GPT-OSS run 1 had an unsupported status
field and Apertus had invalid logic representation. No Apertus quality score is
assigned to the mismatched-identity response. Repeated Apertus outputs do not
constitute independent samples.

| Model | Run | Retained | API calls | API seconds | Pacing seconds | Wall seconds | Reported input tokens | Reported output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Apertus | 1 | 0 | 1 | 59.294 | 0 | 59.495 | 2802 | 902 |
| Apertus | 2 | 0 | 2 | 25.808 | 0 | 25.871 | 6483 | 1294 |
| Apertus | 3 | 0 | 2 | 1.205 | 0 | 1.252 | 6483 | 1294 |
| GPT-OSS | 1 | 0 | 3 | 11.033 | 112.242 | 123.558 | 14107 | 4315 |
| GPT-OSS | 2 | 0 | 3 | 11.100 | 168.717 | 179.905 | 14137 | 4729 |
| GPT-OSS | 3 | 0 | 4 | 15.535 | 225.545 | 241.184 | 18374 | 6278 |
| DeepSeek | 1 | 1 | 2 | 24.300 | 0 | 24.346 | 8481 | 2612 |
| DeepSeek | 2 | 1 | 4 | 49.943 | 0 | 50.028 | 17739 | 5579 |
| DeepSeek | 3 | 1 | 4 | 43.685 | 0 | 43.764 | 17733 | 5082 |

The primary comparison used 25 HTTP calls, plus seven preserved Groq setup calls
described below: 32 live calls in total. Reported usage includes rejected
responses and repeated upstream completions; it is not an invoice. Different
tokenizers, schema handling and reasoning modes also limit token comparisons.
API times cover the requests actually made, including failed workflows with
different call counts. GPT-OSS was fast at drafting but did not deliver a
retained candidate; speed alone does not make it the strongest full pipeline.

## Quality findings

DeepSeek represented all six assertions in three claims in every initial and
repaired extraction. It preserved exact condition excerpts, connected both
prerequisites with a valid OR group, used `gt` with `3 months`, assigned the
Cantonal Migration Offices the issuing role, and avoided invented recipients,
procedures and foreign-national restrictions. Its three questions were answerable
from the claims and source. No substantive footer claim was added.

DeepSeek's weakness was review formatting: in runs 2 and 3, `scope_fields` was
nested inside `condition_logic` instead of beside it. Local validation rejected
both reviews. The existing bounded repair cycle produced a valid extraction
and review in each case. Thus final retention was 3/3, but completion without a
repair was only 1/3. Inspecting the source and outputs found no errors against
the six-assertion rubric; this is assistant inspection, not independent gold
adjudication.

GPT-OSS initially represented all six assertions in all three paced runs, with
valid condition trees, strict duration boundaries and correct issuing roles.
Its main weakness was review judgment. In runs 1 and 2, the reviewer classified
the footer's authority name as missing content. The repair then joined a footer
claim to the Residence concept across unrelated source ownership groups. Local
validation rejected both repairs. Run 1 also set `permit_status="required"`, and
the reviewer incorrectly approved it even though the contract reserves that
field for an evidenced status/category. Run 3's initial review made the opposite
error: it rejected `permit_status="unspecified"` because no status was stated,
despite that being the contract's correct representation of absent information.
Its final review accepted the claims and scope, then rejected all three questions
as having no answers. The requirement, issuing authority and permit taxonomy
were explicitly present in those same claims. This false rejection caused the
third run's zero retention. All paced Groq calls returned HTTP 200 with the
requested model identity; quota or transport failures do not explain these
three final outcomes.

Apertus run 1 returned the identity `aisingapore/Qwen-SEA-LION-v4-32B-IT` and was
rejected before extraction parsing. That response cannot measure Apertus quality.
The other two runs returned the approved PublicAI alias
`swiss-ai/apertus-70b-instruct`, but their initial and repaired proposals failed
local structural checks: `condition_root="OR"` was not a condition/group ID,
the group list was empty, and a condition used a paraphrase instead of an exact
source excerpt. Those proposals represented only three of the six assertions,
omitting the permit taxonomy. They also inferred foreign-national scope from
brochure text and misassigned the issuing office as a recipient in the requirement.
The repair did not correct these problems; no semantic review could run.

## Provider diagnostics and independence

The first Groq cohort received HTTP 403 with `error code: 1010` before inference.
Adding the application's explicit `User-Agent: SwissTIP/0.1` resolved this client
rejection. A subsequent unpaced cohort generated one valid proposal but hit the
account's 8000-token-per-minute limit on review and later runs. These cohorts are
preserved as setup diagnostics and excluded from model quality rates.

The final Groq cohort spaces request starts 60 seconds apart. API time excludes
this deliberate wait; wall time includes it, including waits at run boundaries.
The initial Apertus/DeepSeek cohort rotated model order between repeats; final
Groq runs occurred in a separate paced cohort. This was not a fully randomized
cross-model latency experiment.

Apertus runs 2 and 3 returned exactly the same two response IDs and corresponding
content hashes, despite fresh HTTP calls and zero local checkpoint hits:

| Request | Repeated response ID | Content SHA-256 |
| --- | --- | --- |
| Initial extraction | `chatcmpl-7718af32-755c-4a02-b2e6-1eb18ad06648` | `ef210c9197f642e5a8567026ef66eea4df9e3d98a3bd73e05f1e7557a1799a6a` |
| Repair | `chatcmpl-6eb214f3-37eb-42a7-a57f-176cab881cf2` | `63a5126bfd1dfdc105d1d77e30c8bd010217c2ed47af6406f75c18c7887fb4d6` |

This strongly suggests upstream response reuse, but the trace cannot establish
which service cached it. The 1.25-second third run is not credible evidence of
fresh Apertus generation speed, and the two matching runs are not independent
model generations. Reported token usage on these responses is not evidence of
separate billing. DeepSeek input-cache token accounting does not by itself imply
reused completions; its response IDs differed.

## Interpretation and next use

For this demo source, DeepSeek is the strongest tested candidate for running the
whole extraction/review workflow. GPT-OSS is promising for fast initial drafting,
but its self-review can invent missing work or reject correct unspecified fields.
Apertus through the current PublicAI route remains unreliable for this workflow;
both routing identity and structured extraction failures need attention.

Retained candidates still require human review and promotion. Pipeline
`coverage_complete=false` and `publication_eligible=false` do not automatically
mean a retained DeepSeek candidate omitted the substantive paragraph: the five
blocks marked not substantive by the model still await human disposition.
Neither self-review approval nor candidate count is verified accuracy.

This is one short, previously examined English page whose failures already
informed prompt fixes. It does not establish multilingual, long-page, table,
exception, embedding, ranking or OpenCode chat performance. Before a general
default change, extend the same rubric to unseen pages with conditional rules,
multiple authorities and tables, using independent source-based review. No model
defaults were changed by this experiment.

## Artifacts and implementation validation

A later [DeepSeek GUI run](2026-09-09-deepseek-v4-gui-extraction.md) failed both
reviews with misnested `scope_fields` and retained no candidate. Combined with
the three runs above, retention was 3/4 on this known page. The original measured
cohorts and their results remain as recorded; the follow-up documents the failure
and subsequent offline correction to review feedback and prompt layout.

Raw artifacts are ignored local files under `.local/experiments/model-comparison/`:

- `20260909T184619Z-e02d4c9f`: primary Apertus/DeepSeek results and initial Groq 403 diagnostics.
- `20260909T184948Z-ca40826e`: Groq header fix verification and quota diagnostics.
- `20260909T185200Z-a6987ec4`: final paced GPT-OSS comparison cohort.
- `20260909T184555Z-001abadf`: initial dry-run plans, with zero HTTP calls.
- [20260909-analysis/summary.md](../../.local/experiments/model-comparison/20260909-analysis/summary.md): combined primary run table, links to raw results and observed identities.
- [20260909-analysis/comparison-summary.json](../../.local/experiments/model-comparison/20260909-analysis/comparison-summary.json): measured metrics, result hashes, repeated response IDs and the assistant's source assessment.

Each live cohort retains source bytes, resolved TOML, code/prompt snapshots,
manifest hashes, CLI result/progress, successful checkpoints and redacted wire
request/response bodies, including rejected responses. These allow the findings
to be checked against what was actually sent and received.
An exact-value scan of all 241 files in the three live cohorts found none of the
three current credential values.

The repository now includes a Groq extraction adapter/profile and the reusable
comparison runner. The knowledge-builder suite passed 158 offline tests,
including request shape and identity, bounded recovery, checkpoints, key loading,
trace redaction, rejected-response token accounting, pacing and a three-model
dry run. The control API configuration tests also passed (six tests). Live
transport diagnostics and source-quality findings above are separate from those
offline software checks.
