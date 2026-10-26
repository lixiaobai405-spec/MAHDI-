from __future__ import annotations

import random
import statistics
import unittest
from copy import deepcopy

from backend.assessment import (
    classify_scores, get_config, load_bank, score_answers, select_question_ids,
)


class AssessmentScoringTests(unittest.TestCase):
    def setUp(self):
        self.bank = load_bank()
        self.config = get_config()

    def answers(self, target="M", seed=1019):
        rng = random.Random(seed)
        result = {}
        for question in self.bank["questions"]:
            values = [option.get(target, 0) for option in question["sc"]]
            best = [index for index, value in enumerate(values) if value == max(values)]
            result[question["key"]] = rng.choice(best)
        return result

    def test_original_bank_has_44_unique_questions_and_five_definitions(self):
        self.assertEqual(len(self.bank["questions"]), 44)
        self.assertEqual(len({q["key"] for q in self.bank["questions"]}), 44)
        self.assertEqual(set(self.bank["types"]), set("MAHDI"))

    def test_lite_count_is_configurable_and_covers_all_dimensions(self):
        for count in (10, 12, 20):
            config = dict(self.config, lite_question_count=count)
            ids = select_question_ids(config)
            self.assertEqual(len(ids), count)
            self.assertEqual(len(set(ids)), count)
            self.assertEqual({q["dim"] for q in self.bank["questions"] if q["key"] in ids}, set("EKILP"))
        with self.assertRaises(ValueError):
            select_question_ids(dict(self.config, lite_question_count=9))

    def test_new_scores_are_deterministic_and_not_compositional_shares(self):
        result = score_answers(self.answers(), "full", self.config)
        again = score_answers(self.answers(), "full", self.config)
        self.assertEqual(result["final"], again["final"])
        self.assertEqual(result["pcts"], result["final"])
        self.assertNotEqual(sum(result["final"].values()), 100)
        self.assertTrue(all(20 <= score <= 90 for score in result["final"].values()))
        self.assertEqual(result["algorithm_version"], "standard_v2")
        self.assertEqual(len(result["core_features"]), 5)
        self.assertEqual(len(result["lite_features"]), 3)

    def test_legacy_switch_keeps_original_score_meaning_and_traces_version(self):
        result = score_answers(self.answers(), "full", dict(self.config, algorithm_version="legacy_v1"))
        self.assertEqual(result["algorithm_version"], "legacy_v1")
        self.assertLessEqual(abs(sum(result["pcts"].values()) - 100), 2)
        self.assertTrue(all(isinstance(value, int) for value in result["final"].values()))

    def test_close_scores_do_not_force_a_primary_type(self):
        result = classify_scores(dict(M=61, A=60, H=59, D=58, I=57), self.config)
        self.assertIsNone(result["mainType"])
        self.assertEqual(result["conclusion"], "复合型 / 待观察")
        self.assertTrue(result["conclusion_reason"])
        self.assertEqual(result["tendency_strength"], "倾向不明显")
        for gap, expected in ((5, "倾向不明显"), (10, "中等倾向"), (22, "明显倾向")):
            self.assertEqual(classify_scores(dict(M=80, A=80-gap, H=30, D=25, I=20), self.config)["tendency_strength"], expected)

    def test_legacy_close_scores_explain_the_legacy_double_type_rule(self):
        rng = random.Random(1019)
        answers = {q["key"]: rng.randrange(len(q["opts"])) for q in self.bank["questions"]}
        result = score_answers(answers, "full", dict(self.config, algorithm_version="legacy_v1"))
        self.assertLess(result["top_gap"], 5)
        self.assertIsNotNone(result["mainType"])
        self.assertFalse(result["is_mixed"])
        self.assertIn("双类型", result["conclusion_reason"])
        self.assertNotIn("低于5分", result["conclusion_reason"])

    def test_missing_unknown_and_invalid_answers_are_rejected(self):
        answers = self.answers()
        for modified in ({}, dict(answers, UNKNOWN=0), dict(answers, E1=99), dict(answers, E1=True)):
            with self.assertRaises(ValueError):
                score_answers(modified, "full", self.config)
        with self.assertRaises(ValueError):
            score_answers(answers, "wrong", self.config)

    def test_lite_uses_only_its_own_question_set(self):
        ids = select_question_ids(self.config)
        full = self.answers("D")
        result = score_answers({key: full[key] for key in ids}, "lite", self.config)
        self.assertEqual(result["version"], "lite")
        self.assertEqual(set(result["answers"]), set(ids))
        self.assertEqual(len(result["lite_features"]), 3)

    def test_100_seeded_results_have_spread_and_all_three_strengths(self):
        rng = random.Random(1019)
        results = [
            score_answers({q["key"]: rng.randrange(len(q["opts"])) for q in self.bank["questions"]}, "full", self.config)
            for _ in range(100)
        ]
        spreads = [max(r["final"].values()) - min(r["final"].values()) for r in results]
        self.assertGreaterEqual(statistics.median(spreads), 25)
        self.assertEqual({r["tendency_strength"] for r in results}, {"明显倾向", "中等倾向", "倾向不明显"})

    def test_30_coherent_profile_pairs_keep_direction_at_least_70_percent(self):
        ids = select_question_ids(self.config)
        matches = 0
        for index in range(30):
            full_answers = self.answers("MAHDI"[index % 5], seed=index)
            full = score_answers(full_answers, "full", self.config)
            lite = score_answers({key: full_answers[key] for key in ids}, "lite", self.config)
            matches += full["leadingType"] == lite["leadingType"]
        self.assertGreaterEqual(matches / 30, .70)


if __name__ == "__main__":
    unittest.main()
