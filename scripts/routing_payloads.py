from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

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


def compute_route_options(
    graph,
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    time_factor: float = 1.0,
    k: int = 3,
) -> list[dict]:
    origin = ox.distance.nearest_nodes(graph, X=float(from_lon), Y=float(from_lat))
    dest = ox.distance.nearest_nodes(graph, X=float(to_lon), Y=float(to_lat))
    routes: list[list[int]] = []
    try:
        fastest = ox.routing.shortest_path(graph, origin, dest, weight="travel_time")
        if fastest:
            routes.append(fastest)
    except Exception:
        pass
    try:
        routes.extend(list(islice(ox.routing.k_shortest_paths(graph, origin, dest, k, weight="length"), k)))
    except Exception:
        pass
    if not routes:
        fallback = ox.routing.shortest_path(graph, origin, dest, weight="length")
        routes = [fallback] if fallback else []

    options = []
    seen: set[tuple[int, ...]] = set()
    for route in routes:
        if not route:
            continue
        route_key = tuple(route)
        if route_key in seen:
            continue
        seen.add(route_key)
        base_time_s = route_time_s(graph, route)
        options.append(
            {
                "route_nodes": route,
                "geometry": route_to_geometry(graph, route),
                "dist_m": route_length_m(graph, route),
                "base_time_s": base_time_s,
                "time_s": base_time_s * time_factor,
            }
        )
    options.sort(key=lambda item: (item["time_s"], item["dist_m"]))
    fastest_idx = min(range(len(options)), key=lambda idx: options[idx]["time_s"]) if options else 0
    shortest_idx = min(range(len(options)), key=lambda idx: options[idx]["dist_m"]) if options else 0
    for idx, option in enumerate(options):
        tags = []
        if idx == fastest_idx:
            tags.append("Plus rapide")
        if idx == shortest_idx:
            tags.append("Plus court")
        if not tags:
            tags.append(f"Alternative {idx + 1}")
        option["label"] = f"{' / '.join(tags)} · {_format_minutes(option['time_s'])} · {option['dist_m'] / 1000:.2f} km"
    return options[:k]


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


def get_point_latlon(df: pd.DataFrame, point_id: int) -> tuple[float, float]:
    if point_id == 0:
        depot = df[df["id"] == 0].iloc[0]
        return float(depot["lat"]), float(depot["lon"])
    row = df[df["id"] == point_id]
    if row.empty:
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
            lat, lon = get_point_latlon(df, int(route_ids[-1]))
            depot_lat, depot_lon = get_point_latlon(df, 0)
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
        for segment_idx in range(len(route_ids) - 1):
            from_id, to_id = route_ids[segment_idx], route_ids[segment_idx + 1]
            from_lat, from_lon = get_point_latlon(df, from_id)
            to_lat, to_lon = get_point_latlon(df, to_id)
            route = nx.shortest_path(
                graph,
                ox.nearest_nodes(graph, from_lon, from_lat),
                ox.nearest_nodes(graph, to_lon, to_lat),
                weight="travel_time",
            )
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
