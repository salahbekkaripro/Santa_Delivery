import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


SOLVE_RESPONSE = {
    "results": {"total_time_s": 120.0, "total_weight_kg": 10.0, "tours": [], "dropped_points": []},
    "benchmark": {
        "naive": {"total_time_s": 240.0, "total_dist_m": 420.0},
        "optimized": {"total_time_s": 120.0, "total_dist_m": 250.0},
        "savings": {"time_saved_min": 2, "time_saved_pct": 50.0, "co2_saved_kg": 0.4},
        "budget": {"remaining": 450, "remaining_pct": 90.0},
    },
    "ai_tours": [],
    "ai_segments": [],
    "ai_stop_meta": {},
    "comparison": {
        "depot": {"id": 0, "lat": 48.85, "lon": 2.35, "nom_client": "Depot", "poids_colis": 0},
        "clients": [],
        "human_segments": [],
        "ai_segments": [],
        "human_stop_meta_by_client": {},
        "incidents": {"count": 0, "segments": []},
        "summary_metrics": {"human": {}, "ai": {}},
    },
}


class AiLearningApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @patch(
        "backend.app.services.train_ai_learning_model",
        return_value={
            "status": "trained",
            "model_version": "1.0",
            "model_path": "/tmp/model.json",
            "sample_count": 12,
            "context_count": 4,
            "profiles": ["ecolo", "express"],
            "trained_at": "2026-04-24T00:00:00+00:00",
        },
    )
    def test_train_ai_learning_success(self, train_mock):
        response = self.client.post("/api/ai-learning/train?limit=42")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "trained")
        train_mock.assert_called_once_with(limit=42)

    @patch("backend.app.services.train_ai_learning_model", side_effect=ValueError("Pas assez de données"))
    def test_train_ai_learning_bad_request(self, _train_mock):
        response = self.client.post("/api/ai-learning/train")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Pas assez de données")

    @patch(
        "backend.app.services.evaluate_ai_learning_model",
        return_value={
            "status": "evaluated",
            "model_version": "2.0",
            "target": "composite_cost",
            "sample_count_total": 24,
            "sample_count_train": 16,
            "sample_count_holdout": 8,
            "holdout_ratio": 0.25,
            "sample_match_rate": 0.75,
            "contexts_evaluated": 3,
            "context_top1_accuracy": 0.67,
            "avg_context_regret": 12.3,
            "examples": [],
        },
    )
    def test_evaluate_ai_learning_success(self, evaluate_mock):
        response = self.client.get("/api/ai-learning/evaluate?limit=300&holdout_ratio=0.3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "evaluated")
        evaluate_mock.assert_called_once_with(limit=300, holdout_ratio=0.3)

    @patch("backend.app.services.evaluate_ai_learning_model", side_effect=ValueError("Découpage impossible"))
    def test_evaluate_ai_learning_bad_request(self, _evaluate_mock):
        response = self.client.get("/api/ai-learning/evaluate")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Découpage impossible")

    @patch(
        "backend.app.services.get_ai_learning_recommendation",
        return_value={
            "mission_id": "mission123",
            "recommendation": {
                "profile": "express",
                "label": "Express",
                "context_key": "weather:clear|incidents:0|clients:small",
                "confidence": 0.73,
                "top_candidates": [],
                "model": {"version": "1.0", "sample_count": 12, "trained_at": "2026-04-24T00:00:00+00:00"},
            },
        },
    )
    def test_get_ai_learning_recommendation_success(self, recommendation_mock):
        response = self.client.get("/api/missions/mission123/ai-learning/recommendation")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recommendation"]["profile"], "express")
        recommendation_mock.assert_called_once_with("mission123")

    @patch("backend.app.services.solve_mission_learned", return_value=SOLVE_RESPONSE)
    def test_solve_learned_success(self, solve_mock):
        response = self.client.post(
            "/api/missions/mission123/solve-learned",
            json={"num_vehicles": 1, "vehicle_capacity": 200, "speed_multiplier": 1.0},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("comparison", response.json())
        solve_mock.assert_called_once()

    @patch(
        "backend.app.services.train_ortools_tuner_model",
        return_value={
            "status": "trained",
            "model_version": "1.0",
            "model_path": "/tmp/ortools_tuner_model.json",
            "sample_count": 32,
            "context_count": 7,
            "profile_count": 3,
            "trained_at": "2026-04-24T00:00:00+00:00",
            "target": "composite_cost",
            "fields": ["first_solution_strategy", "local_search_metaheuristic"],
        },
    )
    def test_train_ortools_tuner_success(self, train_mock):
        response = self.client.post("/api/ortools-tuner/train?limit=777")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "trained")
        train_mock.assert_called_once_with(limit=777)

    @patch("backend.app.services.train_ortools_tuner_model", side_effect=ValueError("Pas assez de données OR-Tools"))
    def test_train_ortools_tuner_bad_request(self, _train_mock):
        response = self.client.post("/api/ortools-tuner/train")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Pas assez de données OR-Tools")

    @patch(
        "backend.app.services.evaluate_ortools_tuner_model",
        return_value={
            "status": "evaluated",
            "model_version": "1.0",
            "target": "composite_cost",
            "sample_count_total": 40,
            "sample_count_train": 30,
            "sample_count_holdout": 10,
            "holdout_ratio": 0.25,
            "split_strategy": "stratified_by_context_profile",
            "sample_match_rate": 0.5,
            "contexts_evaluated": 2,
            "context_top1_accuracy": 0.5,
            "avg_context_regret": 25.3,
            "examples": [],
        },
    )
    def test_evaluate_ortools_tuner_success(self, evaluate_mock):
        response = self.client.get("/api/ortools-tuner/evaluate?limit=444&holdout_ratio=0.4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "evaluated")
        evaluate_mock.assert_called_once_with(limit=444, holdout_ratio=0.4)

    @patch("backend.app.services.evaluate_ortools_tuner_model", side_effect=ValueError("Découpage OR-Tools impossible"))
    def test_evaluate_ortools_tuner_bad_request(self, _evaluate_mock):
        response = self.client.get("/api/ortools-tuner/evaluate")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Découpage OR-Tools impossible")

    @patch(
        "backend.app.services.get_ortools_tuner_recommendation",
        return_value={
            "mission_id": "mission123",
            "recommendation": {
                "profile": "express",
                "context_key": "weather:clearish|incidents:0|clients:small",
                "policy_id": "abc123",
                "policy": {"first_solution_strategy": "parallel_cheapest_insertion"},
                "confidence": 0.71,
                "top_candidates": [],
                "model": {"version": "1.0", "sample_count": 32, "trained_at": "2026-04-24T00:00:00+00:00"},
            },
        },
    )
    def test_get_ortools_tuner_recommendation_success(self, recommendation_mock):
        response = self.client.get("/api/missions/mission123/ortools-tuner/recommendation")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recommendation"]["profile"], "express")
        recommendation_mock.assert_called_once_with("mission123")


if __name__ == "__main__":
    unittest.main()
