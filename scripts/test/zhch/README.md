# Concept extraction quality experiment

For the completed 2026-09-05 experiment, see the
[8B/70B comparison and findings](../../../docs/experiments/2026-09-05-zhch-concept-extraction.md).

Run commands from the repository root. The scripts use the repository `.venv`.
The fixture stays under the system temporary directory in `swisstip-zhch-poc`.
Existing downloaded pages are verified and reused. Each extraction gets a new
`runs/<RunName>` directory. Omitting `-RunName` generates a unique name.

```shell
pwsh -File ./scripts/test/zhch/Invoke-ZhChConceptPoc.ps1 -RunName 70b-v3-01 -Verbose
```

The examples use `apertus_70b` and `concept_extraction_v3`. Check `active_profile`
in the configuration before running; use the model name in your run label.
Token loading is unchanged: process `HF_TOKEN` takes precedence over `.env.dev`.
No token value is written into the run artifacts.

Each successful run contains:

- `concept-proposals.json`: original per-page reports, exact source quotations
  and offsets, rejected proposals and reasons, excluded sections, quality counts,
  conservative consolidated groups, the effective non-secret configuration,
  elapsed time, and usage when supplied by the provider.
- `review.csv`: one retained candidate per row, including its primary section,
  with blank human-review fields.
- `run.log`: extraction progress and errors. Extraction verbose output is always
  enabled for this recording, even if the wrapper omits `-Verbose`.
- `download-manifest.json`: a copy identifying the raw downloaded fixture.

A provider failure leaves the run log, downloaded fixture and successful model
responses available. Rerun with a new name to resume using the shared
`checkpoints/` directory beneath the fixture root. Generation and semantic review
are checkpointed separately, so a failed review does not require regenerating
its proposals. Proposal artifacts are written only when the entire batch succeeds;
this does not publish a Knowledge Release.
Runs made before checkpoint support cannot be resumed from their logs.

Checkpoint matching includes the original input hash, normalized page, selected
profile, generation and extraction settings that affect output, and exact prompt
text and schema. Changed inputs/models/prompts do not reuse old results. Changing
only retry policy or request limits preserves completed work. Tokens are not
part of checkpoint identity or contents. Checkpoints are atomically replaced;
corrupt entries are ignored, and structurally invalid responses are evicted.
Keep this directory internal: it contains source quotations and model responses,
and is a trusted cache, not a format for importing third-party files. Use one
process per checkpoint directory; concurrent runs can duplicate inference.

Use `-FreshInference` for independent repeatability measurements. It bypasses
checkpoint reads but still saves new responses, replacing matching cache entries;
older run reports remain unchanged. Omit it when resuming an interrupted run.

`[recovery]` in `config/semantic-models.toml` configures HF transient retries:
two additional attempts by default, with 2s then 4s backoff. HTTP 408, 429, 500,
502, 503 and 504, plus transport failures, are retryable. Authentication and
response-validation failures are not. Ordinary exponential backoff is capped by
`max_backoff_seconds` (30s). Provider `Retry-After` waits have a separate cap,
`max_retry_after_seconds` (300s by default, configurable up to 3600s).
Both delay-seconds and HTTP-date headers are supported. The requested header
value and applicable cap are logged, and longer waits show progress every 15s.
If the requested delay exceeds the provider-wait cap, the run stops rather than
retrying prematurely. Missing or malformed headers use ordinary backoff.
Waits do not consume model attempts. Ctrl+C interrupts a wait without removing
previously saved responses. Changing either wait cap preserves checkpoint reuse.
No automatic model fallback or semantic rewriting occurs. Ollama failures are
checkpoint-resumable but not automatically retried.

Every actual attempt, including failures and retries, counts toward the page
and run limits. These counters reset on each invocation; cache hits consume no
network budget. Preflight remains conservative and checks the full logical
workload. The six-page fixture now plans at most 22 calls, leaving eight attempts of
retry headroom under the default 30-call run limit; retries can still exhaust
that limit. New calls and failed attempts may incur provider charges.

The `execution` object separates actual `network_attempts`, `retry_attempts`,
`checkpoint_hits`, and usage for newly completed responses. Per-page reports and
`quality_summary` describe the full logical result, including reused responses
and their historical token usage. Neither is a billing receipt; token usage
for failed attempts is unknown. Verbose failure logs retain execution accounting.
For incomplete HF completions, `execution.incomplete_completions` separately
records provider-reported input/output token usage (when available), finish
reason, returned content character count, response byte count and configured
output limit. These diagnostics also appear in failure logs. Partial content is
never logged, checkpointed or accepted as a valid result. An identical truncated
request is not automatically retried.
Usage on incomplete responses is not included in successful-completion totals.

Only an HF semantic review ending with `finish_reason=length` can trigger a
smaller-batch fallback. `recovery.review_fallback_batch_size` defaults to two
proposals (configurable from 1 to 10); each fallback must be smaller than its
parent. If a smaller batch also truncates, it is split again, down to a single
proposal. Single-proposal truncation, generation truncation, authentication
failures and invalid verdicts stop processing. Partial reviews are never used.

Each child review receives only its proposals' primary-section context. IDs are
renumbered for that child and mapped back after strict verdict validation. All
children must succeed before the combined review can be accepted. Native child
responses are checkpointed individually; a `*.split.json` marker remembers to
resume the children instead of repeating the already-truncated parent. The
marker stores no partial response. Existing successful normal checkpoints keep
their original keys. `-FreshInference` ignores both markers and saved responses.

Fallback calls, including failed ones and transient retries, count against the
same page/run attempt limits. The preflight is still the base logical workload,
not a guarantee that fallback fits the remaining budget. `execution.review_fallbacks`
records batch sizes, completion status and child request IDs. A combined review
remains one logical review in page reports, with successful child token usage
summed and no invented provider request ID; `execution.network_attempts` records
the actual new calls. Neither a split nor a retry increases configured limits.

Prior result files at the fixture root are also left intact. `-RefreshFixture`
explicitly removes the entire selected fixture root, including run history and
checkpoints; use a new
`-OutputRoot` when you need fresh downloads and want to keep old experiments.

## Review the first new run

Start with the overview, EU/EFTA residence, and biometric permit pages. In
`review.csv`, fill `Relevant`, `SupportedByEvidence`, and `CorrectType` with
yes/no/uncertain; use `DuplicateOf` and `Notes` where appropriate. Inspect the
original page when deciding whether conditions or exceptions were omitted.
Keep a separate list of 5-10 expected concept labels per reviewed page, with a
supporting section or sentence. Missing concepts cannot be measured from the
generated proposals alone.

The exact evidence check verifies that text came from the supplied chunk. It
does not prove that the generated claim follows from that text. Confidence is
an uncalibrated model assessment. Section citation counts are diagnostic, not
a measure of topic recall. Empty pages and even all-empty batches are saved
for review rather than discarded as a transport failure.

## Repeatability and model comparison

First compare one run per model using the same cached fixture. Change only
`active_profile` to `apertus_8b`, then run:

```shell
pwsh -File ./scripts/test/zhch/Invoke-ZhChConceptPoc.ps1 -RunName 8b-v3-01 -FreshInference -Verbose
```

For the model comparison, change just the selector in
`config/semantic-models.toml`:

```toml
active_profile = "apertus_70b"
```

Then run once using the appropriate account token:

```shell
pwsh -File ./scripts/test/zhch/Invoke-ZhChConceptPoc.ps1 -RunName 70b-v3-02 -FreshInference -Verbose
```

Compare reviewed relevance, support, classification, missing expected concepts,
duplicates, time and tokens. Keep the extraction settings and raw fixture fixed.
Share the run directories and reviewed CSVs for analysis. A lower rejection rate
alone does not establish better semantic quality.

## What v3 changes

V3 fixes numeric scopes such as `> 3 Monate`, excludes embedded News branches
(not standalone news pages), and preserves paragraph, list-item and table-row
boundaries without splitting abbreviations such as `bzw.` or `z.B.`. Source
normalization differs from v2; compare raw fixture hashes, not offsets across
prompt versions. Very long blocks remain bounded to 500-character spans.

An HTML-only structural check now skips entire chunks containing only generic
link lists: every section must have a generic links heading and all visible body
text must be inside links. Explanatory prose, non-generic headings and mixed
chunks remain eligible. Plain-text and Markdown inputs are not classified this
way. Reports record the original chunk index, section IDs and `generic_link_only`
reason in `skipped_chunks`; summary metrics include `skipped_chunk_count`.
Chunks are not repacked or renumbered, and the derived HTML hint is excluded
from content/checkpoint identity. Unaffected prompts and existing checkpoints
therefore remain reusable. Entirely skipped pages produce empty reports with
zero calls/tokens and provider/model `not_called`, rather than invented results.

Each proposal declares a primary section and may cite only that section.
A separate structured call to the same selected model checks all claims,
conditions, applicability, language, answerability and type. Unsupported and
uncertain proposals are rejected with reasons in `semantic_reviews` and
`rejected_candidates`. Invalid reviewer responses fail the run. Truncated
reviews can use the bounded smaller-batch fallback described above.
This is model assessment, not ground truth, and the same model can repeat its
own mistakes. Human review remains necessary.

The preflight reserves up to two calls per chunk, including review. Empty or
fully invalid generations skip review. The default run ceiling is 30 calls;
tokens and logical requests in results include both stages, even when reused.
Transient retries are bounded separately as described above. Expect additional
time and token usage compared with v2 on fresh inference runs.

Duplicate review now also surfaces shared aliases and similar label wording
in `duplicate_review_pairs` (at most 200 pairs, with total and truncation flag).
It never automatically merges these suggestions or different eligibility scopes.
Check the close-relative conditions, permit-vs-quota exemptions, German prose,
and permit-table coverage in the first human review, including rejected proposals.

### Retained v2 safeguards

Known navigation, feedback and generic contact heading branches are excluded
before chunking. Their IDs and reasons are recorded, and original normalized
section IDs, hashes and offsets are preserved. The rule is heading-based and
does not remove arbitrary repeated text or all telephone-related services.

The model selects IDs from numbered source spans of at most 500 characters.
Python attaches the exact original quote. IDs outside the current chunk are
rejected. Questions must be non-empty and scope must describe applicability.
The prompt includes type examples, coverage priorities and guidance for dates,
conditions and exceptions. These semantic instructions still need evaluation.

Consolidation groups exact normalized matches of label, scope, type, granularity,
description and language. Every original candidate and its source evidence is
preserved. Equal labels with differing claims or scope are flagged for review;
synonyms and different eligibility groups are not automatically merged.

The legacy `concept_extraction_v1` and `concept_extraction_v2` prompts remain selectable for controlled
comparison. To reproduce the old extraction settings, also restore its chunk
size of 12000 and overlap of 600 in a separate configuration file and supply
that file with `-ConfigPath`. Model responses may still vary.

## Local regression checks

```shell
./.venv/bin/python -m unittest discover -s packages/ingestion/tests -v
./.venv/bin/python -m unittest discover -s apps/knowledge-builder/tests -v
pwsh -File ./scripts/test/zhch/Test-ZhChScriptEnvironment.ps1
```

On Windows use `.venv/Scripts/python.exe` for Python. Unit tests use fake model
responses. The Windows workflow integration test starts a temporary loopback
fake Ollama server and runs the actual PowerShell wrapper; it makes no external
requests or real inference calls. It checks cache reuse, separate run artifacts,
504 logging, collision rejection and retention of empty results.
