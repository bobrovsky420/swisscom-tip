"""Closed authoring contracts for claim extraction and multidimensional review.

Every structured predicate is a proposal for human review, never executable law.
The validators check shape, references and logical integrity, not entailment.
"""
from __future__ import annotations

import json
import math

VERSION = "swisstip.structured-claims/v1"
POLICY = {"schema_version": "swisstip.extraction-content-policy/v1",
          "include": ["substantive_prose", "conditions", "procedures", "tables", "authority_contacts"],
          "exclude": ["navigation", "heading_only"],
          "human_promotion_required": True}


def obj(properties):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


def string(limit=1200):
    return {"type": "string", "minLength": 1, "maxLength": limit}


def enum(values):
    return {"type": "string", "enum": list(values)}


def array(items, maximum=16, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}


def validate(value, schema, path="response"):
    """Validate the small JSON Schema subset we emit, including strict types."""
    kind = schema["type"]
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list),
               "string": isinstance(value, str), "integer": type(value) is int,
               "number": type(value) in (int, float) and math.isfinite(value) if type(value) in (int, float) else False,
               "boolean": type(value) is bool}
    if not matches[kind]:
        raise ValueError(f"{path}: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: unknown value")
    if kind == "object":
        if set(value) != set(schema["properties"]):
            raise ValueError(f"{path}: missing or unknown fields")
        for key, item in value.items():
            validate(item, schema["properties"][key], f"{path}.{key}")
    elif kind == "array":
        if not schema["minItems"] <= len(value) <= schema["maxItems"]:
            raise ValueError(f"{path}: array bounds exceeded")
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")
    elif kind == "string" and "minLength" in schema:
        if (schema["minLength"] > 0 and not value.strip()) or not schema["minLength"] <= len(value) <= schema["maxLength"]:
            raise ValueError(f"{path}: empty or oversized text")


def decode(content, schema):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON property: {key}")
            result[key] = value
        return result
    value = json.loads(content, object_pairs_hook=unique)
    validate(value, schema)
    return value


def extraction_schema(evidence_ids, max_concepts):
    refs = array(enum(evidence_ids), 12, 1)
    evidenced = obj({"text": string(), "evidence_ids": refs})
    condition = obj({"condition_id": string(40), "text": string(), "evidence_ids": refs,
                     "subject": string(160), "operator": enum(["stated", "eq", "ne", "gt", "gte", "lt", "lte"]),
                     "value": string(160), "unit": string(120), "time_window": string(200)})
    group = obj({"group_id": string(40), "operator": enum(["AND", "OR", "UNRESOLVED"]),
                 "members": array(string(40), 16, 1), "evidence_ids": refs})
    claim = obj({"claim_id": string(40),
                 "kind": enum(["fact", "requirement", "permission", "prohibition", "procedure"]),
                 "statement": string(), "evidence_ids": refs,
                 "scope": obj({field: string(240) for field in (
                     "population", "jurisdiction", "permit_status", "actor", "recipient", "procedure_branch")}),
                 "scope_evidence_ids": refs,
                 "conditions": array(condition), "condition_groups": array(group),
                 "condition_root": {"type": "string", "maxLength": 40, "minLength": 0},
                 "exceptions": array(evidenced, 8), "limitations": array(string(800), 8)})
    return obj({"concepts": array(obj({"label": string(200),
                 "concept_type": enum(["ENTITY", "PROCESS", "RULE", "SERVICE", "DOCUMENT", "OTHER"]),
                 "primary_section_id": string(80), "claims": array(claim, 8, 1),
                 "questions": array(string(400), 3), "limitations": array(string(800), 8)}), max_concepts),
                "saturated": {"type": "boolean"}})


def evidence_references(concept):
    for claim in concept["claims"]:
        yield from claim["evidence_ids"]
        yield from claim["scope_evidence_ids"]
        for field in ("conditions", "condition_groups", "exceptions"):
            for item in claim[field]:
                yield from item["evidence_ids"]


def validate_concept(concept, evidence, sections):
    """Reject cross-group references, dangling logic, cycles and uncited clauses."""
    if concept["primary_section_id"] not in sections:
        raise ValueError("unknown or out-of-scope primary section")
    refs = list(evidence_references(concept))
    if any(ref not in evidence for ref in refs):
        raise ValueError("unknown or out-of-scope evidence reference")
    if isinstance(sections, dict) and any(sections[evidence[ref]["section_id"]] != sections[concept["primary_section_id"]] for ref in refs):
        raise ValueError("evidence crosses unrelated source ownership groups")
    if not any(evidence[ref]["section_id"] == concept["primary_section_id"] for ref in refs):
        raise ValueError("primary section has no supporting evidence")
    ids = [c["claim_id"] for c in concept["claims"]]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate claim IDs")
    for claim in concept["claims"]:
        conditions = {c["condition_id"]: c for c in claim["conditions"]}
        groups = {g["group_id"]: g for g in claim["condition_groups"]}
        if len(conditions) != len(claim["conditions"]) or len(groups) != len(claim["condition_groups"]) or set(conditions) & set(groups):
            raise ValueError("duplicate condition/group IDs")
        nodes = set(conditions) | set(groups)
        root = claim["condition_root"]
        if bool(nodes) != bool(root) or (root and root not in nodes):
            raise ValueError("conditions require a valid explicit root")
        visited = set()

        def visit(identity, active):
            if identity in active or identity not in nodes:
                raise ValueError("cyclic or dangling condition logic")
            if identity in visited:
                raise ValueError("repeated condition subtree; use a bounded logical tree")
            visited.add(identity)
            if identity in groups:
                members = groups[identity]["members"]
                if len(members) != len(set(members)):
                    raise ValueError("duplicate logical operands")
                for member in members:
                    visit(member, active | {identity})

        if root:
            visit(root, set())
        if visited != nodes:
            raise ValueError("unconnected conditions or groups")
        if any(g["operator"] == "UNRESOLVED" for g in groups.values()) and not claim["limitations"]:
            raise ValueError("unresolved logic requires an explicit limitation")
        for condition in conditions.values():
            if condition["operator"] in {"gt", "gte", "lt", "lte"}:
                try:
                    number = float(condition["value"])
                except ValueError:
                    raise ValueError("numeric comparison requires a finite numeric value") from None
                if not math.isfinite(number):
                    raise ValueError("numeric comparison requires a finite numeric value")
            # The original condition must be visible verbatim, separately from
            # the proposed machine interpretation (which still needs review).
            if not any(condition["text"] in evidence[ref]["text"] for ref in condition["evidence_ids"]):
                raise ValueError("condition text must be an exact source excerpt")


ASSESSMENT = obj({"decision": enum(["supported", "unsupported", "uncertain"]), "reason": string(500)})


def review_schema(concepts, block_ids):
    indices = {"type": "integer", **({"enum": list(range(len(concepts)))} if concepts else {})}
    return obj({"concept_reviews": array(obj({
        "concept_index": indices,
        "claim_support": array(obj({"claim_id": string(40), **ASSESSMENT["properties"]}), 8),
        "scope": ASSESSMENT, "completeness": ASSESSMENT,
        "questions": array(obj({"question_index": {"type": "integer"}, **ASSESSMENT["properties"]}), 3),
    }), len(concepts), len(concepts)),
        "block_coverage": array(obj({"section_id": enum(block_ids),
            "decision": enum(["covered", "partial", "missing", "uncertain", "not_substantive"]),
            "concept_indices": array(indices, len(concepts)),
            "reason": string(500)}), len(block_ids), len(block_ids))})


def parse_review(content, concepts, block_ids):
    result = decode(content, review_schema(concepts, block_ids))
    reviews = result["concept_reviews"]
    if {r["concept_index"] for r in reviews} != set(range(len(concepts))):
        raise ValueError("review must assess every concept exactly once")
    for review in reviews:
        concept = concepts[review["concept_index"]]
        expected = {c["claim_id"] for c in concept["claims"]}
        if len(review["claim_support"]) != len(expected) or {c["claim_id"] for c in review["claim_support"]} != expected:
            raise ValueError("review must assess every claim exactly once")
        if len(review["questions"]) != len(concept["questions"]) or {q["question_index"] for q in review["questions"]} != set(range(len(concept["questions"]))):
            raise ValueError("review must assess every question exactly once")
    if {r["section_id"] for r in result["block_coverage"]} != set(block_ids):
        raise ValueError("coverage review must account for every source block")
    for coverage in result["block_coverage"]:
        if len(set(coverage["concept_indices"])) != len(coverage["concept_indices"]):
            raise ValueError("duplicate coverage concept reference")
        if coverage["decision"] in {"covered", "partial"} and not coverage["concept_indices"]:
            raise ValueError("represented coverage requires a concept reference")
        if coverage["decision"] in {"missing", "not_substantive"} and coverage["concept_indices"]:
            raise ValueError("unrepresented coverage cannot reference concepts")
    return result


def review_passes(review):
    return all(item["decision"] == "supported" for item in
               [*review["claim_support"], review["scope"], review["completeness"], *review["questions"]])


def describe(concept):
    """Render authoring prose from the same connected claims sent for review."""
    parts = []
    for claim in concept["claims"]:
        conditions = {c["condition_id"]: c["text"] for c in claim["conditions"]}
        groups = {g["group_id"]: g for g in claim["condition_groups"]}

        def render(identity):
            if identity in conditions:
                return conditions[identity]
            group = groups[identity]
            return "(" + f" {group['operator']} ".join(render(m) for m in group["members"]) + ")"

        parts.append(claim["statement"])
        if claim["condition_root"]:
            parts.append(render(claim["condition_root"]))
        parts.extend(item["text"] for item in claim["exceptions"])
        parts.extend(claim["limitations"])
    parts.extend(concept["limitations"])
    return "\n".join(parts)
