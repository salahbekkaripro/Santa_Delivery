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

INCIDENT_REPLAN_RESPONSE = {
    "incidents": {"count": 1, "segments": []},
    "before": {"benchmark": {"optimized": {"total_time_s": 100.0, "total_dist_m": 1000.0}, "savings": {"co2_saved_kg": 1.0}}},
    "after": SOLVE_RESPONSE,
    "delta_kpi": {"time_s": 12.0, "dist_m": 150.0, "co2_kg": -0.1, "time_pct": 12.0, "dist_pct": 15.0},
}

VERSUS_MATCH_RESPONSE = {
    "match_id": "match123",
    "mode": "private",
    "template_id": "paris_duel",
    "template_label": "Paris Rush",
    "winner_rule": "score_time",
    "join_code": "ABC123",
    "host_player_id": "player001",
    "status": "waiting_ready",
    "reference_mission_id": None,
    "started_at": None,
    "started_elapsed_s": None,
    "completed_at": None,
    "winner_player_id": None,
    "result_reason": None,
    "created_at": "2026-01-01T10:00:00+00:00",
    "updated_at": "2026-01-01T10:00:00+00:00",
    "participants": [
        {
            "player_id": "player001",
            "display_name": "Host",
            "seat": 0,
            "state": "joined",
            "mission_id": None,
            "is_self": True,
        },
        {
            "player_id": "player002",
            "display_name": "Guest",
            "seat": 1,
            "state": "joined",
            "mission_id": None,
            "is_self": False,
        },
    ],
    "current_player_mission_id": None,
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

    @patch("backend.app.services.search_social_players", return_value={"players": [{"player_id": "p2", "display_name": "Bravo"}]})
    def test_search_social_players_success(self, search_social_players_mock):
        response = self.client.get("/api/social/players?player_id=p1&q=br&limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["players"][0]["player_id"], "p2")
        search_social_players_mock.assert_called_once_with("p1", query="br", limit=10)

    @patch("backend.app.services.send_friend_request", return_value={"status": "pending"})
    def test_send_friend_request_success(self, send_friend_request_mock):
        response = self.client.post(
            "/api/social/friends/request",
            json={"player_id": "player001", "friend_player_id": "player002"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "pending")
        send_friend_request_mock.assert_called_once()

    @patch("backend.app.services.list_direct_messages", side_effect=ValueError("Vous devez être amis"))
    def test_list_direct_messages_bad_request(self, _list_direct_messages_mock):
        response = self.client.get("/api/social/messages?player_id=p1&with_player_id=p2")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Vous devez être amis")

    @patch("backend.app.services.block_player", return_value={"status": "blocked"})
    def test_block_player_success(self, block_player_mock):
        response = self.client.post(
            "/api/social/blocks",
            json={"player_id": "player001", "blocked_player_id": "player002"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "blocked")
        block_player_mock.assert_called_once()

    @patch(
        "backend.app.services.remove_direct_conversation",
        return_value={"status": "cleared", "conversation_key": "player001::player002", "cleared_before_at": "2026-05-14T18:00:00+00:00"},
    )
    def test_remove_direct_conversation_success(self, remove_direct_conversation_mock):
        response = self.client.post(
            "/api/social/messages/conversation/remove",
            json={"player_id": "player001", "with_player_id": "player002"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cleared")
        self.assertEqual(response.json()["conversation_key"], "player001::player002")
        remove_direct_conversation_mock.assert_called_once()

    @patch(
        "backend.app.services.restore_direct_conversation",
        return_value={"status": "restored", "conversation_key": "player001::player002", "restored": True},
    )
    def test_restore_direct_conversation_success(self, restore_direct_conversation_mock):
        response = self.client.post(
            "/api/social/messages/conversation/restore",
            json={"player_id": "player001", "with_player_id": "player002"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "restored")
        self.assertTrue(response.json()["restored"])
        restore_direct_conversation_mock.assert_called_once()

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
            json={"from_id": 0, "to_id": 1, "speed_multiplier": 1.0, "vehicle_capacity": 123, "k": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"options": []})
        get_human_route_options_mock.assert_called_once_with(
            "mission123",
            from_id=0,
            to_id=1,
            sleigh_id=0,
            speed_multiplier=1.0,
            vehicle_capacity=123,
            k=2,
        )

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

    @patch("backend.app.services.simulate_incident_replan", return_value=INCIDENT_REPLAN_RESPONSE)
    def test_incident_replan_accepts_max_vehicles(self, simulate_incident_replan_mock):
        response = self.client.post(
            "/api/missions/mission123/simulation/incident-replan",
            json={
                "incident_count": 1,
                "strategy": "guided",
                "num_vehicles": 2,
                "max_vehicles": 1,
                "vehicle_capacity": 200,
                "speed_multiplier": 1.0,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("delta_kpi", response.json())
        simulate_incident_replan_mock.assert_called_once()
        args, _kwargs = simulate_incident_replan_mock.call_args
        self.assertEqual(args[0], "mission123")
        self.assertEqual(args[1]["max_vehicles"], 1)

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

    @patch("backend.app.services.create_versus_match", return_value=VERSUS_MATCH_RESPONSE)
    def test_create_versus_match_success(self, create_versus_match_mock):
        response = self.client.post(
            "/api/versus/matches",
            json={"player_id": "player001", "mode": "private", "template_id": "paris_duel", "winner_rule": "score_time"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["match_id"], "match123")
        create_versus_match_mock.assert_called_once()

    @patch("backend.app.services.create_versus_match", return_value=VERSUS_MATCH_RESPONSE)
    def test_create_versus_match_custom_map_payload(self, create_versus_match_mock):
        response = self.client.post(
            "/api/versus/matches",
            json={
                "player_id": "player001",
                "mode": "private",
                "map_source": "custom",
                "winner_rule": "time",
                "mission_config": {
                    "zone": "Lyon Centre",
                    "num_clients": 20,
                    "budget": 2200,
                    "sleigh_cost": 500,
                    "max_vehicles": 4,
                    "weather_key": "Rain",
                    "random_incidents": True,
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        create_versus_match_mock.assert_called_once()
        args, _kwargs = create_versus_match_mock.call_args
        self.assertEqual(args[0]["mission_config"]["max_vehicles"], 4)

    def test_create_versus_match_custom_map_invalid_max_vehicles(self):
        response = self.client.post(
            "/api/versus/matches",
            json={
                "player_id": "player001",
                "mode": "private",
                "map_source": "custom",
                "winner_rule": "time",
                "mission_config": {
                    "zone": "Lyon Centre",
                    "num_clients": 20,
                    "budget": 2200,
                    "sleigh_cost": 500,
                    "max_vehicles": 30,
                    "weather_key": "Rain",
                    "random_incidents": True,
                },
            },
        )
        self.assertEqual(response.status_code, 422)

    @patch("backend.app.services.join_versus_match", side_effect=RuntimeError("Partie indisponible"))
    def test_join_versus_match_conflict(self, _join_versus_match_mock):
        response = self.client.post(
            "/api/versus/matches/join",
            json={"player_id": "player002", "join_code": "ABC123"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Partie indisponible")

    @patch("backend.app.services.enter_versus_queue", return_value={"status": "queued"})
    def test_enter_versus_queue_success(self, enter_versus_queue_mock):
        response = self.client.post(
            "/api/versus/queue/enter",
            json={"player_id": "player001", "template_id": "paris_duel", "winner_rule": "score_time"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "queued")
        enter_versus_queue_mock.assert_called_once()

    @patch(
        "backend.app.services.get_versus_queue_status",
        return_value={"status": "queued", "queue_entry": {"player_id": "player001"}},
    )
    def test_get_versus_queue_status_queued(self, get_versus_queue_status_mock):
        response = self.client.get(
            "/api/versus/queue/status?player_id=player001&template_id=paris_duel&winner_rule=score_time"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "queued")
        get_versus_queue_status_mock.assert_called_once_with(
            {
                "player_id": "player001",
                "template_id": "paris_duel",
                "winner_rule": "score_time",
            }
        )

    @patch(
        "backend.app.services.get_versus_queue_status",
        return_value={"status": "matched", "match": VERSUS_MATCH_RESPONSE},
    )
    def test_get_versus_queue_status_matched(self, _get_versus_queue_status_mock):
        response = self.client.get("/api/versus/queue/status?player_id=player001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "matched")
        self.assertEqual(response.json()["match"]["match_id"], "match123")

    @patch("backend.app.services.get_versus_queue_status", side_effect=ValueError("Template invalide"))
    def test_get_versus_queue_status_bad_request(self, _get_versus_queue_status_mock):
        response = self.client.get("/api/versus/queue/status?player_id=player001")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Template invalide")

    @patch("backend.app.services.submit_versus_attempt", side_effect=ValueError("Soumission invalide"))
    def test_submit_versus_attempt_bad_request(self, _submit_versus_attempt_mock):
        response = self.client.post(
            "/api/versus/matches/match123/submit",
            json={"player_id": "player001"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Soumission invalide")

    @patch("backend.app.services.list_versus_leaderboard", return_value={"entries": []})
    def test_list_versus_leaderboard_success(self, list_versus_leaderboard_mock):
        response = self.client.get("/api/versus/leaderboard?limit=5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"entries": []})
        list_versus_leaderboard_mock.assert_called_once_with(limit=5)

    @patch("backend.app.services.list_versus_player_stats", return_value={"entries": []})
    def test_list_versus_player_stats_success(self, list_versus_player_stats_mock):
        response = self.client.get("/api/versus/stats?limit=7&max_matches=300")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"entries": []})
        list_versus_player_stats_mock.assert_called_once_with(limit=7, max_matches=300)


if __name__ == "__main__":
    unittest.main()
