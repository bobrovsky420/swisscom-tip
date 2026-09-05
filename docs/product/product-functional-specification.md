# Swisscom Trusted Information Platform
## Product & Functional Specification - V18

**Hackathon:** Swiss Grounding MCP using selected `admin.ch` / SEM and `zh.ch` sources<br>
**Primary deliverable:** Testable MCP server<br>
**Example MCP client:** OpenCode<br>
**Structured demo:** Swiss Arrival Checklist<br>
**Stretch demo:** Swiss Hike with clearly labelled mock data<br>
**Preferred semantic model:** Apertus, with a model-independent core<br>
**Technical design:** [`technical-specification.md`](../architecture/technical-specification.md)

---

# 1. Summary

The Trusted Information Platform (TIP) turns authoritative knowledge, live data, private context and services into trustworthy structured Information Products for applications and AI agents.

> **AI is infrastructure, not the interface.**

TIP is the target product. The hackathon delivers a narrow vertical slice of it: a working MCP server for focused Swiss public information. That slice builds a versioned knowledge release from selected official sources, resolves requests across declared query and source languages, returns compact evidence with citations, distinguishes jurisdiction and applicability, reports freshness and explicitly declines unsupported questions.

Verified cross-language grounding across a predefined, closed Swiss language catalog is a key TIP differentiator. Within a release's evaluated profile, a user can ask in one supported query language, retrieve authoritative evidence published in another declared source language and receive the result in a supported response language while citations remain linked to original-language evidence. TIP is not a general-purpose translator and provides no standalone translation capability. A provider's capabilities, model training coverage or deployment configuration cannot add a language to the product catalog or an active release.

The vertical slice is not a throwaway demonstration or the complete definition of the product. It is designed to validate the foundation for structured applications, private and enterprise knowledge, automated Knowledge CI/CD, and a publisher Data Product marketplace. Delivery discipline and product ambition are therefore treated as complementary horizons.

---

# 2. Product Vision and Strategic Hypothesis

**Decision class: Team product hypothesis**

TIP is envisioned as trusted-information infrastructure between authoritative data providers and the applications, workflows and AI agents that need reliable, governed and application-ready information.

## Target users and value

| User or customer | Need | TIP value |
|---|---|---|
| AI assistants and application teams | Reliable Swiss and domain-specific answers across supported languages | Verified cross-language grounding, compact evidence, citations, context and structured results without client-side translation for declared combinations |
| Enterprises and regulated teams | Governed external and internal knowledge | Versioning, provenance, applicability, auditability and private overlays |
| Authorities and data publishers | Reusable machine-consumption channel | Maintained Data Products, declared coverage and distribution |
| Swisscom | Reusable trusted-information platform | Hosting, integration, sovereign AI consumption and future commercial services |

## Target-product capabilities

1. **Trusted supply:** onboard authoritative sources, datasets and live capabilities.
2. **Knowledge lifecycle:** version, evaluate, refresh and publish governed knowledge releases.
3. **Product composition:** combine Knowledge Spaces, Data Products, rules, capabilities and optional AI into Information Products.
4. **Verified cross-language grounding:** resolve supported queries against authoritative evidence across declared source languages and render results in supported response languages while preserving original-language citations.
5. **Distribution:** serve agents, applications and workflows through MCP, REST and future SDKs.
6. **Governance:** enforce provenance, coverage, trust, licensing and entitlements.
7. **Economics:** support usage attribution, commercial models, billing and publisher settlement where appropriate.

## Closed language catalog and release profiles

TIP applies language support at two governed levels:

1. The **product language catalog** is a closed, versioned allowlist of exact language tags, accepted aliases, dialect or idiom profiles, role eligibility and routing rules approved by product governance. The initial `tip-language-catalog/v1` catalog permits the client query tags `en`, `de`, `de-CH`, `de-DE`, `fr-CH`, `it-CH`, `gsw`, `gsw-CH` and `rm-CH`. It also defines bare `fr`, `it` and `rm` as detector-only aliases for the corresponding Swiss profiles; they are not accepted client query tags or source-declaration aliases. The catalog permits the exact tags `en`, `de-CH`, `fr-CH`, `it-CH` and `rm-CH` for response, source and metadata-projection roles. The v1 source-declaration alias set is empty. Source support is still declared independently by registered authoritative sources and the active release; it is not inferred from query or response support.
2. An **active release language profile**, represented technically by an immutable `LanguagePolicy`, is an evaluated, referentially closed subset of that catalog. It declares the exact supported tags, mixed-query profile combinations and query/response/source combinations for the release's sources, concepts and jurisdictions. Every enabled alias, detector or source mapping, query-to-projection route, response default, fixed response and allowed combination must resolve entirely to role-specific tags enabled by that release. Every published release enables `en` for query and response roles, evaluates the `en` query-to-`en` response route, publishes an otherwise equivalent English-query/English-response counterpart for every natural-language coverage profile and advertises `fallback_query_language=en`. This mandatory fallback baseline does not imply English source coverage. An Information Product may declare a default response language only when that language is enabled for the product's applicable coverage profiles. Publication fails if any reference points outside the enabled subset. A tag being present in the product catalog does not by itself claim that every release, dialect, idiom, source or language combination supports it. Each Knowledge Release references the exact catalog and policy versions that governed its build and evaluation.

The language roles are independent and must be declared separately:

| Role | Product meaning |
|---|---|
| Query language | A language or accepted input profile in which TIP can interpret a request. Input-only variants may route to another projection and response language. |
| Response language | A language in which TIP may generate optional prose and derivative user-facing fields. |
| Source language | The original language of authoritative evidence admitted by a registered source and the active release. It is never implied by the query or response language. |
| Projection language | A standard language used for compact derived retrieval metadata. A projection is a candidate-retrieval aid, not evidence. |

Neither provider metadata, model training coverage, runtime language detection nor operator configuration can expand either governed level. Adding a language requires an explicit product-catalog version change, implementation support, evaluation criteria and release-gating tests before a release may enable it. The catalog exists to support verified Swiss information retrieval, not open-ended translation.

The product hypothesis is that Swisscom can provide the trusted infrastructure and distribution layer while authorities, enterprises and other publishers remain responsible for their canonical information. Government information may remain free while managed hosting, service levels, inference, enterprise overlays and derived Information Products create business value.

---

# 3. Hackathon Validation Outcome

**Published challenge requirement:** deliver an accessible, reproducible and testable Swiss-grounding MCP server.

**Team validation thesis:** a focused implementation can prove both immediate grounding quality and foundational capabilities of the larger TIP product, including verified cross-language grounding within a finite, release-gated Swiss language profile.

The primary outcome is a GitHub repository that Swisscom can access, start and test with its evaluation harness and standards-compatible MCP clients.

| Validation level | Definition of success |
|---|---|
| Hackathon proof | A focused MCP server performs well on grounding, coverage, efficiency, operability and integration readiness |
| Product validation | The same implementation demonstrates reusable source, evidence, release, trust and distribution concepts that can evolve into the target product |

| Hackathon capability | Target-product hypothesis it validates |
|---|---|
| SEM and `zh.ch` source registry | Repeatable authority, publisher and source onboarding |
| Immutable snapshots and releases | Governed knowledge lifecycle and auditability |
| Evidence and Trust Envelope | Trusted, explainable Information Products |
| Closed release language profile and cross-language retrieval | Verified multilingual access without turning TIP into a general-purpose translator |
| MCP server | Reusable agent distribution channel |
| Arrival Checklist | Structured Information Product composition |
| Provider abstractions | Composition of external datasets and live capabilities |
| Refresh and evaluation | Future Knowledge CI/CD |
| Provenance and dependency records | Future governance, entitlement, usage attribution and settlement |

The solution must demonstrate:

- correct use of authoritative Swiss sources;
- jurisdiction-aware and temporally valid evidence;
- precise citation support;
- verified cross-language retrieval for the predefined language combinations enabled by the active release, with original-language evidence preserved;
- honest unsupported, insufficient and conflicting states;
- useful declared coverage;
- efficient tool selection and compact responses;
- reproducible setup, refresh and caching behaviour;
- resilience, monitoring, source etiquette and maintainability;
- a coherent, extensible MCP contract.

OpenCode is one supported example and test client. It is not a required or privileged integration, and the server must not rely on OpenCode-specific behaviour.

---

# 4. Product Model

## Knowledge Space

An internal, compiled body of knowledge containing sources, snapshots, evidence, concepts, versions, coverage and tests. Examples include `swiss-public`, `emir-core` and `finma`.

## Data Product

A distributable publisher artifact containing knowledge, datasets and/or capabilities together with coverage, license, entitlement and commercial metadata. Examples include `Swiss Public Official`, `Swiss Hiking Routes Pro` and `SIX Market Data`.

## Information Product

An application capability combining typed inputs, Knowledge Spaces or Data Products, live capabilities, deterministic rules, optional AI and typed output. Examples include `swiss-arrival-checklist`, `swiss-hike-finder` and `emir-applicability`.

```text
Publisher Data Products ─┐
Live Capabilities ───────┼→ Information Product → Any Application
Private Knowledge ───────┘
```

---

# 5. Core Principles

1. Stable authoritative information is prepared before request time.
2. Inherently live information uses registered capabilities.
3. External publishers remain the canonical authorities.
4. Deterministic logic handles deterministic problems.
5. Semantic models handle semantic uncertainty only where they add value.
6. Apertus is preferred for relevant semantic tasks, while the core remains compatible with other providers.
7. Cross-language retrieval is a server capability; clients are not required to translate or expand requests.
8. Concept extraction may propose structure, but evidence and evaluation determine what is published.
9. Broad concepts support navigation; answerable concepts support grounded resolution.
10. Search returns evidence, not unsupported answers.
11. Runtime normally uses a small set of high-quality evidence.
12. Structured output precedes optional prose.
13. Original-language evidence remains authoritative; full source content is not machine-translated for retrieval.
14. Compact retrieval metadata is projected only into the standard languages enabled by the active release from the product catalog; generic German, German (Germany) and Swiss German inputs use tested terminology and normalize to Swiss Standard German.
15. Translations are labelled derivative content.
16. Every result carries a Trust Envelope.
17. MCP is the primary hackathon interface, not the entire product architecture.
18. Publisher licensing and entitlements are full-product concerns.
19. Marketplace features and autonomous refresh are post-MVP.

---

# 6. Information Classes

| Class | Example | Functional strategy |
|---|---|---|
| AUTHORITATIVE | Residence rules | Compiled Knowledge Space |
| LIVE | Train fare or weather | Live Capability |
| PRIVATE | Lease or company policy | Private Knowledge Space |
| CONSENSUS | Recommended places | Recommendation data |
| DERIVED | Best hike tomorrow | Data, capabilities and constraints |
| HISTORICAL | Rule in 2024 | Versioned knowledge release |

---

# 7. Hackathon Scenario and Coverage

Primary scenario:

> **I am an EU/EFTA national moving to Canton Zurich for a job. What do I need to do after arriving?**

```text
Swiss Confederation → SEM / federal context
                           ↓
                    Canton Zurich
                           ↓
              declared local limitations
```

The demo tests authority, federal/cantonal applicability, citations, unsupported handling, multilingual queries and efficient retrieval. Its query-language matrix includes English (`en`), generic German (`de`), Swiss Standard German (`de-CH`), German (Germany) (`de-DE`), French (`fr-CH`), Italian (`it-CH`), Swiss German (`gsw` and `gsw-CH`) and Romansh (`rm-CH`) against the source languages declared by the active release. Generic German, German (Germany) and Swiss German are input-only query variants whose generated response prose is always Swiss Standard German (`de-CH`); original-language evidence remains unchanged. Exact Swiss German dialect and Romansh idiom coverage is reported rather than implied.

The solution deliberately begins with selected `admin.ch` / SEM and `zh.ch` material. It does not claim complete Swiss, cantonal or municipal coverage. Exact sources, topics, languages, jurisdictions, exclusions and last refresh are exposed through the product and documented in the repository.

---

# 8. Hackathon Scope and Priority

## P0 - Published challenge outcome

- working MCP server in an accessible GitHub repository;
- clear setup, client configuration, coverage and limitations documentation;
- useful, declared authoritative Swiss coverage;
- grounded retrieval and exact citation support;
- compact responses designed for efficient agent use;
- explicit unsupported, insufficient, conflicting and stale states;
- reproducible refresh, caching, resilience and monitoring behaviour;
- compatibility with the Swisscom harness and standard MCP clients;
- safe secret and test-access handling.

## P0 - Team MVP choices

- focused `admin.ch` / SEM and `zh.ch` coverage;
- operator-triggered, on-demand knowledge builds;
- traceable source versions and immutable published releases;
- a versioned, closed product language catalog and an immutable release-specific profile for evaluated query, response, source and projection roles;
- normalized evidence with source-language, authority, jurisdiction, applicability and temporal metadata;
- a reviewed seed concept graph and multilingual terminology for the principal scenario;
- post-normalization candidate concept extraction and corpus-level aggregation;
- compact retrieval metadata projections for English (`en`), Swiss Standard German (`de-CH`), French (`fr-CH`), Italian (`it-CH`) and Romansh (`rm-CH`);
- tested generic German and German (Germany) terminology plus Swiss German dialect aliases, normalized to Swiss Standard German retrieval terms;
- language-aware lexical, canonical-concept and multilingual vector retrieval;
- automated grounding, citation, multilingual retrieval, efficiency, freshness and integration tests;
- compact Trust Envelopes and high-level resolution calls.

Cross-language retrieval is a P0 functional requirement for the language combinations and concepts declared by the active release. Curated terminology and canonical-concept lookup provide the reproducible baseline. Semantic enrichment, multilingual embeddings and reranking are used only when they improve measured results. Apertus is the preferred semantic provider, while vector retrieval uses a separately evaluated multilingual embedding provider; either provider may be replaced without changing the platform's functional contracts.

## P1 - Product-validation extensions

- Admin Control Plane for sources, builds, evidence, tests and releases;
- REST access to the same published release;
- Swiss Arrival Checklist using typed inputs and outputs.

## P2 - Product-composition stretch

- Flutter Swiss Hike client;
- 10-20 clearly labelled `DEMO/MOCK` routes;
- mock transport, weather and places providers;
- deterministic filters and optional preference ranking.

## Target-product capabilities not implemented during the hackathon

```text
scheduler / periodic watcher
incremental build and promotion
autonomous Knowledge CI/CD
publisher self-service onboarding
marketplace discovery UI
pricing / billing / metering / settlement
publisher payouts
production entitlement engine
real SBB / weather / places integrations
```

These capabilities remain part of the target-product vision and influence current contracts and architectural boundaries. Their implementation is excluded from the hackathon vertical slice. The absence of a scheduler does not remove the requirement for an observable on-demand refresh, cache policy, freshness metadata and stale-result handling.

---

# 9. Knowledge Build Behaviour

An operator can initiate **Build / Full Reload** for the configured sources.

The product must:

1. show which sources are included;
2. discover website language variants within the configured crawl scope, acquire eligible variants and preserve source versions;
3. normalize relevant source content;
4. detect and record the language of each normalized document and evidence object;
5. extract candidate concepts and document-to-concept assignments from normalized sections;
6. aggregate candidates across documents, sources and languages;
7. merge synonyms and translations, create broader/narrower/related relationships, and apply the configured granularity policy;
8. promote only reviewed or automatically verified concepts into the published concept graph;
9. derive evidence and optional candidate facts while preserving original-language text;
10. build compact localized retrieval metadata from official parallel content or labelled machine translation;
11. build language-aware lexical, canonical-concept and multilingual vector representations;
12. evaluate the candidate release against its declared concept and cross-language matrices;
13. publish it only if the evaluation gate passes;
14. preserve the last successful release if a build fails;
15. expose build progress, failures and freshness.

Normal MCP requests use the published release and do not scrape government sites at request time.

### Website language discovery

Website language discovery is a P0 acquisition requirement. Given a configured website root such as `https://admin.ch/`, the builder must inspect the root and subsequently fetched pages for language selectors and alternate-language links, inspect permitted sitemaps, and add discovered eligible language entry URLs to the crawl. An operator must not need to supply a separate seed URL for every language exposed through supported discovery mechanisms. A redirect to one default language must not restrict discovery to that language.

The builder must:

- discover variants from HTML and HTTP `hreflang` links, language-selector links or URL-valued options in returned HTML, and sitemap alternate-language entries; record page-language declarations and redirect observations as supporting hints;
- retain the discovered URL, advertised language and discovery provenance, and distinguish advertised languages from languages verified in fetched content;
- crawl discovered variants admitted by the configured URL scope, source-language declarations and candidate release policy, subject to robots rules, rate limits and shared crawl budgets; discovered subdomains require explicit scope permission;
- preserve language-specific URLs, including meaningful query parameters, and treat alternate-language links as candidate relationships until content and version validation establishes an eligible parallel version;
- report discovered, fetched, validated, excluded, failed and unresolved variants with reasons, plus incomplete discovery caused by crawl limits or inaccessible mechanisms; absence of discovered alternatives must not be reported as proof that a site is monolingual;
- use a configured source adapter for selectors that require JavaScript or cookies when available; otherwise report an observed unresolved selector as requiring an adapter and allow explicit language entry URLs. Automatic browser interaction is not required for P0, and discovery coverage must state this limitation.

Discovery does not add languages to the product catalog, source declaration or release policy. Website labels such as `de` or `fr` are untrusted discovery hints, not valid source declarations or proof of a regional language profile. Admission and content-language validation follow the existing governed language rules. An advertised language alone does not establish published coverage.

For the root-scan acceptance scenario, a fixture representing a multilingual government website redirects to a default-language page whose selector exposes German, French and Italian URLs. With those source languages and paths enabled and sufficient crawl budget, all three variants must be discovered and fetched without separate language seeds. The report must identify any excluded or unreachable variant. A missing required variant blocks publication; optional gaps are reported and excluded from claimed coverage. This fixture defines behavior without assuming the current structure or complete coverage of the live `admin.ch` website.

## 9.1 Concept Compilation and Granularity

Concept extraction occurs during the knowledge build after crawling, snapshotting, normalization and language detection. It is not part of source acquisition. This separation allows extraction to be retried, evaluated or rerun with another provider without fetching the source again.

The published representation is a language-neutral, versioned concept graph rather than a flat keyword list or a strict single-parent tree. A document or evidence object may be assigned to several concepts, and concepts may have `BROADER`, `NARROWER`, `RELATED` and `SAME_AS` relationships.

The granularity model is:

| Level | Purpose | Examples |
|---|---|---|
| Domain | Top-level coverage and navigation | Immigration, Health, Housing |
| Topic or journey | Broad request routing | Residence, Healthcare access |
| Answerable concept | Independent action, obligation or question with its own evidence | Residence permit, Municipal registration, Health insurance |
| Detail | A subtype, deadline, exemption or other precise fact | Permit B, Registration deadline, Insurance exemption |

`ANSWERABLE` is the default grounding level. Broad domain and topic concepts organize coverage and expand broad requests into relevant descendants; they are not sufficient by themselves to support a factual answer.

A candidate becomes a separate answerable concept when one or more of the following differs: required user action, responsible authority, applicability, deadline, legal effect, required documents, authoritative source or independently meaningful user question. Translations, synonyms, abbreviations, spelling variants and dialect variants of the same administrative or legal object are merged as terminology for one concept. For the Swiss residence-permit concept, for example, `Aufenthaltsbewilligung` is the preferred `de-CH` term and `Aufenthaltserlaubnis` can be a reviewed `de-DE` query alias only when it semantically names the Swiss permit being sought or required. This is a concept- and semantic-role-scoped mapping, not a global word replacement: a foreign permit or status mentioned as an existing entity remains distinct even when the request also has Swiss intent.

For example, `Residence` is a broad topic. `Residence permit`, `Municipal registration`, `Change of address` and `Deregistration` are separate answerable concepts. Municipal conduct rules may be related to living in a municipality but are not automatically children of `Residence permit`. Likewise, `Health` is a domain while `Health insurance`, `Healthcare access`, `Emergency care` and `Public health` are separate concepts.

Concept governance states are:

```text
CURATED             producer/admin defined and reviewed
VERIFIED_AUTOMATIC  extracted automatically and accepted by configured validation
CANDIDATE           unverified; usable only as a soft retrieval signal
MERGED              redirected to another stable concept identifier
DEPRECATED          retained for compatibility and audit history
REJECTED            excluded with recorded rationale
```

The Knowledge Space producer owns the seed graph, granularity policy and P0 concepts. An administrator or delegated reviewer approves changes to curated concepts. Apertus may propose candidate concepts, terminology, translations, assignments and relationships, but model output does not automatically become declared coverage. During the hackathon, reviewed concepts may be maintained as repository configuration; authoring and review through the Admin Control Plane is a P1 capability. In the target product, publishers own their domain concept packs subject to platform validation and governance.

Every concept and assignment records provenance, evidence references, extraction method, confidence, lifecycle status and version. Concept identifiers remain stable when labels change, and published Knowledge Releases reference the exact concept graph used for indexing and evaluation.

## 9.2 Localized Retrieval Metadata

TIP preserves each normalized section in its original language and does not machine-translate complete source pages as the default retrieval representation. Instead, each included section receives a compact localized projection containing:

```text
title
section headings
keyphrases and terminology
short retrieval synopsis
canonical concept identifiers
named entities and jurisdiction references
```

The default projection languages are English (`en`), German (`de-CH`), French (`fr-CH`), Italian (`it-CH`) and Romansh (`rm-CH`). The Romansh coverage declaration identifies whether `rm-CH` means Rumantsch Grischun and which additional idioms, if any, are evaluated.

For each field whose target language equals its source language, TIP uses the unchanged normalized original and records `ORIGINAL_SAME_LANGUAGE`. For another target language, it prefers an eligible official parallel-language version published by the same authority, then curated terminology, then a machine-generated translation. Every projected field records its method, provider/model where applicable, review status and original content hash. Canonical concept identifiers, authorities, jurisdictions, dates and other structured values are not translated.

Generic German (`de`), German (Germany) (`de-DE`) and Swiss German (`gsw` and `gsw-CH`) are explicitly supported input-only query variants. They do not receive separate metadata projections or output variants. TIP preserves the supplied or detected query tag, uses reviewed standard-language terminology or dialect aliases, and routes all four tags to Swiss Standard German terminology and the `de-CH` projection. Their effective response language is always `de-CH`, so generated prose and translated user-facing fields use `de-CH`; original-language evidence remains unchanged. Coverage lists the accepted German query tags and tested Swiss German dialect forms.

Localized projections are candidate-retrieval aids, not evidence. Results and citations always resolve to the original source section or an official parallel-language source section.

---

# 10. Resolution Behaviour

For a natural-language request, TIP must:

1. identify or request necessary context;
2. constrain evidence by coverage, authority, jurisdiction, applicability and date;
3. retrieve a small, relevant and diverse evidence bundle;
4. apply deterministic rules where appropriate;
5. expose unresolved uncertainty or conflicts;
6. return structured facts, evidence references and Trust Envelope;
7. generate optional prose only after the supported result is established.

Structured applications normally provide the relevant context directly and receive typed results without requiring a chat prompt.

## 10.1 Multilingual Resolution Behaviour

TIP treats query language, requested response language, effective response language and source language as distinct properties.

For a natural-language request, TIP must:

1. accept or detect the query language and preserve the supplied or detected tag;
2. canonicalize BCP 47 casing and apply only the explicitly declared tag aliases;
3. reject an unsupported query language with English query-fallback guidance;
4. preserve and canonicalize an explicitly requested response language before deriving the effective response language;
5. for `de`, `de-DE`, `gsw` and `gsw-CH` queries, reject any explicit response other than `de-CH`, then set the retrieval projection and effective response language to `de-CH`;
6. for other supported queries, validate the requested response language and default the effective response language to the query language when it is absent;
7. map the request to canonical domain concepts and normalize Swiss jurisdiction names;
8. expand resolved concepts using reviewed terminology for languages declared by the active release;
9. search the routed localized metadata projection, with `de`, `de-DE`, `gsw` and `gsw-CH` routed to `de-CH`;
10. retrieve evidence across all declared source languages unless the client explicitly restricts them;
11. combine localized-metadata, original-query lexical, expanded-query lexical, canonical-concept and multilingual vector candidates;
12. establish supported facts from original authoritative evidence;
13. render optional prose and translated user-facing fields in the effective response language only after the supported result is established.

Terminology expansion is a server responsibility. MCP and REST clients are not required to translate a request, supply synonyms or know the source languages for declared combinations. Query language and response language must not act as implicit filters on source language.

The product catalog defines role eligibility, while each active release enables and evaluates an explicit subset. The initial catalog's query-language set is `en`, `de`, `de-CH`, `de-DE`, `fr-CH`, `it-CH`, `gsw`, `gsw-CH` and `rm-CH`; its response-language and projection-language sets are `en`, `de-CH`, `fr-CH`, `it-CH` and `rm-CH`. The hackathon release declares which of those tags and source languages it enables and the exact combinations it has passed. The `de`, `de-DE`, `gsw` and `gsw-CH` tags are input-only and have a fixed effective response language of `de-CH`; an explicitly supplied `response_language` must therefore be `de-CH`. Supplying another response language for one of these fixed-query mappings returns `UNSUPPORTED_LANGUAGE` with `unsupported_component=language_combination`, the supported response languages and `required_response_language=de-CH`. Selecting an input-only tag as the response language for any other query returns `unsupported_component=response_language` and the supported response-language list.

BCP 47 tags are parsed and compared case-insensitively and returned with canonical casing, so `DE-de` becomes `de-DE`. The initial contract uses exact matching after canonicalization rather than accepting every `de-*` or `gsw-*` tag. Bare `gsw` is an explicit application alias for `gsw-CH` in this Swiss Knowledge Space. `de-AT` and every other tag absent from the product catalog remain unsupported; enabling a new variant requires a catalog change followed by release gating. When region cannot be determined reliably, language detection emits `de` for Standard German and the canonical `gsw-CH` profile for detected Swiss German. High-confidence detector output `fr`, `it` or `rm` may use the catalog's detector-only mapping to `fr-CH`, `it-CH` or `rm-CH`; a client that explicitly supplies one of those bare tags still receives `UNSUPPORTED_LANGUAGE`.

The server guarantees direct handling only for language roles and combinations permitted by the product catalog and declared by the active release. When the query language is unsupported, `UNSUPPORTED_LANGUAGE` includes `unsupported_component=query_language` and `fallback_query_language=en`; the client may translate its request to English and resubmit it as `query_language=en`. An unsupported response language returns `unsupported_component=response_language` and the supported response-language list instead. English is not presented as the remedy for an invalid response language, source-language filter or forbidden query-response combination.

Original-language source excerpts and citations remain authoritative. A translated excerpt is derivative content, uses the effective response language, must be labelled as a machine translation, must identify its provider and model version, and must retain a reference to the original excerpt. A translation is never presented as the cited source.

The functional guarantee applies only within the source, topic, jurisdiction, concept and language matrix declared by the active release. Swiss German is treated as a family of input dialects, never as a standardized output language, and Romansh coverage identifies Rumantsch Grischun and any supported idioms explicitly.

TIP exposes no standalone translate operation. Translation may be used only for bounded retrieval metadata or derivative presentation after supported facts have been established, and it never expands the product catalog or the active release's evaluated coverage.

### User-visible language and rendering outcomes

- An empty or whitespace-only question, a malformed supplied BCP 47 tag or an explicitly empty `source_languages` list is rejected before factual resolution with `INVALID_ARGUMENT`, the affected field and correction guidance. A well-formed tag outside the product catalog or not enabled by the active release returns `UNSUPPORTED_LANGUAGE`, the affected component and the relevant supported list. Only an unsupported query language receives `fallback_query_language=en`.
- Numeric-only, acronym-only, very short or otherwise linguistically indeterminate input without a query tag returns `NEEDS_CONTEXT` with the supported query profiles and asks the user or client to identify the language or restate the request. TIP does not silently pivot to English.
- A mixed-language query succeeds when one enabled query profile is the deterministic carrier language and every other-language semantic span belongs to an evaluated mixed-query combination or is a protected span. Protected spans are limited to release-approved terminology, reviewed jurisdictions or entities, exact schema-validated non-free-text structured-context values and neutral literals such as URLs or identifiers. They are preserved and remain available to concept and entity resolution, but they do not change the carrier language or response default. The initial hackathon profile guarantees this protected-span behavior and declares no free-form mixed-query combinations; later releases may enable only explicitly evaluated carrier/secondary-profile sets.
- For example, `How to get Aufenthaltsbewilligung in Zurich?` has effective query language `en`, records `mixed_language=true`, preserves the reviewed `de-CH` term, resolves it to the Swiss residence-permit concept, searches the source languages permitted by the matching coverage profile and defaults to an English response. This behavior also applies when the client explicitly supplies `query_language=en`.
- The active `LanguagePolicy` defines the minimum classifiable content, span confidence, dominant share and runner-up margin used to select the carrier language. Without a supplied tag, failure to select one returns `NEEDS_CONTEXT` with `reason=mixed_query_language`. With a supplied supported tag, a protected term or registered name in another language does not create a mismatch; a threshold-passing incompatible carrier language returns `NEEDS_CONTEXT` with `reason=query_language_mismatch` and does not retrieve evidence.
- If the same protected text has reviewed mappings to different concepts or entities and structured context and coverage cannot resolve them uniquely, TIP returns `NEEDS_CONTEXT` with `reason=ambiguous_protected_span`. It never selects the highest-scoring mapping silently.
- A term-only query uses `PROTECTED_TERM_PROFILE` only when all retained reviewed matches leave exactly one query-enabled profile. Multiple eligible profiles return `NEEDS_CONTEXT`; no query-enabled profile returns `UNSUPPORTED_LANGUAGE` with English whole-query fallback guidance. De-duplicating matches to one concept never discards their language-profile provenance.
- A material free-form span confidently identified as a language outside the active release returns `UNSUPPORTED_LANGUAGE` with `reason=unsupported_embedded_language`. If a supported carrier is known, remediation asks the client to restate only that span in `required_query_language`; it does not redundantly return English fallback guidance for an already-English carrier. If no supported carrier exists, the response asks the client to restate the entire query in `fallback_query_language=en`. A material unresolved span returns `NEEDS_CONTEXT` with `reason=unresolved_embedded_span`. Free-form spans in individually enabled profiles whose combination has not been evaluated return `OUT_OF_COVERAGE` with `reason=unsupported_mixed_query_combination`. TIP never drops, silently translates or guesses the meaning of such a span. The protected-span exception is bounded terminology and entity handling, not universal translation.
- A Swiss German dialect or Romansh idiom is supported only when the active release names and evaluates it. A clearly identified but unevaluated dialect or idiom returns `OUT_OF_COVERAGE` with the evaluated forms and supported standard-language alternatives. If the form cannot be identified reliably, TIP returns `NEEDS_CONTEXT` instead of claiming support.
- Omitting `source_languages` searches across all source languages declared by the active release. An explicit non-empty list is canonicalized and deduplicated. A well-formed catalog-external or release-disabled source-language tag returns `UNSUPPORTED_LANGUAGE` with `unsupported_component=source_languages` and no English query-fallback guidance. A valid filter whose intersection with the applicable release coverage is empty returns `OUT_OF_COVERAGE`; when covered sources exist but yield no sufficient evidence for the request, TIP returns `INSUFFICIENT_VERIFIED_EVIDENCE`. TIP never retries without the requested filter silently.
- If optional response rendering or derivative excerpt translation fails after facts have been established, TIP returns the established structured facts, original-language evidence and citations, omits the failed derivative content and sets `presentation_status=DEGRADED` with a typed warning identifying the missing presentation field. The factual result status remains unchanged, and TIP never silently substitutes another response language.

## 10.2 Concept-Aware Resolution Behaviour

The planner maps a request to the most specific supported concept that preserves the user's meaning.

- A broad request such as `What should I know about residence in Zurich?` expands the `Residence` topic into a bounded and diverse set of answerable descendants, such as permits, municipal registration, address changes and deregistration. The result is grouped by concept and may return `NEEDS_CONTEXT` when a decision requires more detail.
- A narrow request such as `How do I obtain a residence permit?` starts at `Residence permit` and its relevant details. It must not include unrelated municipal topics merely because they share the word `residence`.
- If concept resolution is uncertain, lexical and vector retrieval remain available and the uncertainty is recorded. A missing or incorrect concept assignment must not make an otherwise relevant document undiscoverable.

---

# 11. Result Statuses

```text
SUPPORTED
PARTIALLY_SUPPORTED
NEEDS_CONTEXT
OUT_OF_COVERAGE
INSUFFICIENT_VERIFIED_EVIDENCE
CONFLICTING_EVIDENCE
STALE
UNSUPPORTED_LANGUAGE
```

A nearest semantic match must never be silently presented as applicable truth.

Each result includes enough Trust Envelope information for a client to understand:

- the status;
- the active release and freshness;
- the relevant authority and jurisdiction;
- the supporting evidence and citations;
- any missing context, conflict, limitation or warning.

`UNSUPPORTED_LANGUAGE` identifies `unsupported_component` as `query_language`, `response_language`, `source_languages` or `language_combination`. It applies to well-formed tags that are outside the product catalog or not enabled by the active release; malformed tags are invalid arguments rather than unsupported-language results. For an unsupported embedded language, it also returns `reason=unsupported_embedded_language`, the detected tag and span offsets without echoing or translating the span. An unsupported whole-query language or an embedded case with no supported carrier returns `fallback_query_language=en`; an unsupported embedded span with a supported carrier instead returns `required_query_language` and `remediation=restate_span_in_required_query_language`. An unsupported response returns the supported response languages, an unsupported source filter returns the supported source languages, and a forbidden fixed mapping returns `required_response_language=de-CH`. It does not claim that the topic itself is out of coverage.

`INVALID_ARGUMENT` is a boundary validation error returned before factual resolution, not a factual result status. Presentation is reported independently as `presentation_status=COMPLETE|DEGRADED`; a degraded presentation contains typed warnings while preserving the established factual status.

---

# 12. MCP Capability

The MCP server provides three user-facing capabilities:

1. resolve a Swiss-information request;
2. inspect cited evidence and provenance;
3. inspect declared coverage, limitations and freshness.

A normal supported request, including a cross-language request, should require one high-level resolution call whenever possible. The requesting application supplies the question and optional context or language preferences; the server performs language detection, canonical-concept resolution, terminology expansion and cross-language retrieval. Client-side translation or terminology expansion must not be required for declared languages. For an unsupported query language only, the client may translate the request to English and resubmit it with `query_language=en`; TIP does not provide that translation. Evidence and coverage inspection remain available when the client or evaluator needs more detail.

Exact tool names, schemas, transports and client configuration are defined in the technical specification.

---

# 13. Admin Control Plane

The P1 Admin UI makes platform state inspectable through:

1. Dashboard
2. Knowledge Spaces
3. Source Registry
4. Full-build initiation and progress
5. Source snapshots and freshness
6. Evidence Explorer
7. Concept Registry, candidate review and graph changes
8. Product language catalog, active `LanguagePolicy`, coverage combinations and tested variants
9. Localized metadata projections and language coverage
10. Evaluations
11. Knowledge Releases
12. MCP/REST integration guidance

Its primary operation is **Build / Full Reload**. The Admin UI is not required for MCP runtime availability.

---

# 14. Swiss Arrival Checklist

The P1 structured application accepts:

- nationality group;
- purpose;
- duration;
- canton and municipality, within declared coverage;
- arrival date;
- work start date;
- optional response language from the active release's response-language set, defaulting to the Information Product's declared `en` setting.

It returns typed requirements, deadlines, evidence identifiers, citations, optional localized presentation and a Trust Envelope. It does not require a natural-language prompt or query language, so query detection, query-to-projection routing and fixed query-response mappings are not applicable to this Information Product request. It validates only the optional response language against the product's applicable coverage profiles and otherwise uses the product's publication-validated default. Original-language evidence remains authoritative. The hackathon form chrome may remain English-only, but the response-language selector exposes only languages enabled for the product and does not offer input-only or arbitrary tags.

If municipal information is not included in the published coverage, the result must declare that limitation rather than infer a local requirement.

---

# 15. Swiss Hike Stretch Demo

The P2 Swiss Hike client demonstrates that the same platform can support a different typed Information Product.

Inputs may include origin, date, duration, difficulty, travel limit, scenery, weather and restaurant preferences. Outputs are typed route cards produced from clearly labelled mock routes and provider abstractions.

The demo illustrates composition and deterministic filtering; it does not claim production hiking, transport, weather or places coverage.

---

# 16. Target Product Capability: Knowledge CI/CD

**Decision class: Target-product capability; not implemented during the hackathon**

The full product may add scheduled source watching, cheap change detection, semantic impact analysis, incremental rebuilds, regression tests, and automatic or approval-based release promotion.

This is a strategic extension of the repeatable on-demand build proven during the hackathon, not a two-day deliverable.

---

# 17. Target Product Capability: Publisher and Data Product Marketplace

**Decision class: Target-product capability; not implemented during the hackathon**

TIP may evolve into a multi-sided platform:

```text
Consumers / Apps / Enterprises
             │ consume
             ▼
        Swisscom TIP
 hosting │ trust │ distribution │ metering │ billing
             │
      licensing / settlement
             ▼
Publishers / Data Providers
Government │ Companies │ Experts │ Individuals
```

Future publishers could create Data Products, connect sources, declare coverage and maintenance policy, configure licensing, publish versions and inspect usage or revenue. Public publication may require Swisscom review or certification.

Possible commercial relationships include usage/revenue share, recurring licenses, one-time licenses, publisher SaaS, and free/open public Data Products.

Before consuming a restricted Data Product, TIP would verify entitlement by tenant, application, purpose, geography, redistribution, retention, volume and contract period. Commercial executions could later create usage records for billing, cost attribution and publisher settlement.

Potential trust levels are:

```text
COMMUNITY
VERIFIED
EXPERT_VERIFIED
OFFICIAL
```

Trust level is independent of price.

---

# 18. Swisscom Alignment and Economics

**Decision class: Team product and business hypothesis**

TIP can strengthen myAI, eGovernment services, the Swiss AI Platform, Apertus-based services, banking services and enterprise AI.

Potential value includes API/MCP consumption, SaaS, hosting, managed knowledge, enterprise deployments, regulatory intelligence, inference consumption and future marketplace margin.

Publishers gain a machine-consumption distribution channel without having to build their own AI platform. Free public information can still support paid hosting, service levels, inference and derived Information Products.

---

# 19. Enterprise Reuse

**Decision class: Target-product reuse hypothesis**

For a UBS or Swiss Re context, public Swiss sources can be replaced or augmented by regulatory sources such as EMIR, ESMA, FINMA and DORA, together with governed internal policies and transaction or product context.

The reusable functional concepts are authority, jurisdiction, applicability, evidence, version, freshness, trust and explicit uncertainty. Any enterprise use would require separate governance, security, legal and production-readiness decisions.

---

# 20. Functional Definition of Done

Swisscom can:

- clone and start the repository from clear instructions;
- understand declared coverage and limitations;
- run an on-demand refresh of configured `admin.ch` / SEM and `zh.ch` sources;
- start a configured website scan from its root, discover eligible language variants without separate language seeds, and inspect discovery provenance, exclusions and completeness limits;
- observe source versions, freshness, build outcome and the active release;
- inspect the published concept graph, concept provenance and lifecycle status;
- inspect localized metadata provenance and completeness for each declared language;
- inspect the versioned product language catalog and the active release's role-specific, evaluated language profile;
- connect its evaluation harness or another standard MCP client;
- obtain compact grounded results with exact citations;
- issue an English, generic German, Swiss Standard German, German (Germany), French, Italian, Swiss German or Romansh query for a declared P0 concept and retrieve relevant evidence in another declared source language;
- receive optional prose in the effective response language while retaining original-language evidence and citations, with `de`, `de-DE`, `gsw` and `gsw-CH` queries always rendered in `de-CH`;
- receive `UNSUPPORTED_LANGUAGE` with English query-fallback guidance for an unsupported query language and precise remediation for an unsupported response, source-language filter or language combination;
- receive deterministic clarification or coverage outcomes for ambiguous detection, tag mismatch, unevaluated dialect or idiom forms and explicit source-language filters;
- retain structured facts and original-language evidence with a typed warning if optional supported-language rendering degrades;
- receive a grouped overview for a broad concept and precise evidence for a narrow answerable concept without unrelated topic leakage;
- see explicit unsupported, insufficient, conflicting and stale states;
- reproduce the supplied grounding, multilingual retrieval, efficiency and integration tests.

OpenCode is demonstrated as one compatible client, not treated as a required integration. Apertus is preferred where it adds evaluated value, while the server remains functional with another compatible semantic provider.

P1 completion additionally provides the Admin Control Plane and structured Swiss Arrival Checklist. P2 completion provides the clearly labelled mock Swiss Hike demonstration.

---

# 21. Product Evolution Roadmap

```text
1  Hackathon: focused Swiss public MCP server and on-demand releases
2  production hardening and broader declared Swiss coverage
3  scheduled/incremental Knowledge CI/CD
4  live capabilities and consumer Information Products
5  enterprise/private overlays
6  publisher self-service and Data Product entitlements
7  metering, billing, settlement and marketplace
8  regulatory impact and workflows
```

---

# 22. Final Positioning

> **Apertus is the preferred semantic model; the platform remains model-independent.**<br>
> **TIP provides verified cross-language grounding across a predefined, closed Swiss language catalog; it is not a general-purpose translator.**<br>
> **TIP provides trusted information, context and orchestration while original-language evidence remains authoritative.**<br>
> **Swisscom provides infrastructure, trust, distribution and commercial reach.**

The hackathon vertical slice proves the working Swiss-grounding MCP foundation and tests the concepts on which the target product depends. Its language profile is an evaluated subset of the governed product catalog; no provider, model or runtime configuration may expand it. Structured applications, autonomous Knowledge CI/CD, enterprise overlays and the publisher marketplace are the intended product evolution - not prerequisites for a credible two-day implementation.
