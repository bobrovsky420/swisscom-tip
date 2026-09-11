"""Mock SwissTIP residence MCP server with hardcoded content for one knowledge fact.

The server speaks MCP over stdio and advertises three tools shaped like the real
SwissTIP server (get_coverage, resolve, get_evidence). Every answer comes from
the constants in this file. It never reads the repository knowledge base, a
database or the network. Diagnostics go to stderr; stdout carries the protocol.

Covered fact: EU/EFTA nationals taking up employment in Switzerland must register
with their municipality within 14 days of arrival and before starting work. The
resolve result deliberately tells the calling LLM which user facts are still
missing (arrival date, first working day) and how to decide which of the two
limits binds. The decision itself is left to the calling LLM.
"""

import asyncio
import json
import logging
import sys

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

SERVER_NAME = "swisstip-mock"
SERVER_VERSION = "0.1.0"
RELEASE_ID = "mock-residence-registration-2026-09-11"
TOPIC_ID = "immigration/residence"
CONCEPT_ID = "eu-efta-municipal-registration-after-arrival"
RETRIEVED_ON = "2026-09-11"
MOCK_NOTE = ("Mock server: hardcoded content for this one concept, taken from official "
             "pages saved on 2026-09-11. It is not the SwissTIP knowledge base and "
             "not legal advice.")

EVIDENCE = {
    "e-sem-faq-en": {
        "source_title": "SEM - FAQ: EU/EFTA citizens in Switzerland (English)",
        "publisher": "State Secretariat for Migration SEM",
        "language": "en",
        "original_excerpt": (
            "Within 14 days of their arrival and before actually taking up work, nationals of "
            "EU/EFTA states have to register with the local authorities of the commune in which "
            "they are residing and apply for a residence permit. A valid ID or passport and a "
            "written confirmation of employment (e.g. the contract of employment containing "
            "details of the duration of employment and the number of working hours) have to be "
            "presented."),
        "url": "https://www.sem.admin.ch/sem/en/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html",
    },
    "e-sem-faq-de": {
        "source_title": "SEM - FAQ: EU/EFTA-Buergerinnen und -Buerger in der Schweiz (Deutsch)",
        "publisher": "Staatssekretariat fuer Migration SEM",
        "language": "de",
        "original_excerpt": (
            "Innert 14 Tagen nach ihrer Ankunft in der Schweiz und vor Stellenantritt, muessen "
            "sich die Buergerinnen und Buerger der EU/EFTA bei ihrer Wohngemeinde anmelden und "
            "eine Aufenthaltsbewilligung beantragen."),
        "url": "https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html",
    },
    "e-aig-art12": {
        "source_title": "AIG (SR 142.20) Art. 12 Anmeldepflicht",
        "publisher": "Fedlex - Swiss federal law",
        "language": "de",
        "original_excerpt": (
            "Art. 12 Anmeldepflicht. 1 Auslaenderinnen und Auslaender, die eine Kurzaufenthalts-, "
            "Aufenthalts- oder Niederlassungsbewilligung benoetigen, muessen sich vor Ablauf des "
            "bewilligungsfreien Aufenthalts oder vor der Aufnahme einer Erwerbstaetigkeit bei der "
            "am Wohnort in der Schweiz zustaendigen Behoerde anmelden. [...] 3 Der Bundesrat "
            "bestimmt die Anmeldefristen."),
        "url": "https://www.fedlex.admin.ch/eli/cc/2007/758/de",
    },
    "e-vzae-art10": {
        "source_title": "VZAE (SR 142.201) Art. 10 Aufenthalt mit Anmeldung",
        "publisher": "Fedlex - Swiss federal law",
        "language": "de",
        "original_excerpt": (
            "Art. 10 Aufenthalt mit Anmeldung. 1 Zur Regelung des Aufenthalts muessen sich "
            "Auslaenderinnen und Auslaender innerhalb von 14 Tagen nach der Einreise bei der "
            "durch den Kanton bezeichneten Stelle anmelden [...]"),
        "url": "https://www.fedlex.admin.ch/eli/cc/2007/759/de",
    },
    "e-zh-eu-efta": {
        "source_title": "Kanton Zuerich - Aufenthalt fuer EU/EFTA-Staatsangehoerige",
        "publisher": "Kanton Zuerich, Migrationsamt",
        "language": "de",
        "original_excerpt": (
            "Als EU/EFTA-Angehoerige, die laenger als 90 Tage in der Schweiz arbeiten moechten, "
            "muessen Sie sich innerhalb von 14 Tagen persoenlich bei Ihrer Wohngemeinde anmelden."),
        "url": "https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html",
    },
    "e-zh-weisung-fza": {
        "source_title": "Kanton Zuerich - Weisung Freizuegigkeitsabkommen EU-26, EFTA-Staaten, Ziff. 2.3 und 3.4.4",
        "publisher": "Kanton Zuerich, Migrationsamt",
        "language": "de",
        "original_excerpt": (
            "Betreffend Anmeldung bei der fuer den Wohnort zustaendigen Einwohnerkontrolle gelten "
            "die in Art. 12 AIG sowie in den Art. 9, 10, 12, 13, 15 und 16 VZAE vorgesehenen "
            "Verpflichtungen und Fristen. [...] Die Taetigkeit kann nach der persoenlichen "
            "Anmeldung und Gesuchseinreichung bei der Einwohnerkontrolle aufgenommen werden."),
        "url": "https://www.zh.ch/content/dam/zhweb/bilder-dokumente/themen/migration-integration/einreise-aufenthalt/weisungen/Freiz%C3%BCgigkeitsabkommen%20EU-26,%20EFTA-Staaten_IW.pdf",
    },
    "e-stadt-zh-zuzug": {
        "source_title": "Stadt Zuerich - Zuzug anmelden",
        "publisher": "Stadt Zuerich, Personenmeldeamt",
        "language": "de",
        "original_excerpt": (
            "Sie muessen sich innerhalb von 14 Tagen bei der Stadt Zuerich anmelden (Meldepflicht). "
            "Eine Anmeldung ist erst ab dem effektiven Einzug moeglich. [...] Fuer die Anmeldung "
            "aus dem Ausland muessen Sie einen Termin vereinbaren. Die Anmeldung findet "
            "persoenlich beim Personenmeldeamt Zuerich Sued statt."),
        "url": "https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html",
    },
    "e-sem-factsheet-short-term": {
        "source_title": "SEM factsheet - Residence permits for EU/EFTA nationals (English)",
        "publisher": "State Secretariat for Migration SEM",
        "language": "en",
        "original_excerpt": (
            "Employment of up to three months per calendar year does not require a residence "
            "permit; such employment requires the electronic notification of short-term stays. "
            "The employer has to submit an online notification form no later than the day before "
            "starting work."),
        "url": "https://www.sem.admin.ch/dam/sem/en/data/eu/fza/personenfreizuegigkeit/factsheets/fs-bew-aufenthalt.pdf.download.pdf/fs-bew-aufenthalt.pdf",
    },
}

CONTEXT_SCHEMA = {
    "nationality_group": {
        "type": "string", "enum": ["EU_EFTA", "THIRD_COUNTRY"],
        "description": "EU_EFTA for citizens of an EU or EFTA state (for example Czech, German, "
                       "Norwegian), otherwise THIRD_COUNTRY.",
    },
    "purpose": {
        "type": "string",
        "enum": ["EMPLOYMENT", "SELF_EMPLOYMENT", "NO_EMPLOYMENT", "FAMILY_REUNIFICATION"],
        "description": "Main purpose of the stay in Switzerland.",
    },
    "employment_duration": {
        "type": "string", "enum": ["UP_TO_3_MONTHS", "MORE_THAN_3_MONTHS", "UNKNOWN"],
        "description": "Contract length. Jobs of up to three months per calendar year follow a "
                       "different notification procedure.",
    },
    "canton_code": {
        "type": "string",
        "description": "ISO 3166-2 code of the canton of residence, for example CH-ZH for Zurich.",
    },
}

COVERAGE = {
    "release_id": RELEASE_ID,
    "knowledge_space": "hackathon",
    "topics": [{
        "topic_id": TOPIC_ID,
        "title": "Residence in Switzerland: registration, permits and deadlines after arrival",
        "jurisdictions": ["CH", "CH-ZH"],
        "concepts": [{
            "concept_id": CONCEPT_ID,
            "title": "Registration with the municipality of residence after arriving in Switzerland "
                     "(EU/EFTA nationals taking up employment): deadline and order of steps",
            "answers_questions_like": [
                "By when must I register my stay with the municipal authority?",
                "I start work in Zurich soon. When do I have to register at the Kreisbuero?",
                "Is the 14-day registration deadline counted from arrival or from the first working day?",
            ],
            "jurisdictions": ["CH", "CH-ZH"],
            "context_schema": CONTEXT_SCHEMA,
            "required_context": ["nationality_group", "purpose"],
        }],
    }],
    "limitations": [MOCK_NOTE],
}

TOOLS = [
    types.Tool(
        name="get_coverage",
        description=(
            "Discover the Swiss immigration and residence topics covered by the SwissTIP trusted "
            "information service: concept IDs, jurisdictions and the context fields each concept "
            "needs. Call this before answering any question about registering a stay, residence or "
            "work permits, or deadlines after moving to Switzerland, then call resolve with a "
            "concept_id."),
        inputSchema={
            "type": "object",
            "properties": {"parent_id": {
                "type": "string",
                "description": "Optional topic ID whose concepts should be listed; omit for the top level.",
            }},
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False),
    ),
    types.Tool(
        name="resolve",
        description=(
            "Return authoritative facts, evidence citations, the user facts that are still needed "
            "and a decision rule for one concept, given the user's situation (nationality group, "
            "purpose of stay, canton, employment duration). Returns status NEEDS_CONTEXT with the "
            "missing fields when the situation is incomplete. It does not generate an answer; the "
            "caller composes the answer from the returned facts and must collect the listed user "
            "facts before computing any date."),
        inputSchema={
            "type": "object",
            "required": ["concept_id"],
            "properties": {
                "concept_id": {"type": "string", "description": "Concept ID from get_coverage."},
                **CONTEXT_SCHEMA,
            },
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False),
    ),
    types.Tool(
        name="get_evidence",
        description=(
            "Read the original source excerpts and citation URLs for up to five evidence IDs "
            "returned by resolve."),
        inputSchema={
            "type": "object",
            "required": ["evidence_ids"],
            "properties": {"evidence_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5,
                "description": "Evidence IDs exactly as returned by resolve.",
            }},
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False),
    ),
]


def citation(evidence_id):
    item = EVIDENCE[evidence_id]
    return {"evidence_id": evidence_id, "source_title": item["source_title"],
            "url": item["url"], "language": item["language"], "retrieved_on": RETRIEVED_ON}


def evidence_object(evidence_id):
    return {"evidence_id": evidence_id, **EVIDENCE[evidence_id],
            "citation": {"url": EVIDENCE[evidence_id]["url"], "retrieved_on": RETRIEVED_ON}}


def error(code, path, message):
    return {"error": {"code": code, "issues": [{"path": path, "message": message}]}}, True


def get_coverage(arguments):
    parent = arguments.get("parent_id")
    if parent not in (None, TOPIC_ID, "hackathon"):
        return error("INVALID_ARGUMENT", "parent_id", f"Unknown parent_id {parent!r}; use {TOPIC_ID!r} or omit it."), True
    return COVERAGE, False


def resolve(arguments):
    concept = arguments.get("concept_id")
    if concept != CONCEPT_ID:
        return error("INVALID_ARGUMENT", "concept_id",
                     f"Unknown concept_id {concept!r}. Call get_coverage and use {CONCEPT_ID!r}.")
    missing = [{"field": field, "options": CONTEXT_SCHEMA[field]["enum"],
                "hint": CONTEXT_SCHEMA[field]["description"]}
               for field in ("nationality_group", "purpose") if not arguments.get(field)]
    if missing:
        return {
            "release_id": RELEASE_ID, "concept_id": CONCEPT_ID, "status": "NEEDS_CONTEXT",
            "missing_context": missing,
            "guidance_for_caller": (
                "Derive the missing fields from what the user already said (for example a Czech "
                "citizen is EU_EFTA and 'starting my work' is EMPLOYMENT) and call resolve again. "
                "Ask the user only for fields that cannot be derived."),
            "limitations": [MOCK_NOTE],
        }, False
    nationality = arguments.get("nationality_group")
    purpose = arguments.get("purpose")
    duration = arguments.get("employment_duration") or "UNKNOWN"
    canton = arguments.get("canton_code")
    if nationality != "EU_EFTA" or purpose != "EMPLOYMENT":
        return {
            "release_id": RELEASE_ID, "concept_id": CONCEPT_ID, "status": "OUT_OF_COVERAGE",
            "applicability": {"nationality_group": nationality, "purpose": purpose},
            "reason": ("This mock release only covers EU/EFTA nationals taking up employment. "
                       "Do not answer other situations from this service; say that the service "
                       "has no coverage for them."),
            "limitations": [MOCK_NOTE],
        }, False
    if duration == "UP_TO_3_MONTHS":
        return {
            "release_id": RELEASE_ID, "concept_id": CONCEPT_ID, "status": "SUPPORTED",
            "applicability": {"nationality_group": nationality, "purpose": purpose,
                              "employment_duration": duration, "jurisdiction": "CH (federal rule)"},
            "facts": [{
                "fact_id": "f-short-term-notification",
                "statement": ("For employment of up to three months per calendar year, EU/EFTA "
                              "nationals need no residence permit. Instead the employer must "
                              "notify the job online no later than the day before work starts."),
                "evidence_ids": ["e-sem-factsheet-short-term"],
            }],
            "required_user_facts": [{
                "name": "first_working_day",
                "instruction": "Confirm the first working day; the employer's notification must be "
                               "submitted at the latest on the day before it.",
            }],
            "decision_rule": {
                "description": "The employer's online notification is due no later than the day "
                               "before the first working day. No 14-day municipal deadline applies "
                               "for stays of up to three months without taking residence.",
            },
            "citations": [citation("e-sem-factsheet-short-term")],
            "limitations": [MOCK_NOTE],
        }, False
    zurich = canton == "CH-ZH"
    facts = [
        {"fact_id": "f-14-days-and-before-work",
         "statement": ("EU/EFTA nationals taking up employment in Switzerland for more than three "
                       "months must register in person with the municipality of residence and "
                       "apply for a residence permit within 14 days of their arrival in "
                       "Switzerland AND before taking up work. Both limits apply at the same time."),
         "evidence_ids": ["e-sem-faq-en", "e-sem-faq-de", "e-aig-art12"]},
        {"fact_id": "f-period-starts-at-arrival",
         "statement": ("The 14-day period starts on the day of arrival in Switzerland (moving in), "
                       "not on the first working day. The first working day does not define the "
                       "arrival date."),
         "evidence_ids": ["e-sem-faq-en", "e-vzae-art10"]},
        {"fact_id": "f-register-before-work",
         "statement": ("Work may only be taken up after the personal registration and the "
                       "submission of the residence application at the residents' registration "
                       "office. Registration therefore has to be completed before the first "
                       "working day, even if fewer than 14 days have passed since arrival."),
         "evidence_ids": ["e-aig-art12", "e-zh-weisung-fza"]},
        {"fact_id": "f-documents",
         "statement": ("Bring a valid identity card or passport and the employer's written "
                       "confirmation of employment (for example the employment contract stating "
                       "duration and working hours)."),
         "evidence_ids": ["e-sem-faq-en"]},
    ]
    if zurich:
        facts.extend([
            {"fact_id": "f-zh-canton-14-days",
             "statement": ("The canton of Zurich instructs EU/EFTA nationals who will work longer "
                           "than 90 days to register in person with their municipality within 14 "
                           "days."),
             "evidence_ids": ["e-zh-eu-efta"]},
            {"fact_id": "f-zh-city-appointment",
             "statement": ("In the City of Zurich, registration is possible only from the actual "
                           "move-in date, and registration after arriving from abroad requires a "
                           "booked appointment at the Personenmeldeamt (in person)."),
             "evidence_ids": ["e-stadt-zh-zuzug"]},
        ])
    evidence_ids = []
    for fact in facts:
        for item in fact["evidence_ids"]:
            if item not in evidence_ids:
                evidence_ids.append(item)
    return {
        "release_id": RELEASE_ID, "concept_id": CONCEPT_ID, "status": "SUPPORTED",
        "applicability": {
            "nationality_group": nationality, "purpose": purpose,
            "employment_duration": duration,
            "jurisdiction": "CH (federal rule)" + (", with City of Zurich details" if zurich
                                                  else "; cantonal and municipal details omitted "
                                                       "because canton_code is not CH-ZH"),
        },
        "facts": facts,
        "required_user_facts": [
            {"name": "arrival_date", "status": "NOT_PROVIDED_BY_SERVICE",
             "instruction": ("Ask the user for the date on which they arrive (or arrived) in "
                             "Switzerland. Never assume the arrival date equals the first working "
                             "day; people usually arrive earlier. Without the arrival date the "
                             "14-day limit cannot be computed.")},
            {"name": "first_working_day", "status": "NOT_PROVIDED_BY_SERVICE",
             "instruction": "Confirm the exact first working day; registration must be completed before it."},
            {"name": "employment_duration", "status": duration,
             "instruction": ("If unknown, confirm that the contract exceeds three months; otherwise "
                             "the short-term notification procedure applies instead of this rule.")},
        ],
        "decision_rule": {
            "description": ("The binding deadline is the EARLIER of two limits: (A) 14 days after "
                            "the arrival date and (B) before the first working day."),
            "steps": [
                "1. Obtain arrival_date and first_working_day from the user; do not guess them.",
                "2. Compute limit A = arrival_date + 14 days.",
                "3. Limit B = registration completed before the first working day, i.e. at the latest "
                "on the last working day of the office before the first working day.",
                "4. If limit B falls before limit A, tell the user to register before the first "
                "working day and name that date. Otherwise tell the user to register within 14 days "
                "of arrival and name the date of limit A.",
                "5. State both limits so the user understands which one binds, and note that "
                "registration is only possible after the actual move-in.",
            ],
        },
        "citations": [citation(item) for item in evidence_ids],
        "limitations": [MOCK_NOTE, "Office opening hours and appointment availability are not covered."],
    }, False


def get_evidence(arguments):
    ids = arguments.get("evidence_ids")
    if not isinstance(ids, list) or not ids:
        return error("INVALID_ARGUMENT", "evidence_ids", "Provide a non-empty list of evidence IDs.")
    if len(ids) > 5:
        return error("INVALID_ARGUMENT", "evidence_ids", "At most five evidence IDs per call.")
    unknown = [item for item in ids if item not in EVIDENCE]
    if unknown:
        return error("INVALID_ARGUMENT", "evidence_ids", f"Unknown evidence IDs: {unknown}.")
    return {"release_id": RELEASE_ID, "evidence": [evidence_object(item) for item in ids],
            "limitations": [MOCK_NOTE]}, False


HANDLERS = {"get_coverage": get_coverage, "resolve": resolve, "get_evidence": get_evidence}


def create_server():
    server = Server(SERVER_NAME, version=SERVER_VERSION)

    @server.list_tools()
    async def list_tools():
        return TOOLS

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        arguments = arguments or {}
        logging.getLogger(SERVER_NAME).info("call %s %s", name, json.dumps(arguments, ensure_ascii=True))
        handler = HANDLERS.get(name)
        if handler is None:
            result, is_error = error("INVALID_ARGUMENT", "name", f"Unknown tool {name!r}.")
        else:
            result, is_error = handler(arguments)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))],
            structuredContent=result, isError=is_error)

    return server


async def serve():
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    asyncio.run(serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
