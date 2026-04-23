import unittest
from types import SimpleNamespace
from unittest.mock import patch

import networkx as nx
import pandas as pd

from backend.app import services


class RouteOptionsFeasibilityTests(unittest.TestCase):
    def test_marks_option_as_safe_when_capacity_and_time_window_are_ok(self):
        df = pd.DataFrame(
            [
                {"id": 0, "poids_colis": 0.0},
                {"id": 1, "poids_colis": 15.0, "tw_end": 7200.0},
            ]
        )
        state = services.human_state_from_payload(services.default_human_state(num_vehicles=1, vehicle_capacity=200))
        options = [
            {"route_nodes": [10, 11], "dist_m": 1200.0, "time_s": 600.0, "label": "Plus rapide"},
        ]

        annotated = services._annotate_route_options_feasibility(
            df,
            state,
            options,
            to_id=1,
            sleigh_id=0,
            time_factor=1.0,
        )

        self.assertEqual(len(annotated), 1)
        self.assertTrue(annotated[0]["is_feasible"])
        self.assertEqual(annotated[0]["feasibility_badges"], ["Sûr"])
        self.assertEqual(annotated[0]["projected_load_kg"], 15.0)

    def test_marks_overload_and_delay_with_explicit_badges(self):
        df = pd.DataFrame(
            [
                {"id": 0, "poids_colis": 0.0},
                {"id": 1, "poids_colis": 30.0, "tw_end": 1000.0},
            ]
        )
        state = services.human_state_from_payload(services.default_human_state(num_vehicles=1, vehicle_capacity=20))
        options = [
            {"route_nodes": [10, 11], "dist_m": 800.0, "time_s": 1200.0, "label": "Option risquee"},
        ]

        annotated = services._annotate_route_options_feasibility(
            df,
            state,
            options,
            to_id=1,
            sleigh_id=0,
            time_factor=1.0,
        )

        self.assertEqual(len(annotated), 1)
        self.assertFalse(annotated[0]["is_feasible"])
        self.assertIn("Surcharge", annotated[0]["feasibility_badges"])
        self.assertIn("Risque retard", annotated[0]["feasibility_badges"])
        self.assertGreater(annotated[0]["projected_overload_kg"], 0.0)

    def test_sorts_feasible_options_first(self):
        df = pd.DataFrame(
            [
                {"id": 0, "poids_colis": 0.0},
                {"id": 1, "poids_colis": 5.0, "tw_end": 4000.0},
            ]
        )
        state = services.human_state_from_payload(services.default_human_state(num_vehicles=1, vehicle_capacity=10))
        options = [
            {"route_nodes": [1, 2], "dist_m": 400.0, "time_s": 5000.0, "label": "Infeasible"},
            {"route_nodes": [1, 3], "dist_m": 420.0, "time_s": 300.0, "label": "Feasible"},
        ]

        annotated = services._annotate_route_options_feasibility(
            df,
            state,
            options,
            to_id=1,
            sleigh_id=0,
            time_factor=1.0,
        )

        self.assertTrue(annotated[0]["is_feasible"])
        self.assertFalse(annotated[1]["is_feasible"])

    def test_marks_incident_overlap_as_not_feasible(self):
        df = pd.DataFrame(
            [
                {"id": 0, "poids_colis": 0.0},
                {"id": 1, "poids_colis": 5.0, "tw_end": 7200.0},
            ]
        )
        state = services.human_state_from_payload(services.default_human_state(num_vehicles=1, vehicle_capacity=100))
        options = [{"route_nodes": [10, 11], "dist_m": 500.0, "time_s": 300.0, "label": "Incident path"}]
        incidents = [{"route_nodes": [10, 11]}]

        annotated = services._annotate_route_options_feasibility(
            df,
            state,
            options,
            to_id=1,
            sleigh_id=0,
            time_factor=1.0,
            incident_segments=incidents,
        )

        self.assertFalse(annotated[0]["is_feasible"])
        self.assertIn("Axe incident", annotated[0]["feasibility_badges"])

    @patch("backend.app.services._serialize_state_with_stats")
    @patch("backend.app.services.load_weather", return_value={"factor": 1.0})
    @patch("backend.app.services.load_graph")
    @patch("backend.app.services.read_points")
    @patch("backend.app.services.load_mission_bundle")
    def test_validate_segment_rejects_non_feasible_option(
        self,
        load_mission_bundle_mock,
        read_points_mock,
        load_graph_mock,
        _load_weather_mock,
        serialize_state_mock,
    ):
        paths = SimpleNamespace(
            data_file="data.csv",
            graph_file="graph.graphml",
            weather_file="weather.json",
            incidents_file="incidents.json",
        )
        mission = {"weather_key": "Clear", "random_incidents": False}
        state_payload = services.default_human_state(num_vehicles=1, vehicle_capacity=20)
        load_mission_bundle_mock.return_value = (paths, mission, state_payload)
        read_points_mock.return_value = pd.DataFrame(
            [
                {"id": 0, "poids_colis": 0.0},
                {"id": 1, "poids_colis": 30.0, "tw_end": 1000.0},
            ]
        )
        graph = nx.MultiDiGraph()
        graph.add_edge(10, 11, length=850.0, travel_time=1200.0)
        load_graph_mock.return_value = graph
        payload = {
            "sleigh_id": 0,
            "from_id": 0,
            "to_id": 1,
            "selected_route": {
                "route_nodes": [10, 11],
                "geometry": [],
                "dist_m": 850.0,
                "base_time_s": 1200.0,
                "time_s": 1200.0,
            },
            "speed_multiplier": 1.0,
            "vehicle_capacity": 20,
            "num_vehicles": 1,
        }

        with self.assertRaises(ValueError) as context:
            services.validate_human_segment("mission-x", payload)

        self.assertIn("Segment non faisable", str(context.exception))
        serialize_state_mock.assert_not_called()

    @patch("backend.app.services._serialize_state_with_stats")
    @patch("backend.app.services.load_weather", return_value={"factor": 1.0})
    @patch("backend.app.services._read_json", return_value={"count": 1, "segments": [{"route_nodes": [10, 11]}]})
    @patch("backend.app.services.load_graph")
    @patch("backend.app.services.read_points")
    @patch("backend.app.services.load_mission_bundle")
    def test_validate_segment_rejects_incident_overlap(
        self,
        load_mission_bundle_mock,
        read_points_mock,
        load_graph_mock,
        _read_json_mock,
        _load_weather_mock,
        serialize_state_mock,
    ):
        paths = SimpleNamespace(
            data_file="data.csv",
            graph_file="graph.graphml",
            weather_file="weather.json",
            incidents_file="incidents.json",
        )
        mission = {"weather_key": "Clear", "random_incidents": True}
        state_payload = services.default_human_state(num_vehicles=1, vehicle_capacity=200)
        load_mission_bundle_mock.return_value = (paths, mission, state_payload)
        read_points_mock.return_value = pd.DataFrame(
            [
                {"id": 0, "poids_colis": 0.0},
                {"id": 1, "poids_colis": 10.0, "tw_end": 7000.0},
            ]
        )
        graph = nx.MultiDiGraph()
        graph.add_edge(10, 11, length=600.0, travel_time=240.0)
        load_graph_mock.return_value = graph
        payload = {
            "sleigh_id": 0,
            "from_id": 0,
            "to_id": 1,
            "selected_route": {
                "route_nodes": [10, 11],
                "geometry": [],
                "dist_m": 600.0,
                "base_time_s": 240.0,
                "time_s": 240.0,
            },
            "speed_multiplier": 1.0,
            "vehicle_capacity": 200,
            "num_vehicles": 1,
        }

        with self.assertRaises(ValueError) as context:
            services.validate_human_segment("mission-x", payload)

        self.assertIn("Axe incident", str(context.exception))
        serialize_state_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
