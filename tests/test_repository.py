import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
