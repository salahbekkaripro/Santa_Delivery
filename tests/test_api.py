import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


MISSION_RESPONSE = {
    "mission_id": "mission123",
    "mission": {
        "zone": "Paris 5e",
        "num_clients": 3,
        "budget": 500,
        "sleigh_cost": 50,
        "weather_key": "Clear",
        "random_incidents": False,
        "level": None,
    },
    "depot": {"id": 0, "lat": 48.85, "lon": 2.35, "nom_client": "Depot", "poids_colis": 0},
    "clients": [
        {"id": 1, "lat": 48.851, "lon": 2.351, "nom_client": "Client 1", "poids_colis": 10},
    ],
    "graph_available": True,
    "weather": {"desc": "Ciel degage", "factor": 1.0},
    "human_state": {
        "routes_by_sleigh": {"0": []},
        "segments_by_sleigh": {"0": []},
        "assigned_clients": [],
        "live_stats": {"0": {}},
        "stop_meta_by_client": {},
        "speed_multiplier": 1.0,
        "vehicle_capacity": 200,
        "num_vehicles": 1,
    },
    "results_available": False,
    "incidents": {"count": 0, "segments": []},
}

HUMAN_STATE_RESPONSE = {
    "routes_by_sleigh": {"0": [1]},
    "segments_by_sleigh": {
        "0": [
            {
                "variant": "human",
                "sleigh_id": 0,
                "from_id": 0,
                "to_id": 1,
                "route_nodes": [10, 11],
                "geometry": [[48.85, 2.35], [48.851, 2.351]],
                "dist_m": 210.0,
                "time_s": 120.0,
                "arrival_eta_s": 120.0,
                "arrival_clock": "18:02",
                "title": "Traineau #1 · Depot -> Client 1",
                "segment_idx": 1,
                "segment_count": 1,
            }
        ]
    },
    "assigned_clients": [1],
    "live_stats": {"0": {"time_s": 180.0, "dist_m": 300.0}},
    "stop_meta_by_client": {1: {"sleigh_id": 0, "stop_order": 1, "arrival_eta_s": 120.0, "arrival_clock": "18:02"}},
    "speed_multiplier": 1.0,
    "vehicle_capacity": 200,
    "num_vehicles": 1,
}

COMPARISON_RESPONSE = {
    "depot": MISSION_RESPONSE["depot"],
    "clients": MISSION_RESPONSE["clients"],
    "human_segments": HUMAN_STATE_RESPONSE["segments_by_sleigh"]["0"],
    "ai_segments": [],
    "human_stop_meta_by_client": HUMAN_STATE_RESPONSE["stop_meta_by_client"],
    "incidents": {"count": 0, "segments": []},
    "summary_metrics": {
        "human": {"total_time_s": 180.0, "total_dist_m": 300.0, "segment_count": 1, "assigned_clients": 1, "sleighs": []},
        "ai": {"total_time_s": 150.0, "total_dist_m": 250.0, "segment_count": 1, "sleighs": [], "dropped_points": 0},
    },
}

DEBRIEF_RESPONSE = {
    "mission": MISSION_RESPONSE["mission"],
    "results": {"total_time_s": 150.0, "total_weight_kg": 10.0, "tours": [], "dropped_points": []},
    "benchmark": {
        "naive": {"total_time_s": 240.0, "total_dist_m": 420.0},
        "optimized": {"total_time_s": 150.0, "total_dist_m": 250.0},
        "savings": {"time_saved_min": 2, "time_saved_pct": 37.5, "co2_saved_kg": 0.4},
        "budget": {"remaining": 450, "remaining_pct": 90.0},
    },
    "score": {"value": 72.5, "rank": "A", "rank_title": "Chef Logisticien", "human_beat_ai": False},
    "human": {
        "summary": {"total_dist_m": 300.0, "total_time_s": 180.0, "segment_count": 1},
        "assigned_clients": [1],
        "live_stats": {"0": {"time_s": 180.0}},
        "sleighs": [],
    },
    "analysis": {
        "human_vs_ai_delta_s": 30.0,
        "naive_vs_ai_delta_s": 90.0,
        "dropped_points": [],
        "ai_sleighs": [],
        "recommendations": ["Tester une meilleure repartition des stops."],
    },
}

SOLVE_RESPONSE = {
    "results": DEBRIEF_RESPONSE["results"],
    "benchmark": DEBRIEF_RESPONSE["benchmark"],
    "ai_tours": [],
    "ai_segments": [],
    "ai_stop_meta": {},
    "comparison": COMPARISON_RESPONSE,
}


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_and_health(self):
        root_response = self.client.get("/")
        self.assertEqual(root_response.status_code, 200)
        self.assertEqual(root_response.json()["health"], "/health")

        health_response = self.client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})

    @patch("backend.app.services.create_mission", return_value=MISSION_RESPONSE)
    def test_create_mission_success(self, create_mission_mock):
        response = self.client.post(
            "/api/missions",
            json={
                "zone": "Paris 5e",
                "num_clients": 3,
                "budget": 500,
                "sleigh_cost": 50,
                "weather_key": "Clear",
                "random_incidents": False,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mission_id"], "mission123")
        create_mission_mock.assert_called_once()

    @patch("backend.app.services.create_mission", side_effect=ValueError("Generation impossible"))
    def test_create_mission_bad_request(self, _create_mission_mock):
        response = self.client.post(
            "/api/missions",
            json={
                "zone": "Paris 5e",
                "num_clients": 3,
                "budget": 500,
                "sleigh_cost": 50,
                "weather_key": "Clear",
                "random_incidents": False,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Generation impossible")

    @patch("backend.app.services.get_mission", side_effect=FileNotFoundError("Mission introuvable"))
    def test_get_mission_not_found(self, _get_mission_mock):
        response = self.client.get("/api/missions/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Mission introuvable")

    @patch("backend.app.services.list_missions", return_value={"missions": [{"mission_id": "mission123", "status": "created"}]})
    def test_list_missions_success(self, list_missions_mock):
        response = self.client.get("/api/missions?limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["missions"][0]["mission_id"], "mission123")
        list_missions_mock.assert_called_once_with(limit=10)

    @patch("backend.app.services.get_human_route_options", return_value={"options": []})
    def test_route_options_success(self, get_human_route_options_mock):
        response = self.client.post(
            "/api/missions/mission123/human/route-options",
            json={"from_id": 0, "to_id": 1, "speed_multiplier": 1.0, "k": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"options": []})
        get_human_route_options_mock.assert_called_once()

    @patch("backend.app.services.validate_human_segment", return_value=HUMAN_STATE_RESPONSE)
    def test_validate_segment_success(self, validate_human_segment_mock):
        response = self.client.post(
            "/api/missions/mission123/human/validate-segment",
            json={
                "sleigh_id": 0,
                "from_id": 0,
                "to_id": 1,
                "selected_route": {
                    "route_nodes": [10, 11],
                    "geometry": [[48.85, 2.35], [48.851, 2.351]],
                    "dist_m": 210.0,
                    "base_time_s": 120.0,
                    "time_s": 120.0,
                },
                "speed_multiplier": 1.0,
                "vehicle_capacity": 200,
                "num_vehicles": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["assigned_clients"], [1])
        validate_human_segment_mock.assert_called_once()

    @patch("backend.app.services.validate_human_segment", side_effect=ValueError("Client deja assigne"))
    def test_validate_segment_bad_request(self, _validate_human_segment_mock):
        response = self.client.post(
            "/api/missions/mission123/human/validate-segment",
            json={
                "sleigh_id": 0,
                "from_id": 0,
                "to_id": 1,
                "selected_route": {
                    "route_nodes": [10, 11],
                    "geometry": [[48.85, 2.35], [48.851, 2.351]],
                    "dist_m": 210.0,
                    "base_time_s": 120.0,
                    "time_s": 120.0,
                },
                "speed_multiplier": 1.0,
                "vehicle_capacity": 200,
                "num_vehicles": 1,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Client deja assigne")

    @patch("backend.app.services.solve_mission", return_value=SOLVE_RESPONSE)
    def test_solve_success(self, solve_mission_mock):
        response = self.client.post(
            "/api/missions/mission123/solve",
            json={"num_vehicles": 1, "vehicle_capacity": 200, "speed_multiplier": 1.0},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("comparison", response.json())
        solve_mission_mock.assert_called_once()

    @patch("backend.app.services.get_comparison", return_value=COMPARISON_RESPONSE)
    def test_get_comparison_success(self, get_comparison_mock):
        response = self.client.get("/api/missions/mission123/comparison")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary_metrics"]["human"]["assigned_clients"], 1)
        get_comparison_mock.assert_called_once()

    @patch("backend.app.services.get_debrief", return_value=DEBRIEF_RESPONSE)
    def test_get_debrief_success(self, get_debrief_mock):
        response = self.client.get("/api/missions/mission123/debrief")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["score"]["rank"], "A")
        get_debrief_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
