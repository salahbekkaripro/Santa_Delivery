from __future__ import annotations

import json
import hashlib
import hmac
import random
import secrets
import shutil
import sqlite3
import unicodedata
import uuid
from collections import OrderedDict, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

import numpy as np

from final_scripts.solve_santa_final import solve_vrp
from backend.app import repository
from scripts.benchmark_engine import calculate_benchmark
from scripts.generator_engine import generate_new_zone
from scripts.mission_paths import MissionPaths, ROOT_DIR, mission_paths
from scripts.routing_payloads import (
    DEFAULT_DEPARTURE_TIME,
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
    parse_clock_to_seconds,
    serialize_human_state,
    summarize_segments,
)
from scripts import ro_improvements
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
        "spatial_sectorization": False,
    },
    "ecolo": {
        "label": "Écolo",
        "signature": "Trajectoires sobres",
        "description": "Réduit les kilomètres au prix d'une exécution un peu plus conservatrice.",
        "difficulty_bonus": 3.0,
        "optimization_target": "distance",
        "speed_multiplier_factor": 0.96,
        "solver_time_limit_s": 18,
        "first_solution_strategy": "savings",
        "local_search_metaheuristic": "simulated_annealing",
        "time_slack_s": 3600,
        "max_route_time_s": 15600,
        "drop_penalty": 1_200_000,
        "global_span_cost": 80,
        "spatial_sectorization": False,
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
        "spatial_sectorization": False,
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
        "spatial_sectorization": False,
    },
    "agressive": {
        "label": "Agressive",
        "signature": "Pression maximale",
        "description": "Prend plus de risques pour gagner du temps, quitte à laisser tomber quelques points coûteux.",
        "difficulty_bonus": 6.0,
        "optimization_target": "time",
        "speed_multiplier_factor": 1.18,
        "solver_time_limit_s": 10,
        "first_solution_strategy": "parallel_cheapest_insertion",
        "local_search_metaheuristic": "guided_local_search",
        "time_slack_s": 1200,
        "max_route_time_s": 13800,
        "drop_penalty": 220_000,
        "global_span_cost": 60,
        "spatial_sectorization": False,
    },
    "championne": {
        "label": "Championne",
        "signature": "Meta complète",
        "description": "Combine vitesse, couverture et recherche plus profonde pour jouer la meilleure note possible.",
        "difficulty_bonus": 8.0,
        "optimization_target": "time",
        "speed_multiplier_factor": 1.08,
        "solver_time_limit_s": 35,
        "first_solution_strategy": "savings",
        "local_search_metaheuristic": "guided_local_search",
        "time_slack_s": 3600,
        "max_route_time_s": 18000,
        "drop_penalty": 1_500_000,
        "global_span_cost": 180,
        "spatial_sectorization": False,
    },
    "championne_zone": {
        "label": "Championne (Secteurs)",
        "signature": "Architecture hybride",
        "description": "Utilise le Clustering Spatial (K-Means) pour sectoriser la ville avant l'optimisation VRPTW.",
        "difficulty_bonus": 10.0,
        "optimization_target": "time",
        "speed_multiplier_factor": 1.10,
        "solver_time_limit_s": 40,
        "first_solution_strategy": "parallel_cheapest_insertion",
        "local_search_metaheuristic": "guided_local_search",
        "time_slack_s": 3600,
        "max_route_time_s": 18000,
        "drop_penalty": 1_800_000,
        "global_span_cost": 200,
        "spatial_sectorization": True,
    },
}

AI_LEARNING_MODEL_FILE = ROOT_DIR / "cache" / "api_missions" / "ai_learning_model.json"
AI_LEARNING_MODEL_VERSION = "2.0"
AI_LEARNING_MIN_SAMPLES = 8
AI_LEARNING_SMOOTHING_ALPHA = 3.0
AI_LEARNING_HOLDOUT_RATIO = 0.25
ORTOOLS_TUNER_MODEL_FILE = ROOT_DIR / "cache" / "api_missions" / "ortools_tuner_model.json"
ORTOOLS_TUNER_MODEL_VERSION = "1.0"
ORTOOLS_TUNER_MIN_SAMPLES = 12
ORTOOLS_TUNER_SMOOTHING_ALPHA = 3.0
ORTOOLS_TUNER_HOLDOUT_RATIO = 0.25
ORTOOLS_TUNER_FIELDS = (
    "first_solution_strategy",
    "local_search_metaheuristic",
    "solver_time_limit_s",
    "time_slack_s",
    "max_route_time_s",
    "drop_penalty",
    "global_span_cost",
)
RO_PORTFOLIO_PRESETS = {
    "pca_gls_fast": {
        "optimization_target": "time",
        "first_solution_strategy": "path_cheapest_arc",
        "local_search_metaheuristic": "guided_local_search",
        "solver_time_limit_s": 12,
        "time_slack_s": 3000,
        "max_route_time_s": 15000,
        "drop_penalty": 900_000,
        "global_span_cost": 80,
    },
    "savings_tabu": {
        "optimization_target": "time",
        "first_solution_strategy": "savings",
        "local_search_metaheuristic": "tabu_search",
        "solver_time_limit_s": 22,
        "time_slack_s": 3600,
        "max_route_time_s": 15600,
        "drop_penalty": 1_050_000,
        "global_span_cost": 110,
    },
    "pca_gls_distance": {
        "optimization_target": "distance",
        "first_solution_strategy": "path_cheapest_arc",
        "local_search_metaheuristic": "guided_local_search",
        "solver_time_limit_s": 20,
        "time_slack_s": 3600,
        "max_route_time_s": 16000,
        "drop_penalty": 1_000_000,
        "global_span_cost": 100,
    },
}
RO_PORTFOLIO_MAX_CANDIDATES = 4
RO_PORTFOLIO_PROBE_OUTPUT_NAME = "_portfolio_probe_result.json"

PASSWORD_HASH_ITERATIONS = 120_000
PASSWORD_RESET_TTL_MINUTES = 30
SEARCH_MIN_RADIUS_KM = 0.5
SEARCH_MAX_RADIUS_KM = 30.0
SEARCH_CLIENT_DENSITY_PER_KM2 = 2.0
SEARCH_MIN_CLIENTS = 8
SEARCH_MAX_CLIENTS = 200
ROUTE_OPTIONS_CACHE_MAX = 512
GRAPH_CACHE_MAX = 32
_route_options_cache: OrderedDict[tuple, list[dict]] = OrderedDict()
_route_options_cache_lock = Lock()
_graph_cache: OrderedDict[tuple[str, int], object] = OrderedDict()
_graph_cache_lock = Lock()
DEFAULT_DEPARTURE_TIME_S = parse_clock_to_seconds(DEFAULT_DEPARTURE_TIME)
VERSUS_FORFEIT_TIMEOUT_SECONDS = 300
VERSUS_COUNTDOWN_SECONDS = 3
VERSUS_WINNER_RULES = {"score_time", "time", "objectives"}
VERSUS_MATCH_MODES = {"private", "queue", "invite"}
VERSUS_MAP_SOURCES = {"template", "custom"}
VERSUS_CUSTOM_MAX_CLIENTS = 60
VERSUS_TEMPLATES = {
    "paris_duel": {
        "template_id": "paris_duel",
        "label": "Paris Rush",
        "description": "Duel urbain rapide sans incidents.",
        "mission": {
            "zone": "Le Marais, Paris",
            "city": "Paris",
            "num_clients": 22,
            "budget": 2600,
            "sleigh_cost": 650,
            "weather_key": "Clear",
            "random_incidents": False,
            "ai_profile": "Express",
        },
    },
    "berlin_rain_duel": {
        "template_id": "berlin_rain_duel",
        "label": "Berlin Rain Clash",
        "description": "Meteo pluie et densite moyenne.",
        "mission": {
            "zone": "Mitte, Berlin",
            "city": "Berlin",
            "num_clients": 28,
            "budget": 3200,
            "sleigh_cost": 700,
            "weather_key": "Rain",
            "random_incidents": False,
            "ai_profile": "Prudent",
        },
    },
    "montreal_snow_duel": {
        "template_id": "montreal_snow_duel",
        "label": "Montreal Snow Battle",
        "description": "Neige et incidents actifs.",
        "mission": {
            "zone": "Le Plateau-Mont-Royal, Montreal, Quebec, Canada",
            "city": "Montreal",
            "num_clients": 34,
            "budget": 3800,
            "sleigh_cost": 800,
            "weather_key": "Snow",
            "random_incidents": True,
            "ai_profile": "Championne",
        },
    },
}


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


def _normalize_oauth_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if not provider:
        raise ValueError("provider OAuth requis")
    return provider


def _oauth_player_id(provider: str, provider_account_id: str) -> str:
    digest = hashlib.sha1(f"{provider}:{provider_account_id}".encode("utf-8")).hexdigest()[:16]
    return f"oauth_{provider}_{digest}"


def _sanitize_avatar_hint(value: str | None) -> str | None:
    avatar = str(value or "").strip()
    if not avatar:
        return None
    if len(avatar) <= 8:
        return avatar
    return None


def _max_clients_for_radius(radius_km: float) -> int:
    area_km2 = float(np.pi) * float(radius_km) * float(radius_km)
    capacity = int(area_km2 * SEARCH_CLIENT_DENSITY_PER_KM2)
    capacity = max(SEARCH_MIN_CLIENTS, capacity)
    return min(SEARCH_MAX_CLIENTS, capacity)


def _validate_search_area_constraints(payload: dict) -> tuple[float | None, int | None]:
    radius_raw = payload.get("search_radius_km")
    if radius_raw is None:
        return None, None
    radius_km = float(radius_raw)
    if radius_km < SEARCH_MIN_RADIUS_KM or radius_km > SEARCH_MAX_RADIUS_KM:
        raise ValueError(
            f"Le rayon doit etre entre {SEARCH_MIN_RADIUS_KM:.1f} km et {SEARCH_MAX_RADIUS_KM:.0f} km."
        )
    max_clients_allowed = _max_clients_for_radius(radius_km)
    requested_clients = int(payload.get("num_clients", 0))
    center_lat = payload.get("center_lat")
    center_lon = payload.get("center_lon")
    if center_lat is None or center_lon is None:
        raise ValueError("Point central manquant: selectionnez une adresse valide avant de lancer la generation.")
    lat_value = float(center_lat)
    lon_value = float(center_lon)
    if lat_value < -90.0 or lat_value > 90.0 or lon_value < -180.0 or lon_value > 180.0:
        raise ValueError("Coordonnees du point central invalides.")
    if requested_clients > max_clients_allowed:
        raise ValueError(
            "Nombre de colis trop eleve pour la zone delimitee: "
            f"{requested_clients} demandes, maximum {max_clients_allowed} pour un rayon de {radius_km:.1f} km."
        )
    return radius_km, max_clients_allowed


def _route_options_cache_get(key: tuple) -> list[dict] | None:
    with _route_options_cache_lock:
        cached = _route_options_cache.get(key)
        if cached is None:
            return None
        _route_options_cache.move_to_end(key)
        return deepcopy(cached)


def _route_options_cache_set(key: tuple, options: list[dict]) -> None:
    with _route_options_cache_lock:
        _route_options_cache[key] = deepcopy(options)
        _route_options_cache.move_to_end(key)
        while len(_route_options_cache) > ROUTE_OPTIONS_CACHE_MAX:
            _route_options_cache.popitem(last=False)


def _graph_cache_key(graph_path: str | Path) -> tuple[str, int]:
    path = Path(graph_path)
    resolved = str(path.resolve())
    mtime_ns = int(path.stat().st_mtime_ns) if path.exists() else 0
    return resolved, mtime_ns


def _load_graph_cached(graph_path: str | Path):
    key = _graph_cache_key(graph_path)
    with _graph_cache_lock:
        cached = _graph_cache.get(key)
        if cached is not None:
            _graph_cache.move_to_end(key)
            return cached
    graph = load_graph(graph_path)
    with _graph_cache_lock:
        _graph_cache[key] = graph
        _graph_cache.move_to_end(key)
        while len(_graph_cache) > GRAPH_CACHE_MAX:
            _graph_cache.popitem(last=False)
    return graph


def _incident_cache_token(incident_segments: list[dict] | None) -> str:
    edges: list[str] = []
    for segment in incident_segments or []:
        route_nodes = [int(node_id) for node_id in segment.get("route_nodes", [])]
        if len(route_nodes) < 2:
            continue
        for source, target in zip(route_nodes[:-1], route_nodes[1:]):
            undirected = tuple(sorted((int(source), int(target))))
            edges.append(f"{undirected[0]}-{undirected[1]}")
    if not edges:
        return "none"
    payload = "|".join(sorted(edges))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _segment_base_time_s(segment: dict) -> float:
    return float(segment.get("base_time_s", segment.get("time_s", 0.0)))


def _sleigh_elapsed_time_s(state, sleigh_id: int, time_factor: float) -> float:
    segments = state.segments_by_sleigh.get(str(int(sleigh_id)), [])
    base_time_s = sum(_segment_base_time_s(segment) for segment in segments)
    return base_time_s * float(time_factor)


def _sleigh_current_load_kg(df, state, sleigh_id: int) -> float:
    routes = state.routes_by_sleigh.get(str(int(sleigh_id)), [])
    if not routes:
        return 0.0
    known_ids = set(int(value) for value in df["id"].astype(int).tolist())
    client_ids = [int(route_id) for route_id in routes if int(route_id) in known_ids and int(route_id) != 0]
    if not client_ids:
        return 0.0
    return float(df[df["id"].isin(client_ids)]["poids_colis"].sum())


def _annotate_route_options_feasibility(
    df,
    state,
    options: list[dict],
    *,
    to_id: int,
    sleigh_id: int,
    time_factor: float,
    incident_segments: list[dict] | None = None,
) -> list[dict]:
    if not options:
        return []

    destination_rows = df[df["id"] == int(to_id)]
    is_known_client = not destination_rows.empty and int(to_id) != 0
    destination = destination_rows.iloc[0] if is_known_client else None

    current_time_s = _sleigh_elapsed_time_s(state, sleigh_id, time_factor)
    current_load_kg = _sleigh_current_load_kg(df, state, sleigh_id)
    vehicle_capacity = float(state.vehicle_capacity)
    active_route_ids = {int(route_id) for route_id in state.routes_by_sleigh.get(str(int(sleigh_id)), [])}
    assigned_elsewhere = int(to_id) in set(state.assigned_clients) and int(to_id) not in active_route_ids
    tw_end = float(destination.get("tw_end", 28800.0)) if destination is not None else 28800.0
    target_weight_kg = float(destination.get("poids_colis", 0.0)) if destination is not None else 0.0
    blocked_directed_edges: set[tuple[int, int]] = set()
    blocked_undirected_edges: set[tuple[int, int]] = set()
    for segment in incident_segments or []:
        route_nodes = [int(node) for node in segment.get("route_nodes", [])]
        if len(route_nodes) < 2:
            continue
        for src, dst in zip(route_nodes[:-1], route_nodes[1:]):
            edge = (int(src), int(dst))
            blocked_directed_edges.add(edge)
            blocked_undirected_edges.add(tuple(sorted(edge)))

    annotated: list[dict] = []
    for option in options:
        next_option = dict(option)
        option_time_s = float(next_option.get("time_s", 0.0))
        arrival_eta_s = current_time_s + option_time_s
        arrival_clock = format_clock(DEFAULT_DEPARTURE_TIME_S + arrival_eta_s)

        badges: list[str] = []
        is_feasible = True
        projected_load_kg = current_load_kg
        projected_overload_kg = 0.0
        route_nodes = [int(node_id) for node_id in next_option.get("route_nodes", [])]

        has_incident_overlap = False
        if len(route_nodes) >= 2 and blocked_undirected_edges:
            route_directed_edges = {(int(src), int(dst)) for src, dst in zip(route_nodes[:-1], route_nodes[1:])}
            route_undirected_edges = {tuple(sorted(edge)) for edge in route_directed_edges}
            has_incident_overlap = bool(
                (route_directed_edges & blocked_directed_edges)
                or (route_undirected_edges & blocked_undirected_edges)
            )
        if has_incident_overlap:
            is_feasible = False
            badges.append("Axe incident")

        if is_known_client:
            projected_load_kg = current_load_kg + target_weight_kg
            projected_overload_kg = max(0.0, projected_load_kg - vehicle_capacity)
            slack_s = tw_end - arrival_eta_s

            if assigned_elsewhere:
                is_feasible = False
                badges.append("Déjà assigné")
            if projected_overload_kg > 0:
                is_feasible = False
                overload_kg = int(np.ceil(projected_overload_kg))
                badges.append(f"Surcharge +{max(1, overload_kg)} kg")
            if slack_s < 0:
                is_feasible = False
                delay_min = int(np.ceil(abs(float(slack_s)) / 60.0))
                badges.append(f"Retard +{max(1, delay_min)} min")
            elif slack_s < 900:
                margin_min = int(np.floor(max(float(slack_s), 0.0) / 60.0))
                badges.append(f"Marge {max(0, margin_min)} min")

        if not badges:
            badges.append("Sûr")

        next_option["is_feasible"] = is_feasible
        next_option["feasibility_badges"] = badges
        next_option["projected_arrival_clock"] = arrival_clock
        next_option["projected_load_kg"] = projected_load_kg
        next_option["projected_overload_kg"] = projected_overload_kg
        annotated.append(next_option)

    annotated.sort(key=lambda item: (not bool(item.get("is_feasible", True)), float(item["time_s"]), float(item["dist_m"])))
    return annotated


def _strict_route_metrics(graph, route_nodes: list[int]) -> tuple[float, float]:
    nodes = [int(node_id) for node_id in route_nodes]
    if len(nodes) < 2:
        raise ValueError("Segment invalide: route vide.")

    total_dist_m = 0.0
    total_base_time_s = 0.0
    fallback_speed_m_s = 30_000.0 / 3600.0
    for from_node, to_node in zip(nodes[:-1], nodes[1:]):
        edge_bundle = graph.get_edge_data(from_node, to_node)
        if not edge_bundle:
            raise ValueError("Segment invalide: route discontinue sur le graphe.")
        best_edge = min(
            edge_bundle.values(),
            key=lambda edge: (
                float(edge.get("travel_time", 1e12)),
                float(edge.get("length", 1e12)),
            ),
        )
        length_m = float(best_edge.get("length", 0.0))
        base_time_s = float(best_edge.get("travel_time", length_m / fallback_speed_m_s))
        total_dist_m += length_m
        total_base_time_s += base_time_s
    return total_dist_m, total_base_time_s


def _infeasible_segment_message(option: dict) -> str:
    badges = [str(badge) for badge in option.get("feasibility_badges", [])]
    if not badges:
        return "Segment non faisable."
    return f"Segment non faisable: {', '.join(badges)}."


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
        import math as _math
        optimization_target = str(payload.get("optimization_target", "time"))
        _nc = max(1, int(mission.get("num_clients", int(payload.get("num_vehicles", 3)) * 3)))
        _max_v = min(_nc, max(1, _math.ceil(_nc / 3)))
        return {
            "profile": "adaptatif",
            "label": "Adaptative",
            "signature": "Mode libre",
            "description": "Réutilise les paramètres de mission sans biais de profil.",
            "difficulty_bonus": 0.0,
            "optimization_target": "distance" if optimization_target == "distance" else "time",
            "num_vehicles": _max_v,
            "vehicle_fixed_cost": int(14400 * 0.15),
            "vehicle_capacity": max(1, int(payload.get("vehicle_capacity", 200))),
            "speed_multiplier": round(max(0.5, float(payload.get("speed_multiplier", 1.0))), 2),
            "solver_time_limit_s": 25,
            "first_solution_strategy": "savings",
            "local_search_metaheuristic": "guided_local_search",
            "time_slack_s": 3600,
            "max_route_time_s": 14400,
            "drop_penalty": 1_000_000,
            "global_span_cost": 100,
        }

    profile_key = _normalize_ai_profile(mission.get("ai_profile"))
    preset = AI_PROFILE_PRESETS.get(profile_key, AI_PROFILE_PRESETS["express"])
    speed_multiplier = max(0.5, float(payload.get("speed_multiplier", 1.0)) * float(preset["speed_multiplier_factor"]))
    vehicle_capacity = max(1, int(payload.get("vehicle_capacity", 200)))
    optimization_target = str(preset.get("optimization_target") or payload.get("optimization_target", "time"))

    # Missions à incidents: les profils prudents et champions prennent plus de marge pour rester stables.
    time_slack_s = int(preset["time_slack_s"])
    max_route_time_s = int(preset["max_route_time_s"])
    if mission.get("random_incidents") and profile_key in {"prudent", "championne"}:
        time_slack_s += 1200
        max_route_time_s += 900

    # Limite de temps adaptative : √(n/20) — petites missions résolues plus vite,
    # grandes missions (>20 clients) bénéficient de plus de budget de recherche.
    num_clients = max(1, int(mission.get("num_clients", 15)))
    base_time_limit = int(preset["solver_time_limit_s"])
    scale = (float(num_clients) / 20.0) ** 0.5
    adaptive_time_limit = max(8, min(45, int(round(float(base_time_limit) * scale))))

    # Plafond de véhicules dynamique : OR-Tools dispose de max_vehicles slots mais
    # choisit librement combien en utiliser grâce au coût fixe par véhicule.
    # Formule : ceil(n / 3) véhicules minimum, plafonné à min(n, 6).
    import math as _math
    max_vehicles = min(num_clients, max(1, _math.ceil(num_clients / 3)))
    # Coût fixe = 15 % du temps max par route — rend chaque véhicule supplémentaire
    # coûteux sauf si il réduit réellement le makespan.
    vehicle_fixed_cost = int(max_route_time_s * 0.15)

    return {
        "profile": profile_key,
        "label": str(preset["label"]),
        "signature": str(preset["signature"]),
        "description": str(preset["description"]),
        "difficulty_bonus": float(preset["difficulty_bonus"]),
        "optimization_target": "distance" if optimization_target == "distance" else "time",
        "num_vehicles": max_vehicles,
        "vehicle_fixed_cost": vehicle_fixed_cost,
        "vehicle_capacity": vehicle_capacity,
        "speed_multiplier": round(speed_multiplier, 2),
        "solver_time_limit_s": adaptive_time_limit,
        "first_solution_strategy": str(preset["first_solution_strategy"]),
        "local_search_metaheuristic": str(preset["local_search_metaheuristic"]),
        "time_slack_s": time_slack_s,
        "max_route_time_s": max_route_time_s,
        "drop_penalty": int(preset["drop_penalty"]),
        "global_span_cost": int(preset["global_span_cost"]),
    }


def _client_bucket(num_clients: int) -> str:
    if num_clients <= 15:
        return "small"
    if num_clients <= 35:
        return "medium"
    return "large"


def _safe_float(value, default: float | None = None) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if np.isfinite(parsed) else default


def _weather_bucket(weather_key: str) -> str:
    normalized = str(weather_key or "clear").strip().lower()
    if normalized in {"clear", "clouds"}:
        return "clearish"
    if normalized in {"rain", "drizzle"}:
        return "rainy"
    if normalized in {"snow"}:
        return "snowy"
    if normalized in {"thunderstorm", "storm"}:
        return "stormy"
    if normalized in {"real", "random"}:
        return normalized
    return "other"


def _budget_bucket(mission: dict, num_clients: int) -> str:
    budget = max(0.0, float(mission.get("budget", 0.0)))
    if budget <= 0:
        return "unknown"
    budget_per_client = budget / float(max(1, num_clients))
    if budget_per_client < 80.0:
        return "tight"
    if budget_per_client < 140.0:
        return "balanced"
    return "relaxed"


def _sleigh_cost_bucket(mission: dict) -> str:
    sleigh_cost = max(0.0, float(mission.get("sleigh_cost", 0.0)))
    if sleigh_cost <= 0:
        return "unknown"
    if sleigh_cost <= 550.0:
        return "light"
    if sleigh_cost <= 750.0:
        return "standard"
    return "expensive"


def _density_bucket(mission: dict, num_clients: int) -> str:
    radius_km = _safe_float(mission.get("search_radius_km"))
    if radius_km is None or radius_km <= 0:
        return "unknown"
    area_km2 = float(np.pi) * radius_km * radius_km
    density = float(num_clients) / max(area_km2, 1e-6)
    if density < 1.5:
        return "sparse"
    if density < 3.5:
        return "urban"
    return "dense"


def _mission_learning_context(mission: dict) -> str:
    weather_key = _weather_bucket(str(mission.get("weather_key", "clear")))
    random_incidents = 1 if bool(mission.get("random_incidents", False)) else 0
    num_clients = max(1, int(mission.get("num_clients", 1)))
    budget = _budget_bucket(mission, num_clients)
    sleigh_cost = _sleigh_cost_bucket(mission)
    density = _density_bucket(mission, num_clients)
    return (
        f"weather:{weather_key}|incidents:{random_incidents}|clients:{_client_bucket(num_clients)}"
        f"|budget:{budget}|sleigh:{sleigh_cost}|density:{density}"
    )


def _extract_training_profile(results: dict) -> str | None:
    ai_strategy = results.get("ai_strategy", {}) if isinstance(results, dict) else {}
    profile = _normalize_ai_profile(ai_strategy.get("profile"))
    if profile in AI_PROFILE_PRESETS:
        return profile
    return None


def _compute_training_cost(mission: dict, results: dict, benchmark: dict | None = None) -> float | None:
    if not isinstance(results, dict):
        return None
    total_time_s = _safe_float(results.get("total_time_s"))
    if total_time_s is None or total_time_s <= 0:
        return None

    num_clients = max(1, int(mission.get("num_clients", 1)))
    dropped_count = len(results.get("dropped_points", [])) if isinstance(results.get("dropped_points", []), list) else 0
    drop_ratio = float(dropped_count) / float(num_clients)

    benchmark_payload = benchmark if isinstance(benchmark, dict) else {}
    optimized_payload = benchmark_payload.get("optimized", {}) if isinstance(benchmark_payload.get("optimized", {}), dict) else {}
    total_dist_m = _safe_float(optimized_payload.get("total_dist_m"))
    if total_dist_m is None:
        total_dist_m = _safe_float(results.get("total_dist_m"), 0.0)
    dist_per_client_km = max(0.0, float(total_dist_m or 0.0) / 1000.0 / float(num_clients))

    ai_strategy = results.get("ai_strategy", {}) if isinstance(results.get("ai_strategy", {}), dict) else {}
    tours = results.get("tours", []) if isinstance(results.get("tours", []), list) else []
    strategy_vehicles = int(ai_strategy.get("num_vehicles", 0))
    used_vehicles = strategy_vehicles if strategy_vehicles > 0 else max(1, len(tours))
    budget = max(0.0, float(mission.get("budget", 0.0)))
    sleigh_cost = max(0.0, float(mission.get("sleigh_cost", 0.0)))
    estimated_spend = float(used_vehicles) * sleigh_cost
    if budget > 0:
        budget_over_ratio = max(0.0, (estimated_spend - budget) / budget)
    else:
        budget_over_ratio = 0.0 if estimated_spend <= 0 else 1.0

    weather_factor = _safe_float((results.get("weather") or {}).get("factor"), 1.0) or 1.0
    weather_penalty = max(0.0, float(weather_factor) - 1.0)

    time_per_client_s = float(total_time_s) / float(num_clients)
    composite_cost = (
        time_per_client_s
        + 95.0 * dist_per_client_km
        + 2400.0 * drop_ratio
        + 1200.0 * budget_over_ratio
        + 180.0 * weather_penalty
    )
    return max(0.0, float(composite_cost))


def calculate_co2_savings(distance_km: float, relief_overhead_pct: float = 0.0) -> dict:
    """
    Calcule l'économie de CO2 basée sur la distance et le relief.
    Modèle : 120g de CO2 par km (standard utilitaire léger).
    Le relief augmente la consommation linéairement.
    """
    BASE_CO2_G_PER_KM = 120.0
    distance_km = max(0.0, distance_km)
    relief_factor = 1.0 + (max(0.0, relief_overhead_pct) / 100.0)
    
    co2_total_g = distance_km * BASE_CO2_G_PER_KM * relief_factor
    
    return {
        "co2_g": round(co2_total_g, 2),
        "co2_kg": round(co2_total_g / 1000.0, 3),
        "distance_km": round(distance_km, 2),
        "relief_factor": round(relief_factor, 3),
        "trees_offset_equivalent": round(co2_total_g / 20.0, 2) # Approximation symbolique
    }


def _iter_solved_training_snapshots(limit: int = 500) -> list[dict]:
    snapshots = repository.list_mission_snapshots(limit=max(1, int(limit)))
    solved_ids = [str(snapshot["mission_id"]) for snapshot in snapshots if snapshot.get("status") == "solved"]
    solved_payloads: list[dict] = []
    for mission_id in solved_ids:
        snapshot = repository.get_mission_snapshot(mission_id)
        if not snapshot:
            continue
        if not snapshot.get("mission") or not snapshot.get("results"):
            continue
        solved_payloads.append(snapshot)
    return solved_payloads


def _init_profile_stats() -> dict[str, dict]:
    return {profile: {"count": 0, "sum_cost": 0.0} for profile in AI_PROFILE_PRESETS}


def _extract_training_samples(snapshots: list[dict]) -> list[dict]:
    samples: list[dict] = []
    for snapshot in snapshots:
        mission = snapshot.get("mission") or {}
        results = snapshot.get("results") or {}
        benchmark = snapshot.get("benchmark") or {}
        profile = _extract_training_profile(results)
        if not profile:
            continue
        cost = _compute_training_cost(mission, results, benchmark=benchmark)
        if cost is None:
            continue
        samples.append(
            {
                "mission_id": str(snapshot.get("mission_id", "")),
                "profile": profile,
                "cost": float(cost),
                "context_key": _mission_learning_context(mission),
                "updated_at": str(snapshot.get("updated_at") or snapshot.get("created_at") or ""),
                "mission": mission,
            }
        )
    return samples


def _build_learning_model_payload(samples: list[dict]) -> dict:
    context_stats: dict[str, dict[str, dict]] = {}
    global_stats = _init_profile_stats()

    for sample in samples:
        context_key = str(sample["context_key"])
        profile = str(sample["profile"])
        cost = float(sample["cost"])
        context_profile_stats = context_stats.setdefault(context_key, _init_profile_stats())
        context_profile_stats[profile]["count"] += 1
        context_profile_stats[profile]["sum_cost"] += cost
        global_stats[profile]["count"] += 1
        global_stats[profile]["sum_cost"] += cost

    profile_means: dict[str, dict] = {}
    all_costs: list[float] = []
    for profile, stats in global_stats.items():
        count = int(stats["count"])
        sum_cost = float(stats["sum_cost"])
        mean_cost = (sum_cost / count) if count else None
        profile_means[profile] = {"count": count, "mean_cost": mean_cost}
        if mean_cost is not None:
            all_costs.append(float(mean_cost))

    if not all_costs:
        raise ValueError("Aucune performance exploitable n'a été trouvée dans l'historique.")

    overall_mean_cost = float(np.mean(np.array(all_costs, dtype=float)))
    serialized_contexts: dict[str, dict] = {}
    for context_key, per_profile in context_stats.items():
        serialized_contexts[context_key] = {}
        for profile, stats in per_profile.items():
            count = int(stats["count"])
            if count <= 0:
                continue
            serialized_contexts[context_key][profile] = {
                "count": count,
                "mean_cost": float(stats["sum_cost"]) / float(count),
            }

    return {
        "version": AI_LEARNING_MODEL_VERSION,
        "trained_at": _utcnow().isoformat(),
        "sample_count": len(samples),
        "context_count": len(serialized_contexts),
        "smoothing_alpha": AI_LEARNING_SMOOTHING_ALPHA,
        "overall_mean_cost": overall_mean_cost,
        "global_profiles": profile_means,
        "contexts": serialized_contexts,
        "context_schema": ["weather", "incidents", "clients", "budget", "sleigh", "density"],
        "target": "composite_cost",
    }


def train_ai_learning_model(limit: int = 500) -> dict:
    solved_snapshots = _iter_solved_training_snapshots(limit=limit)
    samples = _extract_training_samples(solved_snapshots)
    sample_count = len(samples)

    if sample_count < AI_LEARNING_MIN_SAMPLES:
        raise ValueError(
            f"Pas assez de données pour entraîner le modèle ({sample_count} échantillon(s), minimum {AI_LEARNING_MIN_SAMPLES})."
        )

    model_payload = _build_learning_model_payload(samples)
    _write_json(AI_LEARNING_MODEL_FILE, model_payload)
    return {
        "status": "trained",
        "model_version": AI_LEARNING_MODEL_VERSION,
        "model_path": str(AI_LEARNING_MODEL_FILE),
        "sample_count": sample_count,
        "context_count": int(model_payload["context_count"]),
        "profiles": sorted(AI_PROFILE_PRESETS.keys()),
        "trained_at": model_payload["trained_at"],
        "target": model_payload["target"],
    }


def load_ai_learning_model() -> dict | None:
    payload = _read_json(AI_LEARNING_MODEL_FILE)
    if not isinstance(payload, dict):
        return None
    if not payload.get("contexts") or not payload.get("global_profiles"):
        return None
    return payload


def _expected_profile_cost(model: dict, context_key: str, profile: str) -> tuple[float, int]:
    alpha = float(model.get("smoothing_alpha", AI_LEARNING_SMOOTHING_ALPHA))
    overall_mean_cost = float(model.get("overall_mean_cost", 3600.0))
    global_profiles = model.get("global_profiles", {})
    context_profiles = model.get("contexts", {}).get(context_key, {})

    global_profile = global_profiles.get(profile, {})
    global_mean = global_profile.get("mean_cost")
    if global_mean is None:
        base_mean = overall_mean_cost
    else:
        base_mean = float(global_mean)

    context_profile = context_profiles.get(profile)
    if not context_profile:
        return base_mean, 0

    context_count = max(0, int(context_profile.get("count", 0)))
    context_mean = float(context_profile.get("mean_cost", base_mean))
    blended_mean = (context_count * context_mean + alpha * base_mean) / (context_count + alpha)
    return blended_mean, context_count


def _rank_profiles_for_context(model: dict, context_key: str) -> list[dict]:
    ranked_profiles: list[dict] = []
    for profile in sorted(AI_PROFILE_PRESETS.keys()):
        expected_cost, support = _expected_profile_cost(model, context_key, profile)
        ranked_profiles.append(
            {
                "profile": profile,
                "label": AI_PROFILE_PRESETS[profile]["label"],
                "expected_cost": round(float(expected_cost), 3),
                "support": int(support),
            }
        )
    ranked_profiles.sort(key=lambda item: (float(item["expected_cost"]), -int(item["support"])))
    return ranked_profiles


def recommend_ai_profile_for_mission(mission: dict, *, model: dict | None = None) -> dict:
    model_payload = model or load_ai_learning_model()
    if not model_payload:
        raise FileNotFoundError("Modèle apprenant introuvable. Lancez d'abord /api/ai-learning/train.")

    context_key = _mission_learning_context(mission)
    ranked_profiles = _rank_profiles_for_context(model_payload, context_key)
    best = ranked_profiles[0]
    runner_up = ranked_profiles[1] if len(ranked_profiles) > 1 else ranked_profiles[0]
    margin = max(0.0, float(runner_up["expected_cost"]) - float(best["expected_cost"]))
    margin_ratio = margin / max(float(runner_up["expected_cost"]), 1e-6)
    confidence = min(0.95, 0.35 + 0.10 * float(np.log1p(best["support"])) + 0.50 * margin_ratio)
    return {
        "profile": best["profile"],
        "label": best["label"],
        "context_key": context_key,
        "confidence": round(float(confidence), 3),
        "top_candidates": ranked_profiles[:3],
        "model": {
            "version": model_payload.get("version", AI_LEARNING_MODEL_VERSION),
            "sample_count": int(model_payload.get("sample_count", 0)),
            "trained_at": model_payload.get("trained_at"),
        },
    }


def get_ai_learning_recommendation(mission_id: str) -> dict:
    _, mission, _ = load_mission_bundle(mission_id)
    recommendation = recommend_ai_profile_for_mission(mission)
    return {"mission_id": mission_id, "recommendation": recommendation}


def _extract_ortools_policy(ai_strategy: dict) -> dict | None:
    if not isinstance(ai_strategy, dict):
        return None
    required_text_fields = ("first_solution_strategy", "local_search_metaheuristic")
    required_int_fields = (
        "solver_time_limit_s",
        "time_slack_s",
        "max_route_time_s",
        "drop_penalty",
        "global_span_cost",
    )
    optimization_target = str(ai_strategy.get("optimization_target", "time"))
    if optimization_target not in {"time", "distance"}:
        optimization_target = "time"

    policy: dict[str, str | int] = {"optimization_target": optimization_target}
    for field in required_text_fields:
        value = str(ai_strategy.get(field, "")).strip()
        if not value:
            return None
        policy[field] = value
    for field in required_int_fields:
        value = ai_strategy.get(field)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        if parsed <= 0:
            return None
        policy[field] = parsed
    return policy


def _ortools_policy_id(policy: dict) -> str:
    payload = json.dumps(policy, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _extract_ortools_tuner_samples(snapshots: list[dict]) -> list[dict]:
    samples: list[dict] = []
    for snapshot in snapshots:
        mission = snapshot.get("mission") or {}
        results = snapshot.get("results") or {}
        benchmark = snapshot.get("benchmark") or {}
        profile = _extract_training_profile(results)
        if not profile:
            continue
        ai_strategy = results.get("ai_strategy", {}) if isinstance(results.get("ai_strategy", {}), dict) else {}
        policy = _extract_ortools_policy(ai_strategy)
        if not policy:
            continue
        cost = _compute_training_cost(mission, results, benchmark=benchmark)
        if cost is None:
            continue
        samples.append(
            {
                "mission_id": str(snapshot.get("mission_id", "")),
                "profile": str(profile),
                "policy_id": _ortools_policy_id(policy),
                "policy": policy,
                "cost": float(cost),
                "context_key": _mission_learning_context(mission),
                "updated_at": str(snapshot.get("updated_at") or snapshot.get("created_at") or ""),
            }
        )
    return samples


def _build_ortools_tuner_model_payload(samples: list[dict]) -> dict:
    context_stats: dict[str, dict[str, dict[str, dict]]] = {}
    global_stats: dict[str, dict[str, dict]] = {}

    for sample in samples:
        context_key = str(sample["context_key"])
        profile = str(sample["profile"])
        policy_id = str(sample["policy_id"])
        policy = dict(sample["policy"])
        cost = float(sample["cost"])

        per_context_profile = context_stats.setdefault(context_key, {}).setdefault(profile, {})
        context_entry = per_context_profile.setdefault(policy_id, {"count": 0, "sum_cost": 0.0})
        context_entry["count"] += 1
        context_entry["sum_cost"] += cost

        per_global_profile = global_stats.setdefault(profile, {})
        global_entry = per_global_profile.setdefault(policy_id, {"count": 0, "sum_cost": 0.0, "policy": policy})
        global_entry["count"] += 1
        global_entry["sum_cost"] += cost

    serialized_global: dict[str, dict[str, dict]] = {}
    global_means: list[float] = []
    for profile, policies in sorted(global_stats.items()):
        serialized_global[profile] = {}
        for policy_id, stats in sorted(policies.items()):
            count = int(stats["count"])
            if count <= 0:
                continue
            mean_cost = float(stats["sum_cost"]) / float(count)
            serialized_global[profile][policy_id] = {
                "count": count,
                "mean_cost": mean_cost,
                "policy": dict(stats["policy"]),
            }
            global_means.append(mean_cost)

    if not global_means:
        raise ValueError("Aucune configuration OR-Tools exploitable n'a été trouvée.")

    serialized_contexts: dict[str, dict[str, dict[str, dict]]] = {}
    for context_key, profiles in sorted(context_stats.items()):
        serialized_contexts[context_key] = {}
        for profile, policies in sorted(profiles.items()):
            serialized_contexts[context_key][profile] = {}
            for policy_id, stats in sorted(policies.items()):
                count = int(stats["count"])
                if count <= 0:
                    continue
                serialized_contexts[context_key][profile][policy_id] = {
                    "count": count,
                    "mean_cost": float(stats["sum_cost"]) / float(count),
                }

    return {
        "version": ORTOOLS_TUNER_MODEL_VERSION,
        "trained_at": _utcnow().isoformat(),
        "sample_count": len(samples),
        "context_count": len(serialized_contexts),
        "profile_count": len(serialized_global),
        "smoothing_alpha": ORTOOLS_TUNER_SMOOTHING_ALPHA,
        "overall_mean_cost": float(np.mean(np.array(global_means, dtype=float))),
        "global_policies": serialized_global,
        "contexts": serialized_contexts,
        "target": "composite_cost",
    }


def train_ortools_tuner_model(limit: int = 1500) -> dict:
    solved_snapshots = _iter_solved_training_snapshots(limit=limit)
    samples = _extract_ortools_tuner_samples(solved_snapshots)
    sample_count = len(samples)
    if sample_count < ORTOOLS_TUNER_MIN_SAMPLES:
        raise ValueError(
            f"Pas assez de données pour entraîner l'auto-tuner OR-Tools ({sample_count} échantillon(s), minimum {ORTOOLS_TUNER_MIN_SAMPLES})."
        )

    model_payload = _build_ortools_tuner_model_payload(samples)
    _write_json(ORTOOLS_TUNER_MODEL_FILE, model_payload)
    return {
        "status": "trained",
        "model_version": ORTOOLS_TUNER_MODEL_VERSION,
        "model_path": str(ORTOOLS_TUNER_MODEL_FILE),
        "sample_count": sample_count,
        "context_count": int(model_payload["context_count"]),
        "profile_count": int(model_payload["profile_count"]),
        "trained_at": model_payload["trained_at"],
        "target": model_payload["target"],
        "fields": list(ORTOOLS_TUNER_FIELDS),
    }


def load_ortools_tuner_model() -> dict | None:
    payload = _read_json(ORTOOLS_TUNER_MODEL_FILE)
    if not isinstance(payload, dict):
        return None
    if not payload.get("global_policies") or not payload.get("contexts"):
        return None
    return payload


def _expected_ortools_policy_cost(model: dict, context_key: str, profile: str, policy_id: str) -> tuple[float, int]:
    alpha = float(model.get("smoothing_alpha", ORTOOLS_TUNER_SMOOTHING_ALPHA))
    overall_mean_cost = float(model.get("overall_mean_cost", 3600.0))
    global_policies = model.get("global_policies", {}).get(profile, {})
    global_policy = global_policies.get(policy_id)
    if not global_policy:
        return overall_mean_cost, 0
    base_mean = float(global_policy.get("mean_cost", overall_mean_cost))
    context_policy = model.get("contexts", {}).get(context_key, {}).get(profile, {}).get(policy_id)
    if not context_policy:
        return base_mean, 0
    context_count = max(0, int(context_policy.get("count", 0)))
    context_mean = float(context_policy.get("mean_cost", base_mean))
    blended_mean = (context_count * context_mean + alpha * base_mean) / (context_count + alpha)
    return blended_mean, context_count


def _rank_ortools_policies_for_context(model: dict, context_key: str, profile: str) -> list[dict]:
    normalized_profile = _normalize_ai_profile(profile)
    global_policies = model.get("global_policies", {}).get(normalized_profile, {})
    ranked_policies: list[dict] = []
    for policy_id, policy_stats in sorted(global_policies.items()):
        expected_cost, support = _expected_ortools_policy_cost(model, context_key, normalized_profile, str(policy_id))
        policy_payload = dict(policy_stats.get("policy", {}))
        ranked_policies.append(
            {
                "policy_id": str(policy_id),
                "expected_cost": round(float(expected_cost), 3),
                "support": int(support),
                "policy": policy_payload,
            }
        )
    ranked_policies.sort(key=lambda item: (float(item["expected_cost"]), -int(item["support"])))
    return ranked_policies


def recommend_ortools_tuning_for_mission(mission: dict, profile: str, *, model: dict | None = None) -> dict:
    model_payload = model or load_ortools_tuner_model()
    if not model_payload:
        raise FileNotFoundError("Auto-tuner OR-Tools introuvable. Lancez d'abord /api/ortools-tuner/train.")

    normalized_profile = _normalize_ai_profile(profile)
    context_key = _mission_learning_context(mission)
    ranked_policies = _rank_ortools_policies_for_context(model_payload, context_key, normalized_profile)
    if not ranked_policies:
        raise ValueError(f"Aucune configuration OR-Tools disponible pour le profil '{normalized_profile}'.")

    best = ranked_policies[0]
    runner_up = ranked_policies[1] if len(ranked_policies) > 1 else ranked_policies[0]
    margin = max(0.0, float(runner_up["expected_cost"]) - float(best["expected_cost"]))
    margin_ratio = margin / max(float(runner_up["expected_cost"]), 1e-6)
    confidence = min(0.95, 0.35 + 0.10 * float(np.log1p(best["support"])) + 0.50 * margin_ratio)
    return {
        "profile": normalized_profile,
        "context_key": context_key,
        "policy_id": best["policy_id"],
        "policy": dict(best["policy"]),
        "confidence": round(float(confidence), 3),
        "top_candidates": ranked_policies[:3],
        "model": {
            "version": model_payload.get("version", ORTOOLS_TUNER_MODEL_VERSION),
            "sample_count": int(model_payload.get("sample_count", 0)),
            "trained_at": model_payload.get("trained_at"),
        },
    }


def _apply_ortools_tuning_policy(ai_strategy: dict, policy: dict) -> dict:
    tuned = dict(ai_strategy)
    for field in ("optimization_target", *ORTOOLS_TUNER_FIELDS):
        if field not in policy:
            continue
        if field in {"first_solution_strategy", "local_search_metaheuristic", "optimization_target"}:
            tuned[field] = str(policy[field])
        else:
            tuned[field] = int(policy[field])
    return tuned


def _context_complexity_multiplier(mission: dict) -> float:
    multiplier = 1.0
    num_clients = max(1, int(mission.get("num_clients", 1)))
    client_bucket = _client_bucket(num_clients)
    weather_bucket = _weather_bucket(str(mission.get("weather_key", "clear")))
    density_bucket = _density_bucket(mission, num_clients)
    budget_bucket = _budget_bucket(mission, num_clients)

    if client_bucket == "medium":
        multiplier += 0.20
    elif client_bucket == "large":
        multiplier += 0.45

    if weather_bucket == "rainy":
        multiplier += 0.10
    elif weather_bucket == "snowy":
        multiplier += 0.18
    elif weather_bucket in {"stormy", "real"}:
        multiplier += 0.28

    if bool(mission.get("random_incidents", False)):
        multiplier += 0.30
    if density_bucket == "dense":
        multiplier += 0.16
    elif density_bucket == "urban":
        multiplier += 0.08
    if budget_bucket == "tight":
        multiplier += 0.12
    return max(0.8, multiplier)


def _adapt_ai_strategy_budget(ai_strategy: dict, mission: dict, *, phase: str) -> tuple[dict, dict]:
    tuned = dict(ai_strategy)
    base_limit = max(6, int(tuned.get("solver_time_limit_s", 20)))
    complexity = _context_complexity_multiplier(mission)

    if phase == "probe":
        probe_scale = min(0.72, 0.50 + 0.12 * max(0.0, complexity - 1.0))
        tuned_limit = max(6, min(12, int(round(float(base_limit) * probe_scale))))
        tuned["solver_time_limit_s"] = tuned_limit
        return tuned, {
            "phase": "probe",
            "base_limit_s": base_limit,
            "complexity_multiplier": round(complexity, 3),
            "solver_time_limit_s": tuned_limit,
        }

    tuned_limit = max(8, min(45, int(round(float(base_limit) * complexity))))
    tuned["solver_time_limit_s"] = tuned_limit
    if tuned_limit > base_limit:
        ratio = float(tuned_limit) / float(max(base_limit, 1))
        time_slack_s = int(tuned.get("time_slack_s", 3600))
        max_route_time_s = int(tuned.get("max_route_time_s", 14400))
        tuned["time_slack_s"] = int(round(float(time_slack_s) * min(1.35, 1.0 + 0.22 * (ratio - 1.0))))
        tuned["max_route_time_s"] = int(round(float(max_route_time_s) * min(1.30, 1.0 + 0.18 * (ratio - 1.0))))
    return tuned, {
        "phase": "final",
        "base_limit_s": base_limit,
        "complexity_multiplier": round(complexity, 3),
        "solver_time_limit_s": tuned_limit,
    }


def _merge_ro_policy(strategy: dict, policy: dict, *, source: str) -> dict:
    merged = _apply_ortools_tuning_policy(strategy, policy)
    merged["ro_policy_source"] = source
    return merged


def _build_ro_portfolio_candidates(base_strategy: dict, ortools_tuning: dict | None = None) -> list[dict]:
    candidates: list[dict] = []
    seen_policy_ids: set[str] = set()

    def append_candidate(candidate_id: str, strategy: dict, source: str) -> None:
        policy = _extract_ortools_policy(strategy)
        if not policy:
            return
        policy_id = _ortools_policy_id(policy)
        if policy_id in seen_policy_ids:
            return
        seen_policy_ids.add(policy_id)
        candidates.append(
            {
                "candidate_id": candidate_id,
                "source": source,
                "policy_id": policy_id,
                "strategy": dict(strategy),
            }
        )

    append_candidate("base", dict(base_strategy), "base")

    top_candidates = ortools_tuning.get("top_candidates", []) if isinstance(ortools_tuning, dict) else []
    for index, candidate in enumerate(top_candidates[:3], start=1):
        policy = candidate.get("policy", {}) if isinstance(candidate, dict) else {}
        if not isinstance(policy, dict) or not policy:
            continue
        append_candidate(
            f"tuner_top_{index}",
            _merge_ro_policy(base_strategy, policy, source=f"tuner_top_{index}"),
            f"tuner_top_{index}",
        )

    preferred_presets = ["pca_gls_fast", "savings_tabu", "pca_gls_distance"]
    target = str(base_strategy.get("optimization_target", "time"))
    if target == "distance":
        preferred_presets = ["pca_gls_distance", "pca_gls_fast", "savings_tabu"]
    for preset_id in preferred_presets:
        preset = RO_PORTFOLIO_PRESETS.get(preset_id)
        if not preset:
            continue
        append_candidate(
            f"preset_{preset_id}",
            _merge_ro_policy(base_strategy, preset, source=f"preset_{preset_id}"),
            f"preset_{preset_id}",
        )

    return candidates[:RO_PORTFOLIO_MAX_CANDIDATES]

def get_ortools_tuner_recommendation(mission_id: str) -> dict:
    _, mission, _ = load_mission_bundle(mission_id)
    profile = _normalize_ai_profile(mission.get("ai_profile"))
    recommendation = recommend_ortools_tuning_for_mission(mission, profile)
    return {"mission_id": mission_id, "recommendation": recommendation}


def evaluate_ortools_tuner_model(limit: int = 2000, holdout_ratio: float = ORTOOLS_TUNER_HOLDOUT_RATIO) -> dict:
    solved_snapshots = _iter_solved_training_snapshots(limit=limit)
    samples = _extract_ortools_tuner_samples(solved_snapshots)

    min_required = max(ORTOOLS_TUNER_MIN_SAMPLES * 2, 24)
    if len(samples) < min_required:
        raise ValueError(
            f"Pas assez de données pour évaluer l'auto-tuner OR-Tools ({len(samples)} échantillon(s), minimum {min_required})."
        )

    ratio = max(0.10, min(0.50, float(holdout_ratio)))
    train_samples, holdout_samples = _split_samples_stratified_by_context_profile(samples, ratio)
    model_payload = _build_ortools_tuner_model_payload(train_samples)

    sample_match_count = 0
    holdout_context_stats: dict[str, dict] = {}
    for sample in holdout_samples:
        context_key = str(sample["context_key"])
        profile = str(sample["profile"])
        policy_id = str(sample["policy_id"])
        observed_cost = float(sample["cost"])
        ranked = _rank_ortools_policies_for_context(model_payload, context_key, profile)
        if ranked and str(ranked[0]["policy_id"]) == policy_id:
            sample_match_count += 1

        bucket_key = f"{context_key}|profile:{profile}"
        bucket = holdout_context_stats.setdefault(
            bucket_key,
            {"context_key": context_key, "profile": profile, "policies": {}},
        )
        policy_stats = bucket["policies"].setdefault(policy_id, {"count": 0, "sum_cost": 0.0})
        policy_stats["count"] += 1
        policy_stats["sum_cost"] += observed_cost

    context_total = 0
    context_hit_count = 0
    regrets: list[float] = []
    context_examples: list[dict] = []

    for bucket_key, bucket in sorted(holdout_context_stats.items()):
        means = {
            policy_id: float(stats["sum_cost"]) / float(stats["count"])
            for policy_id, stats in bucket["policies"].items()
            if int(stats["count"]) > 0
        }
        if len(means) < 2:
            continue
        context_key = str(bucket["context_key"])
        profile = str(bucket["profile"])
        true_best_policy_id = min(means.items(), key=lambda item: item[1])[0]
        ranked = _rank_ortools_policies_for_context(model_payload, context_key, profile)
        predicted_policy_id = str(ranked[0]["policy_id"]) if ranked else true_best_policy_id
        context_total += 1
        if predicted_policy_id == true_best_policy_id:
            context_hit_count += 1
        if predicted_policy_id in means:
            regret = max(0.0, float(means[predicted_policy_id]) - float(means[true_best_policy_id]))
            regrets.append(regret)
        if len(context_examples) < 5:
            context_examples.append(
                {
                    "context_key": context_key,
                    "profile": profile,
                    "true_best_policy_id": true_best_policy_id,
                    "predicted_policy_id": predicted_policy_id,
                    "true_best_cost": round(float(means[true_best_policy_id]), 3),
                    "predicted_cost": round(float(means.get(predicted_policy_id, means[true_best_policy_id])), 3),
                }
            )

    sample_match_rate = float(sample_match_count) / float(len(holdout_samples))
    context_top1_accuracy = (float(context_hit_count) / float(context_total)) if context_total else 0.0
    avg_regret = float(np.mean(np.array(regrets, dtype=float))) if regrets else 0.0

    return {
        "status": "evaluated",
        "model_version": ORTOOLS_TUNER_MODEL_VERSION,
        "target": model_payload.get("target", "composite_cost"),
        "sample_count_total": len(samples),
        "sample_count_train": len(train_samples),
        "sample_count_holdout": len(holdout_samples),
        "holdout_ratio": ratio,
        "split_strategy": "stratified_by_context_profile",
        "sample_match_rate": round(sample_match_rate, 4),
        "contexts_evaluated": context_total,
        "context_top1_accuracy": round(context_top1_accuracy, 4),
        "avg_context_regret": round(avg_regret, 4),
        "examples": context_examples,
    }


def _sample_sort_key(sample: dict) -> tuple[str, str]:
    return (str(sample.get("updated_at", "")), str(sample.get("mission_id", "")))


def _split_samples_stratified_by_context_profile(samples: list[dict], ratio: float) -> tuple[list[dict], list[dict]]:
    total = len(samples)
    target_holdout = max(AI_LEARNING_MIN_SAMPLES, int(round(total * ratio)))
    target_holdout = min(target_holdout, total - AI_LEARNING_MIN_SAMPLES)
    if target_holdout <= 0:
        raise ValueError("Découpage train/holdout impossible avec les données actuelles.")

    strata: dict[tuple[str, str], list[dict]] = {}
    for sample in samples:
        context_key = str(sample.get("context_key", "unknown"))
        profile = str(sample.get("profile", "express"))
        strata.setdefault((context_key, profile), []).append(sample)
    for stratum_samples in strata.values():
        stratum_samples.sort(key=_sample_sort_key)

    def allocate(caps: dict[tuple[str, str], int], seed: bool) -> tuple[dict[tuple[str, str], int], int]:
        allocations: dict[tuple[str, str], int] = {key: 0 for key in strata}
        remaining = int(target_holdout)

        if seed and remaining > 0:
            seed_candidates = [key for key, cap in caps.items() if int(cap) > 0]
            ranked_seed_candidates = sorted(
                seed_candidates,
                key=lambda key: (len(strata[key]), key[0], key[1]),
                reverse=True,
            )
            if remaining >= len(ranked_seed_candidates):
                chosen = ranked_seed_candidates
            else:
                chosen = ranked_seed_candidates[:remaining]
            for key in chosen:
                allocations[key] += 1
                remaining -= 1

        if remaining <= 0:
            return allocations, 0

        effective_total = sum(len(strata[key]) for key, cap in caps.items() if int(cap) > int(allocations.get(key, 0)))
        if effective_total <= 0:
            return allocations, remaining

        remainders: dict[tuple[str, str], float] = {}
        allocated = 0
        for key, stratum_samples in strata.items():
            current = int(allocations.get(key, 0))
            cap = int(caps.get(key, 0))
            cap_left = max(0, cap - current)
            if cap_left <= 0:
                remainders[key] = 0.0
                continue
            quota = (float(len(stratum_samples)) * float(remaining)) / float(max(1, effective_total))
            base = min(cap_left, int(np.floor(quota)))
            allocations[key] = current + base
            remainders[key] = quota - float(base)
            allocated += base

        remaining_after_base = remaining - allocated
        if remaining_after_base <= 0:
            return allocations, 0

        ranking = sorted(
            strata.keys(),
            key=lambda key: (
                float(remainders.get(key, 0.0)),
                int(caps.get(key, 0)) - int(allocations.get(key, 0)),
                len(strata[key]),
                key,
            ),
            reverse=True,
        )

        while remaining_after_base > 0:
            progressed = False
            for key in ranking:
                if int(allocations.get(key, 0)) >= int(caps.get(key, 0)):
                    continue
                allocations[key] = int(allocations.get(key, 0)) + 1
                remaining_after_base -= 1
                progressed = True
                if remaining_after_base == 0:
                    break
            if not progressed:
                break
        return allocations, remaining_after_base

    preferred_caps = {key: max(0, len(stratum_samples) - 1) for key, stratum_samples in strata.items()}
    allocations, remaining = allocate(preferred_caps, seed=True)
    if remaining > 0:
        relaxed_caps = {key: len(stratum_samples) for key, stratum_samples in strata.items()}
        allocations, remaining = allocate(relaxed_caps, seed=False)
    if remaining > 0:
        raise ValueError("Découpage stratifié impossible avec les données actuelles.")

    train_samples: list[dict] = []
    holdout_samples: list[dict] = []
    for key, stratum_samples in strata.items():
        context_key, profile = key
        holdout_count = int(allocations.get(key, 0))
        if holdout_count <= 0:
            train_samples.extend(stratum_samples)
            continue
        ranked = sorted(
            stratum_samples,
            key=lambda sample: hashlib.sha1(
                (
                    f"{context_key}|{profile}|{sample.get('mission_id', '')}|"
                    f"{sample.get('updated_at', '')}|{sample.get('profile', '')}"
                ).encode("utf-8")
            ).hexdigest(),
        )
        holdout_ids = {str(sample.get("mission_id", "")) for sample in ranked[:holdout_count]}
        for sample in stratum_samples:
            if str(sample.get("mission_id", "")) in holdout_ids:
                holdout_samples.append(sample)
            else:
                train_samples.append(sample)

    if len(train_samples) < AI_LEARNING_MIN_SAMPLES or len(holdout_samples) < AI_LEARNING_MIN_SAMPLES:
        raise ValueError("Découpage train/holdout impossible avec les données actuelles.")

    train_samples.sort(key=_sample_sort_key)
    holdout_samples.sort(key=_sample_sort_key)
    return train_samples, holdout_samples


def evaluate_ai_learning_model(limit: int = 800, holdout_ratio: float = AI_LEARNING_HOLDOUT_RATIO) -> dict:
    solved_snapshots = _iter_solved_training_snapshots(limit=limit)
    samples = _extract_training_samples(solved_snapshots)

    min_required = max(AI_LEARNING_MIN_SAMPLES * 2, 16)
    if len(samples) < min_required:
        raise ValueError(
            f"Pas assez de données pour évaluer le modèle ({len(samples)} échantillon(s), minimum {min_required})."
        )

    ratio = max(0.10, min(0.50, float(holdout_ratio)))
    train_samples, holdout_samples = _split_samples_stratified_by_context_profile(samples, ratio)
    model_payload = _build_learning_model_payload(train_samples)

    sample_match_count = 0
    holdout_context_stats: dict[str, dict[str, dict]] = {}
    for sample in holdout_samples:
        context_key = str(sample["context_key"])
        profile = str(sample["profile"])
        observed_cost = float(sample["cost"])
        ranked = _rank_profiles_for_context(model_payload, context_key)
        if ranked and ranked[0]["profile"] == profile:
            sample_match_count += 1
        context_profiles = holdout_context_stats.setdefault(context_key, {})
        profile_stats = context_profiles.setdefault(profile, {"count": 0, "sum_cost": 0.0})
        profile_stats["count"] += 1
        profile_stats["sum_cost"] += observed_cost

    context_total = 0
    context_hit_count = 0
    regrets: list[float] = []
    context_examples: list[dict] = []

    for context_key, profiles in sorted(holdout_context_stats.items()):
        means = {profile: float(stats["sum_cost"]) / float(stats["count"]) for profile, stats in profiles.items() if int(stats["count"]) > 0}
        if len(means) < 2:
            continue
        true_best_profile = min(means.items(), key=lambda item: item[1])[0]
        ranked = _rank_profiles_for_context(model_payload, context_key)
        predicted_profile = ranked[0]["profile"] if ranked else "express"
        context_total += 1
        if predicted_profile == true_best_profile:
            context_hit_count += 1
        if predicted_profile in means:
            regret = max(0.0, float(means[predicted_profile]) - float(means[true_best_profile]))
            regrets.append(regret)
        if len(context_examples) < 5:
            context_examples.append(
                {
                    "context_key": context_key,
                    "true_best_profile": true_best_profile,
                    "predicted_profile": predicted_profile,
                    "true_best_cost": round(float(means[true_best_profile]), 3),
                    "predicted_cost": round(float(means.get(predicted_profile, means[true_best_profile])), 3),
                }
            )

    sample_match_rate = float(sample_match_count) / float(len(holdout_samples))
    context_top1_accuracy = (float(context_hit_count) / float(context_total)) if context_total else 0.0
    avg_regret = float(np.mean(np.array(regrets, dtype=float))) if regrets else 0.0

    return {
        "status": "evaluated",
        "model_version": AI_LEARNING_MODEL_VERSION,
        "target": model_payload.get("target", "composite_cost"),
        "sample_count_total": len(samples),
        "sample_count_train": len(train_samples),
        "sample_count_holdout": len(holdout_samples),
        "holdout_ratio": ratio,
        "split_strategy": "stratified_by_context_profile",
        "sample_match_rate": round(sample_match_rate, 4),
        "contexts_evaluated": context_total,
        "context_top1_accuracy": round(context_top1_accuracy, 4),
        "avg_context_regret": round(avg_regret, 4),
        "examples": context_examples,
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
    d = {
        "id": int(row["id"]),
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
        "nom_client": str(row.get("nom_client", f"Client {int(row['id'])}")),
        "poids_colis": float(row.get("poids_colis", 0)),
    }
    if "tw_start" in row and "tw_end" in row:
        d["tw_start"] = float(row.get("tw_start", 0))
        d["tw_end"] = float(row.get("tw_end", 28800))
    # Cargo fields — present only on missions generated with the new generator
    cargo_code = row.get("cargo_code")
    if cargo_code and str(cargo_code) not in ("nan", "None", ""):
        d["cargo_code"] = str(cargo_code)
        d["cargo_label"] = str(row.get("cargo_label", ""))
        d["cargo_emoji"] = str(row.get("cargo_emoji", "📦"))
        constraint = row.get("cargo_constraint")
        d["cargo_constraint"] = None if str(constraint) in ("nan", "None", "") else str(constraint)
    return d


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
    radius_km, max_clients_allowed = _validate_search_area_constraints(payload)

    success, message = generate_new_zone(
        payload["zone"],
        payload["num_clients"],
        data_path=str(paths.data_file),
        graph_path=str(paths.graph_file),
        time_matrix_path=str(paths.time_matrix_file),
        dist_matrix_path=str(paths.dist_matrix_file),
        center_lat=payload.get("center_lat"),
        center_lon=payload.get("center_lon"),
        search_radius_km=radius_km,
        departure_hour=payload.get("departure_hour"),
        with_elevation=bool(payload.get("with_elevation", False)),
        elevation_path=str(paths.elevation_file),
    )
    if not success:
        raise ValueError(message or "Generation de zone impossible")

    if payload.get("weather_key") == "random":
        weather = get_simulated_weather(weather_file=str(paths.weather_file))
    elif payload.get("weather_key") == "real":
        weather = get_real_weather(str(payload.get("city") or payload["zone"]), weather_file=str(paths.weather_file))
    else:
        weather = dict(WEATHER_MAP.get(payload.get("weather_key", "Clear"), WEATHER_MAP["Clear"]))
        _write_json(paths.weather_file, weather)

    mission = {
        "mission_id": mission_id,
        **payload,
        "generation_message": message,
        "max_clients_allowed": max_clients_allowed,
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
        "elevation": _read_json(paths.elevation_file, None),
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


def get_human_route_options(
    mission_id: str,
    from_id: int,
    to_id: int,
    sleigh_id: int,
    speed_multiplier: float,
    vehicle_capacity: int | None = None,
    k: int = 3,
) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    df = read_points(paths.data_file)
    graph = _load_graph_cached(paths.graph_file)
    
    from_lat, from_lon = get_point_latlon(df, int(from_id), graph=graph)
    to_lat, to_lon = get_point_latlon(df, int(to_id), graph=graph)

    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    time_factor = float(weather.get("factor", 1.0)) / speed_multiplier
    incidents_payload = _read_json(paths.incidents_file, {"count": 0, "segments": []})
    incident_segments = list((incidents_payload or {}).get("segments", []))
    incident_token = _incident_cache_token(incident_segments)
    cache_key = (
        str(mission_id),
        int(from_id),
        int(to_id),
        round(float(speed_multiplier), 4),
        round(float(time_factor), 4),
        incident_token,
        int(k),
    )
    options = _route_options_cache_get(cache_key)
    if options is None:
        options = compute_route_options(
            graph,
            from_lat,
            from_lon,
            to_lat,
            to_lon,
            time_factor=time_factor,
            k=k,
            incident_segments=incident_segments,
        )
        _route_options_cache_set(cache_key, options)
    human_state = human_state_from_payload(human_state_payload)
    human_state.speed_multiplier = speed_multiplier
    if vehicle_capacity is not None:
        human_state.vehicle_capacity = int(vehicle_capacity)
    options = _annotate_route_options_feasibility(
        df,
        human_state,
        options,
        to_id=int(to_id),
        sleigh_id=int(sleigh_id),
        time_factor=float(time_factor),
        incident_segments=incident_segments,
    )
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
    graph = _load_graph_cached(paths.graph_file)
    client_ids = set(df["id"].astype(int).tolist())
    is_client = to_id in client_ids

    if is_client and to_id in state.assigned_clients:
        raise ValueError(f"Client {to_id} deja assigne")

    selected_route = payload["selected_route"]
    route_nodes = [int(node) for node in selected_route["route_nodes"]]
    dist_m, base_time_s = _strict_route_metrics(graph, route_nodes)
    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    time_factor = float(weather.get("factor", 1.0)) / max(float(state.speed_multiplier), 0.1)
    option_payload = {
        "route_nodes": route_nodes,
        "geometry": selected_route.get("geometry", []),
        "dist_m": float(dist_m),
        "base_time_s": float(base_time_s),
        "time_s": float(base_time_s) * float(time_factor),
        "label": str(selected_route.get("label", "Segment")),
    }
    incidents_payload = _read_json(paths.incidents_file, {"count": 0, "segments": []})
    incident_segments = list((incidents_payload or {}).get("segments", []))
    feasibility = _annotate_route_options_feasibility(
        df,
        state,
        [option_payload],
        to_id=to_id,
        sleigh_id=int(payload["sleigh_id"]),
        time_factor=float(time_factor),
        incident_segments=incident_segments,
    )
    if feasibility and not bool(feasibility[0].get("is_feasible", True)):
        raise ValueError(_infeasible_segment_message(feasibility[0]))

    segment = {
        "variant": "human",
        "sleigh_id": int(payload["sleigh_id"]),
        "from_id": int(payload["from_id"]),
        "to_id": to_id,
        "route_nodes": route_nodes,
        "geometry": selected_route.get("geometry", []),
        "dist_m": float(dist_m),
        "base_time_s": float(base_time_s),
        "time_s": float(base_time_s) * float(time_factor),
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
    
    # Matrices (temps + distance)
    time_matrix = np.load(paths.time_matrix_file)
    dist_matrix = np.load(paths.dist_matrix_file)
    id_to_idx = {int(row["id"]): idx for idx, (_, row) in enumerate(df.iterrows())}
    current_idx = id_to_idx[current_point_id]
    depot_idx = id_to_idx[0]
    
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
        travel_dist_m = float(dist_matrix[current_idx][target_idx])
        return_time = float(time_matrix[target_idx][depot_idx]) * time_factor
        return_dist_m = float(dist_matrix[target_idx][depot_idx])
        arrival_time = current_time_s + travel_time
        
        client_row = df[df["id"] == client_id].iloc[0]
        poids = float(client_row["poids_colis"])
        tw_start = float(client_row.get("tw_start", 0))
        tw_end = float(client_row.get("tw_end", 28800))
        
        # Heuristique multi-critères:
        # - temps d'approche (prioritaire)
        # - retour estimé au depot
        # - respect fenêtre de temps
        # - respect capacité
        wait_time = max(0, tw_start - arrival_time)
        slack = tw_end - arrival_time
        late_penalty = 0.0 if slack >= 0 else 1_000_000.0 + abs(slack) * 5.0
        weight_over = max(0.0, (current_load + poids) - state.vehicle_capacity)
        weight_penalty = 0.0 if weight_over <= 0 else 500_000.0 + weight_over * 100.0
        urgency_penalty = 0.0 if slack > 1800 else float(max(0.0, 1800.0 - slack)) * 0.25
        score = (
            travel_time
            + return_time * 0.25
            + wait_time * 0.4
            + urgency_penalty
            + late_penalty
            + weight_penalty
        )
        
        suggestions.append({
            "client_id": client_id,
            "nom_client": client_row["nom_client"],
            "score": score,
            "travel_time_s": travel_time,
            "travel_dist_m": travel_dist_m,
            "return_time_s": return_time,
            "return_dist_m": return_dist_m,
            "slack_s": slack,
            "arrival_clock": format_clock(32400 + arrival_time), # 9h + offset
            "is_feasible": slack >= 0 and (current_load + poids <= state.vehicle_capacity)
        })
        
    suggestions.sort(key=lambda x: (not x["is_feasible"], x["score"], x["travel_time_s"]))
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


def _build_incident_matrix(paths: MissionPaths, mission: dict, *, force: bool = False) -> str | None:
    if not paths.time_matrix_file.exists():
        return None
    if not force and not mission.get("random_incidents"):
        return None
    incident_payload = _read_json(paths.incidents_file, {"segments": []})
    incident_segments = incident_payload.get("segments", [])
    if not incident_segments:
        return None
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


def _solve_vrp_from_strategy(
    paths: MissionPaths,
    mission: dict,
    weather: dict,
    incident_matrix_path: str | None,
    ai_strategy: dict,
    *,
    output_path: str | Path | None = None,
    human_routes: dict | None = None,
) -> dict:
    target_output_path = str(output_path or paths.results_file)
    return solve_vrp(
        num_vehicles=int(ai_strategy["num_vehicles"]),
        vehicle_capacity=int(ai_strategy["vehicle_capacity"]),
        speed_multiplier=float(ai_strategy["speed_multiplier"]),
        forced_weather=weather,
        incident_matrix_path=incident_matrix_path,
        data_path=str(paths.data_file),
        time_matrix_path=str(paths.time_matrix_file),
        dist_matrix_path=str(paths.dist_matrix_file),
        weather_file=str(paths.weather_file),
        output_path=target_output_path,
        optimization_target=ai_strategy["optimization_target"],
        solver_time_limit_s=int(ai_strategy["solver_time_limit_s"]),
        first_solution_strategy=ai_strategy["first_solution_strategy"],
        local_search_metaheuristic=ai_strategy["local_search_metaheuristic"],
        time_slack_s=int(ai_strategy["time_slack_s"]),
        max_route_time_s=int(ai_strategy["max_route_time_s"]),
        drop_penalty=int(ai_strategy["drop_penalty"]),
        global_span_cost=int(ai_strategy["global_span_cost"]),
        initial_routes=human_routes or None,
        vehicle_fixed_cost=int(ai_strategy.get("vehicle_fixed_cost", 0)),
    )


def _run_ro_portfolio_probe(
    paths: MissionPaths,
    mission: dict,
    weather: dict,
    incident_matrix_path: str | None,
    candidates: list[dict],
) -> dict:
    probe_output_path = paths.root_dir / RO_PORTFOLIO_PROBE_OUTPUT_NAME
    probe_results: list[dict] = []
    best_candidate: dict | None = None

    for candidate in candidates:
        strategy = dict(candidate.get("strategy", {}))
        if not strategy:
            continue
        probe_strategy, budget_meta = _adapt_ai_strategy_budget(strategy, mission, phase="probe")
        try:
            solved = _solve_vrp_from_strategy(
                paths,
                mission,
                weather,
                incident_matrix_path,
                probe_strategy,
                output_path=probe_output_path,
            )
            if not isinstance(solved, dict):
                raise RuntimeError("solve_vrp returned no result")
            cost = _compute_training_cost(mission, solved, benchmark=None)
            if cost is None:
                fallback_time = _safe_float(solved.get("total_time_s"))
                fallback_dist = _safe_float(solved.get("total_dist_m"), 0.0)
                if fallback_time is None:
                    raise RuntimeError("probe solution has no cost")
                cost = float(fallback_time) + 0.01 * float(fallback_dist or 0.0)
            candidate_row = {
                "candidate_id": candidate.get("candidate_id"),
                "source": candidate.get("source"),
                "policy_id": candidate.get("policy_id"),
                "probe_cost": round(float(cost), 4),
                "probe_budget": budget_meta,
                "status": "ok",
            }
            probe_results.append(candidate_row)
            if best_candidate is None or float(cost) < float(best_candidate["cost"]):
                best_candidate = {
                    "cost": float(cost),
                    "strategy": dict(strategy),
                    "candidate": candidate_row,
                }
        except Exception as exc:
            probe_results.append(
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "source": candidate.get("source"),
                    "policy_id": candidate.get("policy_id"),
                    "status": "failed",
                    "error": str(exc),
                    "probe_budget": budget_meta,
                }
            )

    selected_strategy = dict(best_candidate["strategy"]) if best_candidate else dict(candidates[0]["strategy"]) if candidates else {}
    return {
        "selected_strategy": selected_strategy,
        "selected_candidate": best_candidate["candidate"] if best_candidate else None,
        "probe_results": probe_results,
    }


def _solve_mission_internal(
    mission_id: str,
    payload: dict,
    *,
    mission_for_strategy: dict | None = None,
    ai_strategy_override: dict | None = None,
    use_portfolio: bool = False,
    force_incident_matrix: bool = False,
) -> dict:
    paths, mission, human_state_payload = load_mission_bundle(mission_id)
    df = read_points(paths.data_file)
    graph = load_graph(paths.graph_file)
    human_state = human_state_from_payload(human_state_payload)
    human_state.num_vehicles = int(payload["num_vehicles"])
    human_state.vehicle_capacity = int(payload["vehicle_capacity"])
    human_state.speed_multiplier = float(payload["speed_multiplier"])
    _write_json(paths.human_state_file, serialize_human_state(human_state))

    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    incident_matrix_path = _build_incident_matrix(paths, mission, force=force_incident_matrix)
    strategy_mission = mission_for_strategy or mission
    ai_strategy = deepcopy(ai_strategy_override) if ai_strategy_override else resolve_ai_strategy(strategy_mission, payload)

    # Portfolio léger : 2 presets sondés rapidement, on garde la meilleure config.
    # Activé pour solve_mission (basic) ; solve_mission_learned a son propre portfolio
    # complet avec tuner. On saute le portfolio si ai_strategy_override est fourni
    # (évite de re-sonder lors de l'appel interne depuis solve_mission_learned).
    if use_portfolio and ai_strategy_override is None:
        try:
            candidates = _build_ro_portfolio_candidates(ai_strategy)[:2]
            portfolio_probe = _run_ro_portfolio_probe(
                paths, mission, weather, incident_matrix_path, candidates
            )
            selected = portfolio_probe.get("selected_strategy")
            if selected:
                ai_strategy = dict(selected)
                ai_strategy, _ = _adapt_ai_strategy_budget(ai_strategy, mission, phase="final")
                ai_strategy["ro_portfolio"] = {
                    "enabled": True,
                    "candidate_count": len(candidates),
                    "selected_candidate": portfolio_probe.get("selected_candidate"),
                }
        except Exception:
            pass  # repli silencieux sur la stratégie initiale

    human_routes = {k: [int(c) for c in v] for k, v in human_state.routes_by_sleigh.items() if v}
    results = _solve_vrp_from_strategy(
        paths, mission, weather, incident_matrix_path, ai_strategy,
        human_routes=human_routes or None,
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
        time_matrix_path=str(incident_matrix_path or paths.time_matrix_file),
        dist_matrix_path=str(paths.dist_matrix_file),
        optimized_json_path=str(paths.results_file),
        benchmark_file=str(paths.benchmark_file),
        time_scale_factor=float(weather.get("factor", 1.0)) / max(float(ai_strategy.get("speed_multiplier", 1.0)), 0.1),
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


def solve_mission(mission_id: str, payload: dict) -> dict:
    return _solve_mission_internal(mission_id, payload, use_portfolio=True)


def _solve_payload_lite(results: dict, benchmark: dict) -> dict:
    optimized = benchmark.get("optimized", {}) if isinstance(benchmark, dict) else {}
    savings = benchmark.get("savings", {}) if isinstance(benchmark, dict) else {}
    return {
        "results": {
            "total_time_s": float(results.get("total_time_s", 0.0)),
            "dropped_points": [int(point_id) for point_id in results.get("dropped_points", [])],
            "tours": results.get("tours", []),
        },
        "benchmark": {
            "optimized": {
                "total_time_s": float(optimized.get("total_time_s", results.get("total_time_s", 0.0))),
                "total_dist_m": float(optimized.get("total_dist_m", 0.0)),
            },
            "savings": {
                "co2_saved_kg": float(savings.get("co2_saved_kg", 0.0)),
            },
        },
    }


def _pick_incident_pairs(df, current_results: dict, count: int, rng: random.Random) -> list[tuple[int, int]]:
    candidate_pairs: list[tuple[int, int]] = []
    known_ids = set(int(row["id"]) for _, row in df.iterrows())

    for tour in current_results.get("tours", []):
        route = [int(route_id) for route_id in tour.get("route_ids", [])]
        for source_id, dest_id in zip(route[:-1], route[1:]):
            if source_id == dest_id:
                continue
            if source_id not in known_ids or dest_id not in known_ids:
                continue
            candidate_pairs.append((source_id, dest_id))

    if not candidate_pairs:
        client_ids = [int(row["id"]) for _, row in df.iterrows() if int(row["id"]) != 0]
        for source_id in client_ids:
            for dest_id in client_ids:
                if source_id != dest_id:
                    candidate_pairs.append((source_id, dest_id))

    unique_pairs = list(dict.fromkeys(candidate_pairs))
    rng.shuffle(unique_pairs)
    return unique_pairs[: max(1, int(count) * 6)]


def _generate_incident_segments(
    paths: MissionPaths,
    *,
    current_results: dict,
    count: int,
    strategy: str,
    seed: int | None,
) -> list[dict]:
    graph = _load_graph_cached(paths.graph_file)
    df = read_points(paths.data_file)
    rng = random.Random(seed if seed is not None else random.randint(1, 1_000_000))
    selected_pairs = _pick_incident_pairs(df, current_results, count=count, rng=rng)

    if strategy == "random":
        rng.shuffle(selected_pairs)

    row_by_id = {int(row["id"]): row for _, row in df.iterrows()}
    segments: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for source_id, dest_id in selected_pairs:
        if len(segments) >= count:
            break
        pair = (int(source_id), int(dest_id))
        if pair in seen:
            continue
        seen.add(pair)
        source_row = row_by_id.get(pair[0])
        dest_row = row_by_id.get(pair[1])
        if source_row is None or dest_row is None:
            continue
        try:
            options = compute_route_options(
                graph,
                float(source_row["lat"]),
                float(source_row["lon"]),
                float(dest_row["lat"]),
                float(dest_row["lon"]),
                time_factor=1.0,
                k=1,
            )
        except Exception:
            options = []
        if not options:
            continue
        option = options[0]
        segments.append(
            {
                "variant": "incident",
                "sleigh_id": -1,
                "from_id": pair[0],
                "to_id": pair[1],
                "route_nodes": option.get("route_nodes", []),
                "geometry": option.get("geometry", []),
                "dist_m": float(option.get("dist_m", 0.0)),
                "time_s": float(option.get("time_s", 0.0)) * 6.0,
                "title": f"⚠️ Incident live · axe bloque #{pair[0]} -> #{pair[1]}",
            }
        )
    return segments


def _manual_incident_segments_from_payload(
    paths: MissionPaths,
    *,
    before_results: dict,
    manual_segments_raw: list[dict] | None,
) -> list[dict]:
    if not manual_segments_raw:
        return []

    df = read_points(paths.data_file)
    graph = _load_graph_cached(paths.graph_file)
    row_by_id = {int(row["id"]): row for _, row in df.iterrows()}
    ai_segments = before_results.get("ai_segments", []) if isinstance(before_results, dict) else []

    normalized: list[dict] = []
    for idx, raw in enumerate(manual_segments_raw[:3]):
        try:
            source_id = int(raw.get("from_id"))
            dest_id = int(raw.get("to_id"))
        except Exception:
            continue
        if source_id == dest_id:
            continue
        if source_id not in row_by_id or dest_id not in row_by_id:
            continue

        route_nodes = [int(node_id) for node_id in (raw.get("route_nodes") or []) if str(node_id).strip() != ""]
        geometry = raw.get("geometry") or []
        dist_m = float(raw.get("dist_m") or 0.0)
        time_s = float(raw.get("time_s") or 0.0)

        matched = None
        for seg in ai_segments:
            if int(seg.get("from_id", -1)) == source_id and int(seg.get("to_id", -1)) == dest_id:
                matched = seg
                if route_nodes:
                    seg_nodes = [int(node_id) for node_id in seg.get("route_nodes", [])]
                    if seg_nodes == route_nodes:
                        break

        if matched:
            if not route_nodes:
                route_nodes = [int(node_id) for node_id in matched.get("route_nodes", [])]
            if not geometry:
                geometry = matched.get("geometry", [])
            if dist_m <= 0:
                dist_m = float(matched.get("dist_m", 0.0))
            if time_s <= 0:
                time_s = float(matched.get("time_s", 0.0))

        if not geometry or dist_m <= 0 or time_s <= 0:
            source_row = row_by_id[source_id]
            dest_row = row_by_id[dest_id]
            try:
                options = compute_route_options(
                    graph,
                    float(source_row["lat"]),
                    float(source_row["lon"]),
                    float(dest_row["lat"]),
                    float(dest_row["lon"]),
                    time_factor=1.0,
                    k=1,
                )
            except Exception:
                options = []
            if options:
                option = options[0]
                if not route_nodes:
                    route_nodes = [int(node_id) for node_id in option.get("route_nodes", [])]
                if not geometry:
                    geometry = option.get("geometry", [])
                if dist_m <= 0:
                    dist_m = float(option.get("dist_m", 0.0))
                if time_s <= 0:
                    time_s = float(option.get("time_s", 0.0))

        if not geometry:
            continue

        normalized.append(
            {
                "variant": "incident",
                "sleigh_id": -1,
                "from_id": source_id,
                "to_id": dest_id,
                "route_nodes": route_nodes,
                "geometry": geometry,
                "dist_m": float(dist_m),
                "time_s": max(1.0, float(time_s) * 6.0),
                "title": str(raw.get("title") or f"⚠️ Incident live · segment bloque #{source_id} -> #{dest_id}"),
                "manual": True,
                "manual_rank": idx + 1,
            }
        )
    return normalized


def _safe_pct(delta: float, reference: float) -> float:
    if abs(float(reference)) < 1e-6:
        return 0.0
    return (float(delta) / float(reference)) * 100.0


def simulate_incident_replan(mission_id: str, payload: dict) -> dict:
    paths, mission, _ = load_mission_bundle(mission_id)
    if not paths.results_file.exists() or not paths.benchmark_file.exists():
        raise ValueError("Aucune tournée courante: lancez d'abord un solve.")

    before_results = _read_json(paths.results_file, {})
    before_benchmark = _read_json(paths.benchmark_file, {})
    if not before_results or not before_benchmark:
        raise ValueError("Résultat courant introuvable pour cette mission.")

    incident_count = max(1, min(int(payload.get("incident_count", 1)), 3))
    strategy = str(payload.get("strategy", "guided") or "guided").strip().lower()
    if strategy not in {"guided", "random"}:
        strategy = "guided"
    seed = payload.get("seed")

    manual_segments_raw = payload.get("manual_segments")
    incident_segments = _manual_incident_segments_from_payload(
        paths,
        before_results=before_results,
        manual_segments_raw=manual_segments_raw if isinstance(manual_segments_raw, list) else None,
    )
    if not incident_segments:
        incident_segments = _generate_incident_segments(
            paths,
            current_results=before_results,
            count=incident_count,
            strategy=strategy,
            seed=int(seed) if seed is not None else None,
        )
    if not incident_segments:
        raise RuntimeError("Impossible de générer un incident exploitable sur cette mission.")

    incidents_payload = {"count": len(incident_segments), "segments": incident_segments}
    _write_json(paths.incidents_file, incidents_payload)

    before_payload = _solve_payload_lite(before_results, before_benchmark)

    base_strategy = before_results.get("ai_strategy") if isinstance(before_results, dict) else {}
    solve_payload = {
        "num_vehicles": int(payload.get("num_vehicles") or base_strategy.get("num_vehicles") or max(1, len(before_results.get("tours", [])))),
        "vehicle_capacity": int(payload.get("vehicle_capacity") or base_strategy.get("vehicle_capacity") or 200),
        "speed_multiplier": float(payload.get("speed_multiplier") or base_strategy.get("speed_multiplier") or 1.0),
        "optimization_target": str(payload.get("optimization_target") or base_strategy.get("optimization_target") or "time"),
    }

    after_payload = _solve_mission_internal(
        mission_id,
        solve_payload,
        mission_for_strategy=mission,
        use_portfolio=True,
        force_incident_matrix=True,
    )

    after_optimized = after_payload.get("benchmark", {}).get("optimized", {})
    before_optimized = before_payload.get("benchmark", {}).get("optimized", {})
    after_savings = after_payload.get("benchmark", {}).get("savings", {})
    before_savings = before_payload.get("benchmark", {}).get("savings", {})

    delta_time_s = float(after_optimized.get("total_time_s", 0.0)) - float(before_optimized.get("total_time_s", 0.0))
    delta_dist_m = float(after_optimized.get("total_dist_m", 0.0)) - float(before_optimized.get("total_dist_m", 0.0))
    delta_co2_kg = float(after_savings.get("co2_saved_kg", 0.0)) - float(before_savings.get("co2_saved_kg", 0.0))

    return {
        "incidents": incidents_payload,
        "before": before_payload,
        "after": after_payload,
        "delta_kpi": {
            "time_s": delta_time_s,
            "dist_m": delta_dist_m,
            "co2_kg": delta_co2_kg,
            "time_pct": _safe_pct(delta_time_s, float(before_optimized.get("total_time_s", 0.0))),
            "dist_pct": _safe_pct(delta_dist_m, float(before_optimized.get("total_dist_m", 0.0))),
        },
    }


def solve_mission_learned(mission_id: str, payload: dict) -> dict:
    paths, mission, _ = load_mission_bundle(mission_id)
    learning_notes: list[str] = []
    model_payload = load_ai_learning_model()
    if not model_payload:
        try:
            train_ai_learning_model(limit=1000)
        except ValueError as exc:
            learning_notes.append(f"ai_learning_unavailable: {exc}")
        model_payload = load_ai_learning_model()

    recommendation: dict | None = None
    mission_with_learned_profile = dict(mission)
    ai_strategy = resolve_ai_strategy(mission, payload)
    ai_strategy["profile_origin"] = "fallback_preset"

    if model_payload:
        try:
            recommendation = recommend_ai_profile_for_mission(mission, model=model_payload)
            recommended_profile = recommendation["profile"]
            mission_with_learned_profile = {**mission, "ai_profile": recommended_profile}
            ai_strategy = resolve_ai_strategy(mission_with_learned_profile, payload)
            ai_strategy["profile_origin"] = "learned"
            ai_strategy["learning"] = recommendation
        except (FileNotFoundError, ValueError) as exc:
            learning_notes.append(f"ai_recommendation_failed: {exc}")
    else:
        learning_notes.append("ai_learning_model_missing_after_train")

    ortools_tuning: dict | None = None

    tuner_model = load_ortools_tuner_model()
    if not tuner_model:
        try:
            train_ortools_tuner_model(limit=2000)
            tuner_model = load_ortools_tuner_model()
        except ValueError as exc:
            learning_notes.append(f"ortools_tuner_unavailable: {exc}")
            tuner_model = None

    if tuner_model and recommendation:
        try:
            ortools_tuning = recommend_ortools_tuning_for_mission(
                mission,
                recommendation["profile"],
                model=tuner_model,
            )
            ai_strategy = _apply_ortools_tuning_policy(ai_strategy, ortools_tuning["policy"])
            ai_strategy["ortools_tuning"] = ortools_tuning
            ai_strategy["tuning_origin"] = "learned_ortools"
        except ValueError as exc:
            learning_notes.append(f"ortools_recommendation_failed: {exc}")
            ortools_tuning = None

    weather = load_weather(paths.weather_file, mission.get("weather_key"))
    incident_matrix_path = _build_incident_matrix(paths, mission)
    portfolio_candidates = _build_ro_portfolio_candidates(ai_strategy, ortools_tuning=ortools_tuning)
    portfolio_probe = _run_ro_portfolio_probe(
        paths,
        mission,
        weather,
        incident_matrix_path,
        portfolio_candidates,
    )
    selected_strategy = dict(portfolio_probe.get("selected_strategy") or ai_strategy)
    selected_strategy, budget_meta = _adapt_ai_strategy_budget(selected_strategy, mission, phase="final")
    selected_strategy["ro_adaptive_budget"] = budget_meta
    selected_strategy["ro_portfolio"] = {
        "enabled": True,
        "candidate_count": len(portfolio_candidates),
        "selected_candidate": portfolio_probe.get("selected_candidate"),
        "probe_results": portfolio_probe.get("probe_results", []),
    }

    result = _solve_mission_internal(
        mission_id,
        payload,
        mission_for_strategy=mission_with_learned_profile,
        ai_strategy_override=selected_strategy,
    )
    result["learning"] = {
        "used_model": bool(recommendation),
        "model_path": str(AI_LEARNING_MODEL_FILE) if model_payload else None,
        "recommendation": recommendation,
        "ortools_tuning": ortools_tuning,
        "ortools_model_path": str(ORTOOLS_TUNER_MODEL_FILE) if tuner_model else None,
        "fallback_to_preset": recommendation is None,
        "notes": learning_notes,
        "ro_portfolio": selected_strategy.get("ro_portfolio"),
        "ro_adaptive_budget": budget_meta,
    }
    return result


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


def get_graph_metrics(mission_id: str) -> dict:
    paths, _, _ = load_mission_bundle(mission_id)
    if not paths.graph_file.exists():
        raise FileNotFoundError("Graphe introuvable pour cette mission.")
    graph = load_graph(paths.graph_file)
    return ro_improvements.compute_graph_metrics(graph)


def get_dijkstra_steps(mission_id: str, from_node: int, to_node: int) -> dict:
    paths, _, _ = load_mission_bundle(mission_id)
    if not paths.graph_file.exists():
        raise FileNotFoundError("Graphe introuvable pour cette mission.")
    graph = load_graph(paths.graph_file)
    return ro_improvements.dijkstra_steps(graph, from_node, to_node)


def get_bidirectional_astar_steps(mission_id: str, from_node: int, to_node: int) -> dict:
    paths, _, _ = load_mission_bundle(mission_id)
    if not paths.graph_file.exists():
        raise FileNotFoundError("Graphe introuvable pour cette mission.")
    graph = load_graph(paths.graph_file)
    astar = ro_improvements.bidirectional_astar_steps(graph, from_node, to_node)
    unidir = ro_improvements.dijkstra_steps(graph, from_node, to_node)
    astar["nodes_explored_unidir"] = unidir["steps_count"]
    reduction = 0.0
    if unidir["steps_count"] > 0:
        reduction = round(
            (1.0 - astar["nodes_explored_astar_bidir"] / unidir["steps_count"]) * 100.0, 1
        )
    astar["reduction_pct"] = reduction
    return astar


def get_bidirectional_dijkstra_steps(mission_id: str, from_node: int, to_node: int) -> dict:
    paths, _, _ = load_mission_bundle(mission_id)
    if not paths.graph_file.exists():
        raise FileNotFoundError("Graphe introuvable pour cette mission.")
    graph = load_graph(paths.graph_file)
    bidir = ro_improvements.bidirectional_dijkstra_steps(graph, from_node, to_node)
    unidir = ro_improvements.dijkstra_steps(graph, from_node, to_node)
    bidir["nodes_explored_unidir"] = unidir["steps_count"]
    reduction = 0.0
    if unidir["steps_count"] > 0:
        reduction = round(
            (1.0 - bidir["nodes_explored_bidir"] / unidir["steps_count"]) * 100.0, 1
        )
    bidir["reduction_pct"] = reduction
    return bidir


def get_floyd_warshall(mission_id: str) -> dict:
    paths, _, _ = load_mission_bundle(mission_id)
    if not paths.time_matrix_file.exists():
        raise FileNotFoundError("Matrice de temps introuvable pour cette mission.")
    matrix = np.load(paths.time_matrix_file)
    return ro_improvements.floyd_warshall(matrix)


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
    df = read_points(paths.data_file)
    graph = load_graph(paths.graph_file)
    human_live_stats = build_human_live_stats(df=df, graph=graph, state=human_state, weather_factor=float(weather.get("factor", 1.0)))

    two_opt_result = None
    or_opt_result = None
    nearest_neighbor_result = None
    optimality_result = None
    if paths.time_matrix_file.exists() and any(human_state.routes_by_sleigh.values()):
        try:
            time_matrix = np.load(paths.time_matrix_file)
            id_to_idx = {int(row["id"]): idx for idx, (_, row) in enumerate(df.iterrows())}
            depot_idx = id_to_idx.get(0, 0)
            routes_idx = {
                sid: [id_to_idx[int(cid)] for cid in route if int(cid) in id_to_idx]
                for sid, route in human_state.routes_by_sleigh.items()
            }
            two_opt_result = ro_improvements.two_opt_routes(routes_idx, time_matrix, depot_idx)
            or_opt_result = ro_improvements.or_opt_routes(routes_idx, time_matrix, depot_idx)
            num_clients = len(df) - 1  # exclude depot
            if num_clients > 0:
                nearest_neighbor_result = ro_improvements.nearest_neighbor_tour(num_clients, time_matrix, depot_idx)
            human_total_s = float(human_summary.get("total_time_s") or 0.0)
            if human_total_s > 0:
                optimality_result = ro_improvements.optimality_gap(human_total_s, time_matrix, depot_idx)
        except Exception:
            two_opt_result = None

    time_saved_pct = float(benchmark["savings"]["time_saved_pct"])
    co2_saved_kg = float(benchmark["savings"]["co2_saved_kg"])
    budget_remaining_pct = float(benchmark.get("budget", {}).get("remaining_pct", 50.0))

    # Recalibration : OR-Tools économise typiquement 20-40% vs solution naïve.
    # On normalise sur 40% max (× 2.5) pour que 40% → 100 pts sur la composante temps.
    time_score_pct = max(0.0, min(100.0, time_saved_pct * 2.5))

    # CO2 : missions de 10 clients ≈ 0.3-1 kg économisés. Seuil 1 kg pour le max
    # (au lieu de 20 kg, qui rendait la composante quasi nulle).
    num_clients = max(int(mission.get("num_clients", 10)), 1)
    co2_ref_kg = max(1.0, num_clients * 0.1)  # 0.1 kg/client de référence
    co2_score = max(0.0, min(co2_saved_kg / co2_ref_kg * 100.0, 100.0))
    budget_remaining_pct = max(0.0, min(100.0, budget_remaining_pct))

    ai_strategy = results.get("ai_strategy", resolve_ai_strategy(mission, {}))
    base_score = 0.60 * time_score_pct + 0.25 * co2_score + 0.15 * budget_remaining_pct
    base_score = max(0.0, min(base_score, 100.0))
    ai_profile_bonus = float(ai_strategy.get("difficulty_bonus", 0.0))
    incident_bonus = 10.0 if mission.get("random_incidents", False) else 0.0
    human_bonus = 0.0
    human_beat_ai = human_time_s is not None and human_time_s < float(results.get("total_time_s", 0))
    if human_beat_ai:
        human_bonus = 5.0
    # Bonus météo : conditions difficiles récompensées (+0 par temps clair, jusqu'à +8 par tempête)
    weather_factor = float(weather.get("factor", 1.0))
    weather_bonus = round(max(0.0, (weather_factor - 1.0) * 8.0), 1)
    final_score = max(0.0, min(base_score + ai_profile_bonus + incident_bonus + human_bonus + weather_bonus, 100.0))
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
                "weather_bonus": weather_bonus,
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
            "two_opt": two_opt_result,
            "or_opt": or_opt_result,
            "nearest_neighbor": nearest_neighbor_result,
            "optimality_gap": optimality_result,
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


def _public_social_player(player: dict) -> dict:
    return {
        "player_id": player["player_id"],
        "display_name": player["display_name"],
        "callsign": player.get("callsign"),
        "avatar": player.get("avatar"),
    }


def _social_friendship_entry(entry: dict) -> dict:
    return {
        "peer_player_id": str(entry.get("peer_player_id") or ""),
        "peer_display_name": entry.get("peer_display_name"),
        "peer_callsign": entry.get("peer_callsign"),
        "peer_avatar": entry.get("peer_avatar"),
        "status": str(entry.get("status") or ""),
        "requester_player_id": str(entry.get("requester_player_id") or ""),
        "addressee_player_id": str(entry.get("addressee_player_id") or ""),
        "created_at": entry.get("created_at"),
        "updated_at": entry.get("updated_at"),
        "responded_at": entry.get("responded_at"),
    }


def _sanitize_direct_message_body(value: object) -> str:
    body = str(value or "").strip()
    if not body:
        raise ValueError("Message vide")
    if len(body) > 1000:
        raise ValueError("Message trop long (1000 caractères max)")
    return body


def _is_social_blocked(player_a_id: str, player_b_id: str) -> bool:
    return repository.is_user_blocked(player_a_id, player_b_id) or repository.is_user_blocked(player_b_id, player_a_id)


def _direct_message_entry(message: dict, current_player_id: str) -> dict:
    sender_player_id = str(message.get("sender_player_id") or "")
    return {
        "message_id": str(message.get("message_id") or ""),
        "conversation_key": str(message.get("conversation_key") or ""),
        "sender_player_id": sender_player_id,
        "sender_display_name": message.get("sender_display_name"),
        "sender_avatar": message.get("sender_avatar"),
        "recipient_player_id": str(message.get("recipient_player_id") or ""),
        "recipient_display_name": message.get("recipient_display_name"),
        "recipient_avatar": message.get("recipient_avatar"),
        "body": str(message.get("body") or ""),
        "created_at": message.get("created_at"),
        "read_at": message.get("read_at"),
        "is_mine": sender_player_id == current_player_id,
    }


def search_social_players(player_id: str, query: str | None = None, limit: int = 12) -> dict:
    _require_player(player_id)
    bounded_limit = max(1, min(int(limit), 30))
    players = repository.list_players(search=query, limit=bounded_limit, exclude_player_id=player_id)
    filtered: list[dict] = []
    for candidate in players:
        candidate_id = str(candidate.get("player_id") or "")
        if candidate_id and _is_social_blocked(player_id, candidate_id):
            continue
        filtered.append(candidate)
    return {"players": [_public_social_player(player) for player in filtered]}


def list_social_friendships(player_id: str) -> dict:
    _require_player(player_id)
    friendships = repository.list_friendships_for_player(player_id, statuses=("accepted", "pending"))

    friends: list[dict] = []
    incoming_requests: list[dict] = []
    outgoing_requests: list[dict] = []
    for entry in friendships:
        social_entry = _social_friendship_entry(entry)
        peer_player_id = social_entry["peer_player_id"]
        if peer_player_id and _is_social_blocked(player_id, peer_player_id):
            continue
        status = social_entry["status"]
        if status == "accepted":
            friends.append(social_entry)
        elif status == "pending":
            if social_entry["addressee_player_id"] == player_id:
                incoming_requests.append(social_entry)
            else:
                outgoing_requests.append(social_entry)
    return {
        "friends": friends,
        "incoming_requests": incoming_requests,
        "outgoing_requests": outgoing_requests,
    }


def send_friend_request(payload: dict) -> dict:
    requester_player_id = str(payload.get("player_id") or "")
    friend_player_id = str(payload.get("friend_player_id") or "")
    _require_player(requester_player_id)
    _require_player(friend_player_id)
    if requester_player_id == friend_player_id:
        raise ValueError("Impossible de vous ajouter vous-même")
    if _is_social_blocked(requester_player_id, friend_player_id):
        raise ValueError("Action impossible: ce joueur est bloqué")

    existing = repository.get_friendship_between(requester_player_id, friend_player_id)
    if existing:
        status = str(existing.get("status") or "")
        if status == "accepted":
            raise ValueError("Vous êtes déjà amis")
        if status == "pending":
            if str(existing.get("requester_player_id") or "") == requester_player_id:
                raise ValueError("Demande déjà envoyée")
            raise ValueError("Cette personne vous a déjà envoyé une demande")

    friendship = repository.create_or_reset_friend_request(requester_player_id, friend_player_id)
    if not friendship:
        raise RuntimeError("Impossible de créer la demande d'ami")
    return {"status": "pending", "friendship": _social_friendship_entry(friendship)}


def respond_friend_request(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    friend_player_id = str(payload.get("friend_player_id") or "")
    action = str(payload.get("action") or "").strip().lower()
    _require_player(player_id)
    _require_player(friend_player_id)

    if action not in {"accept", "decline"}:
        raise ValueError("Action inconnue")
    if _is_social_blocked(player_id, friend_player_id):
        raise ValueError("Action impossible: ce joueur est bloqué")

    friendship = repository.get_friendship_between(player_id, friend_player_id)
    if not friendship:
        raise FileNotFoundError("Demande d'ami introuvable")
    if str(friendship.get("status") or "") != "pending":
        raise ValueError("Aucune demande en attente")
    if str(friendship.get("addressee_player_id") or "") != player_id:
        raise ValueError("Seul le destinataire peut répondre")

    next_status = "accepted" if action == "accept" else "declined"
    repository.update_friendship_status(
        player_id,
        friend_player_id,
        status=next_status,
        responded_at=_now_iso(),
    )
    updated = repository.get_friendship_between(player_id, friend_player_id)
    if not updated:
        raise FileNotFoundError("Demande d'ami introuvable")
    return {"status": next_status, "friendship": _social_friendship_entry(updated)}


def remove_friendship(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    friend_player_id = str(payload.get("friend_player_id") or "")
    _require_player(player_id)
    _require_player(friend_player_id)

    friendship = repository.get_friendship_between(player_id, friend_player_id)
    if not friendship:
        raise FileNotFoundError("Relation introuvable")
    repository.delete_friendship(player_id, friend_player_id)
    return {"status": "removed"}


def block_player(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    blocked_player_id = str(payload.get("blocked_player_id") or "")
    _require_player(player_id)
    _require_player(blocked_player_id)
    if player_id == blocked_player_id:
        raise ValueError("Impossible de vous bloquer vous-même")
    repository.create_user_block(player_id, blocked_player_id)
    repository.delete_friendship(player_id, blocked_player_id)
    return {"status": "blocked"}


def unblock_player(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    blocked_player_id = str(payload.get("blocked_player_id") or "")
    _require_player(player_id)
    _require_player(blocked_player_id)
    repository.remove_user_block(player_id, blocked_player_id)
    return {"status": "unblocked"}


def list_blocked_players(player_id: str) -> dict:
    _require_player(player_id)
    blocked_rows = repository.list_blocked_players(player_id)
    return {
        "blocked": [
            {
                "player_id": row.get("blocked_player_id"),
                "display_name": row.get("blocked_display_name"),
                "callsign": row.get("blocked_callsign"),
                "avatar": row.get("blocked_avatar"),
                "blocked_at": row.get("created_at"),
            }
            for row in blocked_rows
        ]
    }


def list_direct_conversations(player_id: str, limit: int = 30) -> dict:
    _require_player(player_id)
    bounded_limit = max(1, min(int(limit), 60))
    conversations = repository.list_direct_conversations(player_id, limit=bounded_limit)
    payload: list[dict] = []
    for conversation in conversations:
        peer_player_id = str(conversation.get("peer_player_id") or "")
        if peer_player_id and _is_social_blocked(player_id, peer_player_id):
            continue
        last_message = conversation.get("last_message")
        payload.append(
            {
                "conversation_key": conversation.get("conversation_key"),
                "peer_player_id": conversation.get("peer_player_id"),
                "peer_display_name": conversation.get("peer_display_name"),
                "peer_callsign": conversation.get("peer_callsign"),
                "peer_avatar": conversation.get("peer_avatar"),
                "unread_count": int(conversation.get("unread_count") or 0),
                "last_message_at": conversation.get("last_message_at"),
                "last_message": _direct_message_entry(last_message, player_id) if isinstance(last_message, dict) else None,
                "hidden": bool(conversation.get("hidden")),
                "cleared_before_at": conversation.get("cleared_before_at"),
            }
        )
    return {"conversations": payload}


def send_direct_message(payload: dict) -> dict:
    sender_player_id = str(payload.get("player_id") or "")
    recipient_player_id = str(payload.get("recipient_player_id") or "")
    _require_player(sender_player_id)
    _require_player(recipient_player_id)
    if sender_player_id == recipient_player_id:
        raise ValueError("Impossible de vous envoyer un message")
    if _is_social_blocked(sender_player_id, recipient_player_id):
        raise ValueError("Action impossible: ce joueur est bloqué")

    friendship = repository.get_friendship_between(sender_player_id, recipient_player_id)
    if not friendship or str(friendship.get("status") or "") != "accepted":
        raise ValueError("Vous devez être amis pour écrire à ce joueur")

    body = _sanitize_direct_message_body(payload.get("body"))
    message = repository.create_direct_message(
        message_id=uuid.uuid4().hex[:24],
        sender_player_id=sender_player_id,
        recipient_player_id=recipient_player_id,
        body=body,
    )
    if not message:
        raise RuntimeError("Impossible d'envoyer ce message")
    return {"message": _direct_message_entry(message, sender_player_id)}


def list_direct_messages(player_id: str, peer_player_id: str, limit: int = 60, before: str | None = None) -> dict:
    player = _require_player(player_id)
    peer_player = _require_player(peer_player_id)
    if _is_social_blocked(player_id, peer_player_id):
        raise ValueError("Conversation indisponible")
    friendship = repository.get_friendship_between(player_id, peer_player_id)
    if not friendship or str(friendship.get("status") or "") != "accepted":
        raise ValueError("Vous devez être amis pour consulter cette conversation")

    bounded_limit = max(1, min(int(limit), 200))
    repository.mark_direct_messages_read(recipient_player_id=player_id, sender_player_id=peer_player_id)
    messages = repository.list_direct_messages(player_id, peer_player_id, limit=bounded_limit, before=before)
    return {
        "peer": _public_social_player(peer_player),
        "self": _public_social_player(player),
        "messages": [_direct_message_entry(message, player_id) for message in messages],
    }


def remove_direct_conversation(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    peer_player_id = str(payload.get("with_player_id") or "")
    _require_player(player_id)
    _require_player(peer_player_id)
    state = repository.clear_direct_conversation_for_player(player_id, peer_player_id)
    return {
        "status": "cleared",
        "conversation_key": state.get("conversation_key"),
        "cleared_before_at": state.get("cleared_before_at"),
    }


def restore_direct_conversation(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    peer_player_id = str(payload.get("with_player_id") or "")
    _require_player(player_id)
    _require_player(peer_player_id)
    state = repository.restore_direct_conversation_for_player(player_id, peer_player_id)
    return {
        "status": "restored",
        "conversation_key": state.get("conversation_key"),
        "restored": bool(state.get("restored")),
    }


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


def oauth_sync_player(payload: dict) -> dict:
    provider = _normalize_oauth_provider(payload.get("provider"))
    provider_account_id = str(payload.get("provider_account_id") or "").strip()
    if not provider_account_id:
        raise ValueError("provider_account_id OAuth requis")

    display_name = str(payload.get("display_name") or "").strip()
    if not display_name:
        raise ValueError("Nom de joueur requis")

    email_raw = payload.get("email")
    email = _validate_email(str(email_raw)) if email_raw else None
    callsign = str(payload.get("callsign") or "").strip() or None
    avatar = _sanitize_avatar_hint(payload.get("avatar"))
    now_iso = _utcnow().isoformat()

    existing_by_email = repository.get_player_by_email(email) if email else None
    player_id = str(existing_by_email["player_id"]) if existing_by_email else _oauth_player_id(provider, provider_account_id)
    existing_player = repository.get_player(player_id)
    base_player = existing_player or existing_by_email

    try:
        upserted = repository.upsert_player(
            player_id=player_id,
            display_name=display_name,
            email=email,
            password_hash=base_player.get("password_hash") if base_player else None,
            callsign=callsign if callsign is not None else (base_player.get("callsign") if base_player else None),
            avatar=avatar if avatar is not None else (base_player.get("avatar") if base_player else None),
            last_login_at=now_iso,
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("Impossible de synchroniser le compte OAuth") from exc
    return _public_player(upserted)


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


def _now_iso() -> str:
    return _utcnow().isoformat()


def _require_player(player_id: str) -> dict:
    normalized = str(player_id or "").strip()
    if not normalized:
        raise ValueError("player_id requis")
    player = repository.get_player(normalized)
    if not player:
        raise FileNotFoundError("Joueur introuvable")
    return player


def _normalize_versus_template_id(value: str | None) -> str:
    template_id = str(value or "paris_duel").strip().lower()
    if template_id not in VERSUS_TEMPLATES:
        raise ValueError("Template versus inconnu")
    return template_id


def _normalize_versus_winner_rule(value: str | None) -> str:
    normalized = str(value or "score_time").strip().lower()
    aliases = {
        "score+temps": "score_time",
        "score_temps": "score_time",
        "score_time": "score_time",
        "temps": "time",
        "time": "time",
        "objectifs": "objectives",
        "objectives": "objectives",
    }
    winner_rule = aliases.get(normalized, normalized)
    if winner_rule not in VERSUS_WINNER_RULES:
        raise ValueError("Règle de victoire inconnue")
    return winner_rule


def _normalize_versus_mode(value: str | None) -> str:
    mode = str(value or "private").strip().lower()
    if mode not in VERSUS_MATCH_MODES:
        raise ValueError("Mode versus inconnu")
    return mode


def _normalize_versus_map_source(value: str | None) -> str:
    map_source = str(value or "template").strip().lower()
    if map_source not in VERSUS_MAP_SOURCES:
        raise ValueError("Source de carte inconnue")
    return map_source


def _sanitize_secondary_objectives(value: object) -> list[dict] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("secondary_objectives doit être une liste")
    sanitized: list[dict] = []
    for index, objective in enumerate(value):
        if not isinstance(objective, dict):
            raise ValueError(f"secondary_objectives[{index}] invalide")
        code = str(objective.get("code", "")).strip()
        label = str(objective.get("label", "")).strip()
        if not code or not label:
            raise ValueError("Chaque objectif secondaire doit contenir code et label")
        payload: dict = {"code": code, "label": label}
        target = objective.get("target")
        if target is not None:
            payload["target"] = float(target)
        sanitized.append(payload)
    return sanitized


def _sanitize_and_validate_versus_mission_config(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("mission_config requis pour une carte custom")
    source = dict(payload)

    allowed_keys = {
        "zone",
        "city",
        "center_lat",
        "center_lon",
        "search_radius_km",
        "max_clients",
        "num_clients",
        "budget",
        "sleigh_cost",
        "weather_key",
        "random_incidents",
        "ai_profile",
        "secondary_objectives",
        "level",
    }
    unexpected_keys = set(source) - allowed_keys
    if unexpected_keys:
        unexpected = ", ".join(sorted(unexpected_keys))
        raise ValueError(f"mission_config contient des champs interdits: {unexpected}")
    sanitized = {key: source[key] for key in allowed_keys if key in source}
    zone = str(sanitized.get("zone", "")).strip()
    if not zone:
        raise ValueError("mission_config.zone requis")
    sanitized["zone"] = zone
    city = sanitized.get("city")
    if city is not None:
        sanitized["city"] = str(city).strip()[:120] or None

    num_clients = int(sanitized.get("num_clients", 0))
    if num_clients < 1:
        raise ValueError("mission_config.num_clients invalide")
    if num_clients > VERSUS_CUSTOM_MAX_CLIENTS:
        raise ValueError(f"En versus custom, le nombre maximal de colis est {VERSUS_CUSTOM_MAX_CLIENTS}.")
    sanitized["num_clients"] = num_clients
    sanitized["budget"] = max(0, int(sanitized.get("budget", 0)))
    sanitized["sleigh_cost"] = max(0, int(sanitized.get("sleigh_cost", 0)))
    sanitized["weather_key"] = str(sanitized.get("weather_key", "Clear")).strip() or "Clear"
    sanitized["random_incidents"] = bool(sanitized.get("random_incidents", False))
    ai_profile = sanitized.get("ai_profile")
    sanitized["ai_profile"] = (str(ai_profile).strip() or None) if ai_profile is not None else None
    sanitized["secondary_objectives"] = _sanitize_secondary_objectives(sanitized.get("secondary_objectives"))
    sanitized["level"] = None

    if sanitized.get("search_radius_km") is not None:
        sanitized["search_radius_km"] = float(sanitized["search_radius_km"])
    if sanitized.get("center_lat") is not None:
        sanitized["center_lat"] = float(sanitized["center_lat"])
    if sanitized.get("center_lon") is not None:
        sanitized["center_lon"] = float(sanitized["center_lon"])
    if sanitized.get("max_clients") is not None:
        sanitized["max_clients"] = int(sanitized["max_clients"])

    _validate_search_area_constraints(sanitized)
    return sanitized


def _mission_summary_from_payload(mission_payload: dict | None, *, map_source: str, template_id: str | None) -> dict:
    mission = mission_payload or {}
    objectives = mission.get("secondary_objectives")
    secondary_count = len(objectives) if isinstance(objectives, list) else 0
    summary = {
        "map_source": map_source,
        "template_id": template_id,
        "zone": mission.get("zone"),
        "city": mission.get("city"),
        "num_clients": int(mission.get("num_clients", 0) or 0),
        "weather_key": mission.get("weather_key"),
        "random_incidents": bool(mission.get("random_incidents", False)),
        "budget": int(mission.get("budget", 0) or 0),
        "sleigh_cost": int(mission.get("sleigh_cost", 0) or 0),
        "search_radius_km": _safe_float(mission.get("search_radius_km")),
        "center_lat": _safe_float(mission.get("center_lat")),
        "center_lon": _safe_float(mission.get("center_lon")),
        "ai_profile": mission.get("ai_profile"),
        "secondary_objectives_count": secondary_count,
    }
    if map_source == "template" and template_id in VERSUS_TEMPLATES:
        template = VERSUS_TEMPLATES[str(template_id)]
        summary["template_label"] = template.get("label")
        summary["template_description"] = template.get("description")
    elif map_source == "custom":
        summary["template_label"] = f"Custom · {summary.get('zone') or 'Zone personnalisée'}"
    return summary


def _resolve_versus_map_payload(
    payload: dict,
    *,
    custom_allowed: bool,
) -> tuple[str, str, dict | None]:
    map_source = _normalize_versus_map_source(payload.get("map_source"))
    if map_source == "custom":
        if not custom_allowed:
            raise ValueError("La file auto accepte uniquement les templates prédéfinis.")
        mission_config = _sanitize_and_validate_versus_mission_config(payload.get("mission_config"))
        template_id = str(payload.get("template_id") or "custom_map").strip().lower() or "custom_map"
        return map_source, template_id, mission_config

    template_id = _normalize_versus_template_id(payload.get("template_id"))
    return map_source, template_id, None


def _iso_to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return _parse_datetime(str(value))
    except ValueError:
        return None


def _score_of(participant: dict) -> float:
    return float(participant.get("score") or 0.0)


def _time_of(participant: dict) -> float:
    value = _safe_float(participant.get("total_time_s"))
    return float(value) if value is not None else float("inf")


def _objective_count_of(participant: dict) -> int:
    return int(participant.get("objectives_completed") or 0)


def _submission_order_value(participant: dict) -> str:
    return str(participant.get("submitted_at") or participant.get("created_at") or "")


def _generate_join_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(40):
        candidate = "".join(secrets.choice(alphabet) for _ in range(6))
        if not repository.get_versus_match_by_join_code(candidate):
            return candidate
    raise RuntimeError("Impossible de générer un code de partie unique")


def _template_payload_for_mission(template_id: str) -> dict:
    template = VERSUS_TEMPLATES[_normalize_versus_template_id(template_id)]
    mission_payload = dict(template["mission"])
    mission_payload.setdefault("secondary_objectives", [
        {"code": "assign_all_clients", "label": "Affecter tous les clients"},
        {"code": "beat_ai", "label": "Battre l'IA"},
    ])
    mission_payload.setdefault("level", None)
    return mission_payload


def _mission_payload_for_match(match: dict) -> dict:
    map_source = _normalize_versus_map_source(match.get("map_source"))
    if map_source == "custom":
        mission_config = match.get("mission_config")
        if not isinstance(mission_config, dict):
            raise ValueError("Configuration custom introuvable pour ce match")
        return _sanitize_and_validate_versus_mission_config(mission_config)
    return _template_payload_for_mission(str(match.get("template_id") or "paris_duel"))


def _clone_reference_mission(reference_mission_id: str, new_mission_id: str, match_id: str) -> None:
    source_paths = mission_paths(reference_mission_id)
    target_paths = mission_paths(new_mission_id)
    if target_paths.root_dir.exists():
        shutil.rmtree(target_paths.root_dir)
    shutil.copytree(source_paths.root_dir, target_paths.root_dir)

    mission_payload = _read_json(target_paths.mission_file, {}) or {}
    mission_payload["mission_id"] = new_mission_id
    mission_payload["versus_match_id"] = match_id
    _write_json(target_paths.mission_file, mission_payload)
    _write_json(target_paths.human_state_file, default_human_state())

    for artifact in (target_paths.results_file, target_paths.benchmark_file, target_paths.output_html_file):
        if Path(artifact).exists():
            Path(artifact).unlink()

    weather = load_weather(target_paths.weather_file, mission_payload.get("weather_key"))
    incidents_payload = _read_json(target_paths.incidents_file, {"count": 0, "segments": []})
    repository.upsert_mission(
        mission_id=new_mission_id,
        root_dir=str(target_paths.root_dir),
        mission=mission_payload,
        weather=weather,
        incidents=incidents_payload,
        human_state=default_human_state(),
        status="created",
    )


def _create_versus_match_pair(
    *,
    mode: str,
    host_player_id: str,
    opponent_player_id: str,
    template_id: str,
    map_source: str,
    mission_config: dict | None,
    winner_rule: str,
    join_code: str | None = None,
) -> str:
    match_id = uuid.uuid4().hex[:14]
    repository.create_versus_match(
        match_id=match_id,
        mode=mode,
        template_id=template_id,
        map_source=map_source,
        mission_config=mission_config,
        winner_rule=winner_rule,
        host_player_id=host_player_id,
        join_code=join_code,
        status="waiting_ready",
    )
    repository.add_versus_participant(match_id=match_id, player_id=opponent_player_id, seat=1, state="joined")
    repository.remove_versus_queue_player(host_player_id)
    repository.remove_versus_queue_player(opponent_player_id)
    return match_id


def _touch_versus_participant(match_id: str, player_id: str) -> None:
    match = repository.get_versus_match(match_id)
    if not match or match.get("status") != "live":
        return
    repository.update_versus_participant(match_id, player_id, last_seen_at=_now_iso())


def _select_winner_from_submissions(participants: list[dict], winner_rule: str) -> dict:
    if winner_rule == "time":
        ranked = sorted(
            participants,
            key=lambda item: (_time_of(item), -_score_of(item), _submission_order_value(item)),
        )
        return ranked[0]
    if winner_rule == "objectives":
        ranked = sorted(
            participants,
            key=lambda item: (-_objective_count_of(item), _time_of(item), _submission_order_value(item)),
        )
        return ranked[0]
    ranked = sorted(
        participants,
        key=lambda item: (-_score_of(item), _time_of(item), _submission_order_value(item)),
    )
    return ranked[0]


def _resolve_versus_match(match_id: str, reason: str = "submitted") -> dict | None:
    match = repository.get_versus_match(match_id)
    if not match:
        return None
    if str(match.get("status")) == "finished":
        return match

    participants = repository.list_versus_participants(match_id)
    if len(participants) < 2:
        return match

    submitted = [p for p in participants if p.get("state") == "submitted" and int(p.get("is_valid_submission") or 0) == 1]
    forfeits = [p for p in participants if p.get("state") == "forfeit"]
    winner: dict | None = None
    result_reason = reason

    if len(submitted) == 2:
        winner = _select_winner_from_submissions(submitted, str(match.get("winner_rule") or "score_time"))
        result_reason = "submitted"
    elif len(forfeits) == 1:
        loser_id = str(forfeits[0]["player_id"])
        winner = next((p for p in participants if str(p["player_id"]) != loser_id), None)
        result_reason = "forfeit_timeout"
    elif len(submitted) == 1 and len(forfeits) == 1:
        winner = submitted[0]
        result_reason = "forfeit_timeout"

    if not winner:
        return match

    now_iso = _now_iso()
    winner_id = str(winner["player_id"])
    loser = next((p for p in participants if str(p["player_id"]) != winner_id), None)
    loser_id = str(loser["player_id"]) if loser else None
    repository.update_versus_match(
        match_id,
        status="finished",
        completed_at=now_iso,
        winner_player_id=winner_id,
        result_reason=result_reason,
    )
    repository.save_versus_leaderboard_entry(
        match_id=match_id,
        winner_player_id=winner_id,
        loser_player_id=loser_id,
        winner_score=_safe_float(winner.get("score")),
        winner_time_s=_safe_float(winner.get("total_time_s")),
        winner_rule=str(match.get("winner_rule") or "score_time"),
        template_id=str(match.get("template_id") or "paris_duel"),
    )
    return repository.get_versus_match(match_id)


def _apply_versus_forfeit_timeout(match_id: str) -> None:
    match = repository.get_versus_match(match_id)
    if not match or str(match.get("status")) != "live":
        return
    participants = repository.list_versus_participants(match_id)
    if not participants:
        return
    now_dt = _utcnow()
    updated = False
    for participant in participants:
        state = str(participant.get("state") or "")
        if state in {"submitted", "forfeit"}:
            continue
        last_seen = _iso_to_datetime(participant.get("last_seen_at")) or _iso_to_datetime(match.get("started_at"))
        if not last_seen:
            continue
        if (now_dt - last_seen).total_seconds() <= VERSUS_FORFEIT_TIMEOUT_SECONDS:
            continue
        repository.update_versus_participant(
            match_id,
            str(participant["player_id"]),
            state="forfeit",
            forfeit_at=_now_iso(),
        )
        updated = True
    if updated:
        _resolve_versus_match(match_id, reason="forfeit_timeout")


def _start_versus_match_if_ready(match_id: str) -> None:
    match = repository.get_versus_match(match_id)
    if not match or str(match.get("status")) != "waiting_ready":
        return
    participants = repository.list_versus_participants(match_id)
    if len(participants) != 2:
        return
    if any(str(participant.get("state")) != "ready" for participant in participants):
        return

    mission_payload = _mission_payload_for_match(match)
    reference_bundle = create_mission(mission_payload)
    reference_mission_id = str(reference_bundle["mission_id"])
    now_iso = _now_iso()
    for participant in participants:
        player_mission_id = uuid.uuid4().hex[:12]
        _clone_reference_mission(reference_mission_id, player_mission_id, str(match_id))
        repository.update_versus_participant(
            str(match_id),
            str(participant["player_id"]),
            state="live",
            mission_id=player_mission_id,
            last_seen_at=now_iso,
        )

    repository.update_versus_match(
        str(match_id),
        status="live",
        started_at=now_iso,
        reference_mission_id=reference_mission_id,
        result_reason=None,
        winner_player_id=None,
        completed_at=None,
    )


def _versus_progress_for_mission(mission_id: str | None) -> dict:
    if not mission_id:
        return {
            "assigned_clients": 0,
            "total_clients": 0,
            "progress_pct": 0.0,
            "elapsed_s": 0,
            "updated_at": None,
        }

    snapshot = repository.get_mission_snapshot(str(mission_id))
    if not snapshot:
        return {
            "assigned_clients": 0,
            "total_clients": 0,
            "progress_pct": 0.0,
            "elapsed_s": 0,
            "updated_at": None,
        }

    mission_payload = snapshot.get("mission") if isinstance(snapshot.get("mission"), dict) else {}
    state_payload = snapshot.get("human_state") if isinstance(snapshot.get("human_state"), dict) else {}
    assigned_clients_raw = state_payload.get("assigned_clients") if isinstance(state_payload, dict) else []
    segments_by_sleigh = state_payload.get("segments_by_sleigh") if isinstance(state_payload, dict) else {}

    assigned_clients = {
        int(client_id)
        for client_id in (assigned_clients_raw or [])
        if isinstance(client_id, (int, float, str))
    }
    total_clients = max(0, int(mission_payload.get("num_clients") or 0))
    progress_pct = (float(len(assigned_clients)) / float(total_clients) * 100.0) if total_clients > 0 else 0.0

    elapsed_s = 0.0
    if isinstance(segments_by_sleigh, dict):
        for sleigh_segments in segments_by_sleigh.values():
            if not isinstance(sleigh_segments, list):
                continue
            for segment in sleigh_segments:
                if isinstance(segment, dict):
                    elapsed_s += max(0.0, float(segment.get("time_s") or 0.0))

    return {
        "assigned_clients": len(assigned_clients),
        "total_clients": total_clients,
        "progress_pct": round(progress_pct, 2),
        "elapsed_s": int(round(elapsed_s)),
        "updated_at": snapshot.get("updated_at"),
    }


def _build_versus_match_state(match_id: str, viewer_player_id: str) -> dict:
    match = repository.get_versus_match(match_id)
    if not match:
        raise FileNotFoundError("Match versus introuvable")
    participants = repository.list_versus_participants(match_id)
    if not any(str(participant["player_id"]) == str(viewer_player_id) for participant in participants):
        raise ValueError("Accès interdit à ce match")

    started_at_dt = _iso_to_datetime(match.get("started_at"))
    map_source = _normalize_versus_map_source(match.get("map_source"))
    mission_payload = _mission_payload_for_match(match)
    mission_summary = _mission_summary_from_payload(
        mission_payload,
        map_source=map_source,
        template_id=str(match.get("template_id") or ""),
    )
    now_dt = _utcnow()
    state_participants: list[dict] = []
    for participant in participants:
        last_seen_dt = _iso_to_datetime(participant.get("last_seen_at")) or started_at_dt
        deadline_dt = None
        if str(match.get("status")) == "live" and str(participant.get("state")) not in {"submitted", "forfeit"} and last_seen_dt:
            deadline_dt = last_seen_dt + timedelta(seconds=VERSUS_FORFEIT_TIMEOUT_SECONDS)
        state_participants.append(
            {
                "player_id": participant["player_id"],
                "display_name": participant.get("display_name"),
                "callsign": participant.get("callsign"),
                "avatar": participant.get("avatar"),
                "seat": int(participant.get("seat") or 0),
                "state": participant.get("state"),
                "mission_id": participant.get("mission_id"),
                "ready_at": participant.get("ready_at"),
                "submitted_at": participant.get("submitted_at"),
                "score": _safe_float(participant.get("score")),
                "total_time_s": _safe_float(participant.get("total_time_s")),
                "objectives_completed": int(participant.get("objectives_completed") or 0),
                "is_valid_submission": bool(int(participant.get("is_valid_submission") or 0)),
                "forfeit_at": participant.get("forfeit_at"),
                "last_seen_at": participant.get("last_seen_at"),
                "forfeit_deadline_at": deadline_dt.isoformat() if deadline_dt else None,
                "is_self": str(participant["player_id"]) == str(viewer_player_id),
            }
        )

    self_participant = next((item for item in state_participants if item["is_self"]), None)
    started_elapsed_s = None
    if started_at_dt:
        started_elapsed_s = max(0, int((now_dt - started_at_dt).total_seconds()))
    countdown_remaining_s = None
    if str(match.get("status")) == "live" and started_elapsed_s is not None and started_elapsed_s < VERSUS_COUNTDOWN_SECONDS:
        countdown_remaining_s = max(0, VERSUS_COUNTDOWN_SECONDS - started_elapsed_s)

    return {
        "match_id": match["match_id"],
        "mode": match.get("mode"),
        "template_id": match.get("template_id"),
        "map_source": map_source,
        "mission_config": match.get("mission_config") if map_source == "custom" else None,
        "mission_summary": mission_summary,
        "template_label": mission_summary.get("template_label"),
        "winner_rule": match.get("winner_rule"),
        "join_code": match.get("join_code"),
        "host_player_id": match.get("host_player_id"),
        "status": match.get("status"),
        "reference_mission_id": match.get("reference_mission_id"),
        "started_at": match.get("started_at"),
        "started_elapsed_s": started_elapsed_s,
        "countdown_total_s": VERSUS_COUNTDOWN_SECONDS,
        "countdown_remaining_s": countdown_remaining_s,
        "completed_at": match.get("completed_at"),
        "winner_player_id": match.get("winner_player_id"),
        "result_reason": match.get("result_reason"),
        "created_at": match.get("created_at"),
        "updated_at": match.get("updated_at"),
        "participants": [
            {
                **participant,
                "progress": _versus_progress_for_mission(participant.get("mission_id")),
            }
            for participant in state_participants
        ],
        "current_player_mission_id": self_participant.get("mission_id") if self_participant else None,
    }


def _completed_secondary_objectives_count(debrief: dict) -> int:
    objectives = (((debrief or {}).get("analysis") or {}).get("secondary_objectives") or [])
    if not isinstance(objectives, list):
        return 0
    return sum(1 for objective in objectives if bool((objective or {}).get("completed")))


def list_versus_templates() -> dict:
    templates = []
    for template in VERSUS_TEMPLATES.values():
        templates.append(
            {
                "template_id": template["template_id"],
                "label": template["label"],
                "description": template["description"],
            }
        )
    return {"templates": templates}


def create_versus_match(payload: dict) -> dict:
    host_player_id = str(payload.get("player_id") or payload.get("host_player_id") or "")
    _require_player(host_player_id)
    mode = _normalize_versus_mode(payload.get("mode"))
    if mode != "private":
        raise ValueError("Utilisez les endpoints dédiés pour ce mode (queue/invite).")
    map_source, template_id, mission_config = _resolve_versus_map_payload(payload, custom_allowed=True)
    winner_rule = _normalize_versus_winner_rule(payload.get("winner_rule"))
    match_id = uuid.uuid4().hex[:14]
    repository.create_versus_match(
        match_id=match_id,
        mode=mode,
        template_id=template_id,
        map_source=map_source,
        mission_config=mission_config,
        winner_rule=winner_rule,
        host_player_id=host_player_id,
        join_code=_generate_join_code(),
        status="waiting_opponent",
    )
    return _build_versus_match_state(match_id, host_player_id)


def join_versus_match(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    _require_player(player_id)
    join_code = str(payload.get("join_code") or "").strip().upper()
    if not join_code:
        raise ValueError("Code de partie requis")
    match = repository.get_versus_match_by_join_code(join_code)
    if not match:
        raise FileNotFoundError("Code de partie invalide")
    if str(match.get("mode")) != "private":
        raise ValueError("Cette partie n'accepte pas de jonction par code")
    if str(match.get("status")) != "waiting_opponent":
        raise RuntimeError("Cette partie n'est plus disponible")

    participants = repository.list_versus_participants(str(match["match_id"]))
    if any(str(participant["player_id"]) == player_id for participant in participants):
        raise RuntimeError("Vous êtes déjà dans cette partie")
    repository.add_versus_participant(str(match["match_id"]), player_id, seat=1, state="joined")
    repository.update_versus_match(str(match["match_id"]), status="waiting_ready")
    repository.remove_versus_queue_player(player_id)
    return _build_versus_match_state(str(match["match_id"]), player_id)


def enter_versus_queue(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    _require_player(player_id)
    map_source = _normalize_versus_map_source(payload.get("map_source"))
    if map_source != "template":
        raise ValueError("La file auto accepte uniquement les templates prédéfinis.")
    template_id = _normalize_versus_template_id(payload.get("template_id"))
    winner_rule = _normalize_versus_winner_rule(payload.get("winner_rule"))

    existing_match = repository.get_latest_versus_match_for_player(player_id, statuses=("waiting_ready", "live"))
    if existing_match:
        return {
            "status": "matched",
            "match": _build_versus_match_state(str(existing_match["match_id"]), player_id),
        }

    opponent = repository.find_versus_queue_opponent(player_id, template_id, winner_rule)
    if opponent:
        host_player_id = str(opponent["player_id"])
        match_id = _create_versus_match_pair(
            mode="queue",
            host_player_id=host_player_id,
            opponent_player_id=player_id,
            template_id=template_id,
            map_source="template",
            mission_config=None,
            winner_rule=winner_rule,
        )
        return {
            "status": "matched",
            "match": _build_versus_match_state(match_id, player_id),
        }

    queue_entry = repository.enqueue_versus_player(player_id, template_id, winner_rule)
    return {"status": "queued", "queue_entry": queue_entry}


def leave_versus_queue(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    _require_player(player_id)
    repository.remove_versus_queue_player(player_id)
    return {"status": "left"}


def get_versus_queue_status(payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    _require_player(player_id)
    template_id = _normalize_versus_template_id(payload.get("template_id"))
    winner_rule = _normalize_versus_winner_rule(payload.get("winner_rule"))

    existing_match = repository.get_latest_versus_match_for_player(player_id, statuses=("waiting_ready", "live"))
    if existing_match:
        return {
            "status": "matched",
            "match": _build_versus_match_state(str(existing_match["match_id"]), player_id),
        }

    queue_entry = repository.get_versus_queue_entry(player_id)
    if not queue_entry:
        return {"status": "idle"}

    if (
        str(queue_entry.get("template_id") or "") != template_id
        or str(queue_entry.get("winner_rule") or "") != winner_rule
    ):
        return {"status": "idle"}

    opponent = repository.find_versus_queue_opponent(player_id, template_id, winner_rule)
    if opponent:
        host_player_id = str(opponent["player_id"])
        match_id = _create_versus_match_pair(
            mode="queue",
            host_player_id=host_player_id,
            opponent_player_id=player_id,
            template_id=template_id,
            map_source="template",
            mission_config=None,
            winner_rule=winner_rule,
        )
        return {
            "status": "matched",
            "match": _build_versus_match_state(match_id, player_id),
        }

    return {"status": "queued", "queue_entry": queue_entry}


def create_versus_invite(payload: dict) -> dict:
    inviter_player_id = str(payload.get("player_id") or payload.get("inviter_player_id") or "")
    invitee_player_id = str(payload.get("invitee_player_id") or "")
    _require_player(inviter_player_id)
    _require_player(invitee_player_id)
    if inviter_player_id == invitee_player_id:
        raise ValueError("Impossible de vous inviter vous-même")

    map_source, template_id, mission_config = _resolve_versus_map_payload(payload, custom_allowed=True)
    winner_rule = _normalize_versus_winner_rule(payload.get("winner_rule"))
    invite_id = uuid.uuid4().hex[:16]
    invite = repository.create_versus_invite(
        invite_id=invite_id,
        inviter_player_id=inviter_player_id,
        invitee_player_id=invitee_player_id,
        template_id=template_id,
        map_source=map_source,
        mission_config=mission_config,
        winner_rule=winner_rule,
    )
    mission_payload = mission_config if map_source == "custom" else _template_payload_for_mission(template_id)
    enriched = dict(invite or {})
    enriched["mission_summary"] = _mission_summary_from_payload(
        mission_payload,
        map_source=map_source,
        template_id=template_id,
    )
    return {"invite": enriched}


def list_versus_invites(player_id: str) -> dict:
    _require_player(player_id)
    invites = repository.list_pending_versus_invites(player_id)
    enriched: list[dict] = []
    for invite in invites:
        map_source = _normalize_versus_map_source(invite.get("map_source"))
        mission_payload: dict | None = None
        if map_source == "custom" and isinstance(invite.get("mission_config"), dict):
            try:
                mission_payload = _sanitize_and_validate_versus_mission_config(invite.get("mission_config"))
            except ValueError:
                mission_payload = dict(invite.get("mission_config") or {})
        elif map_source == "template":
            template_id = str(invite.get("template_id") or "paris_duel")
            if template_id in VERSUS_TEMPLATES:
                mission_payload = _template_payload_for_mission(template_id)
        payload = dict(invite)
        payload["map_source"] = map_source
        payload["mission_summary"] = _mission_summary_from_payload(
            mission_payload,
            map_source=map_source,
            template_id=str(invite.get("template_id") or ""),
        )
        enriched.append(payload)
    return {"invites": enriched}


def accept_versus_invite(invite_id: str, payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    _require_player(player_id)
    invite = repository.get_versus_invite(invite_id)
    if not invite:
        raise FileNotFoundError("Invitation introuvable")
    if str(invite.get("invitee_player_id")) != player_id:
        raise ValueError("Cette invitation ne vous est pas destinée")
    if str(invite.get("status")) != "pending":
        raise RuntimeError("Invitation déjà traitée")

    map_source = _normalize_versus_map_source(invite.get("map_source"))
    mission_config: dict | None = None
    if map_source == "custom":
        mission_config = _sanitize_and_validate_versus_mission_config(invite.get("mission_config"))
        template_id = str(invite.get("template_id") or "custom_map").strip().lower() or "custom_map"
    else:
        template_id = _normalize_versus_template_id(str(invite.get("template_id") or "paris_duel"))

    match_id = _create_versus_match_pair(
        mode="invite",
        host_player_id=str(invite["inviter_player_id"]),
        opponent_player_id=player_id,
        template_id=template_id,
        map_source=map_source,
        mission_config=mission_config,
        winner_rule=_normalize_versus_winner_rule(str(invite["winner_rule"])),
    )
    repository.update_versus_invite(invite_id, status="accepted", match_id=match_id, responded_at=_now_iso())
    return {"status": "accepted", "match": _build_versus_match_state(match_id, player_id)}


def decline_versus_invite(invite_id: str, payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    _require_player(player_id)
    invite = repository.get_versus_invite(invite_id)
    if not invite:
        raise FileNotFoundError("Invitation introuvable")
    if str(invite.get("invitee_player_id")) != player_id:
        raise ValueError("Cette invitation ne vous est pas destinée")
    if str(invite.get("status")) != "pending":
        raise RuntimeError("Invitation déjà traitée")
    repository.update_versus_invite(invite_id, status="declined", responded_at=_now_iso())
    return {"status": "declined"}


def set_versus_ready(match_id: str, payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    ready = bool(payload.get("ready", True))
    _require_player(player_id)
    match = repository.get_versus_match(match_id)
    if not match:
        raise FileNotFoundError("Match versus introuvable")
    participant = repository.get_versus_participant(match_id, player_id)
    if not participant:
        raise ValueError("Vous ne participez pas à ce match")
    if str(match.get("status")) == "finished":
        return _build_versus_match_state(match_id, player_id)
    if str(match.get("status")) == "waiting_opponent":
        raise RuntimeError("En attente d'un adversaire")

    repository.update_versus_participant(
        match_id,
        player_id,
        state="ready" if ready else "joined",
        ready_at=_now_iso() if ready else None,
    )
    _start_versus_match_if_ready(match_id)
    return _build_versus_match_state(match_id, player_id)


def get_versus_match_state(match_id: str, player_id: str) -> dict:
    _require_player(player_id)
    participant = repository.get_versus_participant(match_id, player_id)
    if not participant:
        raise ValueError("Vous ne participez pas à ce match")
    _touch_versus_participant(match_id, player_id)
    _apply_versus_forfeit_timeout(match_id)
    return _build_versus_match_state(match_id, player_id)


def submit_versus_attempt(match_id: str, payload: dict) -> dict:
    player_id = str(payload.get("player_id") or "")
    _require_player(player_id)
    match = repository.get_versus_match(match_id)
    if not match:
        raise FileNotFoundError("Match versus introuvable")
    if str(match.get("status")) == "finished":
        raise RuntimeError("Ce match est déjà terminé")
    if str(match.get("status")) != "live":
        raise RuntimeError("Le match n'a pas encore démarré")

    participant = repository.get_versus_participant(match_id, player_id)
    if not participant:
        raise ValueError("Vous ne participez pas à ce match")
    if str(participant.get("state")) == "submitted":
        raise RuntimeError("Tentative déjà soumise")
    if str(participant.get("state")) == "forfeit":
        raise RuntimeError("Impossible de soumettre après forfait")

    mission_id = str(participant.get("mission_id") or "")
    if not mission_id:
        raise RuntimeError("Mission versus non assignée")

    _touch_versus_participant(match_id, player_id)
    _apply_versus_forfeit_timeout(match_id)

    try:
        debrief_payload = get_debrief(mission_id)
    except FileNotFoundError as exc:
        raise ValueError("Résous d'abord la mission avant de soumettre.") from exc

    mission_payload = get_mission(mission_id)
    total_clients = len(mission_payload.get("clients", []))
    assigned_clients = set(int(client_id) for client_id in (debrief_payload.get("human", {}).get("assigned_clients", []) or []))
    if len(assigned_clients) < total_clients:
        raise ValueError("Soumission invalide: tous les clients doivent être assignés.")

    score_value = float(((debrief_payload.get("score") or {}).get("value") or 0.0))
    total_time_s = float((((debrief_payload.get("human") or {}).get("summary") or {}).get("total_time_s") or 0.0))
    objectives_completed = _completed_secondary_objectives_count(debrief_payload)
    repository.update_versus_participant(
        match_id,
        player_id,
        state="submitted",
        submitted_at=_now_iso(),
        score=score_value,
        total_time_s=total_time_s,
        objectives_completed=objectives_completed,
        is_valid_submission=1,
    )

    _resolve_versus_match(match_id, reason="submitted")
    return _build_versus_match_state(match_id, player_id)


def list_versus_leaderboard(limit: int = 20) -> dict:
    entries = repository.list_versus_leaderboard(limit=limit)
    enriched: list[dict] = []
    for entry in entries:
        map_source = _normalize_versus_map_source(entry.get("map_source"))
        mission_payload: dict | None = None
        if map_source == "custom" and isinstance(entry.get("mission_config"), dict):
            try:
                mission_payload = _sanitize_and_validate_versus_mission_config(entry.get("mission_config"))
            except ValueError:
                mission_payload = dict(entry.get("mission_config") or {})
        elif map_source == "template":
            template_id = str(entry.get("template_id") or "paris_duel")
            if template_id in VERSUS_TEMPLATES:
                mission_payload = _template_payload_for_mission(template_id)
        payload = dict(entry)
        payload["map_source"] = map_source
        payload["mission_summary"] = _mission_summary_from_payload(
            mission_payload,
            map_source=map_source,
            template_id=str(entry.get("template_id") or ""),
        )
        payload["map_label"] = payload["mission_summary"].get("template_label") or str(entry.get("template_id") or "template")
        enriched.append(payload)
    return {"entries": enriched}


def list_versus_player_stats(limit: int = 20, max_matches: int = 500) -> dict:
    rows = repository.list_versus_player_history(max_matches=max_matches)
    by_player: dict[str, dict] = {}

    for row in rows:
        player_id = str(row.get("player_id") or "")
        if not player_id:
            continue
        payload = by_player.setdefault(
            player_id,
            {
                "player_id": player_id,
                "display_name": row.get("display_name"),
                "callsign": row.get("callsign"),
                "avatar": row.get("avatar"),
                "matches_played": 0,
                "wins": 0,
                "losses": 0,
                "favorite_rule": None,
                "average_time_s": None,
                "last_match_at": None,
                "_rule_counts": defaultdict(int),
                "_time_sum": 0.0,
                "_time_count": 0,
            },
        )

        payload["matches_played"] += 1
        if str(row.get("winner_player_id") or "") == player_id:
            payload["wins"] += 1
        else:
            payload["losses"] += 1

        winner_rule = _normalize_versus_winner_rule(str(row.get("winner_rule") or "score_time"))
        payload["_rule_counts"][winner_rule] += 1

        if int(row.get("is_valid_submission") or 0) == 1:
            total_time_s = _safe_float(row.get("total_time_s"))
            if total_time_s is not None and total_time_s >= 0:
                payload["_time_sum"] += float(total_time_s)
                payload["_time_count"] += 1

        match_timestamp = str(row.get("completed_at") or row.get("created_at") or "")
        current_match_dt = _iso_to_datetime(match_timestamp)
        previous_match_dt = _iso_to_datetime(payload.get("last_match_at"))
        if match_timestamp and (
            not payload["last_match_at"]
            or (current_match_dt is not None and (previous_match_dt is None or current_match_dt > previous_match_dt))
        ):
            payload["last_match_at"] = match_timestamp

    entries: list[dict] = []
    for player_stats in by_player.values():
        rule_counts: defaultdict[str, int] = player_stats.pop("_rule_counts")
        if rule_counts:
            favorite_rule = sorted(
                rule_counts.items(),
                key=lambda item: (-int(item[1]), item[0]),
            )[0][0]
        else:
            favorite_rule = "score_time"
        player_stats["favorite_rule"] = favorite_rule

        time_count = int(player_stats.pop("_time_count"))
        time_sum = float(player_stats.pop("_time_sum"))
        player_stats["average_time_s"] = (time_sum / time_count) if time_count > 0 else None

        matches_played = int(player_stats.get("matches_played") or 0)
        wins = int(player_stats.get("wins") or 0)
        player_stats["winrate_pct"] = (wins / matches_played * 100.0) if matches_played > 0 else 0.0
        entries.append(player_stats)

    entries.sort(
        key=lambda item: (
            -float(item.get("winrate_pct") or 0.0),
            -int(item.get("wins") or 0),
            -int(item.get("matches_played") or 0),
            _iso_to_datetime(item.get("last_match_at")) or datetime.min.replace(tzinfo=timezone.utc),
        ),
    )

    for item in entries:
        item["winrate_pct"] = round(float(item.get("winrate_pct") or 0.0), 1)
        average_time_s = item.get("average_time_s")
        item["average_time_s"] = round(float(average_time_s), 1) if average_time_s is not None else None

    return {"entries": entries[: max(0, int(limit))]}


# ── Eco / CO2 Analysis ────────────────────────────────────────────────────────

def get_eco_analysis(mission_id: str) -> dict:
    """
    Calcule l'empreinte CO2 et les économies pour les routes IA, humaine et naïve.

    Modèle physique :
    - Camion de livraison urbain standard : 120 g CO2/km
    - Surcoût montée : +4 g CO2/m de dénivelé positif (effort moteur additionnel)
    - Paris 5ème : terrain vallonné (Montagne Sainte-Geneviève) → dénivelé estimé 45 m
    - Traîneau (électrique / traction animale) : ~10 % de l'effort équivalent d'un camion
    """
    paths, mission, human_state_payload = load_mission_bundle(mission_id)

    results = _read_json(paths.results_file, {})
    benchmark = _read_json(paths.benchmark_file, {})

    ai_dist_m = float((benchmark.get("optimized") or {}).get("total_dist_m", 0.0))
    naive_dist_m = float((benchmark.get("naive") or {}).get("total_dist_m", ai_dist_m))

    human_state = human_state_from_payload(human_state_payload)
    human_segments = [seg for segs in human_state.segments_by_sleigh.values() for seg in segs]
    human_dist_m = float(summarize_segments(human_segments).get("total_dist_m", 0.0))

    # Terrain Paris 5ème : Montagne Sainte-Geneviève → vallonné, ~45 m de dénivelé positif
    TERRAIN_TYPE = "vallonné"
    ESTIMATED_CLIMB_M = 45.0
    BASE_CO2_G_PER_KM = 120.0
    CLIMB_CO2_G_PER_M = 4.0
    SLEIGH_FACTOR = 0.10  # traîneau ≈ 10 % de l'effort d'un camion

    def _co2_profile(dist_m: float) -> dict:
        dist_km = max(0.0, dist_m) / 1000.0
        truck_g = dist_km * BASE_CO2_G_PER_KM + ESTIMATED_CLIMB_M * CLIMB_CO2_G_PER_M
        sleigh_g = truck_g * SLEIGH_FACTOR
        saved_g = truck_g - sleigh_g
        return {
            "distance_km": round(dist_km, 3),
            "truck_co2_kg": round(truck_g / 1000.0, 3),
            "sleigh_co2_kg": round(sleigh_g / 1000.0, 3),
            "saved_vs_truck_kg": round(saved_g / 1000.0, 3),
            "trees_month_offset": round(saved_g / 20.0, 1),
        }

    ai_profile = _co2_profile(ai_dist_m)
    naive_profile = _co2_profile(naive_dist_m)
    human_profile = _co2_profile(human_dist_m) if human_dist_m > 0 else None

    # Gain additionnel de l'optimisation : réduction CO2 truck(naïf) → truck(IA)
    route_optimization_saving_kg = round(
        naive_profile["truck_co2_kg"] - ai_profile["truck_co2_kg"], 3
    )

    return {
        "terrain": {
            "type": TERRAIN_TYPE,
            "estimated_climb_m": ESTIMATED_CLIMB_M,
            "zone": mission.get("zone", "Paris 5"),
            "note": "Dénivelé estimé — Montagne Sainte-Geneviève",
        },
        "routes": {
            "ai": ai_profile,
            "naive": naive_profile,
            "human": human_profile,
        },
        "eco_impact": {
            "total_co2_avoided_kg": ai_profile["saved_vs_truck_kg"],
            "route_optimisation_saving_kg": route_optimization_saving_kg,
            "ai_vs_naive_dist_pct": round(
                (1.0 - ai_dist_m / naive_dist_m) * 100.0, 1
            ) if naive_dist_m > 0 else 0.0,
        },
    }


# ── Community Detection / Delivery Sectors ────────────────────────────────────

def get_delivery_sectors(mission_id: str) -> dict:
    """
    Découpe le graphe de la mission en secteurs de livraison naturels via Louvain.

    Retourne les polygones (enveloppe convexe) de chaque secteur pour affichage
    sur la carte frontend.
    """
    from scripts.community_detection import detect_delivery_sectors

    paths, _, _ = load_mission_bundle(mission_id)
    if not paths.graph_file.exists():
        raise FileNotFoundError("Graphe introuvable pour cette mission.")

    graph = _load_graph_cached(paths.graph_file)
    sectors = detect_delivery_sectors(graph, seed=42, resolution=1.0)

    return {
        "sector_count": len(sectors),
        "sectors": sectors,
        "algorithm": "Louvain (NetworkX 3.x)",
        "note": "Secteurs détectés par communautés topologiques sur le graphe de rues.",
    }


# ── Topological Validation ────────────────────────────────────────────────────

def validate_topology(mission_id: str) -> dict:
    """
    Vérifie que les incidents simulés ne coupent pas totalement le dépôt du reste du graphe.

    Algorithme :
    1. Charge le graphe + les segments d'incidents
    2. Retire les arêtes bloquées (edges consécutifs dans route_nodes de chaque incident)
    3. Calcule les composantes fortement connexes
    4. Vérifie si le nœud dépôt est dans la même composante que tous les clients
    5. Retourne la liste des clients isolés et le statut de connexité
    """
    import osmnx as ox
    import networkx as nx

    paths, _, _ = load_mission_bundle(mission_id)
    if not paths.graph_file.exists():
        raise FileNotFoundError("Graphe introuvable pour cette mission.")

    graph = load_graph(paths.graph_file)
    incidents_payload = _read_json(paths.incidents_file, {"count": 0, "segments": []})
    incident_segments = list((incidents_payload or {}).get("segments", []))

    # Construire le graphe amputé des arêtes incidentées
    G_blocked = graph.copy()
    blocked_edges: list[tuple] = []
    for seg in incident_segments:
        nodes = seg.get("route_nodes", [])
        for i in range(len(nodes) - 1):
            u, v = nodes[i], nodes[i + 1]
            if G_blocked.has_edge(u, v):
                G_blocked.remove_edge(u, v)
                blocked_edges.append((u, v))

    # Nœud dépôt (premier point du CSV)
    df = read_points(paths.data_file)
    depot_row = df.iloc[0]
    depot_node = ox.nearest_nodes(G_blocked, float(depot_row["lon"]), float(depot_row["lat"]))

    # Nœuds clients
    client_nodes: dict[int, int] = {}  # client_id → osm_node
    for _, row in df.iloc[1:].iterrows():
        cid = int(row["id"])
        osm_node = ox.nearest_nodes(G_blocked, float(row["lon"]), float(row["lat"]))
        client_nodes[cid] = osm_node

    # Composantes fortement connexes (dirigé) ou faiblement connexes (chemin quelconque)
    wccs = list(nx.weakly_connected_components(G_blocked))
    depot_component = next(
        (i for i, comp in enumerate(wccs) if depot_node in comp), -1
    )

    unreachable_clients: list[int] = []
    reachability: list[dict] = []
    for cid, osm_node in client_nodes.items():
        client_comp = next(
            (i for i, comp in enumerate(wccs) if osm_node in comp), -1
        )
        reachable = (client_comp == depot_component and depot_component >= 0)
        if not reachable:
            unreachable_clients.append(cid)
        reachability.append({
            "client_id": cid,
            "osm_node": osm_node,
            "reachable": reachable,
        })

    is_valid = len(unreachable_clients) == 0
    num_components = len(wccs)

    return {
        "is_valid": is_valid,
        "depot_node": int(depot_node),
        "num_components": num_components,
        "blocked_edges_count": len(blocked_edges),
        "incident_count": len(incident_segments),
        "unreachable_clients": unreachable_clients,
        "reachability": reachability,
        "status": (
            "OK — Dépôt accessible depuis tous les clients."
            if is_valid
            else f"ALERTE — {len(unreachable_clients)} client(s) isolé(s) du dépôt !"
        ),
    }
