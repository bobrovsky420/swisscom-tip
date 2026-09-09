# Model configuration

Model identities and provider connections are defined once in
[model-profiles.toml](model-profiles.toml). The role files select and configure
their use:

| File | Settings | Current selection |
| --- | --- | --- |
| [semantic-models.toml](semantic-models.toml) | Extraction/review profile, prompts, generation, limits and recovery | `apertus_70b`, `concept_extraction_v4` |
| [retrieval-models.toml](retrieval-models.toml) | Embedding and ranking profiles, timeouts and scoring contracts | `qwen_embedding_0_6b`, `apertus_ranking_8b` |

For example, the shared local Apertus definition is:

```toml
# model-profiles.toml
schema_version = "swisstip.model-profiles/v1"

[profiles.apertus_8b_ollama]
adapter = "ollama"
model = "MichelRosselli/apertus:8b-instruct-2509-q4_k_m"
base_url = "http://127.0.0.1:11434"
```

Both role files declare `model_profiles_file = "model-profiles.toml"` at the
top level, alongside their own `schema_version`. Each role profile names a
catalog entry with `model_profile`:

```toml
# semantic-models.toml
[profiles.ollama_local]
model_profile = "apertus_8b_ollama"
timeout_seconds = 180.0
num_ctx = 8192
keep_alive = "5m"
```

```toml
# retrieval-models.toml
[profiles.apertus_ranking_8b]
model_profile = "apertus_8b_ollama"
role = "ranking"
timeout_seconds = 60.0
```

Change a role's `active_profile` to select another configured profile. To add a
model, define its adapter, model ID, endpoint and any provider/credential
references in the catalog, then add a referring profile with the options required
by that role's adapter. The catalog does not add adapter capabilities: extraction
supports Ollama, Hugging Face, Groq and DeepSeek; retrieval supports Ollama, Groq and
DeepSeek. Local
Ollama Apertus and hosted Hugging Face Apertus have separate catalog entries.

Multiple profiles can refer to one model with different settings. For example,
both 70B extraction response modes share `apertus_70b`, and both Groq 20B scoring
contracts share `groq_gpt_oss_20b`. Timeouts, response modes, scoring contracts,
context and keep-alive settings remain in the role files. Referring profiles
cannot override catalog identity fields (`adapter`, `model`, `base_url`,
`provider`, `token_env`, `bill_to`); create another catalog entry for a different
connection. Store only credential environment variable names, never token values.

The catalog path resolves relative to the role file, independently of the current
working directory. When moving a role file, copy its catalog with the same relative
layout or adjust `model_profiles_file`. Unknown references and invalid settings
fail loading; there is no model fallback. Prompt override paths still resolve
relative to the semantic configuration, not the catalog.

Existing standalone configurations with inline adapter/model fields remain valid.
GUI jobs save all resolved model definitions inline, the selected profile, absolute
prompt override paths and disabled provider retries. They can run from their job
directory without the catalog, and later catalog edits do not change saved jobs.

The command-line flags remain `--config config/semantic-models.toml` for extraction
and `--provider-config config/retrieval-models.toml` for retrieval. OpenCode's chat
model is configured separately. Retrieval releases still pin model and adapter
identities and require a matching embedding index; configuration changes do not
replace those release artifacts.

## DeepSeek V4 Pro

The optional `deepseek_v4_pro` profile is available in both role files and in the
GUI's extraction profile selector. Both refer to the same direct API connection
in the catalog, with model `deepseek-v4-pro` and base URL
`https://api.deepseek.com`. The existing active selections are unchanged.

Set `DEEPSEEK_API_KEY` in the environment of the CLI, MCP server or GUI launcher;
no key is stored in TOML or sent to the browser. In a Unix-style shell:

```shell
export DEEPSEEK_API_KEY='your-key'
./.venv/Scripts/python.exe scripts/admin/run.py
```

On PowerShell, set `$env:DEEPSEEK_API_KEY = 'your-key'` before launching. Restart
an already running GUI to inherit the new key, then select `deepseek_v4_pro`.
For CLI extraction, set `[semantic_model].active_profile = "deepseek_v4_pro"`;
for ranking, set `[ranking].active_profile = "deepseek_v4_pro"` independently.
Embedding remains a separate Ollama profile. Do not select DeepSeek for embedding.

The adapter uses the documented [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
with `response_format = {"type": "json_object"}` and explicitly disabled thinking.
The trusted schema is included in the system prompt; DeepSeek's [JSON mode](https://api-docs.deepseek.com/guides/json_mode/)
does not enforce that schema. Extraction and review retain local schema, evidence
and coverage checks. Ranking validates exact candidate membership and finite
numeric scores. Mismatched model identities, empty content, duplicate JSON keys
and incomplete completions are rejected without accepting partial results.

Extraction uses the configured generation limit (currently 4096 output tokens)
and a 180-second timeout. Ranking uses 8192 output tokens and a 60-second timeout.
Thinking mode is fixed off in this adapter; enabling it later requires evaluating
the changed generation contract and checkpoint/release identity. CLI extraction
uses bounded transient retries and checkpoints; GUI provider retries stay disabled.
Runtime ranking makes one attempt, subject to the release's declared fallback.

A retrieval release using this profile must pin `deepseek-ranking/v1` and
`deepseek-v4-pro`. The existing pilot release is not migrated by changing this
selection. Protocol support is covered by offline tests; live model quality and
provider availability have not been qualified by those tests.

## GPT-OSS extraction through Groq

The optional `groq_gpt_oss_120b` extraction profile shares its model definition
with retrieval and requires `GROQ_API_KEY`. It uses `openai/gpt-oss-120b`, low
reasoning effort, `max_completion_tokens` and
[strict JSON schema output](https://console.groq.com/docs/structured-outputs).
Local evidence, condition logic, scope and coverage checks still apply. The
adapter requires an exact returned model identity and a complete response.

Select this profile independently in the GUI or semantic configuration. Account
rate limits also apply to extraction and review calls. The
[comparison runner](../scripts/test/model_comparison/README.md) loads the current
keys and spaces Groq calls 60 seconds apart by default, recording this wait
separately from API time. This pacing belongs to the comparison script; ordinary
CLI and GUI jobs retain their existing bounded recovery settings.
