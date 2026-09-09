# V4 extraction model comparison

Run from the repository root, using the current process credentials first and
`.env.dev` for missing `HF_TOKEN`, `GROQ_API_KEY` and `DEEPSEEK_API_KEY` values:

```shell
./.venv/Scripts/python.exe scripts/test/model_comparison/run.py --dry-run --repeats 1
./.venv/Scripts/python.exe scripts/test/model_comparison/run.py --repeats 3
```

The default source is the saved SEM English Residence page used in the GUI.
Use `--input path/to/page.html` for another saved page. No crawl is performed.
`--output` must name a new directory. By default each batch creates a unique
ignored directory under `.local/experiments/model-comparison/`. Use
`--profiles apertus_70b groq_gpt_oss_120b deepseek_v4_pro` to select/order models.

Every model gets identical saved source bytes and current v4 extraction/review
prompts, temperature, output budget, repair limit and local validation. Each
repeat starts fresh with provider retries disabled and separate checkpoints.
Model order rotates between repeats. Groq calls are spaced at least 60 seconds
apart by default because the current account has an 8000-token/minute allowance;
use `--groq-interval-seconds` to match another account's limits. This pacing is
recorded separately from API time and does not retry failed calls.
Apertus uses HF/PublicAI JSON schema,
GPT-OSS uses Groq strict JSON schema with low reasoning effort, and DeepSeek uses
its direct API's JSON-object mode with thinking disabled. These are different
provider/generation contracts; this compares the configured pipelines, not raw
model weights under identical decoding. GPT-OSS reasoning consumes part of its
output budget. Repository active selections are not changed.

Each run preserves its complete resolved configuration, CLI report/progress,
successful checkpoints and bounded HTTP request/response diagnostics. Request
authorization headers and credentials are excluded; the non-secret User-Agent is
recorded to diagnose API client rejection. Known key values are redacted from logs
and diagnostics. Keep these artifacts local because they contain source and
model output. Manifest usage includes reported tokens even for rejected or
truncated responses; calls without usage are counted explicitly. A completed
CLI report is not a semantic quality pass. Each batch also writes `summary.md`
with a comparison table and links to individual results. Bypassing local
checkpoints cannot force a provider to generate a new completion: compare raw
response IDs and content hashes when assessing independence or unusually short
latencies.

## Source review rubric, fixed before the comparison

For the saved SEM page, assess the six source assertions individually:

1. Working during the stay requires a permit, independently of stay duration.
2. Staying longer than three months requires a permit; preserve the strict
   boundary and its OR relationship with the work branch.
3. Cantonal Migration Offices issue residence permits. Preserve the issuing
   role; do not turn the office into a permit recipient or an invented condition.
4. Short-term residence permits have duration less than one year.
5. Annual residence permits are limited.
6. Permanent residence permits are unlimited.

Check exact supporting quotations, correct logical conditions and scope,
complete permit taxonomy, no invented procedures/exceptions, and questions
answerable from this source. Brochure links, modification dates, navigation and
footer text must not become substantive permit claims. Count proposals only as
an operational metric. Review both raw proposals and retained candidates to
distinguish extraction errors from self-review/validation failures.

This is a small known-source diagnostic. The source has already informed v4
prompt and validator fixes. Model self-review and assistant inspection are not
independent adjudicated gold labels or proof of current legal correctness.

See the [completed 2026-09-09 comparison](../../../docs/experiments/2026-09-09-v4-model-comparison.md)
for measured results, source-level findings and provider limitations.
The [three-model rerun after the review nesting correction](../../../docs/experiments/2026-09-09-v4-model-comparison-rerun.md)
records nine fresh pipeline runs, source checks and browser links to the retained drafts.
