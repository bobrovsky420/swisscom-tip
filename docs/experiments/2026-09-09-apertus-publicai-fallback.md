# Apertus: disable PublicAI fallback and expose the upstream limit

The client now prevents PublicAI's configured fallback from replacing Apertus
with another model and requests completion-cache reuse to be disabled. Apertus
availability remains an external constraint: live requests with fallback disabled
returned HTTP 429 from PublicAI's upstream service. No usable Apertus completion
was obtained during this investigation.

## Root cause

The Hugging Face model mapping still lists
`swiss-ai/Apertus-70B-Instruct-2509` as live on PublicAI, with provider ID
`swiss-ai/apertus-70b-instruct`. The existing model selector and generic
`https://router.huggingface.co/v1/chat/completions` URL are documented and valid.

[PublicAI's published Apertus configuration](https://github.com/forpublicai/chat.publicai.co/blob/main/charts/platform/charts/litellm/models/swiss-ai/apertus-70b-instruct.yaml)
selects an Infomaniak upstream for Apertus 70B and explicitly lists Qwen SEA-LION
and Bielik as fallbacks. Its [LiteLLM values](https://github.com/forpublicai/chat.publicai.co/blob/main/charts/platform/charts/litellm/values.yaml)
enable Redis completion caching with a 600-second TTL. This configuration is
consistent with the Qwen identities and repeated completion IDs observed in the
comparison. It is not evidence that our app selected Qwen.

With fallback and cache reuse disabled, the original extraction request returned:

```text
HTTP 429
litellm.RateLimitError: RateLimitError: OpenAIException - maximum_token_reached
```

A tiny 32-token plain-text probe also returned HTTP 429, this time reporting
`rate_limit_exceeded`. There is no evidence for the exact quota, reset time or
responsible account balance. The limit may concern the shared upstream rather
than the user's Hugging Face account. The observations do not establish that
removing our schema, buying Hugging Face credits or waiting a specific interval
would restore availability.

## Client correction

The Hugging Face adapter adds the following to every PublicAI request, for both
JSON-schema and prompt-only modes:

```json
{
  "disable_fallbacks": true,
  "cache": {"no-cache": true, "no-store": true}
}
```

These controls are defined in the [LiteLLM fallback documentation](https://docs.litellm.ai/docs/proxy/reliability#disable-fallbacks-per-requestkey)
and [dynamic cache controls](https://docs.litellm.ai/docs/proxy/caching#dynamic-cache-controls).
The existing endpoint, model configuration and identity validation remain intact.
No new model alias or implicit fallback is introduced. Other providers receive
their existing payloads. Local checkpoint reuse remains a separate operation.

Known HTTP 429 codes are classified from at most 4096 bytes of valid JSON and
rendered as fixed diagnostics. Raw error prose, unknown fields and credentials
are never copied into the exception message. Both HTTP-error transport paths
preserve request ID and Retry-After metadata. Oversized, malformed and unrecognized
errors remain generic. The code does not guess a quota reset or increase retries.

The comparison runner's HTTP tracer previously consumed error bodies before the
adapter could classify them. It now saves the bounded body and gives the adapter
a fresh stream containing those same bytes. This preserves trace evidence and
the real provider diagnostic in the CLI progress log.

## Live checks

| Diagnostic | Result |
| --- | --- |
| Provider-specific HF/PublicAI route with original JSON schema | Qwen identity; changing URL alone did not fix substitution |
| Generic route with HTTP Cache-Control/Pragma headers | Same Qwen response; HTTP cache bypass did not disable the internal completion cache |
| Generic route in prompt-only mode | Qwen identity; removing response_format alone did not fix substitution |
| Provider-specific route with fallback/cache controls disabled | HTTP 429, maximum_token_reached |
| Generic route, 32-token plain-text probe, fallback/cache controls disabled | HTTP 429, rate_limit_exceeded |
| Actual builder with corrected request controls | One HTTP 429, zero candidates; original raw body retained |
| Actual builder after error-tracing correction | One HTTP 429, maximum_token_reached, 9.442 seconds, zero candidates |

The final progress log reports the specific upstream constraint:

```text
Hugging Face router returned HTTP 429: upstream model token limit reached (maximum_token_reached)
```

The CLI's final "Concept extraction completed successfully" means the report was
written; this run produced no draft and does not demonstrate a working Apertus
extraction.

The provider-specific diagnostic follows the [official HF provider helper](https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/inference/_providers/_common.py),
which uses a provider-specific proxy and mapped model ID. Both supported routes
honored the fallback controls. The production URL therefore did not need changing.

The builder checks use the original saved English Residence page,
`concept_extraction_v4`, JSON-schema mode, temperature 0, 4096 output tokens, one
repair and zero client retries. There is no new crawl or publication. The
metadata query and diagnostic probes are separate from the historical comparison;
no previous results were rewritten.

Artifacts under `.local/admin/apertus-route-20260909/` include the model mapping,
redacted routing probes, `diagnose.py`, the first builder verification and the
final builder run:

- [Final progress log](../../.local/admin/apertus-route-20260909/verified-final/apertus_70b-run-1/progress.log)
- [Final report](../../.local/admin/apertus-route-20260909/verified-final/apertus_70b-run-1/result.json)
- [Final raw call](../../.local/admin/apertus-route-20260909/verified-final/apertus_70b-run-1/calls/call-01.json)

Reproduce one bounded live check with the existing runner:

```shell
./.venv/Scripts/python.exe scripts/test/model_comparison/run.py --input .local/admin/jobs/a3eba5ef2158488696ba603de42433c5/57fdf9ad48164dcab573e7f404bf1327.html --profiles apertus_70b --repeats 1
```

Software checks: the full knowledge-builder suite passed 170 tests before the
final trace/edge-case additions; the final targeted suites passed 22 provider
tests and nine comparison tests. They cover PublicAI-only controls in both modes,
unchanged identity rejection, bounded safe error classification and faithful
traced error replay. Existing request budgets and recovery behavior remain in use.

Next: restore capacity/quota on the PublicAI upstream or configure an available
Apertus endpoint with its own authorized credential. Then rerun the bounded
extraction and source review. Client changes cannot replenish provider capacity,
and the current evidence does not justify claiming Apertus extraction now works.
