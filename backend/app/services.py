from __future__ import annotations

import json
import hashlib
import hmac
import random
import secrets
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from final_scripts.solve_santa_final import solve_vrp
from backend.app import repository
from scripts.benchmark_engine import calculate_benchmark
from scripts.generator_engine import generate_new_zone
from scripts.mission_paths import MissionPaths, mission_paths
from scripts.routing_payloads import (
    WEATHER_MAP,
    build_ai_payload,
    build_human_eta_payload,
    build_human_live_stats,
    compute_route_options,
    default_human_state,
    format_clock,
    get_point_latlon,
    human_state_from_payload,
    load_graph,
    load_weather,
    read_points,
    route_length_m,
    route_time_s,
    serialize_human_state,
    summarize_segments,
)
from scripts.weather_engine import get_real_weather, get_simulated_weather


AI_PROFILE_PRESETS = {
    "express": {
        "label": "Express",
        "signature": "Rush urbain",
        "description": "Cherche la tournée la plus rapide avec des arbitrages agressifs sur le temps.",
        "difficulty_bonus": 2.0,
        "optimization_target": "time",
        "speed_multiplier_factor": 1.12,
        "solver_time_limit_s": 12,
        "first_solution_strategy": "parallel_cheapest_insertion",
        "local_search_metaheuristic": "guided_local_search",
        "time_slack_s": 1800,
        "max_route_time_s": 14400,
        "drop_penalty": 1_000_000,
        "global_span_cost": 120,
    },
    "ecolo": {
        "label": "Écolo",
        "signature": "Trajectoires sobres",
        "description": "Réduit les kilomètres au prix d'une exécution un peu plus conservatrice.",
        "difficulty_bonus": 3.0,
        "optimization_target": "distance",
        "speed_multiplier_factor": 0.96,
        "solver_time_limit_s": 18,
        "first_solution_strategy": "path_cheapest_arc",
        "local_search_metaheuristic": "simulated_annealing",
        "time_slack_s": 3600,
        "max_route_time_s": 15600,
        "drop_penalty": 1_200_000,
        "global_span_cost": 80,
    },
    "prudent": {
        "label": "Prudent",
        "signature": "Marge de sécurité",
        "description": "Lisse les risques, garde de la marge sur les retours et absorbe mieux les incidents.",
        "difficulty_bonus": 4.0,
        "optimization_target": "time",
        "speed_multiplier_factor": 0.9,
        "solver_time_limit_s": 28,
        "first_solution_strategy": "parallel_cheapest_insertion",
        "local_search_metaheuristic": "guided_local_search",
        "time_slack_s": 5400,
        "max_route_time_s": 18000,
        "drop_penalty": 1_300_000,
        "global_span_cost": 160,
    },
    "opportuniste": {
        "label": "Opportuniste",
        "signature": "Rebond tactique",
        "description": "Change vite d'itinéraire et profite des ouvertures créées par la carte.",
        "difficulty_bonus": 4.0,
        "optimization_target": "time",
        "speed_multiplier_factor": 1.02,
        "solver_time_limit_s": 22,
        "first_solution_strategy": "savings",
        "local_search_metaheuristic": "tabu_search",
        "time_slack_s": 3000,
        "max_route_time_s": 15000,
        "drop_penalty": 1_050_000,
        "global_span_cost": 110,
    },
    "agressive": {
        "label": "Agressive",
        "signature": "Pression maximale",
        "description": "Prend plus de risques pour gagner du temps, quitte à laisser tomber quelques points coûteux.",
        "difficulty_bonus": 6.0,
        "optimization_target": "time",
        "speed_multiplier_factor": 1.18,
        "solver_time_limit_s": 10,
        "first_solution_strategy": "path_cheapest_arc",
        "local_search_metaheuristic": "guided_local_search",
        "time_slack_s": 1200,
        "max_route_time_s": 13800,
        "drop_penalty": 220_000,
        "global_span_cost": 60,
    },
    "championne": {
        "label": "Championne",
        "signature": "Meta complète",
        "description": "Combine vitesse, couverture et recherche plus profonde pour jouer la meilleure note possible.",
        "difficulty_bonus": 8.0,
        "optimization_target": "time",
        "speed_multiplier_factor": 1.08,
        "solver_time_limit_s": 30,
        "first_solution_strategy": "parallel_cheapest_insertion",
        "local_search_metaheuristic": "guided_local_search",
        "time_slack_s": 3600,
        "max_route_time_s": 18000,
        "drop_penalty": 1_500_000,
        "global_span_cost": 180,
    },
}

PASSWORD_HASH_ITERATIONS = 120_000
PASSWORD_RESET_TTL_MINUTES = 30


def _read_json(path: str | Path, default=None):
    file_path = Path(path)
    if not file_path.exists():
        return default
    with file_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: str | Path, payload: dict) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _normalize_email(value: str | None) -> str:
    return str(value or "").strip().lower()


def _validate_email(value: str) -> str:
    email = _normalize_email(value)
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Adresse email invalide")
    return email


def _hash_password(password: str) -> str:
    secret = str(password or "")
    if len(secret) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), PASSWORD_HASH_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest.hex()}"


def _verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations_raw, salt, digest = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_raw),
        ).hex()
        return hmac.compare_digest(calculated, digest)
    except (TypeError, ValueError):
        return False


def _public_player(player: dict) -> dict:
    return {
        "player_id": player["player_id"],
        "display_name": player["display_name"],
        "email": player.get("email"),
        "callsign": player.get("callsign"),
        "avatar": player.get("avatar"),
        "last_login_at": player.get("last_login_at"),
        "created_at": player["created_at"],
        "updated_at": player["updated_at"],
    }


def _sync_snapshot(
    mission_id: str,
    paths: MissionPaths,
    mission: dict,
    *,
    weather: dict | None = None,
    incidents: dict | None = None,
    human_state: dict | None = None,
    results: dict | None = None,
    benchmark: dict | None = None,
    comparison: dict | None = None,
    debrief: dict | None = None,
    status: str | None = None,
) -> None:
    repository.upsert_mission(
        mission_id=mission_id,
        root_dir=str(paths.root_dir),
        mission=mission,
        weather=weather,
        incidents=incidents,
        human_state=human_state,
        results=results,
        benchmark=benchmark,
        comparison=comparison,
        debrief=debrief,
        status=status,
    )


def _normalize_ai_profile(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii").strip().lower()
    return normalized or "express"


def resolve_ai_strategy(mission: dict, payload: dict) -> dict:
    if not mission.get("ai_profile"):
        optimization_target = str(payload.get("optimization_target", "time"))
        return {
            "profile": "adaptatif",
            "label": "Adaptative",
            "signature": "Mode libre",
            "description": "Réutilise les paramètres de mission sans biais de profil.",
            "difficulty_bonus": 0.0,
            "optimization_target": "distance" if optimization_target == "distance" else "time",
            "num_vehicles": max(1, int(payload.get("num_vehicles", 3))),
            "vehicle_capacity": max(1, int(payload.get("vehicle_capacity", 200))),
            "speed_multiplier": round(max(0.5, float(payload.get("speed_multiplier", 1.0))), 2),
            "solver_time_limit_s": 20,
            "first_solution_strategy": "path_cheapest_arc",
            "local_search_metaheuristic": "guided_local_search",
            "time_slack_s": 3600,
            "max_route_time_s": 14400,
            "drop_penalty": 1_000_000,
            "global_span_cost": 100,
        }

    profile_key = _normalize_ai_profile(mission.get("ai_profile"))
    preset = AI_PROFILE_PRESETS.get(profile_key, AI_PROFILE_PRESETS["express"])
    speed_multiplier = max(0.5, float(payload.get("speed_multiplier", 1.0)) * float(preset["speed_multiplier_factor"]))
    num_vehicles = max(1, int(payload.get("num_vehicles", 3)))
    vehicle_capacity = max(1, int(payload.get("vehicle_capacity", 200)))
    optimization_target = str(preset.get("optimization_target") or payload.get("optimization_target", "time"))

    # Missions à incidents: les profils prudents et champions prennent plus de marge pour rester stables.
    time_slack_s = int(preset["time_slack_s"])
    max_route_time_s = int(preset["max_route_time_s"])
    if mission.get("random_incidents") and profile_key in {"prudent", "championne"}:
        time_slack_s += 1200
        max_route_time_s += 900

    return {
        "profile": profile_key,
        "label": str(preset["label"]),
        "signature": str(preset["signature"]),
        "description": str(preset["description"]),
        "difficulty_bonus": float(preset["difficulty_bonus"]),
        "optimization_target": "distance" if optimization_target == "distance" else "time",
        "num_vehicles": num_vehicles,
        "vehicle_capacity": vehicle_capacity,
        "speed_multiplier": round(speed_multiplier, 2),
        "solver_time_limit_s": int(preset["solver_time_limit_s"]),
        "first_solution_strategy": str(preset["first_solution_strategy"]),
        "local_search_metaheuristic": str(preset["local_search_metaheuristic"]),
        "time_slack_s": time_slack_s,
        "max_route_time_s": max_route_time_s,
        "drop_penalty": int(preset["drop_penalty"]),
        "global_span_cost": int(preset["global_span_cost"]),
    }


def _build_human_sleigh_summaries(state, live_stats: dict[str, dict]) -> list[dict]:
    summaries: list[dict] = []
    for sleigh_key, route_ids in sorted(state.routes_by_sleigh.items(), key=lambda item: int(item[0])):
        stats = live_stats.get(str(sleigh_key), {})
        summaries.append(
            {
                "sleigh_id": int(sleigh_key),
                "stop_count": len(route_ids),
                "route_ids": [int(route_id) for route_id in route_ids],
                "load_kg": float(stats.get("load_kg", 0.0)),
                "over_kg": float(stats.get("over_kg", 0.0)),
                "dist_m": float(stats.get("dist_m", 0.0)),
                "time_s": float(stats.get("time_s", 0.0)),
                "return_time_s": float(stats.get("return_time_s", 0.0)),
                "return_arrival_clock": stats.get("return_arrival_clock"),
            }
        )
    return summaries


def _build_ai_sleigh_summaries(results: dict) -> list[dict]:
    summaries: list[dict] = []
    for index, tour in enumerate(results.get("tours", [])):
        vehicle_id = int(tour.get("vehicle_id", index))
        route_ids = [int(route_id) for route_id in tour.get("route_ids", [])]
        client_stops = [route_id for route_id in route_ids if route_id != 0]
        summaries.append(
            {
                "sleigh_id": vehicle_id,
                "route_ids": route_ids,
                "stop_count": len(client_stops),
                "time_s": float(tour.get("duration_s", 0.0)),
                "weight_kg": float(tour.get("weight_kg", 0.0)),
            }
        )
    return summaries


def _build_debrief_recommendations(
    mission: dict,
    results: dict,
    human_summary: dict,
    human_state,
    human_live_stats: dict[str, dict],
    benchmark: dict,
) -> list[str]:
    recommendations: list[str] = []
    dropped_points = results.get("dropped_points", [])
    if dropped_points:
        recommendations.append(f"L'IA n'a pas servi {len(dropped_points)} point(s) : augmente la flotte ou la capacite.")
    if len(human_state.assigned_clients) < mission.get("num_clients", 0):
        recommendations.append("Votre trace humaine ne couvre pas encore tous les clients : terminez l'affectation avant de comparer.")
    human_time_s = float(human_summary.get("total_time_s", 0.0))
    ai_time_s = float(results.get("total_time_s", 0.0))
    if human_time_s and human_time_s > ai_time_s:
        recommendations.append(
            f"L'IA gagne {round((human_time_s - ai_time_s) / 60)} min : cherchez surtout a reduire les detours inter-traineaux."
        )
    if any(float(stats.get("over_kg", 0.0)) > 0 for stats in human_live_stats.values()):
        recommendations.append("Au moins un traineau est surcharge : reequilibrez les colis avant de lancer l'IA.")
    if mission.get("random_incidents"):
        recommendations.append("Les incidents sont actifs : gardez une marge de temps pour les retours depot et les axes bloques.")
    if not recommendations:
        recommendations.append(
            f"Le plan est deja propre : il reste surtout a grappiller les {benchmark['savings']['time_saved_pct']}% de gain sur le benchmark naif."
        )
    return recommendations


def _evaluate_secondary_objectives(
    mission: dict,
    *,
    results: dict,
    human_state,
    human_live_stats: dict[str, dict],
    benchmark: dict,
    human_beat_ai: bool,
    final_score: float,
    human_vs_ai_delta_s: float | None,
) -> list[dict]:
    objectives = mission.get("secondary_objectives") or []
    evaluated: list[dict] = []
    assigned_all = len(human_state.assigned_clients) >= int(mission.get("num_clients", 0))
    no_overload = all(float(stats.get("over_kg", 0.0)) <= 0 for stats in human_live_stats.values())
    ai_no_drop = len(results.get("dropped_points", [])) == 0
    budget_remaining_pct = float(benchmark.get("budget", {}).get("remaining_pct", 0.0))

    for objective in objectives:
        code = str(objective.get("code", "")).strip()
        label = str(objective.get("label", code or "Objectif"))
        target = objective.get("target")
        completed = False
        progress_label = "Non évalué"

        if code == "beat_ai":
            completed = human_beat_ai
            progress_label = "IA battue" if completed else "IA encore devant"
        elif code == "assign_all_clients":
            completed = assigned_all
            progress_label = f"{len(human_state.assigned_clients)}/{int(mission.get('num_clients', 0))} clients affectés"
        elif code == "no_overload":
            completed = no_overload
            overloaded = [
                str(int(sleigh_id) + 1)
                for sleigh_id, stats in human_live_stats.items()
                if float(stats.get("over_kg", 0.0)) > 0
            ]
            progress_label = "Aucune surcharge" if completed else f"Surcharge sur T#{', T#'.join(overloaded)}"
        elif code == "ai_no_drop":
            completed = ai_no_drop
            progress_label = "Couverture complète" if completed else f"{len(results.get('dropped_points', []))} point(s) abandonné(s)"
        elif code == "max_human_delta_s":
            limit_s = float(target or 0)
            completed = human_vs_ai_delta_s is not None and float(human_vs_ai_delta_s) <= limit_s
            current_delta = None if human_vs_ai_delta_s is None else round(float(human_vs_ai_delta_s) / 60, 1)
            progress_label = (
                f"Écart {current_delta} min / limite {round(limit_s / 60, 1)} min"
                if current_delta is not None
                else "Aucun run humain complet"
            )
        elif code == "min_score":
            min_score = float(target or 0)
            completed = final_score >= min_score
            progress_label = f"Score {round(final_score, 1)} / {round(min_score, 1)}"
        elif code == "min_budget_remaining_pct":
            min_budget = float(target or 0)
            completed = budget_remaining_pct >= min_budget
            progress_label = f"Budget {round(budget_remaining_pct, 1)}% / {round(min_budget, 1)}%"

        evaluated.append(
            {
                "code": code,
                "label": label,
                "target": target,
                "completed": completed,
                "progress_label": progress_label,
            }
        )

    return evaluated


def _row_to_client(row) -> dict:
    return {
        "id": int(row["id"]),
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
        "nom_client": str(row.get("nom_client", f"Client {int(row['id'])}")),
        "poids_colis": float(row.get("poids_colis", 0)),
    }


def _serialize_state_with_stats(paths: MissionPaths, mission: dict, state) -> dict:
    df = read_points(paths.data_file)
    graph = load_graph(paths.graph_file)
    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    live_stats = build_human_live_stats(df, graph, state, float(weather.get("factor", 1.0)))
    eta_segments_by_sleigh, stop_meta_by_client = build_human_eta_payload(df, state, float(weather.get("factor", 1.0)))
    raw_state = serialize_human_state(state)
    _write_json(paths.human_state_file, raw_state)
    enriched_state = {
        "routes_by_sleigh": state.routes_by_sleigh,
        "segments_by_sleigh": eta_segments_by_sleigh,
        "assigned_clients": state.assigned_clients,
        "live_stats": live_stats,
        "stop_meta_by_client": stop_meta_by_client,
        "speed_multiplier": state.speed_multiplier,
        "vehicle_capacity": state.vehicle_capacity,
        "num_vehicles": state.num_vehicles,
    }
    _sync_snapshot(
        mission.get("mission_id", paths.root_dir.name),
        paths,
        mission,
        weather=weather,
        incidents=_read_json(paths.incidents_file, {"count": 0, "segments": []}),
        human_state=raw_state,
        status="in_progress",
    )
    return enriched_state


def _build_incident_preview(paths: MissionPaths, mission: dict) -> list[dict]:
    if not mission.get("random_incidents") or not paths.time_matrix_file.exists():
        _write_json(paths.incidents_file, {"count": 0, "segments": []})
        return []
    existing = _read_json(paths.incidents_file)
    if existing and "segments" in existing:
        return list(existing["segments"])

    df = read_points(paths.data_file)
    graph = load_graph(paths.graph_file)
    matrix = np.load(paths.time_matrix_file)
    n_points = len(matrix)
    possible_pairs = [(i, j) for i in range(1, n_points) for j in range(1, n_points) if i != j]
    blocked_pairs = random.sample(possible_pairs, min(random.randint(2, 4), len(possible_pairs)))
    segments: list[dict] = []
    for source_idx, dest_idx in blocked_pairs:
        source_id = int(df.iloc[source_idx]["id"])
        dest_id = int(df.iloc[dest_idx]["id"])
        source_lat = float(df.iloc[source_idx]["lat"])
        source_lon = float(df.iloc[source_idx]["lon"])
        dest_lat = float(df.iloc[dest_idx]["lat"])
        dest_lon = float(df.iloc[dest_idx]["lon"])
        try:
            route = compute_route_options(graph, source_lat, source_lon, dest_lat, dest_lon, time_factor=1.0, k=1)
        except Exception:
            route = []
        if not route:
            continue
        segments.append(
            {
                "variant": "incident",
                "sleigh_id": -1,
                "from_id": source_id,
                "to_id": dest_id,
                "route_nodes": route[0]["route_nodes"],
                "geometry": route[0]["geometry"],
                "dist_m": float(route[0]["dist_m"]),
                "time_s": float(route[0]["time_s"]) * 6.0,
                "title": f"Incident · axe bloque #{source_id} -> #{dest_id}",
            }
        )
    _write_json(paths.incidents_file, {"count": len(segments), "segments": segments})
    return segments


def create_mission(payload: dict) -> dict:
    mission_id = uuid.uuid4().hex[:12]
    paths = mission_paths(mission_id)
    paths.ensure_directories()
    repository.init_db()

    success, message = generate_new_zone(
        payload["zone"],
        payload["num_clients"],
        data_path=str(paths.data_file),
        graph_path=str(paths.graph_file),
        time_matrix_path=str(paths.time_matrix_file),
        dist_matrix_path=str(paths.dist_matrix_file),
    )
    if not success:
        raise ValueError(message or "Generation de zone impossible")

    if payload.get("weather_key") == "random":
        weather = get_simulated_weather(weather_file=str(paths.weather_file))
    elif payload.get("weather_key") == "real":
        weather = get_real_weather(payload["zone"], weather_file=str(paths.weather_file))
    else:
        weather = dict(WEATHER_MAP.get(payload.get("weather_key", "Clear"), WEATHER_MAP["Clear"]))
        _write_json(paths.weather_file, weather)

    mission = {
        "mission_id": mission_id,
        **payload,
        "generation_message": message,
    }
    _write_json(paths.mission_file, mission)
    _write_json(paths.human_state_file, default_human_state())
    incident_segments = _build_incident_preview(paths, mission)

    df = read_points(paths.data_file)
    depot_row = df[df["id"] == 0].iloc[0]
    clients = [_row_to_client(row) for _, row in df[df["id"] != 0].iterrows()]
    initial_state = default_human_state()
    incidents_payload = {"count": len(incident_segments), "segments": incident_segments}
    _sync_snapshot(
        mission_id,
        paths,
        mission,
        weather=weather,
        incidents=incidents_payload,
        human_state=initial_state,
        status="created",
    )
    return {
        "mission_id": mission_id,
        "mission": mission,
        "depot": _row_to_client(depot_row),
        "clients": clients,
        "graph_available": paths.graph_file.exists(),
        "weather": weather,
        "human_state": initial_state,
        "results_available": False,
        "incidents": incidents_payload,
    }


def load_mission_bundle(mission_id: str) -> tuple[MissionPaths, dict, object]:
    paths = mission_paths(mission_id)
    mission = _read_json(paths.mission_file)
    snapshot = None
    if not mission:
        snapshot = repository.get_mission_snapshot(mission_id)
        mission = snapshot["mission"] if snapshot else None
    if not mission:
        raise FileNotFoundError("Mission introuvable")
    human_state = _read_json(paths.human_state_file, default_human_state())
    if (not Path(paths.human_state_file).exists()) and snapshot and snapshot.get("human_state") is not None:
        human_state = snapshot["human_state"]
    return paths, mission, human_state


def list_missions(limit: int = 50) -> dict:
    return {"missions": repository.list_mission_snapshots(limit=limit)}


def get_mission(mission_id: str) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    df = read_points(paths.data_file)
    depot_row = df[df["id"] == 0].iloc[0]
    clients = [_row_to_client(row) for _, row in df[df["id"] != 0].iterrows()]
    incident_segments = _build_incident_preview(paths, mission)
    human_state = _serialize_state_with_stats(paths, mission, human_state_from_payload(human_state_payload))
    incidents_payload = {
        "count": len(incident_segments),
        "segments": incident_segments,
    }
    mission_payload = {
        "mission_id": mission_id,
        "mission": mission,
        "depot": _row_to_client(depot_row),
        "clients": clients,
        "graph_available": paths.graph_file.exists(),
        "weather": load_weather(paths.weather_file, mission.get("weather_key")),
        "human_state": human_state,
        "results_available": paths.results_file.exists(),
        "incidents": incidents_payload,
    }
    _sync_snapshot(
        mission_id,
        paths,
        mission,
        weather=mission_payload["weather"],
        incidents=incidents_payload,
        human_state=serialize_human_state(human_state_from_payload(human_state_payload)),
        status="solved" if mission_payload["results_available"] else "in_progress",
    )
    return mission_payload


def get_human_route_options(mission_id: str, from_id: int, to_id: int, speed_multiplier: float, k: int = 3) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    df = read_points(paths.data_file)
    graph = load_graph(paths.graph_file)
    
    from_lat, from_lon = get_point_latlon(df, int(from_id), graph=graph)
    to_lat, to_lon = get_point_latlon(df, int(to_id), graph=graph)

    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    time_factor = float(weather.get("factor", 1.0)) / speed_multiplier
    options = compute_route_options(graph, from_lat, from_lon, to_lat, to_lon, time_factor=time_factor, k=k)
    human_state = human_state_from_payload(human_state_payload)
    human_state.speed_multiplier = speed_multiplier
    raw_state = serialize_human_state(human_state)
    _write_json(paths.human_state_file, raw_state)
    _sync_snapshot(
        mission_id,
        paths,
        mission,
        weather=weather,
        incidents=_read_json(paths.incidents_file, {"count": 0, "segments": []}),
        human_state=raw_state,
        status="in_progress",
    )
    return {"options": options}


def validate_human_segment(mission_id: str, payload: dict) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    state = human_state_from_payload(human_state_payload)
    state.speed_multiplier = float(payload.get("speed_multiplier", state.speed_multiplier))
    state.vehicle_capacity = int(payload.get("vehicle_capacity", state.vehicle_capacity))
    state.num_vehicles = int(payload.get("num_vehicles", max(state.num_vehicles, payload["sleigh_id"] + 1)))

    sleigh_key = str(payload["sleigh_id"])
    state.routes_by_sleigh.setdefault(sleigh_key, [])
    state.segments_by_sleigh.setdefault(sleigh_key, [])

    to_id = int(payload["to_id"])
    
    # Vérifier si c'est un client ou un nœud OSM direct
    df = read_points(paths.data_file)
    client_ids = set(df["id"].astype(int).tolist())
    is_client = to_id in client_ids

    if is_client and to_id in state.assigned_clients:
        raise ValueError(f"Client {to_id} deja assigne")

    selected_route = payload["selected_route"]
    segment = {
        "variant": "human",
        "sleigh_id": int(payload["sleigh_id"]),
        "from_id": int(payload["from_id"]),
        "to_id": to_id,
        "route_nodes": [int(node) for node in selected_route["route_nodes"]],
        "geometry": selected_route.get("geometry", []),
        "dist_m": float(selected_route["dist_m"]),
        "base_time_s": float(selected_route.get("base_time_s", selected_route["time_s"])),
        "time_s": float(selected_route["time_s"]),
    }
    state.routes_by_sleigh[sleigh_key].append(to_id)
    state.segments_by_sleigh[sleigh_key].append(segment)
    
    if is_client:
        state.assigned_clients.append(to_id)
        state.assigned_clients = sorted(set(state.assigned_clients))
    
    # Incidents DYNAMIQUES (Phase 2.1)
    if mission.get("random_incidents") and random.random() < 0.15:
        print("⚠️ Un incident dynamique vient de se produire !")
        incidents = _read_json(paths.incidents_file, {"count": 0, "segments": []})
        # On simule un nouvel incident entre deux points non servis
        unassigned = [int(row["id"]) for _, row in df.iterrows() if int(row["id"]) not in state.assigned_clients and int(row["id"]) != 0]
        if len(unassigned) >= 2:
            pair = random.sample(unassigned, 2)
            try:
                graph = load_graph(paths.graph_file)
                p1 = df[df["id"] == pair[0]].iloc[0]
                p2 = df[df["id"] == pair[1]].iloc[0]
                route = compute_route_options(graph, p1["lat"], p1["lon"], p2["lat"], p2["lon"], time_factor=1.0, k=1)
                if route:
                    incidents["segments"].append({
                        "variant": "incident",
                        "sleigh_id": -1,
                        "from_id": int(pair[0]),
                        "to_id": int(pair[1]),
                        "route_nodes": route[0]["route_nodes"],
                        "geometry": route[0]["geometry"],
                        "dist_m": float(route[0]["dist_m"]),
                        "time_s": float(route[0]["time_s"]) * 6.0,
                        "title": f"⚠️ INCIDENT : Axe bloqué #{pair[0]} -> #{pair[1]}",
                    })
                    incidents["count"] = len(incidents["segments"])
                    _write_json(paths.incidents_file, incidents)
            except Exception as e:
                print(f"Échec génération incident : {e}")

    return _serialize_state_with_stats(paths, mission, state)


def undo_last_human_segment(mission_id: str, payload: dict) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    state = human_state_from_payload(human_state_payload)
    state.speed_multiplier = float(payload.get("speed_multiplier", state.speed_multiplier))
    state.vehicle_capacity = int(payload.get("vehicle_capacity", state.vehicle_capacity))
    state.num_vehicles = int(payload.get("num_vehicles", state.num_vehicles))
    sleigh_id = payload.get("sleigh_id")
    if sleigh_id is None:
        raise ValueError("sleigh_id requis")
    sleigh_key = str(int(sleigh_id))
    routes = state.routes_by_sleigh.get(sleigh_key, [])
    segments = state.segments_by_sleigh.get(sleigh_key, [])
    if routes:
        removed = routes.pop()
        state.assigned_clients = [client_id for client_id in state.assigned_clients if int(client_id) != int(removed)]
    if segments:
        segments.pop()
    return _serialize_state_with_stats(paths, mission, state)


def clear_human_sleigh(mission_id: str, payload: dict) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    state = human_state_from_payload(human_state_payload)
    state.speed_multiplier = float(payload.get("speed_multiplier", state.speed_multiplier))
    state.vehicle_capacity = int(payload.get("vehicle_capacity", state.vehicle_capacity))
    state.num_vehicles = int(payload.get("num_vehicles", state.num_vehicles))
    sleigh_id = payload.get("sleigh_id")
    if sleigh_id is None:
        raise ValueError("sleigh_id requis")
    sleigh_key = str(int(sleigh_id))
    removed_clients = set(state.routes_by_sleigh.get(sleigh_key, []))
    state.routes_by_sleigh[sleigh_key] = []
    state.segments_by_sleigh[sleigh_key] = []
    state.assigned_clients = [client_id for client_id in state.assigned_clients if int(client_id) not in removed_clients]
    return _serialize_state_with_stats(paths, mission, state)


def reset_human_state(mission_id: str, payload: dict) -> dict:
    paths, mission, _ = load_mission_bundle(mission_id)
    num_vehicles = int(payload.get("num_vehicles", 3))
    vehicle_capacity = int(payload.get("vehicle_capacity", 200))
    speed_multiplier = float(payload.get("speed_multiplier", 1.0))
    state = human_state_from_payload(default_human_state(num_vehicles=num_vehicles, vehicle_capacity=vehicle_capacity))
    state.speed_multiplier = speed_multiplier
    return _serialize_state_with_stats(paths, mission, state)


def suggest_next_stops(mission_id: str, payload: dict) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    df = read_points(paths.data_file)
    state = human_state_from_payload(human_state_payload)
    
    sleigh_id = int(payload.get("sleigh_id", 0))
    sleigh_key = str(sleigh_id)
    route = state.routes_by_sleigh.get(sleigh_key, [])
    current_point_id = int(route[-1]) if route else 0
    
    # Matrice de temps (pour l'ETA et la proximité)
    time_matrix = np.load(paths.time_matrix_file)
    id_to_idx = {int(row["id"]): idx for idx, (_, row) in enumerate(df.iterrows())}
    current_idx = id_to_idx[current_point_id]
    
    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    time_factor = float(weather.get("factor", 1.0)) / state.speed_multiplier
    
    # Stats actuelles du traineau
    graph = load_graph(paths.graph_file)
    live_stats = build_human_live_stats(df, graph, state, float(weather.get("factor", 1.0)))
    sleigh_stats = live_stats.get(sleigh_key, {})
    current_load = float(sleigh_stats.get("load_kg", 0.0))
    current_time_s = float(sleigh_stats.get("time_s", 0.0))
    
    unassigned = [int(row["id"]) for _, row in df.iterrows() if int(row["id"]) not in state.assigned_clients and int(row["id"]) != 0]
    
    suggestions = []
    for client_id in unassigned:
        target_idx = id_to_idx[client_id]
        travel_time = float(time_matrix[current_idx][target_idx]) * time_factor
        arrival_time = current_time_s + travel_time
        
        client_row = df[df["id"] == client_id].iloc[0]
        poids = float(client_row["poids_colis"])
        tw_start = float(client_row.get("tw_start", 0))
        tw_end = float(client_row.get("tw_end", 28800))
        
        # Heuristique : temps d'approche + pénalité si fenêtre de temps serrée
        # Si on arrive trop tôt, on attend (pénalité légère)
        wait_time = max(0, tw_start - arrival_time)
        # Si on arrive trop tard, gros malus (infaisable)
        late_penalty = 0
        if arrival_time > tw_end:
            late_penalty = 1000000
            
        # Malus si surcharge
        weight_penalty = 0
        if current_load + poids > state.vehicle_capacity:
            weight_penalty = 500000
            
        score = travel_time + wait_time * 0.5 + late_penalty + weight_penalty
        
        suggestions.append({
            "client_id": client_id,
            "nom_client": client_row["nom_client"],
            "score": score,
            "travel_time_s": travel_time,
            "arrival_clock": format_clock(32400 + arrival_time), # 9h + offset
            "is_feasible": arrival_time <= tw_end and (current_load + poids <= state.vehicle_capacity)
        })
        
    suggestions.sort(key=lambda x: x["score"])
    return {"suggestions": suggestions[:3]}


def get_nearest_node(mission_id: str, lat: float, lon: float) -> dict:
    paths, mission, _ = load_mission_bundle(mission_id)
    graph = load_graph(paths.graph_file)
    import osmnx as ox
    node_id = ox.nearest_nodes(graph, lon, lat)
    node_data = graph.nodes[node_id]
    return {
        "node_id": int(node_id),
        "lat": float(node_data["y"]),
        "lon": float(node_data["x"])
    }


def get_adjacent_nodes(mission_id: str, node_id: int, speed_multiplier: float) -> dict:
    paths, mission, _ = load_mission_bundle(mission_id)
    graph = load_graph(paths.graph_file)
    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    time_factor = float(weather.get("factor", 1.0)) / speed_multiplier

    if node_id not in graph:
        if node_id == 0:
            df = read_points(paths.data_file)
            import osmnx as ox
            depot_row = df[df["id"] == 0].iloc[0]
            node_id = ox.nearest_nodes(graph, depot_row["lon"], depot_row["lat"])
        else:
            raise ValueError(f"Nœud {node_id} introuvable")

    def format_edge(u, v):
        edge_data = graph.get_edge_data(u, v)[0]
        from_node = graph.nodes[u]
        to_node = graph.nodes[v]
        geometry = edge_data.get("geometry")
        if geometry:
            coords = [[float(y), float(x)] for x, y in list(geometry.coords)]
        else:
            coords = [
                [float(from_node["y"]), float(from_node["x"])],
                [float(to_node["y"]), float(to_node["x"])]
            ]
        dist_m = float(edge_data.get("length", 0.0))
        time_s = float(edge_data.get("travel_time", 0.0)) * time_factor
        return {
            "node_id": int(v),
            "lat": float(to_node["y"]),
            "lon": float(to_node["x"]),
            "geometry": coords,
            "dist_m": dist_m,
            "time_s": time_s,
            "label": f"Rue {edge_data.get('name', 'sans nom')}"
        }

    adjacents = []
    future_adjacents = []
    seen_edges = set()

    for neighbor in graph.successors(node_id):
        adjacents.append(format_edge(node_id, neighbor))
        seen_edges.add((node_id, neighbor))
        
        # Niveau 2 : les voisins du voisin
        for next_neighbor in graph.successors(neighbor):
            # Éviter de revenir en arrière au point de départ
            if next_neighbor == node_id:
                continue
            if (neighbor, next_neighbor) in seen_edges:
                continue
            future_adjacents.append(format_edge(neighbor, next_neighbor))
            seen_edges.add((neighbor, next_neighbor))
        
    return {"adjacents": adjacents, "future_adjacents": future_adjacents}


def _build_incident_matrix(paths: MissionPaths, mission: dict) -> str | None:
    if not mission.get("random_incidents") or not paths.time_matrix_file.exists():
        return None
    incident_payload = _read_json(paths.incidents_file, {"segments": []})
    incident_segments = incident_payload.get("segments", [])
    matrix = np.load(paths.time_matrix_file)
    incident_matrix = matrix.copy()
    df = read_points(paths.data_file)
    id_to_idx = {int(row["id"]): idx for idx, (_, row) in enumerate(df.iterrows())}
    for segment in incident_segments:
        source = id_to_idx.get(int(segment["from_id"]))
        dest = id_to_idx.get(int(segment["to_id"]))
        if source is None or dest is None:
            continue
        incident_matrix[source][dest] = min(float(matrix[source][dest]) * 6.0, 999_999.0)
    np.save(paths.incident_matrix_file, incident_matrix)
    return str(paths.incident_matrix_file)


def solve_mission(mission_id: str, payload: dict) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    df = read_points(paths.data_file)
    graph = load_graph(paths.graph_file)
    human_state = human_state_from_payload(human_state_payload)
    human_state.num_vehicles = int(payload["num_vehicles"])
    human_state.vehicle_capacity = int(payload["vehicle_capacity"])
    human_state.speed_multiplier = float(payload["speed_multiplier"])
    _write_json(paths.human_state_file, serialize_human_state(human_state))

    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    incident_matrix_path = _build_incident_matrix(paths, mission)
    ai_strategy = resolve_ai_strategy(mission, payload)
    results = solve_vrp(
        num_vehicles=int(ai_strategy["num_vehicles"]),
        vehicle_capacity=int(ai_strategy["vehicle_capacity"]),
        speed_multiplier=float(ai_strategy["speed_multiplier"]),
        forced_weather=weather,
        incident_matrix_path=incident_matrix_path,
        data_path=str(paths.data_file),
        time_matrix_path=str(paths.time_matrix_file),
        dist_matrix_path=str(paths.dist_matrix_file),
        weather_file=str(paths.weather_file),
        output_path=str(paths.results_file),
        optimization_target=ai_strategy["optimization_target"],
        solver_time_limit_s=int(ai_strategy["solver_time_limit_s"]),
        first_solution_strategy=ai_strategy["first_solution_strategy"],
        local_search_metaheuristic=ai_strategy["local_search_metaheuristic"],
        time_slack_s=int(ai_strategy["time_slack_s"]),
        max_route_time_s=int(ai_strategy["max_route_time_s"]),
        drop_penalty=int(ai_strategy["drop_penalty"]),
        global_span_cost=int(ai_strategy["global_span_cost"]),
    )
    if not results:
        raise RuntimeError("Aucune solution VRP trouvee")
    results["ai_strategy"] = ai_strategy
    _write_json(paths.results_file, results)

    benchmark = calculate_benchmark(
        num_vehicles=int(ai_strategy["num_vehicles"]),
        budget_initial=int(mission.get("budget", 0)),
        budget_spent=int(ai_strategy["num_vehicles"]) * int(mission.get("sleigh_cost", 0)),
        data_path=str(paths.data_file),
        time_matrix_path=str(paths.time_matrix_file),
        dist_matrix_path=str(paths.dist_matrix_file),
        optimized_json_path=str(paths.results_file),
        benchmark_file=str(paths.benchmark_file),
    )
    ai_segments, ai_stop_meta = build_ai_payload(df, graph, results)
    comparison = get_comparison(mission_id)
    solve_payload = {
        "results": results,
        "benchmark": benchmark,
        "ai_tours": results.get("tours", []),
        "ai_segments": ai_segments,
        "ai_stop_meta": ai_stop_meta,
        "comparison": comparison,
    }
    _sync_snapshot(
        mission_id,
        paths,
        mission,
        weather=weather,
        incidents=_read_json(paths.incidents_file, {"count": 0, "segments": []}),
        human_state=serialize_human_state(human_state),
        results=results,
        benchmark=benchmark,
        comparison=comparison,
        status="solved",
    )
    return solve_payload


def get_comparison(mission_id: str) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    df = read_points(paths.data_file)
    depot_row = df[df["id"] == 0].iloc[0]
    clients = [_row_to_client(row) for _, row in df[df["id"] != 0].iterrows()]
    human_state = human_state_from_payload(human_state_payload)
    ai_segments: list[dict] = []
    ai_results: dict = {}
    if paths.results_file.exists():
        graph = load_graph(paths.graph_file)
        ai_results = _read_json(paths.results_file, {})
        ai_segments, _ = build_ai_payload(df, graph, ai_results)

    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    live_stats = {}
    human_segments: list[dict] = []
    stop_meta_by_client: dict[int, dict] = {}
    if paths.graph_file.exists():
        graph = load_graph(paths.graph_file)
        live_stats = build_human_live_stats(df, graph, human_state, float(weather.get("factor", 1.0)))
        eta_segments_by_sleigh, stop_meta_by_client = build_human_eta_payload(df, human_state, float(weather.get("factor", 1.0)))
        human_segments = [segment for segments in eta_segments_by_sleigh.values() for segment in segments]

    comparison_payload = {
        "depot": _row_to_client(depot_row),
        "clients": clients,
        "human_segments": human_segments,
        "ai_segments": ai_segments,
        "human_stop_meta_by_client": stop_meta_by_client,
        "incidents": _read_json(paths.incidents_file, {"count": 0, "segments": []}),
        "summary_metrics": {
            "human": {
                **summarize_segments(human_segments),
                "assigned_clients": len(human_state.assigned_clients),
                "live_stats": live_stats,
                "sleighs": _build_human_sleigh_summaries(human_state, live_stats),
            },
            "ai": {
                **summarize_segments(ai_segments),
                "sleighs": _build_ai_sleigh_summaries(ai_results),
                "dropped_points": len(ai_results.get("dropped_points", [])),
                "strategy": ai_results.get("ai_strategy"),
            },
        },
    }
    _sync_snapshot(
        mission_id,
        paths,
        mission,
        weather=weather,
        incidents=comparison_payload["incidents"],
        human_state=serialize_human_state(human_state),
        results=ai_results if ai_results else None,
        comparison=comparison_payload,
        status="solved" if ai_results else "in_progress",
    )
    return comparison_payload


def get_debrief(mission_id: str) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    results = _read_json(paths.results_file)
    benchmark = _read_json(paths.benchmark_file)
    if not results or not benchmark:
        raise FileNotFoundError("Resultats ou benchmark introuvables")

    human_state = human_state_from_payload(human_state_payload)
    human_segments = [segment for segments in human_state.segments_by_sleigh.values() for segment in segments]
    human_summary = summarize_segments(human_segments)
    human_time_s = human_summary["total_time_s"] or None
    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    graph = load_graph(paths.graph_file)
    human_live_stats = build_human_live_stats(df=read_points(paths.data_file), graph=graph, state=human_state, weather_factor=float(weather.get("factor", 1.0)))

    time_saved_pct = float(benchmark["savings"]["time_saved_pct"])
    co2_saved_kg = float(benchmark["savings"]["co2_saved_kg"])
    budget_remaining_pct = float(benchmark.get("budget", {}).get("remaining_pct", 50.0))
    co2_score = min(co2_saved_kg / 20.0 * 100.0, 100.0)
    ai_strategy = results.get("ai_strategy", resolve_ai_strategy(mission, {}))
    base_score = 0.60 * time_saved_pct + 0.25 * co2_score + 0.15 * budget_remaining_pct
    ai_profile_bonus = float(ai_strategy.get("difficulty_bonus", 0.0))
    incident_bonus = 10.0 if mission.get("random_incidents", False) else 0.0
    human_bonus = 0.0
    human_beat_ai = human_time_s is not None and human_time_s < float(results.get("total_time_s", 0))
    if human_beat_ai:
        human_bonus = 5.0
    final_score = min(base_score + ai_profile_bonus + incident_bonus + human_bonus, 100.0)
    final_score = round(final_score, 1)
    secondary_objectives = _evaluate_secondary_objectives(
        mission,
        results=results,
        human_state=human_state,
        human_live_stats=human_live_stats,
        benchmark=benchmark,
        human_beat_ai=human_beat_ai,
        final_score=final_score,
        human_vs_ai_delta_s=(float(human_time_s) - float(results.get("total_time_s", 0.0))) if human_time_s is not None else None,
    )

    if final_score >= 85:
        rank, rank_title = "S", "Eco-Livreur Legendaire"
    elif final_score >= 70:
        rank, rank_title = "A", "Chef Logisticien"
    elif final_score >= 50:
        rank, rank_title = "B", "Livreur Efficace"
    elif final_score >= 30:
        rank, rank_title = "C", "Apprenti Pere Noel"
    else:
        rank, rank_title = "D", "En formation"

    ai_time_s = float(results.get("total_time_s", 0.0))
    human_vs_ai_delta_s = (float(human_time_s) - ai_time_s) if human_time_s is not None else None

    debrief_payload = {
        "mission": mission,
        "results": results,
        "benchmark": benchmark,
        "score": {
            "value": final_score,
            "rank": rank,
            "rank_title": rank_title,
            "human_beat_ai": human_beat_ai,
            "breakdown": {
                "base_score": round(base_score, 1),
                "ai_profile_bonus": round(ai_profile_bonus, 1),
                "incident_bonus": round(incident_bonus, 1),
                "human_bonus": round(human_bonus, 1),
                "final_score": final_score,
            },
        },
        "human": {
            "summary": human_summary,
            "routes_by_sleigh": human_state.routes_by_sleigh,
            "assigned_clients": human_state.assigned_clients,
            "live_stats": human_live_stats,
            "sleighs": _build_human_sleigh_summaries(human_state, human_live_stats),
        },
        "analysis": {
            "human_vs_ai_delta_s": human_vs_ai_delta_s,
            "naive_vs_ai_delta_s": float(benchmark["naive"]["total_time_s"]) - ai_time_s,
            "dropped_points": results.get("dropped_points", []),
            "ai_sleighs": _build_ai_sleigh_summaries(results),
            "ai_strategy": results.get("ai_strategy"),
            "secondary_objectives": secondary_objectives,
            "recommendations": _build_debrief_recommendations(
                mission, results, human_summary, human_state, human_live_stats, benchmark
            ),
        },
    }
    _sync_snapshot(
        mission_id,
        paths,
        mission,
        weather=weather,
        incidents=_read_json(paths.incidents_file, {"count": 0, "segments": []}),
        human_state=serialize_human_state(human_state),
        results=results,
        benchmark=benchmark,
        debrief=debrief_payload,
        status="solved",
    )
    return debrief_payload


def save_leaderboard(mission_id: str, payload: dict) -> dict:
    paths, mission, _ = load_mission_bundle(mission_id)
    snapshot = repository.get_mission_snapshot(mission_id)
    debrief = snapshot.get("debrief") if snapshot else None
    if not debrief:
        raise ValueError("Debrief introuvable pour cette mission")
    player_id = payload.get("player_id")
    player_name = payload.get("player_name", "Père Noël")
    if player_id:
        player = repository.get_player(str(player_id))
        if not player:
            player = repository.upsert_player(
                player_id=str(player_id),
                display_name=str(player_name),
                callsign=payload.get("callsign"),
                avatar=payload.get("avatar"),
            )
        player_name = player.get("display_name", player_name)

    repository.save_leaderboard_entry(
        mission_id=mission_id,
        zone=mission.get("zone", "Inconnue"),
        score=float(debrief["score"]["value"]),
        rank=debrief["score"]["rank"],
        player_name=player_name,
        player_id=str(player_id) if player_id else None,
    )
    return {"status": "success"}


def list_leaderboard(limit: int = 20) -> dict:
    return {"entries": repository.list_leaderboard(limit=limit)}


def upsert_player(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or uuid.uuid4().hex[:16])
    display_name = str(payload.get("display_name", "")).strip()
    if not display_name:
        raise ValueError("display_name requis")
    try:
        player = repository.upsert_player(
            player_id=player_id,
            display_name=display_name,
            callsign=str(payload.get("callsign", "")).strip() or None,
            avatar=str(payload.get("avatar", "")).strip() or None,
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("Impossible de mettre à jour ce joueur") from exc
    return _public_player(player)


def get_player(player_id: str) -> dict:
    player = repository.get_player(player_id)
    if not player:
        raise FileNotFoundError("Joueur introuvable")
    return _public_player(player)


def register_player(payload: dict) -> dict:
    email = _validate_email(payload.get("email"))
    display_name = str(payload.get("display_name", "")).strip()
    if not display_name:
        raise ValueError("Nom de joueur requis")

    existing = repository.get_player_by_email(email)
    if existing:
        raise ValueError("Un compte existe déjà avec cet email")

    player_id = uuid.uuid4().hex[:16]
    try:
        player = repository.upsert_player(
            player_id=player_id,
            display_name=display_name,
            email=email,
            password_hash=_hash_password(str(payload.get("password", ""))),
            callsign=str(payload.get("callsign", "")).strip() or None,
            avatar=str(payload.get("avatar", "")).strip() or None,
            last_login_at=_utcnow().isoformat(),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("Impossible de créer le compte") from exc
    return _public_player(player)


def login_player(payload: dict) -> dict:
    email = _validate_email(payload.get("email"))
    player = repository.get_player_by_email(email)
    if not player or not _verify_password(str(payload.get("password", "")), player.get("password_hash")):
        raise ValueError("Email ou mot de passe incorrect")

    try:
        updated = repository.upsert_player(
            player_id=player["player_id"],
            display_name=player["display_name"],
            email=player.get("email"),
            password_hash=player.get("password_hash"),
            callsign=player.get("callsign"),
            avatar=player.get("avatar"),
            last_login_at=_utcnow().isoformat(),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("Impossible de connecter ce compte") from exc
    return _public_player(updated)


def request_password_reset(payload: dict) -> dict:
    email = _validate_email(payload.get("email"))
    player = repository.get_player_by_email(email)
    if not player:
        raise ValueError("Aucun compte trouvé avec cet email")

    raw_token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = (_utcnow() + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES)).isoformat()
    repository.create_password_reset_token(
        player_id=player["player_id"],
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return {
        "status": "reset_requested",
        "reset_token": raw_token,
        "reset_url": f"/reset-password?token={raw_token}",
        "expires_at": expires_at,
    }


def reset_password(payload: dict) -> dict:
    raw_token = str(payload.get("token", "")).strip()
    if len(raw_token) < 12:
        raise ValueError("Token de réinitialisation invalide")

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    token_entry = repository.get_password_reset_token(token_hash)
    if not token_entry:
        raise ValueError("Lien de réinitialisation invalide")
    if token_entry.get("consumed_at"):
        raise ValueError("Ce lien de réinitialisation a déjà été utilisé")
    if _parse_datetime(token_entry["expires_at"]) < _utcnow():
        raise ValueError("Ce lien de réinitialisation a expiré")

    player = repository.update_player_password(
        player_id=token_entry["player_id"],
        password_hash=_hash_password(str(payload.get("password", ""))),
    )
    repository.consume_password_reset_token(token_hash)
    if not player:
        raise ValueError("Compte introuvable pour la réinitialisation")
    return _public_player(player)
