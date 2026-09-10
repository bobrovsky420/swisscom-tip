"""Actionable, bounded diagnostics preserve strict schema rejection."""
import copy
import json
import unittest

from swisstip.ingestion import claim_contracts as contracts
import test_structured_extraction as helpers


class SchemaDiagnosticTests(unittest.TestCase):
    def test_array_diagnostic_identifies_count_and_both_bounds(self):
        schema = contracts.array({"type": "integer"}, maximum=6, minimum=1)
        for count in (0, 7):
            with self.subTest(count=count), self.assertRaises(ValueError) as caught:
                contracts.validate([0] * count, schema, "response.concepts")
            self.assertEqual(str(caught.exception),
                f"response.concepts: array bounds exceeded (received={count}, min=1, max=6)")
        for count in (1, 6):
            contracts.validate([0] * count, schema)

    def test_concept_type_diagnostic_identifies_invalid_and_all_allowed_values(self):
        schema = contracts.extraction_schema([], 6)["properties"]["concepts"]["items"]["properties"]["concept_type"]
        with self.assertRaises(ValueError) as caught:
            contracts.validate("FACT", schema, "response.concepts[4].concept_type")
        message = str(caught.exception)
        self.assertTrue(message.startswith("response.concepts[4].concept_type: unknown value"))
        self.assertIn('received="FACT"', message)
        for allowed in ("ENTITY", "PROCESS", "RULE", "SERVICE", "DOCUMENT", "OTHER"):
            self.assertIn(json.dumps(allowed), message)
            contracts.validate(allowed, schema)
        with self.assertRaisesRegex(ValueError, "expected string"):
            contracts.validate(1, schema)

    def test_large_untrusted_value_and_evidence_enum_have_bounded_escaped_diagnostics(self):
        allowed = [f"section-{index:04d}:" + "x" * 10000 for index in range(40)]
        with self.assertRaises(ValueError) as caught:
            contracts.validate("\n\t" * 10000, contracts.enum(allowed), "response.evidence_ids[0]")
        message = str(caught.exception)
        self.assertLess(len(message), 2000)
        self.assertNotIn("\n", message)
        self.assertNotIn("\t", message)
        self.assertIn("28 more omitted", message)
        self.assertIn("...", message)
        self.assertNotIn("section-0039", message)
        contracts.validate(allowed[-1], contracts.enum(allowed))

    def test_integer_enum_diagnostic_and_boolean_type_remain_strict(self):
        schema = {"type": "integer", "enum": [0, 1]}
        with self.assertRaisesRegex(ValueError, r"unknown value; received=2; allowed=\[0, 1\]"):
            contracts.validate(2, schema)
        with self.assertRaisesRegex(ValueError, "unknown value; received=<integer exceeds 256 bits>"):
            contracts.validate(1 << 300, schema)
        with self.assertRaisesRegex(ValueError, "expected integer"):
            contracts.validate(True, schema)
        contracts.validate(1, schema)

    def test_repair_feedback_identifies_enum_error_beyond_raw_prefix(self):
        def generate(response, payload):
            prototype = response["concepts"][0]
            response["concepts"] = [copy.deepcopy(prototype) for _ in range(5)]
            for index, concept in enumerate(response["concepts"]):
                concept["label"] = f"Offline concept {index}"
                concept["claims"][0]["statement"] = "Offline source assertion. " * 40
            response["concepts"][-1]["concept_type"] = "FACT"

        provider = helpers.Provider(generate=generate)
        helper = helpers.StructuredTests()
        report = helper.engine(provider, max_concepts_per_chunk=6).extract(helper.page("<p>Offline evidence.</p>"))
        self.assertEqual(len(provider.calls), 2)
        repair = json.loads(provider.calls[1]["user_prompt"])["repair"]
        self.assertTrue(repair["invalid_completion_truncated"])
        self.assertEqual(len(repair["invalid_completion"]), 6000)
        self.assertNotIn('"FACT"', repair["invalid_completion"])
        self.assertIn('response.concepts[4].concept_type: unknown value; received="FACT"', repair["validation_error"])
        self.assertIn('"OTHER"', repair["validation_error"])
        self.assertFalse(report.candidates)
        self.assertEqual(provider.discarded, 2)
        self.assertEqual(report.quality_metrics["review_request_count"], 0)


if __name__ == "__main__":
    unittest.main()
