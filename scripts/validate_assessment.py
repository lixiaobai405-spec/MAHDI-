"""Reproducible MAHID distribution and lite/full comparison diagnostics.

Examples:
  python scripts/validate_assessment.py --synthetic
  python scripts/validate_assessment.py --answers actual_answers.json

Input: a JSON list of full 44-question answer dictionaries, or records with
an 'answers' field. Legacy zero-based numeric question indexes are accepted.
Output contains only aggregate metrics, never names or individual answers.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.assessment import get_config, load_bank, score_answers, select_question_ids


def normalize_answers(record):
    answers = record.get("answers", record)
    questions = load_bank()["questions"]
    if not isinstance(answers, dict):
        raise ValueError("Each answer record must be an object")
    if answers and all(str(key).isdigit() for key in answers):
        if any(not 0 <= int(key) < len(questions) for key in answers):
            raise ValueError("Legacy answer contains an unknown question index")
        answers = {questions[int(key)]["key"]: value for key, value in answers.items()}
    return answers


def diagnostic_samples():
    questions = load_bank()["questions"]
    rng = random.Random(1019)
    distribution = [{q["key"]: rng.randrange(len(q["opts"])) for q in questions} for _ in range(100)]
    pairs = []
    for index in range(30):
        target = "MAHDI"[index % 5]
        answers = {}
        for question in questions:
            scores = [option.get(target, 0) for option in question["sc"]]
            best = [i for i, value in enumerate(scores) if value == max(scores)]
            answers[question["key"]] = rng.choice(best) if rng.random() < .85 else rng.randrange(len(scores))
        pairs.append(answers)
    return distribution, pairs


def validate(distribution_answers, paired_answers, source_kind):
    config = get_config()
    ids = select_question_ids(config)
    full_results = [score_answers(normalize_answers(record), "full", config) for record in distribution_answers]
    spans = [max(result["final"].values()) - min(result["final"].values()) for result in full_results]
    strengths = {key: sum(result["tendency_strength"] == key for result in full_results) for key in ("明显倾向", "中等倾向", "倾向不明显")}
    matches = definite_conflicts = mixed_pairs = 0
    for record in paired_answers:
        answers = normalize_answers(record)
        full = score_answers(answers, "full", config)
        lite = score_answers({key: answers[key] for key in ids}, "lite", config)
        matches += full["leadingType"] == lite["leadingType"]
        mixed_pairs += full["is_mixed"] or lite["is_mixed"]
        definite_conflicts += full["mainType"] is not None and lite["mainType"] is not None and full["mainType"] != lite["mainType"]
    median_span = statistics.median(spans) if spans else 0
    agreement = matches / len(paired_answers) if paired_answers else 0
    checks = {
        "distribution_has_at_least_100_results": len(full_results) >= 100,
        "median_max_min_gap_at_least_25": median_span >= 25,
        "three_tendency_strengths_present": all(strengths.values()),
        "pairs_have_at_least_30_samples": len(paired_answers) >= 30,
        "leading_direction_agreement_at_least_70_percent": agreement >= .70,
    }
    return {
        "evidence_kind": source_kind,
        "algorithm_version": config["algorithm_version"],
        "question_bank_version": load_bank()["bank_version"],
        "reference_distribution": full_results[0]["reference_distribution"] if full_results else None,
        "lite_question_count": len(ids), "lite_question_ids": ids,
        "distribution_result_count": len(full_results), "median_max_min_gap": median_span,
        "tendency_strength_counts": strengths,
        "pair_count": len(paired_answers), "leading_direction_agreement": agreement,
        "definite_type_conflicts": definite_conflicts, "pairs_with_a_mixed_conclusion": mixed_pairs,
        "checks": checks, "diagnostic_passed": all(checks.values()),
        "scope_note": "Synthetic checks verify these constructed inputs only; they do not establish population norms or real-user validity." if source_kind == "synthetic_diagnostic" else "Metrics apply only to the supplied answer records. Source provenance must be verified separately.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--synthetic", action="store_true")
    source.add_argument("--answers", type=Path)
    args = parser.parse_args()
    if args.synthetic:
        distribution, pairs = diagnostic_samples()
        result = validate(distribution, pairs, "synthetic_diagnostic")
    else:
        records = json.loads(args.answers.read_text(encoding="utf-8"))
        if isinstance(records, dict):
            records = records["records"]
        if not isinstance(records, list):
            parser.error("Answer data must be a JSON list or an object containing records")
        result = validate(records, records, "provided_answer_records")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["diagnostic_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
