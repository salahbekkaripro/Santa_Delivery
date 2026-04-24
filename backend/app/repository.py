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
            CREATE TABLE IF NOT EXISTS versus_matches (
                match_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                template_id TEXT NOT NULL,
                map_source TEXT NOT NULL DEFAULT 'template',
                mission_config_json TEXT,
                winner_rule TEXT NOT NULL,
                join_code TEXT,
                host_player_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'waiting_opponent',
                reference_mission_id TEXT,
                started_at TEXT,
                completed_at TEXT,
                winner_player_id TEXT,
                result_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (host_player_id) REFERENCES players(player_id),
                FOREIGN KEY (winner_player_id) REFERENCES players(player_id)
            );
            CREATE TABLE IF NOT EXISTS versus_participants (
                match_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                seat INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'joined',
                mission_id TEXT,
                ready_at TEXT,
                submitted_at TEXT,
                score REAL,
                total_time_s REAL,
                objectives_completed INTEGER,
                is_valid_submission INTEGER NOT NULL DEFAULT 0,
                forfeit_at TEXT,
                last_seen_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (match_id, player_id),
                FOREIGN KEY (match_id) REFERENCES versus_matches(match_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );
            CREATE TABLE IF NOT EXISTS versus_invites (
                invite_id TEXT PRIMARY KEY,
                inviter_player_id TEXT NOT NULL,
                invitee_player_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                map_source TEXT NOT NULL DEFAULT 'template',
                mission_config_json TEXT,
                winner_rule TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                match_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                responded_at TEXT,
                FOREIGN KEY (inviter_player_id) REFERENCES players(player_id),
                FOREIGN KEY (invitee_player_id) REFERENCES players(player_id),
                FOREIGN KEY (match_id) REFERENCES versus_matches(match_id)
            );
            CREATE TABLE IF NOT EXISTS versus_queue (
                player_id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                winner_rule TEXT NOT NULL,
                enqueued_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );
            CREATE TABLE IF NOT EXISTS versus_leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                winner_player_id TEXT NOT NULL,
                loser_player_id TEXT,
                winner_score REAL,
                winner_time_s REAL,
                winner_rule TEXT NOT NULL,
                template_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (match_id) REFERENCES versus_matches(match_id),
                FOREIGN KEY (winner_player_id) REFERENCES players(player_id),
                FOREIGN KEY (loser_player_id) REFERENCES players(player_id)
            );
            """
        )
        _ensure_column(conn, "players", "email", "email TEXT")
        _ensure_column(conn, "players", "password_hash", "password_hash TEXT")
        _ensure_column(conn, "players", "last_login_at", "last_login_at TEXT")
        _ensure_column(conn, "leaderboard", "player_id", "player_id TEXT")
        _ensure_column(conn, "versus_matches", "map_source", "map_source TEXT NOT NULL DEFAULT 'template'")
        _ensure_column(conn, "versus_matches", "mission_config_json", "mission_config_json TEXT")
        _ensure_column(conn, "versus_invites", "map_source", "map_source TEXT NOT NULL DEFAULT 'template'")
        _ensure_column(conn, "versus_invites", "mission_config_json", "mission_config_json TEXT")
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
            CREATE UNIQUE INDEX IF NOT EXISTS idx_versus_matches_join_code
            ON versus_matches(join_code);
            CREATE INDEX IF NOT EXISTS idx_versus_matches_status
            ON versus_matches(status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_versus_participants_match
            ON versus_participants(match_id, seat);
            CREATE INDEX IF NOT EXISTS idx_versus_participants_player
            ON versus_participants(player_id, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_versus_invites_invitee_status
            ON versus_invites(invitee_player_id, status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_versus_queue_template_rule
            ON versus_queue(template_id, winner_rule, enqueued_at ASC);
            CREATE INDEX IF NOT EXISTS idx_versus_leaderboard_created_at
            ON versus_leaderboard(created_at DESC);
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


_VERSUS_MATCH_FIELDS = {
    "status",
    "reference_mission_id",
    "started_at",
    "completed_at",
    "winner_player_id",
    "result_reason",
    "join_code",
    "map_source",
    "mission_config_json",
}

_VERSUS_PARTICIPANT_FIELDS = {
    "state",
    "mission_id",
    "ready_at",
    "submitted_at",
    "score",
    "total_time_s",
    "objectives_completed",
    "is_valid_submission",
    "forfeit_at",
    "last_seen_at",
}


def create_versus_match(
    match_id: str,
    mode: str,
    template_id: str,
    map_source: str,
    mission_config: dict | None,
    winner_rule: str,
    host_player_id: str,
    join_code: str | None = None,
    status: str = "waiting_opponent",
    db_path: str | Path | None = None,
) -> dict:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO versus_matches (
                match_id, mode, template_id, map_source, mission_config_json, winner_rule, join_code, host_player_id, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match_id,
                mode,
                template_id,
                map_source,
                _json_dumps(mission_config),
                winner_rule,
                join_code,
                host_player_id,
                status,
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO versus_participants (
                match_id, player_id, seat, state, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (match_id, host_player_id, 0, "joined", now, now),
        )
        conn.commit()
    return get_versus_match(match_id, db_path=db_path) or {}


def get_versus_match(match_id: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT match_id, mode, template_id, map_source, mission_config_json, winner_rule, join_code, host_player_id, status,
                   reference_mission_id, started_at, completed_at, winner_player_id, result_reason,
                   created_at, updated_at
            FROM versus_matches
            WHERE match_id = ?
            """,
            (match_id,),
        ).fetchone()
    if not row:
        return None
    payload = dict(row)
    payload["mission_config"] = _json_loads(payload.pop("mission_config_json", None))
    return payload


def get_versus_match_by_join_code(join_code: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT match_id, mode, template_id, map_source, mission_config_json, winner_rule, join_code, host_player_id, status,
                   reference_mission_id, started_at, completed_at, winner_player_id, result_reason,
                   created_at, updated_at
            FROM versus_matches
            WHERE join_code = ?
            """,
            (join_code,),
        ).fetchone()
    if not row:
        return None
    payload = dict(row)
    payload["mission_config"] = _json_loads(payload.pop("mission_config_json", None))
    return payload


def list_versus_participants(match_id: str, db_path: str | Path | None = None) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                p.match_id,
                p.player_id,
                p.seat,
                p.state,
                p.mission_id,
                p.ready_at,
                p.submitted_at,
                p.score,
                p.total_time_s,
                p.objectives_completed,
                p.is_valid_submission,
                p.forfeit_at,
                p.last_seen_at,
                p.created_at,
                p.updated_at,
                players.display_name,
                players.callsign,
                players.avatar
            FROM versus_participants AS p
            LEFT JOIN players ON players.player_id = p.player_id
            WHERE p.match_id = ?
            ORDER BY p.seat ASC, p.created_at ASC
            """,
            (match_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_latest_versus_match_for_player(
    player_id: str,
    statuses: tuple[str, ...] = ("waiting_ready", "live"),
    db_path: str | Path | None = None,
) -> dict | None:
    init_db(db_path)
    if not statuses:
        return None
    placeholders = ", ".join("?" for _ in statuses)
    with connect(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT matches.match_id
            FROM versus_matches AS matches
            INNER JOIN versus_participants AS participants ON participants.match_id = matches.match_id
            WHERE participants.player_id = ? AND matches.status IN ({placeholders})
            ORDER BY matches.updated_at DESC
            LIMIT 1
            """,
            (player_id, *statuses),
        ).fetchone()
    if not row:
        return None
    return get_versus_match(str(row["match_id"]), db_path=db_path)


def get_versus_participant(match_id: str, player_id: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                p.match_id,
                p.player_id,
                p.seat,
                p.state,
                p.mission_id,
                p.ready_at,
                p.submitted_at,
                p.score,
                p.total_time_s,
                p.objectives_completed,
                p.is_valid_submission,
                p.forfeit_at,
                p.last_seen_at,
                p.created_at,
                p.updated_at,
                players.display_name,
                players.callsign,
                players.avatar
            FROM versus_participants AS p
            LEFT JOIN players ON players.player_id = p.player_id
            WHERE p.match_id = ? AND p.player_id = ?
            """,
            (match_id, player_id),
        ).fetchone()
    return dict(row) if row else None


def add_versus_participant(
    match_id: str,
    player_id: str,
    seat: int,
    state: str = "joined",
    db_path: str | Path | None = None,
) -> dict | None:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO versus_participants (
                match_id, player_id, seat, state, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (match_id, player_id, int(seat), state, now, now),
        )
        conn.commit()
    return get_versus_participant(match_id, player_id, db_path=db_path)


def update_versus_match(
    match_id: str,
    db_path: str | Path | None = None,
    **fields,
) -> None:
    payload = {key: value for key, value in fields.items() if key in _VERSUS_MATCH_FIELDS}
    if not payload:
        return
    if "mission_config_json" in payload and isinstance(payload["mission_config_json"], dict):
        payload["mission_config_json"] = _json_dumps(payload["mission_config_json"])
    init_db(db_path)
    payload["updated_at"] = _utcnow()
    keys = list(payload.keys())
    values = [payload[key] for key in keys]
    assignment = ", ".join(f"{key} = ?" for key in keys)
    with connect(db_path) as conn:
        conn.execute(
            f"UPDATE versus_matches SET {assignment} WHERE match_id = ?",
            (*values, match_id),
        )
        conn.commit()


def update_versus_participant(
    match_id: str,
    player_id: str,
    db_path: str | Path | None = None,
    **fields,
) -> None:
    payload = {key: value for key, value in fields.items() if key in _VERSUS_PARTICIPANT_FIELDS}
    if not payload:
        return
    init_db(db_path)
    payload["updated_at"] = _utcnow()
    keys = list(payload.keys())
    values = [payload[key] for key in keys]
    assignment = ", ".join(f"{key} = ?" for key in keys)
    with connect(db_path) as conn:
        conn.execute(
            f"UPDATE versus_participants SET {assignment} WHERE match_id = ? AND player_id = ?",
            (*values, match_id, player_id),
        )
        conn.commit()


def enqueue_versus_player(
    player_id: str,
    template_id: str,
    winner_rule: str,
    db_path: str | Path | None = None,
) -> dict:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        existing = conn.execute(
            "SELECT enqueued_at FROM versus_queue WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        enqueued_at = existing["enqueued_at"] if existing else now
        conn.execute(
            """
            INSERT INTO versus_queue (player_id, template_id, winner_rule, enqueued_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                template_id = excluded.template_id,
                winner_rule = excluded.winner_rule,
                updated_at = excluded.updated_at
            """,
            (player_id, template_id, winner_rule, enqueued_at, now),
        )
        conn.commit()
    return get_versus_queue_entry(player_id, db_path=db_path) or {}


def get_versus_queue_entry(player_id: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT player_id, template_id, winner_rule, enqueued_at, updated_at
            FROM versus_queue
            WHERE player_id = ?
            """,
            (player_id,),
        ).fetchone()
    return dict(row) if row else None


def find_versus_queue_opponent(
    player_id: str,
    template_id: str,
    winner_rule: str,
    db_path: str | Path | None = None,
) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT player_id, template_id, winner_rule, enqueued_at, updated_at
            FROM versus_queue
            WHERE player_id <> ? AND template_id = ? AND winner_rule = ?
            ORDER BY enqueued_at ASC
            LIMIT 1
            """,
            (player_id, template_id, winner_rule),
        ).fetchone()
    return dict(row) if row else None


def remove_versus_queue_player(player_id: str, db_path: str | Path | None = None) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM versus_queue WHERE player_id = ?", (player_id,))
        conn.commit()


def create_versus_invite(
    invite_id: str,
    inviter_player_id: str,
    invitee_player_id: str,
    template_id: str,
    map_source: str,
    mission_config: dict | None,
    winner_rule: str,
    db_path: str | Path | None = None,
) -> dict | None:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO versus_invites (
                invite_id, inviter_player_id, invitee_player_id, template_id, map_source, mission_config_json, winner_rule, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                invite_id,
                inviter_player_id,
                invitee_player_id,
                template_id,
                map_source,
                _json_dumps(mission_config),
                winner_rule,
                now,
                now,
            ),
        )
        conn.commit()
    return get_versus_invite(invite_id, db_path=db_path)


def get_versus_invite(invite_id: str, db_path: str | Path | None = None) -> dict | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                invites.invite_id,
                invites.inviter_player_id,
                invites.invitee_player_id,
                invites.template_id,
                invites.map_source,
                invites.mission_config_json,
                invites.winner_rule,
                invites.status,
                invites.match_id,
                invites.created_at,
                invites.updated_at,
                invites.responded_at,
                inviter.display_name AS inviter_display_name,
                inviter.callsign AS inviter_callsign,
                inviter.avatar AS inviter_avatar,
                invitee.display_name AS invitee_display_name,
                invitee.callsign AS invitee_callsign,
                invitee.avatar AS invitee_avatar
            FROM versus_invites AS invites
            LEFT JOIN players AS inviter ON inviter.player_id = invites.inviter_player_id
            LEFT JOIN players AS invitee ON invitee.player_id = invites.invitee_player_id
            WHERE invites.invite_id = ?
            """,
            (invite_id,),
        ).fetchone()
    if not row:
        return None
    payload = dict(row)
    payload["mission_config"] = _json_loads(payload.pop("mission_config_json", None))
    return payload


def list_pending_versus_invites(invitee_player_id: str, db_path: str | Path | None = None) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                invites.invite_id,
                invites.inviter_player_id,
                invites.invitee_player_id,
                invites.template_id,
                invites.map_source,
                invites.mission_config_json,
                invites.winner_rule,
                invites.status,
                invites.match_id,
                invites.created_at,
                invites.updated_at,
                invites.responded_at,
                inviter.display_name AS inviter_display_name,
                inviter.callsign AS inviter_callsign,
                inviter.avatar AS inviter_avatar
            FROM versus_invites AS invites
            LEFT JOIN players AS inviter ON inviter.player_id = invites.inviter_player_id
            WHERE invites.invitee_player_id = ? AND invites.status = 'pending'
            ORDER BY invites.created_at DESC
            """,
            (invitee_player_id,),
        ).fetchall()
    payloads: list[dict] = []
    for row in rows:
        payload = dict(row)
        payload["mission_config"] = _json_loads(payload.pop("mission_config_json", None))
        payloads.append(payload)
    return payloads


def update_versus_invite(
    invite_id: str,
    *,
    status: str,
    match_id: str | None = None,
    responded_at: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE versus_invites
            SET status = ?, match_id = COALESCE(?, match_id), responded_at = COALESCE(?, responded_at), updated_at = ?
            WHERE invite_id = ?
            """,
            (status, match_id, responded_at, now, invite_id),
        )
        conn.commit()


def save_versus_leaderboard_entry(
    match_id: str,
    winner_player_id: str,
    loser_player_id: str | None,
    winner_score: float | None,
    winner_time_s: float | None,
    winner_rule: str,
    template_id: str,
    db_path: str | Path | None = None,
) -> None:
    init_db(db_path)
    now = _utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO versus_leaderboard (
                match_id, winner_player_id, loser_player_id, winner_score, winner_time_s, winner_rule, template_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (match_id, winner_player_id, loser_player_id, winner_score, winner_time_s, winner_rule, template_id, now),
        )
        conn.commit()


def list_versus_leaderboard(limit: int = 20, db_path: str | Path | None = None) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                leaderboard.match_id,
                leaderboard.winner_player_id,
                winner.display_name AS winner_display_name,
                winner.callsign AS winner_callsign,
                winner.avatar AS winner_avatar,
                leaderboard.loser_player_id,
                loser.display_name AS loser_display_name,
                leaderboard.winner_score,
                leaderboard.winner_time_s,
                leaderboard.winner_rule,
                leaderboard.template_id,
                matches.map_source,
                matches.mission_config_json,
                leaderboard.created_at
            FROM versus_leaderboard AS leaderboard
            LEFT JOIN versus_matches AS matches ON matches.match_id = leaderboard.match_id
            LEFT JOIN players AS winner ON winner.player_id = leaderboard.winner_player_id
            LEFT JOIN players AS loser ON loser.player_id = leaderboard.loser_player_id
            ORDER BY leaderboard.created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    payloads: list[dict] = []
    for row in rows:
        payload = dict(row)
        payload["mission_config"] = _json_loads(payload.pop("mission_config_json", None))
        payloads.append(payload)
    return payloads


def list_versus_player_history(
    max_matches: int = 500,
    db_path: str | Path | None = None,
) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            WITH recent_matches AS (
                SELECT
                    match_id,
                    winner_player_id,
                    winner_rule,
                    completed_at,
                    created_at
                FROM versus_matches
                WHERE status = 'finished'
                ORDER BY COALESCE(completed_at, created_at) DESC
                LIMIT ?
            )
            SELECT
                matches.match_id,
                matches.winner_player_id,
                matches.winner_rule,
                matches.completed_at,
                matches.created_at,
                participants.player_id,
                participants.total_time_s,
                participants.score,
                participants.is_valid_submission,
                players.display_name,
                players.callsign,
                players.avatar
            FROM recent_matches AS matches
            INNER JOIN versus_participants AS participants ON participants.match_id = matches.match_id
            LEFT JOIN players ON players.player_id = participants.player_id
            ORDER BY COALESCE(matches.completed_at, matches.created_at) DESC, participants.seat ASC
            """,
            (int(max_matches),),
        ).fetchall()
    return [dict(row) for row in rows]
