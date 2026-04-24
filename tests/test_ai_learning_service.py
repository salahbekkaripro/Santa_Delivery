import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import services


def _build_snapshot(mission_id: str, profile: str, total_time_s: float, *, updated_at: str | None = None) -> dict:
    snapshot = {
        "mission_id": mission_id,
        "mission": {
            "mission_id": mission_id,
            "weather_key": "Clear",
            "random_incidents": False,
            "num_clients": 12,
            "budget": 2400,
            "sleigh_cost": 600,
        },
        "results": {
            "total_time_s": total_time_s,
            "dropped_points": [],
            "ai_strategy": {"profile": profile},
        },
        "benchmark": {
            "optimized": {"total_dist_m": 12_000.0 if profile == "express" else 15_000.0},
        },
    }
    if updated_at is not None:
        snapshot["updated_at"] = updated_at
    return snapshot


def _build_tuner_snapshot(
    mission_id: str,
    profile: str,
    total_time_s: float,
    *,
    first_solution_strategy: str,
    local_search_metaheuristic: str,
    solver_time_limit_s: int,
    drop_penalty: int,
    global_span_cost: int,
    updated_at: str | None = None,
) -> dict:
    snapshot = _build_snapshot(mission_id, profile, total_time_s, updated_at=updated_at)
    optimization_target = "distance" if profile == "ecolo" else "time"
    snapshot["results"]["ai_strategy"] = {
        "profile": profile,
        "optimization_target": optimization_target,
        "num_vehicles": 3,
        "vehicle_capacity": 200,
        "speed_multiplier": 1.0,
        "first_solution_strategy": first_solution_strategy,
        "local_search_metaheuristic": local_search_metaheuristic,
        "solver_time_limit_s": solver_time_limit_s,
        "time_slack_s": 3600,
        "max_route_time_s": 15000,
        "drop_penalty": drop_penalty,
        "global_span_cost": global_span_cost,
    }
    return snapshot


class AiLearningServiceTests(unittest.TestCase):
    def test_train_and_recommend_profile(self):
        snapshots = [{"mission_id": f"m{i}", "status": "solved"} for i in range(1, 9)]
        full_snapshots = {
            "m1": _build_snapshot("m1", "express", 1200),
            "m2": _build_snapshot("m2", "express", 1180),
            "m3": _build_snapshot("m3", "express", 1250),
            "m4": _build_snapshot("m4", "express", 1220),
            "m5": _build_snapshot("m5", "ecolo", 1500),
            "m6": _build_snapshot("m6", "ecolo", 1480),
            "m7": _build_snapshot("m7", "ecolo", 1520),
            "m8": _build_snapshot("m8", "ecolo", 1490),
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "ai_learning_model.json"
            with patch.object(services, "AI_LEARNING_MODEL_FILE", model_path):
                with patch("backend.app.repository.list_mission_snapshots", return_value=snapshots):
                    with patch("backend.app.repository.get_mission_snapshot", side_effect=lambda mission_id: full_snapshots[mission_id]):
                        train_summary = services.train_ai_learning_model(limit=100)

                self.assertEqual(train_summary["status"], "trained")
                self.assertEqual(train_summary["sample_count"], 8)
                self.assertTrue(model_path.exists())

                recommendation = services.recommend_ai_profile_for_mission(
                    {"weather_key": "Clear", "random_incidents": False, "num_clients": 10}
                )
                self.assertEqual(recommendation["profile"], "express")
                self.assertGreaterEqual(recommendation["confidence"], 0.0)

    def test_train_requires_minimum_samples(self):
        snapshots = [{"mission_id": "m1", "status": "solved"}]
        full_snapshots = {"m1": _build_snapshot("m1", "express", 1200)}
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "ai_learning_model.json"
            with patch.object(services, "AI_LEARNING_MODEL_FILE", model_path):
                with patch("backend.app.repository.list_mission_snapshots", return_value=snapshots):
                    with patch("backend.app.repository.get_mission_snapshot", side_effect=lambda mission_id: full_snapshots[mission_id]):
                        with self.assertRaises(ValueError):
                            services.train_ai_learning_model(limit=50)

    def test_evaluate_ai_learning_model(self):
        snapshots = [{"mission_id": f"m{i:02d}", "status": "solved"} for i in range(1, 21)]
        full_snapshots = {}
        for i in range(1, 21):
            mission_id = f"m{i:02d}"
            profile = "express" if i % 2 == 1 else "ecolo"
            total_time = 1050.0 + i if profile == "express" else 1550.0 + i
            full_snapshots[mission_id] = _build_snapshot(
                mission_id,
                profile,
                total_time,
                updated_at=f"2026-04-{i:02d}T10:00:00+00:00",
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "ai_learning_model.json"
            with patch.object(services, "AI_LEARNING_MODEL_FILE", model_path):
                with patch("backend.app.repository.list_mission_snapshots", return_value=snapshots):
                    with patch("backend.app.repository.get_mission_snapshot", side_effect=lambda mission_id: full_snapshots[mission_id]):
                        evaluation = services.evaluate_ai_learning_model(limit=100, holdout_ratio=0.30)

        self.assertEqual(evaluation["status"], "evaluated")
        self.assertGreaterEqual(evaluation["sample_count_holdout"], services.AI_LEARNING_MIN_SAMPLES)
        self.assertGreaterEqual(evaluation["sample_match_rate"], 0.5)
        self.assertGreaterEqual(evaluation["contexts_evaluated"], 1)
        self.assertGreaterEqual(evaluation["context_top1_accuracy"], 0.5)

    def test_train_and_recommend_ortools_tuner(self):
        snapshots = [{"mission_id": f"o{i:02d}", "status": "solved"} for i in range(1, 13)]
        full_snapshots = {
            "o01": _build_tuner_snapshot("o01", "express", 980.0, first_solution_strategy="parallel_cheapest_insertion", local_search_metaheuristic="guided_local_search", solver_time_limit_s=20, drop_penalty=1_200_000, global_span_cost=130),
            "o02": _build_tuner_snapshot("o02", "express", 995.0, first_solution_strategy="parallel_cheapest_insertion", local_search_metaheuristic="guided_local_search", solver_time_limit_s=20, drop_penalty=1_200_000, global_span_cost=130),
            "o03": _build_tuner_snapshot("o03", "express", 1005.0, first_solution_strategy="parallel_cheapest_insertion", local_search_metaheuristic="guided_local_search", solver_time_limit_s=20, drop_penalty=1_200_000, global_span_cost=130),
            "o04": _build_tuner_snapshot("o04", "express", 1380.0, first_solution_strategy="path_cheapest_arc", local_search_metaheuristic="tabu_search", solver_time_limit_s=10, drop_penalty=400_000, global_span_cost=60),
            "o05": _build_tuner_snapshot("o05", "express", 1410.0, first_solution_strategy="path_cheapest_arc", local_search_metaheuristic="tabu_search", solver_time_limit_s=10, drop_penalty=400_000, global_span_cost=60),
            "o06": _build_tuner_snapshot("o06", "express", 1430.0, first_solution_strategy="path_cheapest_arc", local_search_metaheuristic="tabu_search", solver_time_limit_s=10, drop_penalty=400_000, global_span_cost=60),
            "o07": _build_tuner_snapshot("o07", "ecolo", 1160.0, first_solution_strategy="path_cheapest_arc", local_search_metaheuristic="simulated_annealing", solver_time_limit_s=24, drop_penalty=1_300_000, global_span_cost=80),
            "o08": _build_tuner_snapshot("o08", "ecolo", 1175.0, first_solution_strategy="path_cheapest_arc", local_search_metaheuristic="simulated_annealing", solver_time_limit_s=24, drop_penalty=1_300_000, global_span_cost=80),
            "o09": _build_tuner_snapshot("o09", "ecolo", 1188.0, first_solution_strategy="path_cheapest_arc", local_search_metaheuristic="simulated_annealing", solver_time_limit_s=24, drop_penalty=1_300_000, global_span_cost=80),
            "o10": _build_tuner_snapshot("o10", "ecolo", 1460.0, first_solution_strategy="parallel_cheapest_insertion", local_search_metaheuristic="guided_local_search", solver_time_limit_s=14, drop_penalty=900_000, global_span_cost=120),
            "o11": _build_tuner_snapshot("o11", "ecolo", 1480.0, first_solution_strategy="parallel_cheapest_insertion", local_search_metaheuristic="guided_local_search", solver_time_limit_s=14, drop_penalty=900_000, global_span_cost=120),
            "o12": _build_tuner_snapshot("o12", "ecolo", 1500.0, first_solution_strategy="parallel_cheapest_insertion", local_search_metaheuristic="guided_local_search", solver_time_limit_s=14, drop_penalty=900_000, global_span_cost=120),
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "ortools_tuner_model.json"
            with patch.object(services, "ORTOOLS_TUNER_MODEL_FILE", model_path):
                with patch("backend.app.repository.list_mission_snapshots", return_value=snapshots):
                    with patch("backend.app.repository.get_mission_snapshot", side_effect=lambda mission_id: full_snapshots[mission_id]):
                        train_summary = services.train_ortools_tuner_model(limit=100)

                self.assertEqual(train_summary["status"], "trained")
                self.assertEqual(train_summary["sample_count"], 12)
                self.assertTrue(model_path.exists())

                recommendation = services.recommend_ortools_tuning_for_mission(
                    {"weather_key": "Clear", "random_incidents": False, "num_clients": 12, "budget": 2400, "sleigh_cost": 600},
                    "express",
                )
                self.assertEqual(recommendation["profile"], "express")
                self.assertEqual(recommendation["policy"]["first_solution_strategy"], "parallel_cheapest_insertion")
                self.assertGreaterEqual(recommendation["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
