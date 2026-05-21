import unittest

from final_scripts.solve_santa_final import (
    _resolve_night_horizon_s,
    _sanitize_postprocessed_tours,
    _served_priority_drop_penalty,
)


class SolverPostprocessIntegrityTests(unittest.TestCase):
    def test_fallbacks_to_raw_when_duplicates_detected(self):
        tours_raw = {0: [1, 2], 1: [3, 4]}
        improved = {0: [1, 2, 3], 1: [3, 4]}

        result = _sanitize_postprocessed_tours(tours_raw, improved, num_locations=6)

        self.assertEqual(result, tours_raw)

    def test_fallbacks_to_raw_when_client_lost(self):
        tours_raw = {0: [1, 2], 1: [3, 4]}
        improved = {0: [1, 2], 1: [3]}

        result = _sanitize_postprocessed_tours(tours_raw, improved, num_locations=6)

        self.assertEqual(result, tours_raw)

    def test_keeps_improved_when_valid(self):
        tours_raw = {0: [1, 2], 1: [3, 4]}
        improved = {0: [2, 1], 1: [4, 3]}

        result = _sanitize_postprocessed_tours(tours_raw, improved, num_locations=6)

        self.assertEqual(result, improved)

    def test_resolve_night_horizon_s(self):
        self.assertEqual(_resolve_night_horizon_s(28800), 28800)
        self.assertEqual(_resolve_night_horizon_s("7200"), 7200)
        self.assertIsNone(_resolve_night_horizon_s(0))
        self.assertIsNone(_resolve_night_horizon_s(None))

    def test_served_priority_drop_penalty_is_bounded_and_not_lower_than_base(self):
        penalty = _served_priority_drop_penalty(
            base_drop_penalty=150000,
            num_locations=35,
            num_vehicles=4,
            route_horizon_s=28800,
        )
        self.assertGreaterEqual(penalty, 150000)
        self.assertLessEqual(penalty, 2_000_000_000)


if __name__ == "__main__":
    unittest.main()
