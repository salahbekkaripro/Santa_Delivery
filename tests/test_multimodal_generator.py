import unittest

import numpy as np

from scripts import generator_engine


class MultimodalGeneratorTests(unittest.TestCase):
    def test_normalize_objective_weights_returns_unit_sum(self):
        weights = generator_engine._normalize_objective_weights(
            {"time": 2, "distance": 1, "co2": 1, "risk": 0}
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        self.assertGreater(weights["time"], weights["distance"])

    def test_build_composite_cost_matrix_keeps_zero_diagonal(self):
        time_m = np.array([[0, 10], [10, 0]], dtype=float)
        dist_m = np.array([[0, 1000], [1000, 0]], dtype=float)
        co2_m = np.array([[0, 120], [120, 0]], dtype=float)
        risk_m = np.array([[0, 2], [2, 0]], dtype=float)
        weights = {"time": 0.5, "distance": 0.2, "co2": 0.2, "risk": 0.1}

        composite = generator_engine._build_composite_cost_matrix(
            time_m, dist_m, co2_m, risk_m, weights
        )

        self.assertEqual(composite.shape, (2, 2))
        self.assertAlmostEqual(float(composite[0, 0]), 0.0, places=6)
        self.assertAlmostEqual(float(composite[1, 1]), 0.0, places=6)
        self.assertGreater(float(composite[0, 1]), 0.0)


if __name__ == "__main__":
    unittest.main()

