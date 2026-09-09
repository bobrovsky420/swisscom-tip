# V4 model comparison rerun after review nesting correction

DeepSeek V4 Pro retained a draft in all three runs and passed assistant inspection
against the saved Residence page and extraction contract in all three. GPT-OSS
120B also retained three drafts, but inspection found contract or scope defects
in two of them. All three Apertus 70B requests returned a different model identity
and were rejected before extraction parsing; this batch cannot measure Apertus
quality or inference speed.

The batch completed on 2026-09-09, from 19:50:01 to 19:57:32 UTC: nine pipeline
runs, 17 HTTP calls and 451.35 seconds overall. All calls returned HTTP 200.
There were no provider retries, rate-limit errors or local checkpoint hits.

## Results

| Selected model | Runs retaining a draft | Drafts without identified rubric/contract defects | Runs using repair | Mean API time/run | Mean wall time/run |
| --- | --- | --- | --- | --- | --- |
| DeepSeek V4 Pro | 3/3 | 3/3 | 0/3 | 19.737 s | 19.918 s |
| GPT-OSS 120B, Groq | 3/3 | 1/3 | 1/3 | 10.537 s | 104.835 s |
| Apertus 70B, HF/PublicAI route | 0/3 | Not assessable: wrong model | 0/3 | 25.305 s, failed route | 25.394 s, failed route |

The second column measures draft retention. The third is assistant inspection
against the predeclared source rubric and explicit extraction contract, not
independent human adjudication or a general accuracy score. Groq's 60-second
request-start interval added 282.465 seconds of pacing across its three runs;
API time excludes that deliberate wait. Apertus-route timing measures responses
that reported another model, including repeated upstream output.

| Model | Run | Drafts | Calls | API seconds | Pacing seconds | Wall seconds | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DeepSeek | 1 | 1 | 2 | 21.267 | 0 | 21.541 | 8922 | 2722 |
| DeepSeek | 2 | 1 | 2 | 19.121 | 0 | 19.230 | 8916 | 2458 |
| DeepSeek | 3 | 1 | 2 | 18.823 | 0 | 18.984 | 8922 | 2493 |
| GPT-OSS | 1 | 1 | 2 | 7.337 | 56.943 | 64.451 | 8719 | 3042 |
| GPT-OSS | 2 | 1 | 4 | 14.809 | 169.631 | 184.577 | 19279 | 6243 |
| GPT-OSS | 3 | 1 | 2 | 9.464 | 55.891 | 65.478 | 9031 | 3883 |
| Apertus route | 1 | 0 | 1 | 55.696 | 0 | 55.775 | 2802 | 902 |
| Apertus route | 2 | 0 | 1 | 10.260 | 0 | 10.354 | 2802 | 902 |
| Apertus route | 3 | 0 | 1 | 9.960 | 0 | 10.054 | 2802 | 902 |

Reported usage totals 72195 input tokens and 23547 output tokens, including
rejected and repeated responses. Every response included usage. This is provider
accounting, not an invoice; repeated token counts do not establish separate billing.

## Source and review findings

DeepSeek preserved all six source assertions in three claims in every run:
work OR a stay strictly longer than three months requires a permit, cantonal
migration offices issue the permits, and the three permit categories retain
their stated durations. Conditions use exact source excerpts, a connected OR
group and `gt` with `3 months`. Issuing authority and recipient roles remain
distinct. Each draft has three source-answerable questions.

All three DeepSeek reviews repeated the known nesting error. The parser moved
three existing `scope_fields` objects per run, nine in total, then passed the
unchanged validation. Each normalized review equals its raw review after those
exact moves, with every verdict and reason preserved. No repair extraction or
second review was needed. This directly exercises the implemented correction.

GPT-OSS run 1 passed the source and representation checks. It preserved all six
assertions, exact condition excerpts, the combined OR rule and issuing role, with
two answerable questions. Its review treated unspecified status fields and the
footer correctly; no repair or nesting correction was needed.

GPT-OSS run 2 retained an incorrect `permit-required.scope.permit_status="required"`.
The contract reserves this field for an evidenced status/category. Both reviewer
revisions approved the value. The first review also classified the footer's
authority name as missing substantive content, triggering repair. The final
review changed that footer disposition to `not_substantive`, but the scope defect
remained in the retained draft. The repair also set `saturated=true`. All six
substantive assertions and three answerable questions are present; this remains
a review-judgment failure despite successful retention.

GPT-OSS run 3 split the source's A OR B requirement into separate work and stay
claims, with no shared OR tree. The two statements collectively preserve both
alternatives, but violate the prompt's explicit instruction to represent the
complete alternatives in one claim. Both requirement claims also leave
`scope.jurisdiction="unspecified"` despite Switzerland appearing in their own
evidence and condition text; the reviewer incorrectly says jurisdiction is absent.
The short-term category is paraphrased as permits "for stays of less than 1 year",
which merits human checking against the source's permit-duration wording. All
six topics are represented. `questions=[]` is allowed by the schema and is not
counted as a validation failure.

All six retained outputs remain `CANDIDATE`, with `publication_eligible=false`.
Their ancillary source blocks still await human disposition; candidate retention
does not certify complete source coverage. GUI-equivalent **Needs attention**
also includes the standard human-review warning.

## Apertus routing and response reuse

Every Apertus request selected `swiss-ai/Apertus-70B-Instruct-2509:publicai`.
Every response instead reported `aisingapore/Qwen-SEA-LION-v4-32B-IT`, which is
neither the selected model nor its approved PublicAI alias. The provider identity
guard rejected these responses before extracting candidates. They are provider
routing failures and supply no attributable Apertus semantic-quality result.

All three returned response ID `chatcmpl-bf1949125329ff3d` and identical completion
SHA-256 `79490236e369b909ed242d03fc44338b6f241035f54c3002eb7da60533bdc592`.
This indicates upstream response reuse; the traces do not identify which service
reused it. They are three HTTP attempts, not evidence of three independent Apertus
generations. DeepSeek and Groq response IDs are distinct. DeepSeek's initial
completion text matches between runs 1 and 3, with different response IDs; equal
text at temperature zero alone does not establish completion reuse.

## Controls and comparison with the earlier batch

The [existing comparison runner](../../scripts/test/model_comparison/README.md)
used the same saved `ch-sem-residence-en` HTML bytes and fixed six-assertion rubric.
All nine initial user payloads and effective prompt hashes match. Configuration
uses temperature 0, a nominal 4096-token output limit, 180-second request timeout,
one repair revision and zero provider retries. Model order rotates each round:
DeepSeek/Groq/Apertus, Groq/Apertus/DeepSeek, Apertus/DeepSeek/Groq.

DeepSeek uses JSON-object mode with thinking disabled; Groq uses strict JSON
schema with low reasoning effort; Apertus is configured for HF/PublicAI JSON
schema. Provider contracts and reasoning accounting differ, so this compares
the configured extraction/review pipelines.

Source SHA-256: `4e24815fa1ac301c1d0e3c4cd7c4f63eec1802e3af00529526774c7515d578bb`.
Extraction prompt SHA-256: `4b870022420a0be39e16b8d993a8b1a44ee122375088807835d3d1c4efc5290e`.
Review prompt SHA-256: `854222e23c4209f5786f2e09cd1ad97f7d9f9f314fe3340eb8a881a4c616ed9b`.

Compared with the [earlier comparison](2026-09-09-v4-model-comparison.md), DeepSeek
still retains 3/3, now with zero repair runs versus two, and mean API time of
19.7 seconds versus 39.3. Groq retention improves from 0/3 to 3/3, but two retained
drafts have issues on inspection. Apertus retention stays 0/3; all new attempts
fail identity, whereas two earlier attempts had a matching identity and failed
structural extraction checks.

This is a current-pipeline rerun, not an isolated causal experiment on the nesting
parser. The review prompt and validation-feedback handling also changed since
the earlier comparison. The source is a short, known English page that informed
those changes; no general multilingual or unseen-page accuracy claim follows.

## Reproduce and review

```shell
./.venv/Scripts/python.exe scripts/test/model_comparison/run.py --input .local/admin/jobs/a3eba5ef2158488696ba603de42433c5/57fdf9ad48164dcab573e7f404bf1327.html --profiles deepseek_v4_pro groq_gpt_oss_120b apertus_70b --repeats 3
```

- [Browser comparison and six draft review pages](../../.local/experiments/model-comparison/20260909-nesting-fix-analysis/index.html)
- [Independent assistant source assessment](../../.local/experiments/model-comparison/20260909-nesting-fix-analysis/source-assessment.md)
- [Per-run metrics and response diagnostics](../../.local/experiments/model-comparison/20260909-nesting-fix-analysis/comparison-summary.json)
- [Experiment control verification](../../.local/experiments/model-comparison/20260909-nesting-fix-analysis/verification.json)
- [Raw batch manifest](../../.local/experiments/model-comparison/20260909-nesting-fix-live/manifest.json)

The local artifacts preserve source and code snapshots, resolved model settings,
raw request/response diagnostics, reports, progress and successful checkpoints.
The verification checks source/code hashes, identical initial payloads/prompts,
run limits, zero retries/checkpoint hits and absence of current credential values
in the scanned artifacts. The nine-run dry plan sent zero model requests and
reserved at most four calls per run. No production code or model defaults were
changed during this comparison.

Next: retain DeepSeek as the current authoring choice for this demo page. Add
the two GPT-OSS false approvals as scope/representation regression cases, and
resolve the Apertus route's model identity and response reuse before comparing
it again. Then extend the source rubric to additional pages with human review.
