from __future__ import annotations

import json
import hashlib
import math
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from threading import Lock
from typing import Any
from collections import OrderedDict

import networkx as nx
import osmnx as ox
import pandas as pd


WEATHER_MAP: dict[str, dict[str, float | str]] = {
    "Clear": {"condition": "Clear", "desc": "Ciel degage", "factor": 1.0},
    "Rain": {"condition": "Rain", "desc": "Pluie moderee", "factor": 1.3},
    "Snow": {"condition": "Snow", "desc": "Tempete de neige", "factor": 2.0},
    "Thunderstorm": {"condition": "Thunderstorm", "desc": "Orage violent", "factor": 2.5},
    "Clouds": {"condition": "Clouds", "desc": "Nuageux", "factor": 1.0},
    "Drizzle": {"condition": "Drizzle", "desc": "Bruine legere", "factor": 1.3},
    "Mist": {"condition": "Mist", "desc": "Brouillard givrant", "factor": 2.0},
}

DEFAULT_DEPARTURE_TIME = "18:00"
INCIDENT_GRAPH_CACHE_MAX = 32
_incident_graph_cache: OrderedDict[tuple[int, int, str], Any] = OrderedDict()
_incident_graph_cache_lock = Lock()
ROUTE_CANDIDATES_CACHE_MAX = 2048
_route_candidates_cache: OrderedDict[tuple[int, int, int, int, int], list[list[int]]] = OrderedDict()
_route_candidates_cache_lock = Lock()


@dataclass
class HumanState:
    routes_by_sleigh: dict[str, list[int]]
    segments_by_sleigh: dict[str, list[dict]]
    assigned_clients: list[int]
    speed_multiplier: float
    vehicle_capacity: int
    num_vehicles: int


def _edge_time_s(edge_data: dict) -> float:
    if edge_data.get("travel_time") is not None:
        return float(edge_data["travel_time"])
    length_m = float(edge_data.get("length", 0.0))
    return length_m / (30_000 / 3600)


def load_graph(graph_path: str | Path):
    graph = ox.load_graphml(graph_path)
    if not all("travel_time" in data and data.get("travel_time") is not None for _, _, data in graph.edges(data=True)):
        graph = ox.add_edge_speeds(graph)
        graph = ox.add_edge_travel_times(graph)
    return graph


def read_points(data_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(data_path)


def load_weather(weather_file: str | Path, weather_key: str | None = None) -> dict:
    if weather_key and weather_key != "random":
        return dict(WEATHER_MAP.get(weather_key, WEATHER_MAP["Clear"]))
    path = Path(weather_file)
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return dict(WEATHER_MAP["Clear"])


def parse_clock_to_seconds(clock: str) -> int:
    hours, minutes = [int(part) for part in str(clock).split(":", 1)]
    return hours * 3600 + minutes * 60


def format_clock(total_seconds: float) -> str:
    seconds = int(round(float(total_seconds)))
    hours = (seconds // 3600) % 24
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def route_length_m(graph, route: list[int]) -> float:
    total = 0.0
    for u, v in zip(route[:-1], route[1:]):
        edge_data = graph.get_edge_data(u, v)
        if not edge_data:
            continue
        total += float(min(data.get("length", 0.0) for data in edge_data.values()))
    return total


def route_time_s(graph, route: list[int]) -> float:
    total = 0.0
    for u, v in zip(route[:-1], route[1:]):
        edge_data = graph.get_edge_data(u, v)
        if not edge_data:
            continue
        total += min(_edge_time_s(data) for data in edge_data.values())
    return total


def route_to_geometry(graph, route: list[int]) -> list[list[float]]:
    coords: list[list[float]] = []
    for u, v in zip(route[:-1], route[1:]):
        edge_data = graph.get_edge_data(u, v)
        if not edge_data:
            continue
        data = min(edge_data.values(), key=lambda item: item.get("length", 1e12))
        geometry = data.get("geometry")
        if geometry is not None:
            segment = [[float(y), float(x)] for x, y in list(geometry.coords)]
        else:
            segment = [
                [float(graph.nodes[u]["y"]), float(graph.nodes[u]["x"])],
                [float(graph.nodes[v]["y"]), float(graph.nodes[v]["x"])],
            ]
        if coords and segment and coords[-1] == segment[0]:
            coords.extend(segment[1:])
        else:
            coords.extend(segment)
    return coords


def point_label(points_data: dict[int, dict], point_id: int) -> str:
    if point_id == 0:
        return "Depot"
    return str(points_data.get(point_id, {}).get("nom_client", f"Client #{point_id}"))


def _format_minutes(seconds: float) -> str:
    minutes = max(0, int(round(float(seconds) / 60)))
    return f"{minutes} min"


def _route_edge_set(route_nodes: list[int]) -> set[tuple[int, int]]:
    if len(route_nodes) < 2:
        return set()
    return {(int(u), int(v)) for u, v in zip(route_nodes[:-1], route_nodes[1:])}


def _route_overlap_ratio(route_a: list[int], route_b: list[int]) -> float:
    edges_a = _route_edge_set(route_a)
    edges_b = _route_edge_set(route_b)
    if not edges_a or not edges_b:
        return 0.0
    inter = len(edges_a & edges_b)
    union = len(edges_a | edges_b)
    if union == 0:
        return 0.0
    return float(inter) / float(union)


def _pick_diverse_options(options: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    if len(options) <= k:
        return options

    selected: list[dict[str, Any]] = [options[0]]
    remaining = options[1:]
    overlap_threshold = 0.65

    while remaining and len(selected) < k:
        picked_idx = None
        for idx, candidate in enumerate(remaining):
            overlap = max(
                _route_overlap_ratio(candidate["route_nodes"], kept["route_nodes"])
                for kept in selected
            )
            if overlap <= overlap_threshold:
                picked_idx = idx
                break

        if picked_idx is None:
            picked_idx = 0
        selected.append(remaining.pop(picked_idx))

    return selected


def _incident_edge_sets(incident_segments: list[dict] | None) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    blocked_directed: set[tuple[int, int]] = set()
    blocked_undirected: set[tuple[int, int]] = set()
    for segment in incident_segments or []:
        route_nodes = [int(node_id) for node_id in segment.get("route_nodes", [])]
        if len(route_nodes) < 2:
            continue
        for source, target in zip(route_nodes[:-1], route_nodes[1:]):
            edge = (int(source), int(target))
            blocked_directed.add(edge)
            blocked_undirected.add(tuple(sorted(edge)))
    return blocked_directed, blocked_undirected


def _route_has_incident_overlap(
    route_nodes: list[int],
    blocked_directed: set[tuple[int, int]],
    blocked_undirected: set[tuple[int, int]],
) -> bool:
    if len(route_nodes) < 2 or (not blocked_directed and not blocked_undirected):
        return False
    route_directed = {(int(source), int(target)) for source, target in zip(route_nodes[:-1], route_nodes[1:])}
    route_undirected = {tuple(sorted(edge)) for edge in route_directed}
    return bool((route_directed & blocked_directed) or (route_undirected & blocked_undirected))


def _remove_incident_edges(graph, blocked_undirected: set[tuple[int, int]]):
    if not blocked_undirected:
        return graph
    cleaned = graph.copy()
    for source, target in blocked_undirected:
        if cleaned.has_edge(source, target):
            keys = list(cleaned[source][target].keys())
            for key in keys:
                cleaned.remove_edge(source, target, key=key)
        if cleaned.has_edge(target, source):
            keys = list(cleaned[target][source].keys())
            for key in keys:
                cleaned.remove_edge(target, source, key=key)
    return cleaned


def _apply_incident_penalties(
    graph,
    blocked_undirected: set[tuple[int, int]],
    penalty_factor: float = 1.5,
) -> Any:
    """
    Pénalités douces sur les arêtes incidentées : multiplie travel_time et length
    par penalty_factor au lieu de supprimer l'arête.

    Avantage vs. suppression : le joueur conserve toujours des options de route,
    même à travers une zone accidentée, mais paie un surcoût en temps.
    Permet d'expliquer le compromis coût/disponibilité (ex. : détour 2 km
    vs. traverser l'incident avec +50% de temps).
    """
    if not blocked_undirected or penalty_factor <= 1.0:
        return graph
    penalized = graph.copy()
    for source, target in blocked_undirected:
        for u, v in ((source, target), (target, source)):
            if penalized.has_edge(u, v):
                for key in penalized[u][v]:
                    edata = penalized[u][v][key]
                    if "travel_time" in edata and edata["travel_time"] is not None:
                        edata["travel_time"] = float(edata["travel_time"]) * penalty_factor
                    if "length" in edata and edata["length"] is not None:
                        edata["length"] = float(edata["length"]) * penalty_factor
    return penalized


def _incident_signature(blocked_undirected: set[tuple[int, int]]) -> str:
    if not blocked_undirected:
        return "none"
    payload = "|".join(f"{source}-{target}" for source, target in sorted(blocked_undirected))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _cached_incident_safe_graph(graph, blocked_undirected: set[tuple[int, int]]):
    if not blocked_undirected:
        return graph
    signature = _incident_signature(blocked_undirected)
    cache_key = (id(graph), int(graph.number_of_edges()), signature)
    with _incident_graph_cache_lock:
        cached = _incident_graph_cache.get(cache_key)
        if cached is not None:
            _incident_graph_cache.move_to_end(cache_key)
            return cached
    safer_graph = _remove_incident_edges(graph, blocked_undirected)
    with _incident_graph_cache_lock:
        _incident_graph_cache[cache_key] = safer_graph
        _incident_graph_cache.move_to_end(cache_key)
        while len(_incident_graph_cache) > INCIDENT_GRAPH_CACHE_MAX:
            _incident_graph_cache.popitem(last=False)
    return safer_graph


_incident_penalty_cache: OrderedDict[tuple, Any] = OrderedDict()
_incident_penalty_cache_lock = Lock()


def _cached_incident_penalty_graph(
    graph, blocked_undirected: set[tuple[int, int]], penalty_factor: float = 1.5
):
    if not blocked_undirected:
        return graph
    signature = _incident_signature(blocked_undirected)
    cache_key = (id(graph), int(graph.number_of_edges()), signature, round(penalty_factor, 3))
    with _incident_penalty_cache_lock:
        cached = _incident_penalty_cache.get(cache_key)
        if cached is not None:
            _incident_penalty_cache.move_to_end(cache_key)
            return cached
    penalized = _apply_incident_penalties(graph, blocked_undirected, penalty_factor)
    with _incident_penalty_cache_lock:
        _incident_penalty_cache[cache_key] = penalized
        _incident_penalty_cache.move_to_end(cache_key)
        while len(_incident_penalty_cache) > INCIDENT_GRAPH_CACHE_MAX:
            _incident_penalty_cache.popitem(last=False)
    return penalized


def _make_haversine_heuristic(graph):
    """Heuristique admissible pour A* : distance vol à 50 km/h (13.89 m/s)."""
    def _h(u: int, v: int) -> float:
        ud = graph.nodes[u]
        vd = graph.nodes[v]
        lat1 = math.radians(float(ud["y"]))
        lon1 = math.radians(float(ud["x"]))
        lat2 = math.radians(float(vd["y"]))
        lon2 = math.radians(float(vd["x"]))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        dist_m = 6_371_000.0 * 2.0 * math.asin(math.sqrt(a))
        return dist_m / 13.89
    return _h


def _route_candidates_cache_get(cache_key: tuple[int, int, int, int, int]) -> list[list[int]] | None:
    with _route_candidates_cache_lock:
        cached = _route_candidates_cache.get(cache_key)
        if cached is None:
            return None
        _route_candidates_cache.move_to_end(cache_key)
        return [list(route) for route in cached]


def _route_candidates_cache_set(cache_key: tuple[int, int, int, int, int], routes: list[list[int]]) -> None:
    with _route_candidates_cache_lock:
        _route_candidates_cache[cache_key] = [list(route) for route in routes]
        _route_candidates_cache.move_to_end(cache_key)
        while len(_route_candidates_cache) > ROUTE_CANDIDATES_CACHE_MAX:
            _route_candidates_cache.popitem(last=False)


def _collect_candidate_routes(graph, origin: int, dest: int, k_pool: int) -> list[list[int]]:
    cache_key = (id(graph), int(graph.number_of_edges()), int(origin), int(dest), int(k_pool))
    cached = _route_candidates_cache_get(cache_key)
    if cached is not None:
        return cached

    routes: list[list[int]] = []
    try:
        heuristic = _make_haversine_heuristic(graph)
        fastest = nx.astar_path(graph, origin, dest, heuristic=heuristic, weight="travel_time")
        if fastest:
            routes.append(fastest)
    except Exception:
        try:
            fastest = ox.routing.shortest_path(graph, origin, dest, weight="travel_time")
            if fastest:
                routes.append(fastest)
        except Exception:
            pass
    try:
        shortest = ox.routing.shortest_path(graph, origin, dest, weight="length")
        if shortest:
            routes.append(shortest)
    except Exception:
        pass
    try:
        routes.extend(list(islice(ox.routing.k_shortest_paths(graph, origin, dest, k_pool, weight="length"), k_pool)))
    except Exception:
        pass
    try:
        routes.extend(
            list(
                islice(
                    ox.routing.k_shortest_paths(graph, origin, dest, k_pool, weight="travel_time"),
                    k_pool,
                )
            )
        )
    except Exception:
        pass
    if routes:
        _route_candidates_cache_set(cache_key, routes)
        return routes
    fallback = ox.routing.shortest_path(graph, origin, dest, weight="length")
    fallback_routes = [fallback] if fallback else []
    _route_candidates_cache_set(cache_key, fallback_routes)
    return fallback_routes


def compute_route_options(
    graph,
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    time_factor: float = 1.0,
    k: int = 3,
    incident_segments: list[dict] | None = None,
    incident_penalty_factor: float = 1.5,
) -> list[dict]:
    """
    incident_penalty_factor : multiplicateur appliqué sur travel_time et length
    des arêtes incidentées (1.5 = +50% de temps). Les routes traversant une zone
    accidentée restent disponibles mais coûtent plus cher. Mettre à 0.0 pour
    revenir au comportement strict (suppression des arêtes).
    """
    origin = ox.distance.nearest_nodes(graph, X=float(from_lon), Y=float(from_lat))
    dest = ox.distance.nearest_nodes(graph, X=float(to_lon), Y=float(to_lat))
    blocked_directed, blocked_undirected = _incident_edge_sets(incident_segments)
    k_pool = max(int(k) * 4, 8)
    routing_graph = graph
    if blocked_undirected:
        use_soft = incident_penalty_factor > 1.0
        if use_soft:
            routing_graph = _cached_incident_penalty_graph(graph, blocked_undirected, incident_penalty_factor)
            routes = _collect_candidate_routes(routing_graph, int(origin), int(dest), k_pool)
        else:
            safer_graph = _cached_incident_safe_graph(graph, blocked_undirected)
            routes = _collect_candidate_routes(safer_graph, int(origin), int(dest), k_pool)
            if routes:
                routing_graph = safer_graph
            else:
                routes = _collect_candidate_routes(graph, int(origin), int(dest), k_pool)
    else:
        routes = _collect_candidate_routes(graph, int(origin), int(dest), k_pool)

    options = []
    seen: set[tuple[int, ...]] = set()
    for route in routes:
        if not route:
            continue
        route_key = tuple(route)
        if route_key in seen:
            continue
        seen.add(route_key)
        base_time_s = route_time_s(routing_graph, route)
        has_incident_overlap = _route_has_incident_overlap(route, blocked_directed, blocked_undirected)
        options.append(
            {
                "route_nodes": route,
                "geometry": route_to_geometry(routing_graph, route),
                "dist_m": route_length_m(routing_graph, route),
                "base_time_s": base_time_s,
                "time_s": base_time_s * time_factor,
                "incident_overlap": has_incident_overlap,
            }
        )
    use_soft_penalties = incident_penalty_factor > 1.0 and bool(blocked_undirected)
    options.sort(key=lambda item: (bool(item.get("incident_overlap", False)), item["time_s"], item["dist_m"]))
    safe_options = [option for option in options if not option.get("incident_overlap", False)]
    blocked_options = [option for option in options if option.get("incident_overlap", False)]
    picked = _pick_diverse_options(safe_options, int(k))
    if len(picked) < int(k):
        picked.extend(_pick_diverse_options(blocked_options, int(k) - len(picked)))
    options = picked[: int(k)]
    fastest_idx = min(range(len(options)), key=lambda idx: options[idx]["time_s"]) if options else 0
    shortest_idx = min(range(len(options)), key=lambda idx: options[idx]["dist_m"]) if options else 0
    for idx, option in enumerate(options):
        tags = []
        if idx == fastest_idx:
            tags.append("Plus rapide")
        if idx == shortest_idx:
            tags.append("Plus court")
        if not tags:
            tags.append(f"Alternative diverse {idx + 1}")
        label = f"{' / '.join(tags)} · {_format_minutes(option['time_s'])} · {option['dist_m'] / 1000:.2f} km"
        has_overlap = bool(option.get("incident_overlap", False))
        if has_overlap and use_soft_penalties:
            label += f" · ⚠ Zone incidentée (+{int((incident_penalty_factor - 1) * 100)}%)"
            option["incident_warning"] = True
        elif has_overlap:
            label += " · ⚠ Incident signalé"
            option["incident_warning"] = True
        option["label"] = label
        option.pop("incident_overlap", None)
    return options[: int(k)]


def default_human_state(num_vehicles: int = 3, vehicle_capacity: int = 200) -> dict:
    return {
        "routes_by_sleigh": {str(i): [] for i in range(num_vehicles)},
        "segments_by_sleigh": {str(i): [] for i in range(num_vehicles)},
        "assigned_clients": [],
        "speed_multiplier": 1.0,
        "vehicle_capacity": vehicle_capacity,
        "num_vehicles": num_vehicles,
    }


def human_state_from_payload(payload: dict | None) -> HumanState:
    data = payload or default_human_state()
    return HumanState(
        routes_by_sleigh={str(key): [int(v) for v in value] for key, value in data.get("routes_by_sleigh", {}).items()},
        segments_by_sleigh={
            str(key): list(value) for key, value in data.get("segments_by_sleigh", {}).items()
        },
        assigned_clients=[int(client_id) for client_id in data.get("assigned_clients", [])],
        speed_multiplier=float(data.get("speed_multiplier", 1.0)),
        vehicle_capacity=int(data.get("vehicle_capacity", 200)),
        num_vehicles=int(data.get("num_vehicles", 3)),
    )


def serialize_human_state(state: HumanState) -> dict:
    return {
        "routes_by_sleigh": state.routes_by_sleigh,
        "segments_by_sleigh": state.segments_by_sleigh,
        "assigned_clients": state.assigned_clients,
        "speed_multiplier": state.speed_multiplier,
        "vehicle_capacity": state.vehicle_capacity,
        "num_vehicles": state.num_vehicles,
    }


def get_point_latlon(df: pd.DataFrame, point_id: int, graph=None) -> tuple[float, float]:
    if point_id == 0:
        depot = df[df["id"] == 0].iloc[0]
        return float(depot["lat"]), float(depot["lon"])
    row = df[df["id"] == point_id]
    if row.empty:
        if graph is not None and point_id in graph.nodes:
            node_data = graph.nodes[point_id]
            return float(node_data["y"]), float(node_data["x"])
        raise KeyError(f"Point {point_id} introuvable")
    return float(row.iloc[0]["lat"]), float(row.iloc[0]["lon"])


def build_human_live_stats(
    df: pd.DataFrame,
    graph,
    state: HumanState,
    weather_factor: float,
    departure_time: str = DEFAULT_DEPARTURE_TIME,
) -> dict:
    time_factor = weather_factor / max(state.speed_multiplier, 0.1)
    departure_time_s = parse_clock_to_seconds(departure_time)
    points_data = {int(row["id"]): row.to_dict() for _, row in df.iterrows()}
    stats: dict[str, dict] = {}
    for sleigh_id in range(state.num_vehicles):
        key = str(sleigh_id)
        route_ids = state.routes_by_sleigh.get(key, [])
        segments = state.segments_by_sleigh.get(key, [])
        dist_m = 0.0
        base_time_s = 0.0
        for segment in segments:
            dist_m += float(segment.get("dist_m", 0.0))
            base_time_s += float(segment.get("base_time_s", segment.get("time_s", 0.0)))
        load_kg = float(df[df["id"].isin(route_ids)]["poids_colis"].sum()) if route_ids else 0.0
        return_dist_m = 0.0
        return_time_s = 0.0
        return_segment = None
        if route_ids:
            lat, lon = get_point_latlon(df, int(route_ids[-1]), graph=graph)
            depot_lat, depot_lon = get_point_latlon(df, 0, graph=graph)
            back_options = compute_route_options(graph, lat, lon, depot_lat, depot_lon, time_factor=1.0, k=1)
            if back_options:
                return_dist_m = float(back_options[0]["dist_m"])
                return_time_s = float(back_options[0]["base_time_s"])
                return_segment = {
                    "variant": "human-return",
                    "sleigh_id": sleigh_id,
                    "from_id": int(route_ids[-1]),
                    "to_id": 0,
                    "route_nodes": back_options[0]["route_nodes"],
                    "geometry": back_options[0]["geometry"],
                    "dist_m": return_dist_m,
                    "time_s": return_time_s * time_factor,
                    "base_time_s": return_time_s,
                    "arrival_eta_s": (base_time_s + return_time_s) * time_factor,
                    "arrival_clock": format_clock(departure_time_s + (base_time_s + return_time_s) * time_factor),
                    "segment_idx": len(route_ids) + 1,
                    "segment_count": len(route_ids) + 1,
                    "title": (
                        f"Retour depot · Traineau #{sleigh_id + 1} · "
                        f"{point_label(points_data, int(route_ids[-1]))} -> Depot"
                    ),
                }
        stats[key] = {
            "stops": len(route_ids),
            "load_kg": load_kg,
            "over_kg": max(0.0, load_kg - state.vehicle_capacity),
            "dist_m": dist_m + return_dist_m,
            "time_s": (base_time_s + return_time_s) * time_factor,
            "return_dist_m": return_dist_m,
            "return_time_s": return_time_s * time_factor,
            "return_arrival_clock": (
                format_clock(departure_time_s + (base_time_s + return_time_s) * time_factor) if route_ids else None
            ),
            "return_segment": return_segment,
        }
    return stats


def build_human_eta_payload(
    df: pd.DataFrame,
    state: HumanState,
    weather_factor: float,
    departure_time: str = DEFAULT_DEPARTURE_TIME,
) -> tuple[dict[str, list[dict]], dict[int, dict]]:
    time_factor = weather_factor / max(state.speed_multiplier, 0.1)
    departure_time_s = parse_clock_to_seconds(departure_time)
    points_data = {int(row["id"]): row.to_dict() for _, row in df.iterrows()}
    segments_by_sleigh: dict[str, list[dict]] = {}
    stop_meta_by_client: dict[int, dict] = {}
    for sleigh_id in range(state.num_vehicles):
        key = str(sleigh_id)
        source_segments = state.segments_by_sleigh.get(key, [])
        cumulative_eta_s = 0.0
        stop_order = 0
        enriched_segments: list[dict] = []
        for index, segment in enumerate(source_segments):
            adjusted_time_s = float(segment.get("base_time_s", segment.get("time_s", 0.0))) * time_factor
            cumulative_eta_s += adjusted_time_s
            arrival_clock = format_clock(departure_time_s + cumulative_eta_s)
            enriched = {
                **segment,
                "variant": "human",
                "sleigh_id": int(segment.get("sleigh_id", sleigh_id)),
                "time_s": adjusted_time_s,
                "arrival_eta_s": cumulative_eta_s,
                "arrival_clock": arrival_clock,
                "segment_idx": index + 1,
                "segment_count": len(source_segments),
                "title": segment.get("title")
                or (
                    f"Traineau #{sleigh_id + 1} · "
                    f"{point_label(points_data, int(segment.get('from_id', 0)))} -> "
                    f"{point_label(points_data, int(segment.get('to_id', 0)))}"
                ),
            }
            enriched_segments.append(enriched)
            to_id = int(segment.get("to_id", 0))
            if to_id != 0:
                stop_order += 1
                stop_meta_by_client[to_id] = {
                    "sleigh_id": sleigh_id,
                    "stop_order": stop_order,
                    "arrival_eta_s": cumulative_eta_s,
                    "arrival_clock": arrival_clock,
                }
        segments_by_sleigh[key] = enriched_segments
    return segments_by_sleigh, stop_meta_by_client


def build_ai_payload(
    df: pd.DataFrame,
    graph,
    results: dict,
    departure_time: str = DEFAULT_DEPARTURE_TIME,
) -> tuple[list[dict], dict[int, dict]]:
    points_data = {int(row["id"]): row.to_dict() for _, row in df.iterrows()}
    departure_time_s = parse_clock_to_seconds(departure_time)
    ai_segments: list[dict] = []
    ai_stop_meta: dict[int, dict] = {}
    for index, tour in enumerate(results.get("tours", [])):
        vehicle_id = int(tour.get("vehicle_id", index))
        route_ids = [int(route_id) for route_id in tour.get("route_ids", [])]
        segment_infos = []
        heuristic = _make_haversine_heuristic(graph)
        for segment_idx in range(len(route_ids) - 1):
            from_id, to_id = route_ids[segment_idx], route_ids[segment_idx + 1]
            from_lat, from_lon = get_point_latlon(df, from_id)
            to_lat, to_lon = get_point_latlon(df, to_id)
            src = ox.nearest_nodes(graph, from_lon, from_lat)
            dst = ox.nearest_nodes(graph, to_lon, to_lat)
            try:
                route = nx.astar_path(graph, src, dst, heuristic=heuristic, weight="travel_time")
            except Exception:
                route = nx.shortest_path(graph, src, dst, weight="travel_time")
            segment_infos.append(
                {
                    "sleigh_id": vehicle_id,
                    "from_id": from_id,
                    "to_id": to_id,
                    "route_nodes": route,
                    "geometry": route_to_geometry(graph, route),
                    "dist_m": route_length_m(graph, route),
                    "base_time_s": route_time_s(graph, route),
                    "title": f"Traineau #{vehicle_id + 1} · {point_label(points_data, from_id)} -> {point_label(points_data, to_id)}",
                    "segment_idx": segment_idx + 1,
                    "segment_count": max(0, len(route_ids) - 1),
                }
            )
        total_base_time_s = sum(segment["base_time_s"] for segment in segment_infos)
        target_tour_time_s = float(tour.get("duration_s", total_base_time_s))
        scale = (target_tour_time_s / total_base_time_s) if total_base_time_s > 0 else 1.0
        cumulative_eta_s = 0.0
        stop_order = 0
        for segment in segment_infos:
            adjusted_time_s = float(segment["base_time_s"]) * scale
            cumulative_eta_s += adjusted_time_s
            arrival_clock = format_clock(departure_time_s + cumulative_eta_s)
            payload = {
                "variant": "ai",
                "sleigh_id": segment["sleigh_id"],
                "from_id": segment["from_id"],
                "to_id": segment["to_id"],
                "route_nodes": segment["route_nodes"],
                "geometry": segment["geometry"],
                "dist_m": segment["dist_m"],
                "time_s": adjusted_time_s,
                "arrival_eta_s": cumulative_eta_s,
                "arrival_clock": arrival_clock,
                "title": segment["title"],
                "segment_idx": segment["segment_idx"],
                "segment_count": segment["segment_count"],
            }
            ai_segments.append(payload)
            if segment["to_id"] != 0:
                stop_order += 1
                ai_stop_meta[int(segment["to_id"])] = {
                    "vehicle_id": segment["sleigh_id"],
                    "stop_order": stop_order,
                    "arrival_eta_s": cumulative_eta_s,
                    "arrival_clock": arrival_clock,
                }
    return ai_segments, ai_stop_meta


def summarize_segments(segments: list[dict]) -> dict:
    return {
        "total_dist_m": float(sum(float(segment.get("dist_m", 0.0)) for segment in segments)),
        "total_time_s": float(sum(float(segment.get("time_s", 0.0)) for segment in segments)),
        "segment_count": len(segments),
    }
