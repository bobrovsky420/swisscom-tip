"""Strict contract for a separate, bounded review of proposed claims."""

from __future__ import annotations

import json

from .prompt_templates import load_bundled_prompt

REVIEW_SYSTEM_PROMPT = load_bundled_prompt("concept_review_v3.md")

ISSUES = ["none", "unsupported_claim", "missing_condition", "wrong_scope",
          "wrong_language", "wrong_type", "unanswerable_question", "irrelevant",
          "insufficient_context"]


def review_schema(count: int) -> dict[str, object]:
    return {
        "type": "object", "additionalProperties": False, "required": ["verdicts"],
        "properties": {"verdicts": {
            "type": "array", "minItems": count, "maxItems": count,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["review_id", "decision", "issue", "reason"],
                "properties": {
                    "review_id": {"type": "integer", "enum": list(range(1, count + 1))},
                    "decision": {"type": "string", "enum": ["supported", "unsupported", "uncertain"]},
                    "issue": {"type": "string", "enum": ISSUES},
                    "reason": {"type": "string", "minLength": 1, "maxLength": 500},
                },
            },
        }},
    }


def parse_verdicts(content: str, count: int) -> list[dict[str, object]]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("semantic review returned invalid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"verdicts"}:
        raise ValueError("semantic review must contain only verdicts")
    verdicts = payload["verdicts"]
    if not isinstance(verdicts, list) or len(verdicts) != count:
        raise ValueError("semantic review must cover every proposal")
    seen = set()
    for verdict in verdicts:
        if not isinstance(verdict, dict) or set(verdict) != {"review_id", "decision", "issue", "reason"}:
            raise ValueError("semantic review verdict properties do not match schema")
        identity = verdict["review_id"]
        if type(identity) is not int or identity not in range(1, count + 1) or identity in seen:
            raise ValueError("semantic review has a duplicate or unknown review_id")
        seen.add(identity)
        decision, issue, reason = verdict["decision"], verdict["issue"], verdict["reason"]
        if decision not in ("supported", "unsupported", "uncertain") or issue not in ISSUES:
            raise ValueError("semantic review has an invalid decision or issue")
        if (decision == "supported") != (issue == "none"):
            raise ValueError("semantic review decision contradicts its issue")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            raise ValueError("semantic review reason must contain 1-500 characters")
    return sorted(verdicts, key=lambda verdict: verdict["review_id"])
