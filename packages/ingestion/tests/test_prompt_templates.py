from __future__ import annotations

import tempfile
import json
import unittest
from pathlib import Path

from swisstip.ingestion.prompt_templates import load_prompts
from swisstip.ingestion.prompt_templates import load_bundled_prompt
from swisstip.ingestion import claim_contracts as contracts


class PromptTemplateTests(unittest.TestCase):
    def test_review_shape_example_has_sibling_assessments_and_no_implicit_approval(self):
        prompt = load_bundled_prompt("structured_claim_review_v4.md")
        example = prompt.split("```json\n")[1].split("```")[0]
        schema = contracts.review_schema([], ["section-example"])
        claim_schema = schema["properties"]["concept_reviews"]["items"]["properties"]["claim_support"]["items"]
        entry = contracts.decode(example, claim_schema)
        self.assertEqual(set(entry["condition_logic"]), {"source_applicability", "decision", "reason"})
        self.assertEqual(set(entry["scope_fields"]), set(contracts.SCOPE_FIELDS))
        self.assertEqual(entry["decision"], "uncertain")
        self.assertTrue(all(field["decision"] == "uncertain" for field in entry["scope_fields"].values()))

    def test_worked_example_has_cited_connected_logic_and_separate_issuing_role(self):
        text = load_bundled_prompt("structured_claim_example_v4.md")
        ref = text.split("Source evidence ID: ")[1].splitlines()[0]
        source = text.split("Source text: ")[1].splitlines()[0]
        evidence = {ref: {"section_id": "section-example", "text": source}}
        example = contracts.decode(text.split("```json\n")[1].split("```")[0],
                                   contracts.extraction_schema([ref], 6))
        item = example["concepts"][0]
        contracts.validate_concept(item, evidence, {"section-example": "example-scope"})
        requirement, issuance = item["claims"]
        self.assertEqual(requirement["condition_root"], "either")
        self.assertEqual(requirement["condition_groups"][0]["operator"], "OR")
        threshold = requirement["conditions"][1]
        self.assertEqual((threshold["operator"], threshold["value"], threshold["unit"]), ("gt", "5", "days"))
        self.assertEqual(requirement["scope"]["actor"], "visitor")
        self.assertEqual(issuance["scope"]["actor"], "Site Office")
        self.assertEqual(issuance["kind"], "fact")
        self.assertFalse(issuance["conditions"])
        self.assertTrue(all(c["scope"]["recipient"] == "unspecified" for c in item["claims"]))

    def test_bundled_prompts_match_reviewed_system_prompt_bytes(self):
        # v1-v3 preserve the original Python literals. v4 was revised to clarify
        # source-bounded coverage, explicit per-claim review and a worked example.
        expected = {
            "concept_extraction_v1": ("c518de718fc062fde17189160eb86fa1208be5f057c5a3af8d7207b6cece9404", None),
            "concept_extraction_v2": ("8db37071451acce8b4475a8cea6e4c2f44c4fc927aff2a4f8bcecc01df6fd1d4", None),
            "concept_extraction_v3": ("ccd968b7b59b7ef144255483d42cda016872c0c82b49d00deb384578b234ee83",
                                      "893394d896520067767f1c69eaeefd8efad780658710b99fde64112d8390c78e"),
            "concept_extraction_v4": ("4b870022420a0be39e16b8d993a8b1a44ee122375088807835d3d1c4efc5290e",
                                      "854222e23c4209f5786f2e09cd1ad97f7d9f9f314fe3340eb8a881a4c616ed9b"),
        }
        for profile, (extraction, review) in expected.items():
            with self.subTest(profile=profile):
                prompts = load_prompts(profile).to_dict()
                self.assertEqual(prompts["extraction"]["sha256"], extraction)
                self.assertEqual(prompts.get("review", {}).get("sha256"), review)
        self.assertEqual(len(load_prompts("concept_extraction_v3").extraction.sources), 2)

    def test_override_is_a_snapshot_with_normalized_utf8_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.md"
            path.write_bytes(b"\xef\xbb\xbfCustom extraction.\r\nKeep {literal} text.\r\n")
            prompts = load_prompts("concept_extraction_v3", extraction_prompt_file=path)
            self.assertEqual(prompts.extraction.text, "Custom extraction.\nKeep {literal} text.\n")
            self.assertEqual(prompts.extraction.sources, (str(path.resolve()),))
            self.assertEqual(prompts.review, load_prompts("concept_extraction_v3").review)
            original = prompts.to_dict()
            path.write_text("Changed", encoding="utf-8")
            self.assertEqual(prompts.to_dict(), original)
            self.assertNotEqual(load_prompts("concept_extraction_v3", extraction_prompt_file=path)
                                .to_dict()["extraction"]["sha256"], original["extraction"]["sha256"])

    def test_invalid_overrides_fail_instead_of_falling_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.md"
            for content in (None, b" \n\t", b"\xff"):
                with self.subTest(content=content):
                    if content is not None:
                        path.write_bytes(content)
                    with self.assertRaises(ValueError):
                        load_prompts("concept_extraction_v3", extraction_prompt_file=path)
            with self.assertRaisesRegex(ValueError, "not supported"):
                load_prompts("concept_extraction_v1", review_prompt_file=path)
            with self.assertRaisesRegex(ValueError, "unsupported prompt profile"):
                load_prompts("unknown")
