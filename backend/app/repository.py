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


def init_db(db_path: str | Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
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
            CREATE INDEX IF NOT EXISTS idx_mission_snapshots_updated_at
            ON mission_snapshots(updated_at DESC);
            """
        )


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
