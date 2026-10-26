from __future__ import annotations

import unittest

from backend.assessment import load_bank
from scripts.validate_assessment import normalize_answers, validate


class AssessmentValidationTests(unittest.TestCase):
    def test_legacy_numeric_answers_are_mapped_to_stable_ids(self):
        answers = normalize_answers({str(index): 0 for index in range(44)})
        self.assertEqual(set(answers), {q["key"] for q in load_bank()["questions"]})

    def test_invalid_legacy_index_is_not_silently_dropped(self):
        with self.assertRaises(ValueError):
            normalize_answers({str(index): 0 for index in range(45)})

    def test_small_supplied_sample_is_reported_as_insufficient(self):
        answers = {q["key"]: 0 for q in load_bank()["questions"]}
        result = validate([answers], [answers], "provided_answer_records")
        self.assertFalse(result["diagnostic_passed"])
        self.assertFalse(result["checks"]["distribution_has_at_least_100_results"])
        self.assertFalse(result["checks"]["pairs_have_at_least_30_samples"])


if __name__ == "__main__":
    unittest.main()
