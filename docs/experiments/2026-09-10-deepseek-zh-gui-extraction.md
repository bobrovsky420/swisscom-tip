# DeepSeek Zurich GUI extraction: output truncation

GUI job `008afd0e4bb14328867ae790e945a880` retained zero candidates from the
saved `zh-eu-efta` page. Its first extraction response ended with
`finish_reason=length` at the configured 4096-token output limit. The adapter
rejected the incomplete response; no semantic review or repair ran. The report
took 29.742 seconds and records one network attempt, zero usable completions,
zero provider retries and no checkpoint hits. Reported zero usage excludes the
failed completion; it does not establish zero consumption or billing.

The progress line `requests=0` counts completed responses. It does not mean no
request was sent: `execution.network_attempts=1` and
`quality_metrics.request_attempt_count=1` record the attempt. The final
`Concept extraction completed successfully` message means the CLI wrote its
report, not that the page produced a usable draft. The GUI's **Needs attention**
therefore identifies an actual extraction failure in this run.

The saved page has 105 blocks and 20333 normalized characters. Planning packs
69 eligible blocks into three bundles of 26, 24 and 19 blocks (6005, 5989 and
3993 evidence characters); 36 navigation/heading blocks are excluded by policy.
The first bundle's 26 blocks became `provider_failure`; the remaining 43 were
`not_processed_provider_failure`. All remain unresolved. No partial response
was checkpointed or retained as a candidate.

## Prepared adjustment, verified offline only

`config/semantic-models.toml` now sets `generation.max_output_tokens=8192`.
This shared setting affects extraction and review for any selected semantic
profile. DeepSeek remains selected. Source packet size, concept limit, prompts,
validation, one-repair limit, 180-second timeout and 12-call page ceiling are
unchanged. GUI provider retries remain disabled. New GUI jobs read the current
configuration without restarting the server; old jobs retain their frozen
4096-token setting.

Doubling the allowance is a controlled next experiment. The truncated response
does not reveal how much output was needed, so 8192 is not an established fix.
Complete output must still fit the separate 25600-character source/proposal
review-input allowance and pass all existing checks. A larger limit permits
more output and potentially longer and more costly calls, even though the
request ceiling is unchanged.

Smaller source packets were considered offline. A 4800-character packet limit
plans four bundles, reserving eight initial extraction/review calls and leaving
four repair calls within the 12-call ceiling. At 3200, six bundles consume all
12 initial calls, leaving no repair capacity. At 2400, the budget omits 19
eligible blocks. Reducing this limit also reduces the review-input allowance.
The prepared output-only change preserves the original three-bundle plan.

Verification artifacts are in `.local/admin/zh-output-008afd0e-20260910/`:
the GUI-resolved configuration, `plan.json`, `progress.log`, `audit.json` and
the offline audit script. Provider construction was blocked. The plan sent
zero model requests and retained the same 12-call ceiling, source inventory,
source hashes and effective prompts. The only effective configuration change
from the failed job is the output limit. All six Control API configuration
tests and 13 builder profile tests passed. No live retry was performed.

| Preserved artifact | SHA-256 |
| --- | --- |
| Failed report | `3fae78064f63124a9d0a6313375914cbf574bc5580c8499e69b0c9e6af9bf1f1` |
| Original source | `b2da0b36fe559eda757496393c8e9db616cf7444fd796e14a8a8e030b458f1f4` |
| Original configuration | `4756246277094b08db46839ce7538c8a53e1d0eb4341584cdbf747a63ca5d6cf` |

All original job files retained their hashes during verification.

## GUI resume checkpoint

In **Saved pages**, select only **Zurich EU/EFTA** (`zh-eu-efta`), keep
`deepseek_v4_pro`, and click **Preview extraction plan**. Verify the new job's
frozen configuration has 8192 output tokens, one page, at most 12 planned
requests and zero sent. Continue to **Run extraction** / **Confirm extraction**
as the following user-controlled GUI step. Check actual network attempts,
retained candidates, review history and source coverage after the run.

The earlier GUI decisions remain separate: Alex accepted the English Residence
draft from job `87ca1a63d46f49c7afa6343714fb4e8d`. The latest German decision for
job `7ed3c77f27fe4b5381957929a8093d11` is `needs_changes`, following an earlier
acceptance. Its work condition contains only `arbeitet`, dropping the source
qualification `während seines Aufenthaltes in der Schweiz`. The complete
statement retains that qualification, but the structured condition needs it
too. The review note records that correction; it does not edit or publish the
draft. No extraction/prompt correction for that semantic issue is included here.
