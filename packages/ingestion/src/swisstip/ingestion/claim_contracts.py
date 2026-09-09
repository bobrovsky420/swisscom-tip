"""Closed authoring contracts for claim extraction and multidimensional review.

Every structured predicate is a proposal for human review, never executable law.
The validators check shape, references and logical integrity, not entailment.
"""
from __future__ import annotations

import json
import math

VERSION = "swisstip.structured-claims/v1"
REVIEW_VERSION = "swisstip.structured-review/v2"
SCOPE_FIELDS = ("population", "jurisdiction", "permit_status", "actor", "recipient", "procedure_branch")
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
            missing = sorted(set(schema["properties"]) - set(value))
            unknown = sorted(set(value) - set(schema["properties"]))
            # Field names can originate in model output. Bound diagnostic size.
            def names(items):
                return repr([name[:120] for name in items[:12]]) + (" (more omitted)" if len(items) > 12 else "")
            raise ValueError(f"{path}: missing or unknown fields; missing={names(missing)}; unknown={names(unknown)}")
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


def _decode_json(content):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON property: {key}")
            result[key] = value
        return result
    return json.loads(content, object_pairs_hook=unique)


def decode(content, schema):
    value = _decode_json(content)
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
                 "scope": obj({field: string(240) for field in SCOPE_FIELDS}),
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


class ConceptValidationError(ValueError):
    """All independently checkable issues in a schema-valid proposal."""

    def __init__(self, errors):
        self.errors = errors
        # Preserve the first-error summary for existing report consumers.
        super().__init__(errors[0]["reason"])


def _condition_tree_errors(claim, path):
    errors = []
    def add(field, reason, **details):
        errors.append({"path": f"{path}.{field}", "reason": reason, **details})

    conditions = {c["condition_id"]: c for c in claim["conditions"]}
    groups = {g["group_id"]: g for g in claim["condition_groups"]}
    duplicate_ids = (len(conditions) != len(claim["conditions"])
                     or len(groups) != len(claim["condition_groups"]) or set(conditions) & set(groups))
    if duplicate_ids:
        add("conditions", "duplicate condition/group IDs")
    nodes = set(conditions) | set(groups)
    root = claim["condition_root"]
    root_valid = bool(nodes) == bool(root) and (not root or root in nodes)
    if not root_valid:
        add("condition_root", "conditions require a valid explicit root",
            hint="Use a defined condition_id or group_id as the root. Put AND/OR on a defined group with members, not in the root as an operator.")
    if any(g["operator"] == "UNRESOLVED" for g in groups.values()) and not claim["limitations"]:
        add("limitations", "unresolved logic requires an explicit limitation")
    # Duplicate IDs make graph traversal ambiguous; clause checks still run.
    if duplicate_ids:
        return errors

    incoming = {}
    for index, group in enumerate(claim["condition_groups"]):
        members = group["members"]
        field = f"condition_groups[{index}].members"
        if len(members) != len(set(members)):
            add(field, "duplicate logical operands")
        if any(member not in nodes for member in members):
            add(field, "cyclic or dangling condition logic")
        for member in dict.fromkeys(members):
            if member in incoming:
                add(field, "repeated condition subtree; use a bounded logical tree")
                break
        for member in members:
            incoming[member] = True

    # Inspect every component, including when the root itself is invalid.
    states = {}
    group_indices = {g["group_id"]: i for i, g in enumerate(claim["condition_groups"])}
    def visit(identity):
        states[identity] = "active"
        if identity in groups:
            for member in groups[identity]["members"]:
                if member not in nodes:
                    continue
                if states.get(member) == "active":
                    add(f"condition_groups[{group_indices[identity]}].members", "cyclic or dangling condition logic")
                elif member not in states:
                    visit(member)
        states[identity] = "complete"
    for identity in [*conditions, *groups]:
        if identity not in states:
            visit(identity)

    if root_valid and root:
        visited, pending = set(), [root]
        while pending:
            identity = pending.pop()
            if identity in visited or identity not in nodes:
                continue
            visited.add(identity)
            if identity in groups:
                pending.extend(groups[identity]["members"])
        if visited != nodes:
            add("condition_root", "unconnected conditions or groups")
    return errors


def validate_concept(concept, evidence, sections):
    """Collect independent reference, tree and clause errors after schema validation.

    An invalid root must not hide bad quotations or errors in later claims.
    No source text or proposed logic is corrected by this validator.
    """
    errors = []
    def add(path, reason):
        errors.append({"path": path, "reason": reason})

    primary = concept["primary_section_id"]
    if primary not in sections:
        add("primary_section_id", "unknown or out-of-scope primary section")
    refs = list(evidence_references(concept))
    known_refs = [ref for ref in refs if ref in evidence]
    if len(known_refs) != len(refs):
        add("claims", "unknown or out-of-scope evidence reference")
    if primary in sections and isinstance(sections, dict) and any(
            sections[evidence[ref]["section_id"]] != sections[primary] for ref in known_refs):
        add("claims", "evidence crosses unrelated source ownership groups")
    if primary in sections and not any(evidence[ref]["section_id"] == primary for ref in known_refs):
        add("primary_section_id", "primary section has no supporting evidence")
    ids = [c["claim_id"] for c in concept["claims"]]
    if len(set(ids)) != len(ids):
        add("claims", "duplicate claim IDs")
    for index, claim in enumerate(concept["claims"]):
        path = f"claims[{index}]"
        errors.extend(_condition_tree_errors(claim, path))
        for condition_index, condition in enumerate(claim["conditions"]):
            field = f"{path}.conditions[{condition_index}]"
            if condition["operator"] in {"gt", "gte", "lt", "lte"}:
                try:
                    finite = math.isfinite(float(condition["value"]))
                except ValueError:
                    finite = False
                if not finite:
                    add(f"{field}.value", "numeric comparison requires a finite numeric value")
            available = [ref for ref in condition["evidence_ids"] if ref in evidence]
            if available and not any(condition["text"] in evidence[ref]["text"] for ref in available):
                add(f"{field}.text", "condition text must be an exact source excerpt")
    if errors:
        raise ConceptValidationError(errors)


ASSESSMENT = obj({"decision": enum(["supported", "unsupported", "uncertain"]), "reason": string(500)})


def review_schema(concepts, block_ids):
    indices = {"type": "integer", **({"enum": list(range(len(concepts)))} if concepts else {})}
    claim_assessment = obj({"claim_id": string(40), **ASSESSMENT["properties"],
        "condition_logic": obj({
            "source_applicability": enum(["conditional", "unconditional", "uncertain"]),
            **ASSESSMENT["properties"]}),
        "scope_fields": obj({field: ASSESSMENT for field in SCOPE_FIELDS})})
    return obj({"schema_version": enum([REVIEW_VERSION]), "concept_reviews": array(obj({
        "concept_index": indices,
        "claim_support": array(claim_assessment, 8),
        "scope": ASSESSMENT, "completeness": ASSESSMENT,
        "questions": array(obj({"question_index": {"type": "integer"}, **ASSESSMENT["properties"]}), 3),
    }), len(concepts), len(concepts)),
        "block_coverage": array(obj({"section_id": enum(block_ids),
            "decision": enum(["covered", "partial", "missing", "uncertain", "not_substantive"]),
            "concept_indices": array(indices, len(concepts)),
            "reason": string(500)}), len(block_ids), len(block_ids))})


def _normalize_review_nesting(result, schema):
    """Relocate one observed JSON nesting error without changing assessments.

    Some JSON-object providers put the complete scope_fields object inside
    condition_logic. Move that existing object only when the two claim objects
    otherwise have exactly their expected keys. Conflicting sibling/nested
    assessments and other shape errors remain invalid. Full validation follows.
    """
    changes = []
    if not isinstance(result, dict) or not isinstance(result.get("concept_reviews"), list):
        return changes
    claim_schema = schema["properties"]["concept_reviews"]["items"]["properties"]["claim_support"]["items"]
    expected_claim_keys = set(claim_schema["properties"]) - {"scope_fields"}
    expected_logic_keys = set(claim_schema["properties"]["condition_logic"]["properties"]) | {"scope_fields"}
    for review_index, review in enumerate(result["concept_reviews"]):
        if not isinstance(review, dict) or not isinstance(review.get("claim_support"), list):
            continue
        for claim_index, claim in enumerate(review["claim_support"]):
            if not isinstance(claim, dict) or set(claim) != expected_claim_keys:
                continue
            logic = claim["condition_logic"]
            if not isinstance(logic, dict) or set(logic) != expected_logic_keys:
                continue
            path = f"response.concept_reviews[{review_index}].claim_support[{claim_index}]"
            claim["scope_fields"] = logic.pop("scope_fields")
            changes.append({"from": f"{path}.condition_logic.scope_fields", "to": f"{path}.scope_fields"})
    return changes


def parse_review(content, concepts, block_ids, *, normalizations=None):
    schema = review_schema(concepts, block_ids)
    result = _decode_json(content)
    changes = _normalize_review_nesting(result, schema)
    validate(result, schema)
    reviews = result["concept_reviews"]
    if {r["concept_index"] for r in reviews} != set(range(len(concepts))):
        raise ValueError("review must assess every concept exactly once")
    for review in reviews:
        concept = concepts[review["concept_index"]]
        expected = {c["claim_id"] for c in concept["claims"]}
        if len(review["claim_support"]) != len(expected) or {c["claim_id"] for c in review["claim_support"]} != expected:
            raise ValueError("review must assess every claim exactly once")
        claims = {c["claim_id"]: c for c in concept["claims"]}
        for assessment in review["claim_support"]:
            logic = assessment["condition_logic"]
            if logic["decision"] != "supported":
                continue
            claim = claims[assessment["claim_id"]]
            applicability = logic["source_applicability"]
            prefix = f"concept {review['concept_index']}, claim {claim['claim_id']}: "
            if applicability == "uncertain":
                raise ValueError(prefix + "uncertain source applicability cannot have supported condition logic")
            if applicability == "conditional" and not claim["conditions"]:
                raise ValueError(prefix + "conditional source rule cannot have supported condition logic with empty conditions")
            if applicability == "unconditional" and (claim["conditions"] or claim["condition_groups"] or claim["condition_root"]):
                raise ValueError(prefix + "unconditional source assertion cannot have supported added conditions")
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
    if normalizations is not None:
        normalizations.extend(changes)
    return result


def review_passes(review):
    # Detailed failures cannot be hidden by a supported statement or summary.
    # These are model assessments, not deterministic source entailment checks.
    assessments = [review["scope"], review["completeness"], *review["questions"]]
    for claim in review["claim_support"]:
        if "condition_logic" not in claim or "scope_fields" not in claim:
            return False
        if set(claim["scope_fields"]) != set(SCOPE_FIELDS):
            return False
        assessments.extend([claim, claim["condition_logic"], *claim["scope_fields"].values()])
    return all(item["decision"] == "supported" for item in assessments)


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
