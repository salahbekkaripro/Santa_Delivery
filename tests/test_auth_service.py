import tempfile
import unittest
from pathlib import Path

from backend.app import repository, services


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "auth.db"
        self.previous_db_path = repository.DB_PATH
        repository.DB_PATH = self.db_path

    def tearDown(self):
        repository.DB_PATH = self.previous_db_path
        self.temp_dir.cleanup()

    def test_register_login_and_reset_password_flow(self):
        created = services.register_player(
            {
                "display_name": "Capitaine Nord",
                "email": "capitaine@pole-nord.com",
                "password": "motdepasse123",
                "callsign": "POLAR-7",
                "avatar": "🦌",
            }
        )

        self.assertEqual(created["email"], "capitaine@pole-nord.com")
        self.assertEqual(created["display_name"], "Capitaine Nord")

        logged = services.login_player({"email": "capitaine@pole-nord.com", "password": "motdepasse123"})
        self.assertEqual(logged["player_id"], created["player_id"])
        self.assertIsNotNone(logged["last_login_at"])

        reset_request = services.request_password_reset({"email": "capitaine@pole-nord.com"})
        self.assertEqual(reset_request["status"], "reset_requested")
        self.assertIn("/reset-password?token=", reset_request["reset_url"])

        reset_player = services.reset_password(
            {
                "token": reset_request["reset_token"],
                "password": "nouveaumotdepasse456",
            }
        )
        self.assertEqual(reset_player["player_id"], created["player_id"])

        relogged = services.login_player({"email": "capitaine@pole-nord.com", "password": "nouveaumotdepasse456"})
        self.assertEqual(relogged["player_id"], created["player_id"])


if __name__ == "__main__":
    unittest.main()
