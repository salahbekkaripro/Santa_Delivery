import unittest
from types import SimpleNamespace

from backend.app.services import _evaluate_secondary_objectives, resolve_ai_strategy


class AiProfileTests(unittest.TestCase):
    def test_resolve_ai_strategy_supports_accented_profile(self):
        mission = {"ai_profile": "Écolo", "random_incidents": False}
        payload = {"num_vehicles": 3, "vehicle_capacity": 200, "speed_multiplier": 1.0, "optimization_target": "time"}

        strategy = resolve_ai_strategy(mission, payload)

        self.assertEqual(strategy["profile"], "ecolo")
        self.assertEqual(strategy["label"], "Écolo")
        self.assertEqual(strategy["optimization_target"], "distance")
        self.assertEqual(strategy["difficulty_bonus"], 3.0)
        self.assertAlmostEqual(strategy["speed_multiplier"], 0.96)
        self.assertEqual(strategy["local_search_metaheuristic"], "simulated_annealing")

    def test_resolve_ai_strategy_expands_margin_for_prudent_with_incidents(self):
        mission = {"ai_profile": "Prudent", "random_incidents": True}
        payload = {"num_vehicles": 4, "vehicle_capacity": 220, "speed_multiplier": 1.0, "optimization_target": "time"}

        strategy = resolve_ai_strategy(mission, payload)

        self.assertEqual(strategy["profile"], "prudent")
        self.assertEqual(strategy["num_vehicles"], 4)
        self.assertEqual(strategy["vehicle_capacity"], 220)
        self.assertEqual(strategy["time_slack_s"], 6600)
        self.assertEqual(strategy["max_route_time_s"], 18900)

    def test_resolve_ai_strategy_aggressive_can_drop_more_easily(self):
        mission = {"ai_profile": "Agressive", "random_incidents": False}
        payload = {"num_vehicles": 2, "vehicle_capacity": 180, "speed_multiplier": 1.0, "optimization_target": "time"}

        strategy = resolve_ai_strategy(mission, payload)

        self.assertEqual(strategy["profile"], "agressive")
        self.assertEqual(strategy["drop_penalty"], 220_000)
        self.assertEqual(strategy["difficulty_bonus"], 6.0)
        self.assertAlmostEqual(strategy["speed_multiplier"], 1.18)
        self.assertEqual(strategy["solver_time_limit_s"], 10)

    def test_resolve_ai_strategy_without_profile_keeps_payload_target(self):
        mission = {"random_incidents": False}
        payload = {"num_vehicles": 3, "vehicle_capacity": 200, "speed_multiplier": 1.5, "optimization_target": "distance"}

        strategy = resolve_ai_strategy(mission, payload)

        self.assertEqual(strategy["profile"], "adaptatif")
        self.assertEqual(strategy["optimization_target"], "distance")
        self.assertAlmostEqual(strategy["speed_multiplier"], 1.5)

    def test_evaluate_secondary_objectives_reports_progress(self):
        mission = {
            "num_clients": 3,
            "secondary_objectives": [
                {"code": "assign_all_clients", "label": "Tout affecter"},
                {"code": "no_overload", "label": "Zéro surcharge"},
                {"code": "max_human_delta_s", "label": "Moins de 5 min", "target": 300},
            ],
        }
        human_state = SimpleNamespace(assigned_clients=[1, 2, 3])
        human_live_stats = {"0": {"over_kg": 0.0}}
        results = {"dropped_points": []}
        benchmark = {"budget": {"remaining_pct": 40.0}}

        evaluated = _evaluate_secondary_objectives(
            mission,
            results=results,
            human_state=human_state,
            human_live_stats=human_live_stats,
            benchmark=benchmark,
            human_beat_ai=True,
            final_score=82.0,
            human_vs_ai_delta_s=240.0,
        )

        self.assertEqual(len(evaluated), 3)
        self.assertTrue(all(item["completed"] for item in evaluated))
        self.assertEqual(evaluated[0]["progress_label"], "3/3 clients affectés")


if __name__ == "__main__":
    unittest.main()
