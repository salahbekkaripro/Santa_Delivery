from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.mission_paths import ROOT_DIR


DB_PATH = ROOT_DIR / "cache" / "api_missions" / "operation_noel.db"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(payload: Any) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False)


def _json_loads(payload: str | None) -> Any:
    if not payload:
        return None
    return json.loads(payload)


def get_db_path() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    if not _has_column(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def init_db(db_path: str | Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                email TEXT,
                password_hash TEXT,
                callsign TEXT,
                avatar TEXT,
                last_login_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );
            CREATE TABLE IF NOT EXISTS mission_snapshots (
                mission_id TEXT PRIMARY KEY,
                root_dir TEXT NOT NULL,
                mission_json TEXT NOT NULL,
                weather_json TEXT,
                incidents_json TEXT,
                human_state_json TEXT,
                results_json TEXT,
                benchmark_json TEXT,
                comparison_json TEXT,
                debrief_json TEXT,
                status TEXT NOT NULL DEFAULT 'created',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id TEXT NOT NULL,
                zone TEXT NOT NULL,
                score REAL NOT NULL,
                rank TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (mission_id) REFERENCES mission_snapshots(mission_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );
            """
        )
        _ensure_column(conn, "players", "email", "email TEXT")
        _ensure_column(conn, "players", "password_hash", "password_hash TEXT")
        _ensure_column(conn, "players", "last_login_at", "last_login_at TEXT")
        _ensure_column(conn, "leaderboard", "player_id", "player_id TEXT")
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_mission_snapshots_updated_at
            ON mission_snapshots(updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_score
            ON leaderboard(score DESC);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_player_id
            ON leaderboard(player_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_players_email
            ON players(email);
            CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_player_id
            ON password_reset_tokens(player_id);
            """
        )
        conn.commit()


def upsert_mission(
    mission_id: str,
    root_dir: str,
    mission: dict,
    weather: dict | None = None,
    incidents: dict | None = None,
    human_state: dict | None = None,
    results: dict | None = None,
    benchmark: dict | None = None,
    comparison: dict | None = None,
    debrief: dict | None = None,
    status: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        existing = conn.execute(
            "SELECT created_at FROM mission_snapshots WHERE mission_id = ?",
            (mission_id,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        if status is None:
            status = "solved" if results else "in_progress"
        conn.execute(
            """
            INSERT INTO mission_snapshots (
                mission_id, root_dir, mission_json, weather_json, incidents_json, human_state_json,
                results_json, benchmark_json, comparison_json, debrief_json, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mission_id) DO UPDATE SET
                root_dir = excluded.root_dir,
                mission_json = excluded.mission_json,
                weather_json = COALESCE(excluded.weather_json, mission_snapshots.weather_json),
                incidents_json = COALESCE(excluded.incidents_json, mission_snapshots.incidents_json),
                human_state_json = COALESCE(excluded.human_state_json, mission_snapshots.human_state_json),
                results_json = COALESCE(excluded.results_json, mission_snapshots.results_json),
                benchmark_json = COALESCE(excluded.benchmark_json, mission_snapshots.benchmark_json),
                comparison_json = COALESCE(excluded.comparison_json, mission_snapshots.comparison_json),
                debrief_json = COALESCE(excluded.debrief_json, mission_snapshots.debrief_json),
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                mission_id,
                root_dir,
                _json_dumps(mission),
                _json_dumps(weather),
                _json_dumps(incidents),
                _json_dumps(human_state),
                _json_dumps(results),
                _json_dumps(benchmark),
                _json_dumps(comparison),
                _json_dumps(debrief),
                status,
                created_at,
                now,
            ),
        )
        conn.commit()


def get_mission_snapshot(mission_id: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT mission_id, root_dir, mission_json, weather_json, incidents_json, human_state_json,
                   results_json, benchmark_json, comparison_json, debrief_json, status, created_at, updated_at
            FROM mission_snapshots
            WHERE mission_id = ?
            """,
            (mission_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "mission_id": row["mission_id"],
        "root_dir": row["root_dir"],
        "mission": _json_loads(row["mission_json"]),
        "weather": _json_loads(row["weather_json"]),
        "incidents": _json_loads(row["incidents_json"]),
        "human_state": _json_loads(row["human_state_json"]),
        "results": _json_loads(row["results_json"]),
        "benchmark": _json_loads(row["benchmark_json"]),
        "comparison": _json_loads(row["comparison_json"]),
        "debrief": _json_loads(row["debrief_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_mission_snapshots(limit: int = 50, db_path: str | Path | None = None) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT mission_id, mission_json, status, created_at, updated_at
            FROM mission_snapshots
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [
        {
            "mission_id": row["mission_id"],
            "mission": _json_loads(row["mission_json"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def upsert_player(
    player_id: str,
    display_name: str,
    email: str | None = None,
    password_hash: str | None = None,
    callsign: str | None = None,
    avatar: str | None = None,
    last_login_at: str | None = None,
    db_path: str | Path | None = None,
) -> dict:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        existing = conn.execute(
            "SELECT created_at, email, password_hash, last_login_at FROM players WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        email = email if email is not None else (existing["email"] if existing else None)
        password_hash = password_hash if password_hash is not None else (existing["password_hash"] if existing else None)
        last_login_at = last_login_at if last_login_at is not None else (existing["last_login_at"] if existing else None)
        conn.execute(
            """
            INSERT INTO players (
                player_id, display_name, email, password_hash, callsign, avatar, last_login_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                display_name = excluded.display_name,
                email = excluded.email,
                password_hash = excluded.password_hash,
                callsign = excluded.callsign,
                avatar = excluded.avatar,
                last_login_at = excluded.last_login_at,
                updated_at = excluded.updated_at
            """,
            (player_id, display_name, email, password_hash, callsign, avatar, last_login_at, created_at, now),
        )
        conn.commit()
    return {
        "player_id": player_id,
        "display_name": display_name,
        "email": email,
        "callsign": callsign,
        "avatar": avatar,
        "last_login_at": last_login_at,
        "created_at": created_at,
        "updated_at": now,
    }


def get_player(player_id: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT player_id, display_name, email, callsign, avatar, last_login_at, created_at, updated_at
            FROM players
            WHERE player_id = ?
            """,
            (player_id,),
        ).fetchone()
    return dict(row) if row else None


def get_player_by_email(email: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT player_id, display_name, email, password_hash, callsign, avatar, last_login_at, created_at, updated_at
            FROM players
            WHERE email = ?
            """,
            (email,),
        ).fetchone()
    return dict(row) if row else None


def create_password_reset_token(
    player_id: str,
    token_hash: str,
    expires_at: str,
    db_path: str | Path | None = None,
) -> dict:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO password_reset_tokens (player_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (player_id, token_hash, expires_at, now),
        )
        conn.commit()
    return {
        "player_id": player_id,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "created_at": now,
    }


def get_password_reset_token(token_hash: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                password_reset_tokens.id,
                password_reset_tokens.player_id,
                password_reset_tokens.token_hash,
                password_reset_tokens.expires_at,
                password_reset_tokens.consumed_at,
                password_reset_tokens.created_at,
                players.display_name,
                players.email,
                players.callsign,
                players.avatar,
                players.created_at AS player_created_at,
                players.updated_at AS player_updated_at
            FROM password_reset_tokens
            JOIN players ON players.player_id = password_reset_tokens.player_id
            WHERE password_reset_tokens.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
    return dict(row) if row else None


def consume_password_reset_token(token_hash: str, db_path: str | Path | None = None) -> None:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE password_reset_tokens
            SET consumed_at = ?
            WHERE token_hash = ? AND consumed_at IS NULL
            """,
            (now, token_hash),
        )
        conn.commit()


def update_player_password(
    player_id: str,
    password_hash: str,
    db_path: str | Path | None = None,
) -> dict | None:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE players
            SET password_hash = ?, updated_at = ?
            WHERE player_id = ?
            """,
            (password_hash, now, player_id),
        )
        conn.commit()
    return get_player(player_id, db_path=db_path)


def save_leaderboard_entry(
    mission_id: str,
    zone: str,
    score: float,
    rank: str,
    player_name: str = "Père Noël",
    player_id: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO leaderboard (mission_id, zone, score, rank, player_name, player_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mission_id, zone, score, rank, player_name, player_id, now),
        )
        conn.commit()


def list_leaderboard(limit: int = 20, db_path: str | Path | None = None) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                leaderboard.mission_id,
                leaderboard.zone,
                leaderboard.score,
                leaderboard.rank,
                COALESCE(players.display_name, leaderboard.player_name) AS player_name,
                leaderboard.player_id,
                players.callsign,
                players.avatar,
                leaderboard.created_at
            FROM leaderboard
            LEFT JOIN players ON players.player_id = leaderboard.player_id
            ORDER BY leaderboard.score DESC, leaderboard.created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]
