from __future__ import annotations

import tempfile
import unittest
import sqlite3
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend import app as app_module, storage
from backend.assessment import get_config, load_bank, score_answers

USER = {"id": "student-a", "role": "student", "display_name": "Test Student", "email": "test@example.invalid", "company_name": "Test Company", "job_title": "Tester"}


class AssessmentApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = patch.object(storage, "DB_PATH", Path(self.temp.name) / "assessment.db")
        self.db.start()
        self.current = dict(USER)
        self.auth = patch.object(app_module, "get_current", side_effect=lambda _: self.current)
        self.auth.start()
        self.client = TestClient(app_module.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.auth.stop()
        self.db.stop()
        self.temp.cleanup()

    def select(self, version="lite", **extra):
        response = self.client.post("/api/assessment/selections", json={"version": version, **extra})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def complete(self, selected):
        answers = {q["key"]: 0 for q in selected["questions"]}
        response = self.client.post("/api/assessment/evaluate", json={"selection_id": selected["selection"]["id"], "answers": answers})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"], answers

    def test_public_config_uses_shared_bank_and_configured_counts(self):
        response = self.client.get("/api/assessment/config")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["lite_question_count"], 12)
        self.assertEqual(len(body["questions"]), 44)
        self.assertEqual(body["full_question_count"], 44)
        self.assertEqual(body["agent_type"], "mahid")
        self.assertEqual(set(body["types"]), set("MAHDI"))

    def test_selection_is_persisted_and_retry_does_not_double_count(self):
        first = self.select(client_request_id="one-click")
        second = self.select(client_request_id="one-click")
        self.assertEqual(first["selection"]["id"], second["selection"]["id"])
        with storage.connect() as conn:
            rows = conn.execute("SELECT payload FROM assessment_selections").fetchall()
        self.assertEqual(len(rows), 1)
        payload = storage.load_json(rows[0]["payload"])
        self.assertEqual(payload["agent_type"], "mahid")
        self.assertEqual(payload["version"], "lite")
        self.assertEqual(len(payload["question_ids"]), 12)
        conflict = self.client.post("/api/assessment/selections", json={"version": "full", "client_request_id": "one-click"})
        self.assertEqual(conflict.status_code, 409)

    def test_result_is_server_scored_saved_versioned_and_idempotent(self):
        selected = self.select()
        result, answers = self.complete(selected)
        expected = score_answers(answers, "lite", get_config())
        self.assertEqual(result["final"], expected["final"])
        self.assertEqual(result["answers"], answers)
        for key in ("version", "algorithm_version", "question_bank_version", "generated_at", "createdAt"):
            self.assertTrue(result[key])
        self.assertEqual(result["generated_at"], result["createdAt"])
        repeat = self.client.post("/api/assessment/evaluate", json={"selection_id": selected["selection"]["id"], "answers": answers})
        self.assertEqual(repeat.json()["result"]["id"], result["id"])
        with storage.connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM results").fetchone()[0], 1)
        forged = self.client.post("/api/assessment/evaluate", json={"selection_id": selected["selection"]["id"], "answers": answers, "final": {"M": 100}})
        self.assertEqual(forged.status_code, 422)

    def test_algorithm_snapshot_survives_global_switch(self):
        selected = self.select()
        legacy = dict(get_config(), algorithm_version="legacy_v1")
        with patch.object(app_module, "get_assessment_config", return_value=legacy):
            result, _ = self.complete(selected)
            new = self.select()
        self.assertEqual(result["algorithm_version"], "standard_v2")
        self.assertEqual(new["selection"]["config"]["algorithm_version"], "legacy_v1")

    def test_latest_result_comes_from_the_current_users_saved_records(self):
        self.assertEqual(self.client.get("/api/results/latest").status_code, 404)
        result, _ = self.complete(self.select())
        response = self.client.get("/api/results/latest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], result)
        self.current = dict(USER, id="student-b")
        self.assertEqual(self.client.get("/api/results/latest").status_code, 404)

    def test_upgrade_inherits_answers_and_only_asks_remaining_questions(self):
        lite = self.select()
        lite_result, lite_answers = self.complete(lite)
        full = self.select("full", source_result_id=lite_result["id"])
        self.assertEqual(full["selection"]["inherited_answers"], lite_answers)
        self.assertEqual(len(full["questions"]), 32)
        self.assertFalse(set(lite_answers).intersection(q["key"] for q in full["questions"]))
        result, new_answers = self.complete(full)
        self.assertEqual(len(result["answers"]), 44)
        self.assertEqual({key: result["answers"][key] for key in lite_answers}, lite_answers)
        self.assertEqual(result["source_result_id"], lite_result["id"])
        self.assertEqual(result["version"], "full")

    def test_upgrade_rejects_an_incompatible_source_question_bank(self):
        result, _ = self.complete(self.select())
        changed_bank = deepcopy(load_bank())
        changed_bank["bank_version"] = "mahid-changed-options"
        changed_bank["questions"][1]["opts"].reverse()
        with patch.object(app_module, "load_assessment_bank", return_value=changed_bank):
            response = self.client.post("/api/assessment/selections", json={"version": "full", "source_result_id": result["id"]})
        self.assertEqual(response.status_code, 409)

    def test_completed_selection_retry_returns_original_result_after_bank_update(self):
        selected = self.select()
        result, answers = self.complete(selected)
        changed_bank = dict(load_bank(), bank_version="mahid-next-bank")
        with patch.object(app_module, "load_assessment_bank", return_value=changed_bank):
            response = self.client.post("/api/assessment/evaluate", json={"selection_id": selected["selection"]["id"], "answers": answers})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], result)

    def test_cross_user_selection_or_upgrade_is_not_accessible(self):
        selected = self.select()
        result, answers = self.complete(selected)
        self.current = dict(USER, id="student-b")
        response = self.client.post("/api/assessment/evaluate", json={"selection_id": selected["selection"]["id"], "answers": answers})
        self.assertEqual(response.status_code, 404)
        response = self.client.post("/api/assessment/selections", json={"version": "full", "source_result_id": result["id"]})
        self.assertEqual(response.status_code, 404)

    def test_invalid_or_missing_answers_never_create_a_result(self):
        selected = self.select()
        for answers in ({}, {q["key"]: True for q in selected["questions"]}, {q["key"]: 99 for q in selected["questions"]}):
            response = self.client.post("/api/assessment/evaluate", json={"selection_id": selected["selection"]["id"], "answers": answers})
            self.assertEqual(response.status_code, 422, response.text)
        with storage.connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM results").fetchone()[0], 0)

    def test_instructor_sees_selection_ratio_and_completion_counts(self):
        lite = self.select()
        self.complete(lite)
        self.select()
        self.select("full")
        self.assertEqual(self.client.get("/api/instructor/version-stats").status_code, 403)
        self.current = dict(USER, role="instructor")
        response = self.client.get("/api/instructor/version-stats")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_selections"], 3)
        self.assertEqual(body["versions"]["lite"]["selections"], 2)
        self.assertEqual(body["versions"]["lite"]["completed"], 1)
        self.assertAlmostEqual(body["versions"]["lite"]["share"], 2 / 3)

    def test_instructor_cannot_start_an_assessment(self):
        self.current = dict(USER, role="instructor")
        self.assertEqual(self.client.post("/api/assessment/selections", json={"version": "lite"}).status_code, 403)


class StorageTransactionTests(unittest.TestCase):
    def test_connection_is_closed_after_context_and_transaction_is_committed(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(storage, "DB_PATH", Path(temporary) / "storage.db"):
                with storage.connect() as conn:
                    conn.execute("CREATE TABLE value (number INTEGER)")
                    conn.execute("INSERT INTO value VALUES (7)")
                with self.assertRaises(sqlite3.ProgrammingError):
                    conn.execute("SELECT 1")
                with storage.connect() as next_connection:
                    self.assertEqual(next_connection.execute("SELECT number FROM value").fetchone()[0], 7)


if __name__ == "__main__":
    unittest.main()
