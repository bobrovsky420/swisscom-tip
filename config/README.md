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
supports Ollama and Hugging Face; retrieval supports Ollama and Groq. Local
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
