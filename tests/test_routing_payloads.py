import unittest
from unittest.mock import patch

import pandas as pd

from scripts.routing_payloads import HumanState, build_human_eta_payload, build_human_live_stats


class RoutingPayloadTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            [
                {"id": 0, "lat": 48.85, "lon": 2.35, "nom_client": "Depot", "poids_colis": 0},
                {"id": 1, "lat": 48.851, "lon": 2.351, "nom_client": "Client 1", "poids_colis": 10},
                {"id": 2, "lat": 48.852, "lon": 2.352, "nom_client": "Client 2", "poids_colis": 15},
            ]
        )
        self.state = HumanState(
            routes_by_sleigh={"0": [1, 2]},
            segments_by_sleigh={
                "0": [
                    {"from_id": 0, "to_id": 1, "sleigh_id": 0, "dist_m": 100.0, "base_time_s": 120.0, "time_s": 120.0},
                    {"from_id": 1, "to_id": 2, "sleigh_id": 0, "dist_m": 160.0, "base_time_s": 240.0, "time_s": 240.0},
                ]
            },
            assigned_clients=[1, 2],
            speed_multiplier=1.0,
            vehicle_capacity=50,
            num_vehicles=1,
        )

    def test_build_human_eta_payload_is_monotonic(self):
        segments_by_sleigh, stop_meta_by_client = build_human_eta_payload(self.df, self.state, weather_factor=1.0)

        segments = segments_by_sleigh["0"]
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["arrival_eta_s"], 120.0)
        self.assertEqual(segments[1]["arrival_eta_s"], 360.0)
        self.assertLess(segments[0]["arrival_eta_s"], segments[1]["arrival_eta_s"])
        self.assertEqual(segments[0]["title"], "Traineau #1 · Depot -> Client 1")
        self.assertEqual(stop_meta_by_client[2]["arrival_clock"], "18:06")

    @patch("scripts.routing_payloads.compute_route_options")
    def test_build_human_live_stats_includes_return_segment(self, compute_route_options_mock):
        compute_route_options_mock.return_value = [
            {
                "route_nodes": [20, 21],
                "geometry": [[48.852, 2.352], [48.85, 2.35]],
                "dist_m": 180.0,
                "base_time_s": 180.0,
                "time_s": 180.0,
            }
        ]

        stats = build_human_live_stats(self.df, graph=object(), state=self.state, weather_factor=1.0)
        sleigh_stats = stats["0"]

        self.assertEqual(sleigh_stats["stops"], 2)
        self.assertEqual(sleigh_stats["load_kg"], 25.0)
        self.assertEqual(sleigh_stats["return_time_s"], 180.0)
        self.assertEqual(sleigh_stats["return_arrival_clock"], "18:09")
        self.assertEqual(sleigh_stats["return_segment"]["arrival_clock"], "18:09")
        self.assertEqual(sleigh_stats["return_segment"]["title"], "Retour depot · Traineau #1 · Client 2 -> Depot")


if __name__ == "__main__":
    unittest.main()
