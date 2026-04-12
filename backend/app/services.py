from __future__ import annotations

import json
import random
import uuid
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
    results = solve_vrp(
        num_vehicles=int(payload["num_vehicles"]),
        vehicle_capacity=int(payload["vehicle_capacity"]),
        speed_multiplier=float(payload["speed_multiplier"]),
        forced_weather=weather,
        incident_matrix_path=incident_matrix_path,
        data_path=str(paths.data_file),
        time_matrix_path=str(paths.time_matrix_file),
        dist_matrix_path=str(paths.dist_matrix_file),
        weather_file=str(paths.weather_file),
        output_path=str(paths.results_file),
        optimization_target=payload.get("optimization_target", "time"),
    )
    if not results:
        raise RuntimeError("Aucune solution VRP trouvee")

    benchmark = calculate_benchmark(
        num_vehicles=int(payload["num_vehicles"]),
        budget_initial=int(mission.get("budget", 0)),
        budget_spent=int(payload["num_vehicles"]) * int(mission.get("sleigh_cost", 0)),
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
    final_score = 0.60 * time_saved_pct + 0.25 * co2_score + 0.15 * budget_remaining_pct
    if mission.get("random_incidents", False):
        final_score = min(final_score + 10.0, 100.0)
    human_beat_ai = human_time_s is not None and human_time_s < float(results.get("total_time_s", 0))
    if human_beat_ai:
        final_score = min(final_score + 5.0, 100.0)
    final_score = round(final_score, 1)

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

    repository.save_leaderboard_entry(
        mission_id=mission_id,
        zone=mission.get("zone", "Inconnue"),
        score=float(debrief["score"]["value"]),
        rank=debrief["score"]["rank"],
        player_name=payload.get("player_name", "Père Noël"),
    )
    return {"status": "success"}


def list_leaderboard(limit: int = 20) -> dict:
    return {"entries": repository.list_leaderboard(limit=limit)}

