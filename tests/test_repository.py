import tempfile
import unittest
import sqlite3
from pathlib import Path

from backend.app import repository


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "missions.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_upsert_and_get_snapshot(self):
        repository.init_db(self.db_path)
        repository.upsert_mission(
            mission_id="mission-1",
            root_dir="/tmp/mission-1",
            mission={"zone": "Paris 5e", "num_clients": 4},
            weather={"desc": "Ciel degage", "factor": 1.0},
            incidents={"count": 1, "segments": []},
            human_state={"routes_by_sleigh": {"0": [1]}},
            status="created",
            db_path=self.db_path,
        )

        snapshot = repository.get_mission_snapshot("mission-1", db_path=self.db_path)

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["mission_id"], "mission-1")
        self.assertEqual(snapshot["mission"]["zone"], "Paris 5e")
        self.assertEqual(snapshot["weather"]["factor"], 1.0)
        self.assertEqual(snapshot["status"], "created")

    def test_list_snapshots_sorted(self):
        repository.upsert_mission(
            mission_id="mission-a",
            root_dir="/tmp/mission-a",
            mission={"zone": "A"},
            status="created",
            db_path=self.db_path,
        )
        repository.upsert_mission(
            mission_id="mission-b",
            root_dir="/tmp/mission-b",
            mission={"zone": "B"},
            results={"status": "Success"},
            status="solved",
            db_path=self.db_path,
        )

        snapshots = repository.list_mission_snapshots(limit=10, db_path=self.db_path)

        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0]["mission_id"], "mission-b")
        self.assertEqual(snapshots[0]["status"], "solved")
        self.assertEqual(snapshots[1]["mission_id"], "mission-a")

    def test_players_are_joined_into_leaderboard_entries(self):
        repository.upsert_mission(
            mission_id="mission-42",
            root_dir="/tmp/mission-42",
            mission={"zone": "Lille"},
            status="solved",
            db_path=self.db_path,
        )
        repository.upsert_player(
            player_id="captain-north",
            display_name="Capitaine Nord",
            callsign="POLAR-7",
            avatar="🦌",
            db_path=self.db_path,
        )
        repository.save_leaderboard_entry(
            mission_id="mission-42",
            zone="Lille",
            score=91.5,
            rank="S",
            player_name="Nom local",
            player_id="captain-north",
            db_path=self.db_path,
        )

        entries = repository.list_leaderboard(limit=5, db_path=self.db_path)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["player_name"], "Capitaine Nord")
        self.assertEqual(entries[0]["player_id"], "captain-north")
        self.assertEqual(entries[0]["callsign"], "POLAR-7")
        self.assertEqual(entries[0]["avatar"], "🦌")

    def test_init_db_migrates_legacy_leaderboard_without_player_id(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE leaderboard (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL,
                    zone TEXT NOT NULL,
                    score REAL NOT NULL,
                    rank TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

        repository.init_db(self.db_path)

        with sqlite3.connect(self.db_path) as conn:
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(leaderboard)").fetchall()
            }
            indexes = {
                row[1]
                for row in conn.execute("PRAGMA index_list(leaderboard)").fetchall()
            }

        self.assertIn("player_id", columns)
        self.assertIn("idx_leaderboard_player_id", indexes)

    def test_create_versus_match_and_participants(self):
        repository.upsert_player(
            player_id="p1",
            display_name="Host",
            db_path=self.db_path,
        )
        repository.upsert_player(
            player_id="p2",
            display_name="Guest",
            db_path=self.db_path,
        )
        repository.create_versus_match(
            match_id="match-1",
            mode="private",
            template_id="paris_duel",
            map_source="template",
            mission_config=None,
            winner_rule="score_time",
            host_player_id="p1",
            join_code="ABC123",
            status="waiting_opponent",
            db_path=self.db_path,
        )
        repository.add_versus_participant("match-1", "p2", seat=1, db_path=self.db_path)
        repository.update_versus_match("match-1", status="waiting_ready", db_path=self.db_path)

        match = repository.get_versus_match("match-1", db_path=self.db_path)
        participants = repository.list_versus_participants("match-1", db_path=self.db_path)

        self.assertIsNotNone(match)
        self.assertEqual(match["status"], "waiting_ready")
        self.assertEqual(len(participants), 2)
        self.assertEqual(participants[0]["player_id"], "p1")
        self.assertEqual(participants[1]["player_id"], "p2")

    def test_versus_queue_and_invites(self):
        repository.upsert_player(
            player_id="p1",
            display_name="Host",
            db_path=self.db_path,
        )
        repository.upsert_player(
            player_id="p2",
            display_name="Guest",
            db_path=self.db_path,
        )
        repository.enqueue_versus_player("p1", "paris_duel", "score_time", db_path=self.db_path)
        opponent = repository.find_versus_queue_opponent("p2", "paris_duel", "score_time", db_path=self.db_path)
        self.assertIsNotNone(opponent)
        self.assertEqual(opponent["player_id"], "p1")

        repository.create_versus_invite(
            invite_id="invite-1",
            inviter_player_id="p1",
            invitee_player_id="p2",
            template_id="paris_duel",
            map_source="template",
            mission_config=None,
            winner_rule="score_time",
            db_path=self.db_path,
        )
        invites = repository.list_pending_versus_invites("p2", db_path=self.db_path)
        self.assertEqual(len(invites), 1)
        self.assertEqual(invites[0]["invite_id"], "invite-1")

    def test_custom_map_payload_is_persisted_for_match_and_invite(self):
        repository.upsert_player(
            player_id="p1",
            display_name="Host",
            db_path=self.db_path,
        )
        repository.upsert_player(
            player_id="p2",
            display_name="Guest",
            db_path=self.db_path,
        )
        mission_config = {
            "zone": "Lyon Centre",
            "city": "Lyon",
            "num_clients": 30,
            "budget": 3500,
            "sleigh_cost": 700,
            "weather_key": "Rain",
            "random_incidents": True,
            "search_radius_km": 4.5,
        }
        repository.create_versus_match(
            match_id="match-custom",
            mode="private",
            template_id="custom_map",
            map_source="custom",
            mission_config=mission_config,
            winner_rule="score_time",
            host_player_id="p1",
            join_code="ZZ99YY",
            status="waiting_opponent",
            db_path=self.db_path,
        )
        repository.create_versus_invite(
            invite_id="invite-custom",
            inviter_player_id="p1",
            invitee_player_id="p2",
            template_id="custom_map",
            map_source="custom",
            mission_config=mission_config,
            winner_rule="time",
            db_path=self.db_path,
        )

        stored_match = repository.get_versus_match("match-custom", db_path=self.db_path)
        stored_invite = repository.get_versus_invite("invite-custom", db_path=self.db_path)

        self.assertEqual(stored_match["map_source"], "custom")
        self.assertEqual(stored_match["mission_config"]["zone"], "Lyon Centre")
        self.assertEqual(stored_invite["map_source"], "custom")
        self.assertEqual(stored_invite["mission_config"]["num_clients"], 30)

    def test_list_versus_player_history_returns_finished_match_rows(self):
        repository.upsert_player(player_id="p1", display_name="Alpha", db_path=self.db_path)
        repository.upsert_player(player_id="p2", display_name="Bravo", db_path=self.db_path)
        repository.upsert_player(player_id="p3", display_name="Charlie", db_path=self.db_path)

        repository.create_versus_match(
            match_id="m1",
            mode="private",
            template_id="paris_duel",
            map_source="template",
            mission_config=None,
            winner_rule="score_time",
            host_player_id="p1",
            join_code="A1B2C3",
            status="waiting_opponent",
            db_path=self.db_path,
        )
        repository.add_versus_participant("m1", "p2", seat=1, db_path=self.db_path)
        repository.update_versus_participant("m1", "p1", state="submitted", total_time_s=600, is_valid_submission=1, db_path=self.db_path)
        repository.update_versus_participant("m1", "p2", state="submitted", total_time_s=720, is_valid_submission=1, db_path=self.db_path)
        repository.update_versus_match(
            "m1",
            status="finished",
            winner_player_id="p1",
            completed_at="2026-04-24T12:00:00+00:00",
            db_path=self.db_path,
        )

        repository.create_versus_match(
            match_id="m2",
            mode="invite",
            template_id="paris_duel",
            map_source="template",
            mission_config=None,
            winner_rule="time",
            host_player_id="p2",
            join_code="D4E5F6",
            status="waiting_opponent",
            db_path=self.db_path,
        )
        repository.add_versus_participant("m2", "p1", seat=1, db_path=self.db_path)
        repository.update_versus_participant("m2", "p2", state="submitted", total_time_s=540, is_valid_submission=1, db_path=self.db_path)
        repository.update_versus_participant("m2", "p1", state="submitted", total_time_s=580, is_valid_submission=1, db_path=self.db_path)
        repository.update_versus_match(
            "m2",
            status="finished",
            winner_player_id="p2",
            completed_at="2026-04-24T13:00:00+00:00",
            db_path=self.db_path,
        )

        repository.create_versus_match(
            match_id="m3",
            mode="private",
            template_id="paris_duel",
            map_source="template",
            mission_config=None,
            winner_rule="objectives",
            host_player_id="p1",
            join_code="G7H8J9",
            status="waiting_opponent",
            db_path=self.db_path,
        )
        repository.add_versus_participant("m3", "p3", seat=1, db_path=self.db_path)
        repository.update_versus_participant("m3", "p1", state="forfeit", is_valid_submission=0, db_path=self.db_path)
        repository.update_versus_participant("m3", "p3", state="submitted", total_time_s=660, is_valid_submission=1, db_path=self.db_path)
        repository.update_versus_match(
            "m3",
            status="finished",
            winner_player_id="p3",
            completed_at="2026-04-24T14:00:00+00:00",
            db_path=self.db_path,
        )

        history = repository.list_versus_player_history(max_matches=10, db_path=self.db_path)
        self.assertEqual(len(history), 6)
        self.assertEqual(history[0]["match_id"], "m3")
        self.assertIn(history[0]["winner_rule"], {"score_time", "time", "objectives"})


if __name__ == "__main__":
    unittest.main()
