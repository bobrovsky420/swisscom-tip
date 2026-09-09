# Project and pitch review - 2026-09-09

The Swiss Grounding MCP challenge is a credible choice for this team. The project has enough implemented depth to support a strong technical demonstration and a clear connection to the challenge. Winning potential depends most on turning that depth into a simple user experience and demonstrating trustworthy behavior with reviewed evidence. The documentation currently makes the architecture easier to understand than the user benefit.

This review prioritizes documentation, samples the implementation and reruns the runtime and MCP suites. It is not a full code, security or semantic-quality audit. The [one-page pitch](one-page-pitch.md) assumes an internal team audience deciding which challenge to choose. The jury criteria are those supplied by the user; they do not establish weights or allow a reliable winning probability.

**1. Lead with the user problem and the decisive demonstration.**

The [existing selection rationale](../hackathon/ubs-challenge-rationale.md) makes a detailed case for learning, engineering breadth and UBS reuse. Those are team benefits, but they do not directly establish superior functionality, UX or creativity. The [first-round deck](first-round-10min.md) opens with a governed knowledge service and spends much of its time explaining contracts, release machinery and responsibilities. The human question appears on slide 2; the most detailed runtime slide is JSON. Seven slides consume the allocated 8:45 without a separately budgeted live demonstration.

Put the relocation question first, show the evidence-backed experience, then reveal enough implementation to explain why it works. Keep the full schema for Q&A. Reserve a specific live-demo slot by shortening architecture coverage. The one-page pitch maps directly to all five criteria without assigning artificial scores or predicting a win.

**2. The strongest product claims still exceed the real pilot.**

The [pilot handover](../pilots/2026-09-08-retrieval-pilot.md#outcome-and-limits) states that the real-source releases have synthetic catalog IDs, coverage and approval references, and zero published facts or rules. They return excerpts or no evidence, with insufficient verified support. The ten final Zurich observations were accumulated across runs, including one failed attempt followed by a passing rerun; they are not ten independent clean successes. Guided caller checks required corrections. Five-language projections are drafts, not proof of five-language retrieval quality.

The decks do explicitly label themselves intended behavior. Retain that distinction when speaking: call the current result an evidence-retrieval pilot, describe verified applicability as a completion target, and keep source excerpts distinct from approved facts. Avoid "answers any Swiss question," "five languages proven," "hallucination-free," "production-ready" or a general claim of Apertus superiority. The [pilot model decisions and failures](../pilots/2026-09-08-retrieval-pilot.md#model-decisions) support a model-independent story and explain why model review alone is insufficient.

**3. End-user UX is the largest unproven jury criterion.**

The [knowledge studio](../../apps/admin-console/README.md) is implemented and its retained screenshot shows a coherent interface for inspecting source evidence. The saved browser-smoke report records desktop/mobile checks. This is useful operator UX. The [Arrival Checklist](../product/product-functional-specification.md#14-swiss-arrival-checklist) remains a P1 specification, and the pilot does not qualify an unguided assistant's discovery, clarification and final explanation.

Prioritize one caller journey: question, only necessary clarifications, readable evidence/result, source inspection and a clear unsupported state. Include loading and failure behavior. Use the studio briefly to reveal the preparation process. This recommendation does not require moving conversation or answer generation into the MCP server.

**4. Reproducibility has a working baseline and an unfinished delivery path.**

The [MCP README](../../apps/mcp-server/README.md) provides executable synthetic-fixture setup and the actual stdio adapter is exercised by tests. The real pilot corpus and harness are recorded under Git-ignored `.local/` paths. A checkout alone therefore does not reproduce that pilot, and the documented database migration is not a completed portable, reviewed release pipeline. Standard SDK integration also does not establish compatibility with an unavailable Swisscom harness.

Before presenting the prototype as ready for sponsor testing, rehearse setup from a clean checkout, provide the bounded corpus or permitted rebuild procedure, pin the demonstrated release and model profiles, and document credentials, coverage and failure recovery. Provide deterministic replay for the demo where useful, explicitly labeled if it replaces live model calls. Test an unguided standard caller and the sponsor harness when available.

**5. Status drift weakens the credibility of otherwise careful documentation.**

| Location | Observed inconsistency | Recommended correction |
| --- | --- | --- |
| [Root README](../../README.md) | Opening describes a planned MCP server, while later bullets describe its implementation | Open with the implemented runtime, MCP and local studio; immediately state that reviewed publication remains pending |
| [Operations guide, current state](../hackathon/hackathon-operations.md#1-scope-and-current-state) | Says scoped retrieval and MCP are unimplemented and the admin UI is planned | Align with the runtime, studio and September 8 pilot; keep production publication and complete deployment separate |
| [Operations guide](../hackathon/hackathon-operations.md) | Links `../TODO.md` and `architecture/technical-specification.md` resolve incorrectly from `docs/hackathon/` | Use `../../TODO.md` and `../architecture/technical-specification.md` |
| [First-round deck](first-round-10min.md) and [selection rationale](../hackathon/ubs-challenge-rationale.md) | Examples use `swiss_information.get_coverage`, `resolve` and `get_evidence` as namespaced tools | Explain any client display namespace; the server advertises the unprefixed names `get_coverage`, `resolve`, `get_evidence` |
| [Pitch decks](full-presentation.md) | Proposed five-language service and future enterprise product dominate the present proof | Add a short, dated "implemented / demonstrated / remaining" note and use the latest pilot as evidence |

This review records those corrections without rewriting the product requirements or the existing decks. The older challenge URLs in the rationale could not be retrieved during this review. The organizer's [current challenge listing](https://ai-weeks.ch/2026/challenges) was available in indexed form and confirms the Swiss-source grounding problem, sponsor-testable prototype and potential myAI integration. The detailed harness requirements recorded in the repository were not independently revalidated.

**How the opportunity maps to the jury**

| Criterion | Credible strength | What the jury still needs to see |
| --- | --- | --- |
| Technical functionality | Ingestion, strict runtime contracts, scoped hybrid retrieval, MCP, persisted storage and review UI | One connected, repeatable real-source journey, including a failure or missing-context path |
| User experience | Clear evidence-first studio and a relatable relocation use case | A polished caller experience with readable sources, responsive layout and graceful waiting/failure states |
| Skillful AI | Extraction and review experiments, separate embedding/ranking roles, explicit limits on model authority | Correct results on a reviewed slice and a concise example of catching an unsupported answer |
| Uniqueness / creativity / fun | A Swiss multilingual evidence service with visible scope, provenance and explicit gaps | A memorable source reveal and gap-handling demonstration; MCP, RAG and citations alone do not establish novelty |
| Potential / market impact | Reuse across callers and the sponsor's stated possible integration path | One initial customer/use case and a plausible reason to pay for maintained knowledge and integration |

The strongest differentiation is the combination of a Swiss use case, a reusable interface and observable evidence behavior. The [product specification](../product/product-functional-specification.md#product-positioning) correctly recognizes that other search and RAG systems can incorporate governance. Present a valuable implementation and product hypothesis without claiming an exclusive invention or established market demand.

**Recommended demonstration and completion order**

1. Finish a small reviewed SEM/Zurich serving slice, including real catalog/approval provenance and the required five-language metadata validation. Keep the corpus narrow instead of silently dropping accepted P0 requirements.
2. Rehearse "How to get Aufenthaltsbewilligung in Zurich?" through a caller. Establish the intended geography and missing scenario facts, then show the structured request and original cited evidence.
3. Ask for a fee absent from the selected evidence. Say the selected evidence is insufficient; do not imply the official source or authority has no such information. This negative path has a basis in the recorded pilot.
4. Show scope enforcement or missing context using a reviewed case. Label any synthetic fixture used to demonstrate a contract behavior not yet supported by real knowledge.
5. Complete clean setup and caller/harness checks. Add a second consuming application only if this is already reliable; keep marketplace, broad geographic expansion and Swiss Hike out of the main pitch.

**Verification performed**

- `./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -v`: 73 discovered, 67 passed, six PostgreSQL integration tests skipped because `SWISSTIP_TEST_DATABASE_URL` was not set.
- `./.venv/Scripts/python.exe -m unittest discover -s apps/mcp-server/tests -v`: four passed, including real SDK stdio discovery/resolution/evidence checks over fixtures.
- Inspected the MCP adapter, runtime behavior/test cases, current component READMEs, product and architecture documentation, pitch documents, backlog and pilot handover. Viewed the retained studio evidence-screen screenshot and read the saved browser-smoke report; did not rerun the browser or database integration suites.

These checks support the implementation baseline. They do not qualify legal knowledge, live models, independent multilingual quality or production deployment. The jury's qualitative criteria make a compelling demonstration valuable; they do not remove the need for honest claims.
