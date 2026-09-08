# Retrieval pilot handover - 2026-09-08

This is the durable handover for the SEM/Zurich pilot, including unsuccessful
attempts and decisions. Detailed chronology and hashes remain in the
[experiment record](../experiments/2026-09-06-structured-extraction.md).
[BUILD-05](../experiments/2026-09-07-build05-retrieval.md) covers runtime integration;
[TODO](../../TODO.md) owns remaining review, language and publication requirements.

## Outcome and limits

The final Zurich checkpoint has ten distinct passing observations across runs:
six relevant-evidence lookups and four abstentions. Nine were direct runtime
checks and one was MCP stdio. One frontier lookup failed operationally before an
explicit rerun passed. This is not a clean ten-request run or an independent gold
evaluation. Guided Ling caller checks subsequently passed one positive and one
negative case after recorded prompt/reporting corrections.

Both SEM and Zurich releases are experimental: real saved excerpts and real
document embeddings, but synthetic catalog IDs, coverage, temporal bounds,
evaluation/approval references and freshness policies. They contain zero published
facts and rules. Literal `APPROVED` fields satisfy fixture contracts; they do not
represent genuine review. Applicable outcomes remain `EXCERPTS_ONLY` or `NONE`,
with `INSUFFICIENT_VERIFIED_EVIDENCE`, never supported legal advice.

## Model decisions

| Role | Selected model/profile | Location and findings |
| --- | --- | --- |
| Caller | `opencode/ling-3.0-flash-fin-free` | OpenCode hosted caller; useful guided tool execution, but reporting required corrections |
| Embedding | `qwen_embedding_0_6b`, `qwen3-embedding:0.6b` | Ollama in WSL, reached from Windows localhost:11434; 1024 dimensions |
| Evidence ranking | `groq_answer_relevance_20b`, `openai/gpt-oss-20b` | Groq API; `GROQ_API_KEY` environment variable; `groq-ranking/v2` |
| Extraction experiments | Local Apertus 8B; HF/PublicAI Apertus 70B; Groq GPT-OSS 20B/120B | Experimental outputs, not independently qualified production extractors |
| Review experiments | Groq GPT-OSS 120B | Better observed structured review in this pilot; still model-assisted review |

OpenCode, ranking and embedding do not need the same model. Semantic extraction
and retrieval have independent named profile configurations. The root retrieval
config retains its earlier default; these runs explicitly use each harness's
`providers.toml`. Default `.local/opencode.json` still selects the synthetic
BUILD-03 fixture. Pilot caller runs used child-process configuration overrides.

## What failed and what was learned

- HTML initially retained navigation and footer material. Filtering was improved,
  but short labels and metadata still required coverage review. Filtered text is
  not automatically substantive, complete or legally applicable.
- Ollama cold loading caused timeouts. Windows-to-WSL connectivity and warmed
  inference were tested separately. A warmed early embedding check took 0.341s;
  this is not a latency guarantee. Batch preparation used a longer local timeout.
- Local Apertus produced structural review failures and zero proposals despite
  CLI exit 0. Inspect quality and execution summaries, not only process success.
- HF/PublicAI Apertus 70B encountered 403, 504/Retry-After, observed-name aliases,
  truncated completions and invalid structured output. A tiny schema probe passed
  while real extraction failed. No general 70B quality improvement was established.
- Checkpoints retain valid completed responses; incomplete or structurally invalid
  outputs must not become accepted knowledge. Preserve requested/observed identity.
- Groq extraction failed on missing fields, invalid evidence IDs and non-exact
  condition excerpts. Structural validity alone missed inferred scope and omitted
  claims. Separate claim, scope, completeness and coverage reviews are essential.
- Model review once emitted duplicate JSON keys. Another review accepted missing
  details or misassigned authority roles. Bigger reviewers do not establish truth.
- English/German evidence must retain differences: annual and time-limited permit
  categories were not silently treated as verified equivalents. Assistant repairs
  and translated projections remain explicitly distinguished from model outputs.
- Original Groq ranking used inconsistent numeric scales (0-1, 0-5, 0-10). A 0.5
  cutoff admitted missing-information queries. The v2 rubric uses integer grades
  0 unrelated, 1 topic association, 2 partial answer, 3 direct complete answer.
  The pilot accepts only grade 3; relevance never creates published support.
- Ranking-only self-employment emitted string `"0"` instead of an integer and
  failed schema validation. A separate format-repair experiment passed, but was
  not counted as an unmodified v2 result. The final runtime attempt passed without
  repair; all earlier failures remain in the chronology.
- Groq TPM limits caused 429 responses, even where individual requests were fast.
  Later runs used 35-second pacing, no automatic retries, and persisted completed
  checks. Pacing is not a guarantee. The first frontier runtime failure has no
  retained cause; its later successful attempt cannot establish a cause.
- The runtime initially converted errors into its correct public operational
  contract while local logs lost the underlying cause. The diagnostic helper now
  records failure type/status and opt-in bounded provider details before conversion.
- One German query exceeded the 120-character runtime limit. The shortened
  `de-notification-short` variant preserves annual allowance and reporting authority,
  has its own recorded identity, and is not an unchanged ranking-query replay.
- Ling initially inferred that empty evidence meant the source had no facts,
  labelled the query as a source excerpt, and claimed a comparison for a skipped
  evidence read. Guided instructions now require explicit None/Not applicable,
  source-only quotations and synthetic approval qualification. Final checks passed;
  unguided caller reliability remains unqualified.

## Frozen corpus and results

Pilot root: `.local/live-retrieval-20260907-161418/` (Git ignored).

Raw crawl contains eight pages: SEM residence DE/EN/FR/IT and Zurich EU/EFTA,
family, non-employment and third-country employment. The serving corpus selected
for database migration comprises SEM DE/EN and the Zurich EU/EFTA page. Other raw
pages are archived, not silently promoted into serving evidence.

| Release folder | Serving content | File SHA-256 |
| --- | --- | --- |
| `sem-answer-relevance-20260908-182238-130324` | 2 normalized documents, 6 excerpts, 30 draft projections, 6 vectors | `c5b8ece8a347ad75cf06f27f37045a0c7a71dbee5ab745c3226750f23e242046` |
| `zh-runtime-harness-20260908-190309-949650` | 1 normalized document, 12 excerpts, 60 draft projections, 12 vectors | `e822e48737c661cf87ddd2a910c4ad79b5a52addd3e9f2b1c4b3bcc0af40ac6c` |

Zurich packet: `zh-ranking-packet-20260908-183716-424632/packet.json`, hash
`87e4a0b11a0eb503ba377b71ba78a9d2cfd363b78a99808ada0984912eddb209`.
The saved raw Zurich HTML hash is
`b2da0b36fe559eda757496393c8e9db616cf7444fd796e14a8a8e030b458f1f4`.
All evidence offsets refer to retained normalized Unicode text, not raw HTML bytes.
Historical external references are declarations, not proof that every referenced
snapshot/review artifact has been validated. Database migration preserves these
limitations rather than rewriting hashes to imply stronger provenance.

Zurich embedding file: the packet folder's
`embeddings-20260908-185929-413480/embeddings.json`, hash
`03dc9aefda06cf9b550185fdcda32bcdcda4457ba8f3f73b1e50a7c6610a1c54`.
It has 12 document and 10 query vectors. Six positive targets were within top 3;
only three were top 1. Preserve candidate breadth before ranking. Embedding
similarity alone does not establish answerability.

The authoritative consolidated local result is the Zurich harness's
`runtime-checkpoint-audit.json`: per-result and summary hashes, the retained
frontier failure, query variant, and direct-runtime/MCP distinctions. Final cases:

| Query | Expected evidence |
| --- | --- |
| en-move | zh-e002 |
| de-notification-short | zh-e003 |
| en-short-stay | zh-e004 |
| de-residence | zh-e005 |
| en-frontier | zh-e006 |
| de-self-employed | zh-e007 |
| en-fee, de-processing, en-appointment, de-partial | None |

Final subset `abstention-20260908-193315-943134` passed in 107.251s including
pacing. Guided caller final negative run: `opencode-check-20260908-191822-333507`;
positive: `opencode-check-20260908-192057-083269`. The positive caller displayed
an abridged quote; retained fragments matched, and both MCP evidence objects
matched the full source object exactly.

## Reuse and next boundaries

Database setup/migration/smoke commands live in [storage operations](../storage.md).
Keep source hashes, release IDs, provider identities, query variants and failed
attempts when reusing these observations. Database-backed replay smoke tests
prove storage and query integration, not new live model quality.

Remaining work includes source-backed public catalog IDs, typed applicability,
reviewed promotion and projection/language validation, unseen-case evaluation,
unguided caller discovery, genuine release publication, retention and deployment
qualification. Storage adoption does not close those knowledge-quality gates.
