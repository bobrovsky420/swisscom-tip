"""Explicit calendar dates preserve comparisons without coercing their values."""
import copy
import unittest

from swisstip.ingestion import claim_contracts as contracts
from test_structured_extraction import concept


OPERATORS = ("stated", "eq", "ne", "gt", "gte", "lt", "lte")
ORDERED = ("gt", "gte", "lt", "lte")


class CalendarDateConditionTests(unittest.TestCase):
    def proposal(self, operator, value, unit):
        text = f"Apply when the stated boundary is {value}."
        ref = f"section-boundary:0:{len(text)}"
        evidence = {ref: {"section_id": "section-boundary", "scope_id": "scope-boundary", "text": text}}
        item = concept(ref, evidence[ref])
        claim = item["claims"][0]
        claim["statement"] = text
        claim["conditions"] = [{"condition_id": "boundary", "text": text, "evidence_ids": [ref],
            "subject": "applicant", "operator": operator, "value": value, "unit": unit,
            "time_window": "unspecified"}]
        claim["condition_root"] = "boundary"
        return item, evidence, {"section-boundary": "scope-boundary"}

    def validate(self, proposal):
        item, evidence, sections = proposal
        schema = contracts.extraction_schema(list(evidence), 1)["properties"]["concepts"]["items"]
        contracts.validate(item, schema)
        contracts.validate_concept(item, evidence, sections)

    def test_real_canonical_dates_validate_for_every_operator_without_mutation(self):
        for operator in OPERATORS:
            for value in ("2020-12-31", "2024-02-29", "2000-02-29", "0001-01-01", "9999-12-31"):
                with self.subTest(operator=operator, value=value):
                    proposal = self.proposal(operator, value, "date")
                    original = copy.deepcopy(proposal)
                    self.validate(proposal)
                    self.assertEqual(proposal, original)

    def test_date_unit_rejects_invalid_calendars_and_noncanonical_formats_for_every_operator(self):
        invalid = ("2023-02-29", "1900-02-29", "2024-04-31", "2024-00-01", "2024-13-01",
            "2024-01-00", "0000-01-01", "10000-01-01", "20240229", "2024-W09-4", "2024-060",
            "2024-2-29", "2024-02-9", "2024-02", "2024", "29 February 2024", " 2024-02-29",
            "2024-02-29 ", "2024-02-29T00:00:00", "2024-02-29Z", "\u0662\u0660\u0662\u0664-02-29",
            "NaN", "Infinity", "unspecified")
        for operator in OPERATORS:
            for value in invalid:
                with self.subTest(operator=operator, value=value):
                    with self.assertRaisesRegex(ValueError, "date condition requires .* canonical YYYY-MM-DD"):
                        self.validate(self.proposal(operator, value, "date"))

    def test_nondate_ordered_comparisons_keep_finite_numeric_validation(self):
        for operator in ORDERED:
            for value in ("-3", "0", "3.5", "1e3"):
                with self.subTest(operator=operator, numeric=value):
                    self.validate(self.proposal(operator, value, "days"))
            for value in ("2020-12-31", "NaN", "nan", "Infinity", "-inf", "1e309", "unspecified"):
                with self.subTest(operator=operator, invalid=value):
                    with self.assertRaisesRegex(ValueError, "numeric comparison requires a finite numeric value"):
                        self.validate(self.proposal(operator, value, "days"))

    def test_calendar_comparison_requires_the_explicit_date_unit(self):
        for operator in ORDERED:
            for unit in ("Date", "DATE", "calendar_date", "days", "unspecified"):
                with self.subTest(operator=operator, unit=unit):
                    with self.assertRaisesRegex(ValueError, "numeric comparison requires a finite numeric value"):
                        self.validate(self.proposal(operator, "2024-02-29", unit))
            with self.subTest(operator=operator, numeric_date=True):
                with self.assertRaisesRegex(ValueError, "date condition requires .* canonical YYYY-MM-DD"):
                    self.validate(self.proposal(operator, "20240229", "date"))

    def test_nondate_categorical_and_stated_values_remain_unchanged(self):
        for operator in ("eq", "ne", "stated"):
            for value in ("resident", "2024-02", "unspecified", "-inf"):
                with self.subTest(operator=operator, value=value):
                    proposal = self.proposal(operator, value, "unspecified")
                    original = copy.deepcopy(proposal)
                    self.validate(proposal)
                    self.assertEqual(proposal, original)


if __name__ == "__main__":
    unittest.main()
