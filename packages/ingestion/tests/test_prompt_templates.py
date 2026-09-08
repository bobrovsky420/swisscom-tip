from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swisstip.ingestion.prompt_templates import load_prompts


class PromptTemplateTests(unittest.TestCase):
    def test_bundled_prompts_match_reviewed_system_prompt_bytes(self):
        # v1-v3 preserve the original Python literals. v4 was revised to clarify
        # condition roots, required nesting, statement coverage and semantic roles.
        expected = {
            "concept_extraction_v1": ("c518de718fc062fde17189160eb86fa1208be5f057c5a3af8d7207b6cece9404", None),
            "concept_extraction_v2": ("8db37071451acce8b4475a8cea6e4c2f44c4fc927aff2a4f8bcecc01df6fd1d4", None),
            "concept_extraction_v3": ("ccd968b7b59b7ef144255483d42cda016872c0c82b49d00deb384578b234ee83",
                                      "893394d896520067767f1c69eaeefd8efad780658710b99fde64112d8390c78e"),
            "concept_extraction_v4": ("63bc1325d82bac92cac88f406811daa49195385d2ba2f4a3040cac727e654fe2",
                                      "60c90403561caa628b409a4d4f2b639d3b2ae5e9eec692b707a8d98486945a87"),
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
