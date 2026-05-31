import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from final_scripts.solve_santa_final import solve_large_scale_vrp, solve_vrp


def _build_test_instance(tmp_dir: str, *, num_clients: int = 4) -> dict:
    rows = [{"id": 0, "poids_colis": 0, "tw_start": 0, "tw_end": 100000}]
    for cid in range(1, num_clients + 1):
        rows.append({"id": cid, "poids_colis": 6, "tw_start": 0, "tw_end": 100000})
    df = pd.DataFrame(rows)
    data_path = os.path.join(tmp_dir, "clients.csv")
    df.to_csv(data_path, index=False)

    n = num_clients + 1
    time_matrix = np.full((n, n), 100.0, dtype=float)
    np.fill_diagonal(time_matrix, 0.0)
    dist_matrix = np.full((n, n), 1000.0, dtype=float)
    np.fill_diagonal(dist_matrix, 0.0)
    co2_matrix = np.full((n, n), 200.0, dtype=float)
    np.fill_diagonal(co2_matrix, 0.0)
    risk_matrix = np.full((n, n), 5.0, dtype=float)
    np.fill_diagonal(risk_matrix, 0.0)
    composite_matrix = np.full((n, n), 1.0, dtype=float)
    np.fill_diagonal(composite_matrix, 0.0)

    time_path = os.path.join(tmp_dir, "time.npy")
    dist_path = os.path.join(tmp_dir, "dist.npy")
    co2_path = os.path.join(tmp_dir, "co2.npy")
    risk_path = os.path.join(tmp_dir, "risk.npy")
    composite_path = os.path.join(tmp_dir, "composite.npy")
    np.save(time_path, time_matrix)
    np.save(dist_path, dist_matrix)
    np.save(co2_path, co2_matrix)
    np.save(risk_path, risk_matrix)
    np.save(composite_path, composite_matrix)

    return {
        "data_path": data_path,
        "time_path": time_path,
        "dist_path": dist_path,
        "co2_path": co2_path,
        "risk_path": risk_path,
        "composite_path": composite_path,
        "output_path": os.path.join(tmp_dir, "result.json"),
    }


class LargeScaleSolverTests(unittest.TestCase):
    def test_dispatch_uses_classic_under_threshold(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = _build_test_instance(tmp_dir, num_clients=3)
            with patch.dict(os.environ, {"NOEL_LARGE_SCALE_CLIENT_THRESHOLD": "10"}):
                with patch("final_scripts.solve_santa_final._solve_vrp_classic", return_value={"status": "classic"}) as classic_mock:
                    with patch("final_scripts.solve_santa_final.solve_large_scale_vrp", return_value={"status": "large"}) as large_mock:
                        solved = solve_vrp(data_path=paths["data_path"])
            self.assertEqual(solved["status"], "classic")
            classic_mock.assert_called_once()
            large_mock.assert_not_called()

    def test_dispatch_uses_large_scale_at_or_above_threshold(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = _build_test_instance(tmp_dir, num_clients=4)
            with patch.dict(os.environ, {"NOEL_LARGE_SCALE_CLIENT_THRESHOLD": "4"}):
                with patch("final_scripts.solve_santa_final._solve_vrp_classic", return_value={"status": "classic"}) as classic_mock:
                    with patch("final_scripts.solve_santa_final.solve_large_scale_vrp", return_value={"status": "large"}) as large_mock:
                        solved = solve_vrp(data_path=paths["data_path"])
            self.assertEqual(solved["status"], "large")
            large_mock.assert_called_once()
            classic_mock.assert_not_called()

    def test_large_scale_respects_route_constraints_and_can_drop(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = _build_test_instance(tmp_dir, num_clients=4)
            solved = solve_large_scale_vrp(
                num_vehicles=2,
                vehicle_capacity=10,
                speed_multiplier=1.0,
                data_path=paths["data_path"],
                time_matrix_path=paths["time_path"],
                dist_matrix_path=paths["dist_path"],
                co2_matrix_path=paths["co2_path"],
                risk_matrix_path=paths["risk_path"],
                composite_matrix_path=paths["composite_path"],
                output_path=paths["output_path"],
                optimization_target="time",
                max_route_time_s=300,
                drop_penalty=1_000_000,
                random_seed=123,
                solver_time_limit_s=3,
            )

            self.assertIsInstance(solved, dict)
            self.assertTrue(solved.get("large_scale", {}).get("enabled"))
            self.assertGreaterEqual(solved.get("large_scale", {}).get("dropped_count", 0), 1)

            delivered_clients = []
            for tour in solved.get("tours", []):
                route_ids = [int(x) for x in tour.get("route_ids", [])]
                self.assertGreaterEqual(len(route_ids), 3)
                self.assertEqual(route_ids[0], 0)
                self.assertEqual(route_ids[-1], 0)
                self.assertLessEqual(float(tour.get("weight_kg", 0.0)), 10.0 + 1e-9)
                self.assertLessEqual(int(tour.get("duration_s", 0)), 300)
                delivered_clients.extend([cid for cid in route_ids if cid != 0])

            self.assertEqual(len(delivered_clients), len(set(delivered_clients)))
            self.assertGreaterEqual(len(solved.get("dropped_points", [])), 1)


if __name__ == "__main__":
    unittest.main()
