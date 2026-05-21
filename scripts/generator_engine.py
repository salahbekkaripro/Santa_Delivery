import osmnx as ox
import pandas as pd
import random
import os
import json
import math
import numpy as np
import requests
import networkx as nx

# ---------------------------------------------------------------------------
# Profil de congestion horaire (facteur multiplicatif sur la durée de trajet)
# ---------------------------------------------------------------------------
TRAFFIC_PROFILE: dict[int, float] = {
    7: 1.4, 8: 1.7, 9: 1.5, 10: 1.1, 11: 1.0, 12: 1.2,
    13: 1.3, 14: 1.1, 15: 1.0, 16: 1.1, 17: 1.6, 18: 1.8,
    19: 1.4, 20: 1.1,
}

# ---------------------------------------------------------------------------
# Catégories de cargaison
# ---------------------------------------------------------------------------
CARGO_CATEGORIES = [
    {"code": "normal",    "label": "Colis standard", "emoji": "📦", "weight_factor": 1.0, "constraint": None},
    {"code": "fragile",   "label": "Fragile",        "emoji": "🔮", "weight_factor": 0.8, "constraint": "slow"},
    {"code": "refrigere", "label": "Réfrigéré",      "emoji": "🧊", "weight_factor": 1.0, "constraint": "time_window_strict"},
    {"code": "gros",      "label": "Encombrant",     "emoji": "🛋️", "weight_factor": 1.5, "constraint": "capacity"},
]
_CARGO_WEIGHTS = [0.60, 0.20, 0.10, 0.10]

# Configuration des chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CORE_DATA = os.path.join(BASE_DIR, 'core_data')
DATA_PATH = os.path.join(CORE_DATA, 'livraisons_5eme.csv') # On garde le même nom pour compatibilité ou on change ? On va garder le même pour l'instant mais on pourrait le rendre dynamique
GRAPH_PATH = os.path.join(CORE_DATA, 'paris5.graphml')
TIME_MATRIX = os.path.join(CORE_DATA, 'live_time_matrix.npy')
DIST_MATRIX = os.path.join(CORE_DATA, 'matrix_5eme.npy')
CO2_MATRIX = os.path.join(CORE_DATA, 'co2_matrix.npy')
RISK_MATRIX = os.path.join(CORE_DATA, 'risk_matrix.npy')
COMPOSITE_MATRIX = os.path.join(CORE_DATA, 'composite_cost_matrix.npy')
MODAL_PROFILE = os.path.join(CORE_DATA, 'multimodal_profile.json')

SUPPORTED_TRANSPORT_MODES = ("drive", "bike", "walk")
DEFAULT_OBJECTIVE_WEIGHTS = {
    "time": 0.55,
    "distance": 0.20,
    "co2": 0.15,
    "risk": 0.10,
}

MODE_BASE_SPEED_KPH = {
    "drive": 35.0,
    "bike": 18.0,
    "walk": 5.0,
}
MODE_CO2_G_PER_KM = {
    "drive": 120.0,
    "bike": 8.0,
    "walk": 0.0,
}
ADEME_TRANSPORT_ID_BY_MODE = {
    "drive": 4,   # Voiture thermique
    "bike": 7,    # Vélo mécanique
    "walk": 30,   # Marche
}
ADEME_CO2_API_URL = os.getenv("NOEL_ADEME_CO2_API_URL", "https://impactco2.fr/api/v1/transport").strip()
ADEME_CO2_TIMEOUT_S = float(os.getenv("NOEL_ADEME_CO2_TIMEOUT_S", "8.0"))
HIGHWAY_DEFAULT_SPEED_KPH = {
    "motorway": 110.0,
    "trunk": 90.0,
    "primary": 70.0,
    "secondary": 60.0,
    "tertiary": 50.0,
    "residential": 30.0,
    "living_street": 20.0,
    "service": 20.0,
}
HIGHWAY_RISK_FACTOR = {
    "motorway": 1.8,
    "trunk": 1.6,
    "primary": 1.45,
    "secondary": 1.30,
    "tertiary": 1.20,
    "residential": 0.90,
    "living_street": 0.75,
    "service": 0.85,
    "cycleway": 0.55,
    "footway": 0.45,
    "path": 0.60,
    "pedestrian": 0.50,
}


def _as_highway_str(raw_highway) -> str:
    if isinstance(raw_highway, (list, tuple, set)):
        return str(next(iter(raw_highway), "residential")).strip().lower()
    return str(raw_highway or "residential").strip().lower()


def _parse_speed_kph(maxspeed_raw) -> float | None:
    if maxspeed_raw is None:
        return None
    if isinstance(maxspeed_raw, (list, tuple, set)):
        for item in maxspeed_raw:
            parsed = _parse_speed_kph(item)
            if parsed is not None:
                return parsed
        return None
    token = str(maxspeed_raw).strip().lower()
    if not token:
        return None
    parts = token.replace(",", ".").split()
    value = None
    for part in parts:
        try:
            value = float(part)
            break
        except Exception:
            continue
    if value is None:
        return None
    if "mph" in token:
        value *= 1.60934
    if value <= 0:
        return None
    return float(value)


def _normalize_objective_weights(raw_weights: dict | None) -> dict[str, float]:
    if not isinstance(raw_weights, dict):
        return dict(DEFAULT_OBJECTIVE_WEIGHTS)
    normalized: dict[str, float] = {}
    for key in ("time", "distance", "co2", "risk"):
        value = raw_weights.get(key, DEFAULT_OBJECTIVE_WEIGHTS[key])
        try:
            parsed = max(0.0, float(value))
        except Exception:
            parsed = float(DEFAULT_OBJECTIVE_WEIGHTS[key])
        normalized[key] = parsed
    total = sum(normalized.values())
    if total <= 1e-9:
        return dict(DEFAULT_OBJECTIVE_WEIGHTS)
    return {k: v / total for k, v in normalized.items()}


def _annotate_multimodal_edges(graph: nx.MultiDiGraph, mode: str) -> nx.MultiDiGraph:
    mode = str(mode or "drive").strip().lower()
    if mode not in SUPPORTED_TRANSPORT_MODES:
        mode = "drive"
    default_speed = MODE_BASE_SPEED_KPH[mode]
    mode_co2 = MODE_CO2_G_PER_KM[mode]

    for u, v, key, data in graph.edges(keys=True, data=True):
        length_m = float(data.get("length", 0.0) or 0.0)
        if length_m <= 0.0:
            src = graph.nodes.get(u, {})
            dst = graph.nodes.get(v, {})
            if "x" in src and "y" in src and "x" in dst and "y" in dst:
                length_m = _haversine_m(float(src["y"]), float(src["x"]), float(dst["y"]), float(dst["x"]))
            else:
                length_m = 1.0
        highway = _as_highway_str(data.get("highway"))
        maxspeed = _parse_speed_kph(data.get("maxspeed"))

        if mode == "drive":
            speed_kph = maxspeed if maxspeed is not None else HIGHWAY_DEFAULT_SPEED_KPH.get(highway, default_speed)
        elif mode == "bike":
            speed_kph = min(max(10.0, default_speed), 25.0)
        else:
            speed_kph = min(max(3.0, default_speed), 6.5)

        speed_m_s = max(0.8, float(speed_kph) * (1000.0 / 3600.0))
        travel_time_s = length_m / speed_m_s
        co2_g = (length_m / 1000.0) * mode_co2
        risk_base = HIGHWAY_RISK_FACTOR.get(highway, 1.0)
        oneway = str(data.get("oneway", "")).strip().lower() in {"yes", "true", "1"}
        oneway_penalty = 1.08 if oneway and mode in {"bike", "walk"} else 1.0
        risk_score = (length_m / 1000.0) * risk_base * oneway_penalty

        data["transport_mode"] = mode
        data["speed_kph_legal"] = round(float(speed_kph), 3)
        data["travel_time"] = float(travel_time_s)
        data["co2_g"] = float(co2_g)
        data["risk_score"] = float(risk_score)
        data["oneway_effective"] = bool(oneway)
        data["length"] = float(length_m)
        graph.edges[u, v, key].update(data)
    return graph


def _build_multimodal_union_graph(mode_graphs: dict[str, nx.MultiDiGraph]) -> nx.MultiDiGraph:
    if not mode_graphs:
        raise ValueError("mode_graphs vide")
    ordered_graphs = [mode_graphs[m] for m in SUPPORTED_TRANSPORT_MODES if m in mode_graphs]
    union_graph = nx.compose_all(ordered_graphs)
    union_graph.graph["multimodal"] = True
    union_graph.graph["available_modes"] = [m for m in SUPPORTED_TRANSPORT_MODES if m in mode_graphs]
    return union_graph

def _fetch_overpass_pois(lat: float, lon: float, radius_m: int = 1500, max_results: int = 200) -> list[str]:
    """Fetch real POI names from OpenStreetMap via Overpass API.
    Tries multiple public endpoints to reduce transient 406/429 failures.
    """
    query = (
        "[out:json][timeout:20];"
        "("
        f'node(around:{int(radius_m)},{float(lat)},{float(lon)})["name"]["shop"];'
        f'way(around:{int(radius_m)},{float(lat)},{float(lon)})["name"]["shop"];'
        f'node(around:{int(radius_m)},{float(lat)},{float(lon)})["name"]["amenity"];'
        f'way(around:{int(radius_m)},{float(lat)},{float(lon)})["name"]["amenity"];'
        f'node(around:{int(radius_m)},{float(lat)},{float(lon)})["name"]["tourism"];'
        f'way(around:{int(radius_m)},{float(lat)},{float(lon)})["name"]["tourism"];'
        ");"
        f"out tags {int(max_results)};"
    )
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]
    headers = {
        "User-Agent": "NoelGraphes/1.0 (academic project)",
        "Accept": "application/json",
    }
    last_error = None
    for endpoint in endpoints:
        try:
            response = requests.post(
                endpoint,
                data={"data": query},
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            elements = payload.get("elements", [])
            names = [
                str(el["tags"]["name"]).strip()
                for el in elements
                if isinstance(el, dict)
                and isinstance(el.get("tags"), dict)
                and el["tags"].get("name")
            ]
            unique = list(dict.fromkeys(names))
            if unique:
                return unique[:max_results]
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        print(f"⚠️ Overpass API indisponible : {last_error}")
    return []


def apply_traffic_factor(durations: np.ndarray, departure_hour: int) -> np.ndarray:
    """Apply hourly congestion multiplier to a duration matrix."""
    factor = TRAFFIC_PROFILE.get(int(departure_hour), 1.0)
    return durations * factor


def _fallback_dist_m(num_clients: int) -> int:
    # Distance en mètres pour graph_from_point si la géométrie d'un lieu est
    # trop petite / invalide (ou ne contient aucun axe "drive").
    # Ajusté pour fournir suffisamment de nœuds même à 50-100 clients.
    return int(min(8000, max(1500, 800 + num_clients * 40)))


def _build_co2_matrix_from_distance(distance_matrix: np.ndarray, factor_g_per_km: float) -> np.ndarray:
    matrix = np.full(distance_matrix.shape, 1e9, dtype=float)
    finite_mask = np.isfinite(distance_matrix) & (distance_matrix < 1e8)
    matrix[finite_mask] = (distance_matrix[finite_mask] / 1000.0) * max(0.0, float(factor_g_per_km))
    np.fill_diagonal(matrix, 0.0)
    return matrix


def _resolve_ademe_transport_id(mode: str, requested_id: int | None) -> int:
    if requested_id is not None:
        return int(requested_id)
    return int(ADEME_TRANSPORT_ID_BY_MODE.get(str(mode or "drive").strip().lower(), 4))


def _extract_ademe_kgco2e(item: dict) -> float:
    value = item.get("value")
    if value is not None:
        return float(value)
    emissions = item.get("emissions")
    if isinstance(emissions, dict):
        if emissions.get("kgco2e") is not None:
            return float(emissions["kgco2e"])
        if emissions.get("gco2e") is not None:
            return float(emissions["gco2e"]) / 1000.0
    raise ValueError("Réponse ADEME invalide (champ CO2 manquant).")


def _fetch_ademe_factor_g_per_km(transport_id: int) -> tuple[float | None, dict]:
    requested_km = 1.0
    key = (
        os.getenv("NOEL_ADEME_CO2_API_KEY")
        or os.getenv("ADEME_API_KEY")
        or os.getenv("HERE_API_KEY")
        or ""
    ).strip()
    headers = {
        "Accept": "application/json",
        "User-Agent": "NoelGraphes/1.0",
    }
    if key:
        headers["x-api-key"] = key
        headers["Authorization"] = f"Bearer {key}"
    meta = {
        "enabled": True,
        "provider": "ademe_impact_co2",
        "endpoint": ADEME_CO2_API_URL,
        "transport_id": int(transport_id),
        "api_key_supplied": bool(key),
    }
    try:
        response = requests.get(
            ADEME_CO2_API_URL,
            params={
                "km": requested_km,
                "transports": int(transport_id),
                "displayAll": 0,
            },
            headers=headers,
            timeout=max(1.0, float(ADEME_CO2_TIMEOUT_S)),
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise ValueError("Réponse ADEME sans données transport.")
        selected = None
        for item in data:
            try:
                if int(item.get("id")) == int(transport_id):
                    selected = item
                    break
            except Exception:
                continue
        if selected is None:
            selected = data[0]
        kgco2e = _extract_ademe_kgco2e(selected)
        factor = (float(kgco2e) * 1000.0) / requested_km
        meta.update(
            {
                "selected_transport_id": int(selected.get("id", transport_id)),
                "selected_transport_name": str(selected.get("name", f"transport_{transport_id}")),
                "factor_g_per_km": float(factor),
                "status": "ok",
            }
        )
        return float(factor), meta
    except Exception as exc:
        meta.update(
            {
                "status": "fallback_local",
                "error": str(exc),
            }
        )
        return None, meta

def _prepare_graph(G, min_nodes: int):
    """
    Réduit le graphe au plus grand composant connecté pour éviter des paires
    inatteignables lors du calcul local des matrices.
    """
    try:
        Gs = ox.truncate.largest_component(G, strongly=True)
        if len(Gs.nodes) >= min_nodes:
            return Gs
    except Exception:
        pass
    try:
        Gw = ox.truncate.largest_component(G, strongly=False)
        if len(Gw.nodes) >= min_nodes:
            return Gw
    except Exception:
        pass
    return G


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * earth_radius_m * math.asin(math.sqrt(a))


def _select_depot_and_clients(
    nodes: list[tuple[int, dict]],
    num_clients: int,
    center_lat: float | None = None,
    center_lon: float | None = None,
) -> tuple[tuple[int, dict], list[tuple[int, dict]]]:
    if len(nodes) < int(num_clients) + 1:
        raise ValueError("Not enough nodes to select depot and clients")

    if center_lat is not None and center_lon is not None:
        depot_node = min(
            nodes,
            key=lambda node: _haversine_m(float(center_lat), float(center_lon), float(node[1]["y"]), float(node[1]["x"])),
        )
        remaining_nodes = [node for node in nodes if int(node[0]) != int(depot_node[0])]
        if len(remaining_nodes) < int(num_clients):
            raise ValueError("Not enough client nodes after depot selection")
        clients_nodes = random.sample(remaining_nodes, int(num_clients))
        return depot_node, clients_nodes

    selected_nodes = random.sample(nodes, int(num_clients) + 1)
    depot_node = selected_nodes[0]
    clients_nodes = selected_nodes[1:]
    return depot_node, clients_nodes


def _compute_matrices_local(
    graph: nx.MultiDiGraph,
    node_ids: list[int],
    *,
    weights: tuple[str, ...] = ("travel_time", "length", "co2_g", "risk_score"),
) -> dict[str, np.ndarray]:
    """Calcule des matrices de plus court chemin sur un graphe local."""
    if not node_ids:
        raise ValueError("node_ids vide")

    n = len(node_ids)
    matrices: dict[str, np.ndarray] = {
        weight: np.full((n, n), 1e9, dtype=float)
        for weight in weights
    }
    for matrix in matrices.values():
        np.fill_diagonal(matrix, 0.0)

    for i, origin in enumerate(node_ids):
        for weight in weights:
            shortest = nx.single_source_dijkstra_path_length(graph, origin, weight=weight)
            matrix = matrices[weight]
            for j, dest in enumerate(node_ids):
                if dest in shortest:
                    matrix[i, j] = float(shortest[dest])
    return matrices


def _infer_edge_metric_value(
    graph: nx.MultiDiGraph,
    source: int,
    target: int,
    metric: str,
    mode: str,
) -> float:
    edge_bundle = graph.get_edge_data(source, target, default={})
    if not edge_bundle:
        return 1e9
    best = 1e9
    for data in edge_bundle.values():
        value = data.get(metric)
        if value is None:
            length_m = float(data.get("length", 0.0) or 0.0)
            if metric == "travel_time":
                speed_kph = float(data.get("speed_kph_legal", MODE_BASE_SPEED_KPH.get(mode, 30.0)))
                speed_m_s = max(0.8, speed_kph * (1000.0 / 3600.0))
                value = length_m / speed_m_s
            elif metric == "co2_g":
                value = (length_m / 1000.0) * MODE_CO2_G_PER_KM.get(mode, 120.0)
            elif metric == "risk_score":
                highway = _as_highway_str(data.get("highway"))
                value = (length_m / 1000.0) * HIGHWAY_RISK_FACTOR.get(highway, 1.0)
            else:
                value = length_m
        value = float(value)
        if value < best:
            best = value
    return best


def _compute_multimodal_matrices(
    mode_graphs: dict[str, nx.MultiDiGraph],
    node_ids_by_mode: dict[str, list[int]],
) -> dict[str, np.ndarray]:
    """Fusionne les coûts des modes disponibles par minimum inter-mode."""
    if not mode_graphs:
        raise ValueError("Aucun graphe modal disponible")
    reference_mode = "drive" if "drive" in mode_graphs else next(iter(mode_graphs.keys()))
    reference_nodes = node_ids_by_mode[reference_mode]
    n = len(reference_nodes)
    if n == 0:
        raise ValueError("Aucun noeud modal")

    modal_mats: dict[str, dict[str, np.ndarray]] = {}
    for mode, graph in mode_graphs.items():
        modal_mats[mode] = _compute_matrices_local(graph, node_ids_by_mode[mode])

    idx_by_mode: dict[str, dict[int, int]] = {
        mode: {int(node): idx for idx, node in enumerate(nodes)}
        for mode, nodes in node_ids_by_mode.items()
    }

    merged = {
        "travel_time": np.full((n, n), 1e9, dtype=float),
        "length": np.full((n, n), 1e9, dtype=float),
        "co2_g": np.full((n, n), 1e9, dtype=float),
        "risk_score": np.full((n, n), 1e9, dtype=float),
    }
    for matrix in merged.values():
        np.fill_diagonal(matrix, 0.0)

    for i, source in enumerate(reference_nodes):
        for j, target in enumerate(reference_nodes):
            if i == j:
                continue
            for mode, graph in mode_graphs.items():
                mode_idx = idx_by_mode[mode]
                if int(source) in mode_idx and int(target) in mode_idx:
                    si = mode_idx[int(source)]
                    ti = mode_idx[int(target)]
                    for metric in merged:
                        value = float(modal_mats[mode][metric][si, ti])
                        if value < merged[metric][i, j]:
                            merged[metric][i, j] = value
                    continue

                try:
                    route = nx.shortest_path(graph, int(source), int(target), weight="travel_time")
                except Exception:
                    route = None
                if not route or len(route) < 2:
                    continue
                metric_values = {metric: 0.0 for metric in merged}
                for u, v in zip(route[:-1], route[1:]):
                    for metric in merged:
                        metric_values[metric] += _infer_edge_metric_value(graph, int(u), int(v), metric, mode)
                for metric in merged:
                    if metric_values[metric] < merged[metric][i, j]:
                        merged[metric][i, j] = metric_values[metric]
    return merged


def _robust_scale(matrix: np.ndarray) -> np.ndarray:
    positive = matrix[np.isfinite(matrix) & (matrix > 0)]
    if positive.size == 0:
        return np.zeros_like(matrix)
    scale = float(np.median(positive))
    if scale <= 1e-9:
        scale = float(np.mean(positive))
    if scale <= 1e-9:
        scale = 1.0
    scaled = matrix / scale
    scaled[~np.isfinite(scaled)] = 1e9
    return scaled


def _build_composite_cost_matrix(
    time_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    co2_matrix: np.ndarray,
    risk_matrix: np.ndarray,
    weights: dict[str, float],
) -> np.ndarray:
    w = _normalize_objective_weights(weights)
    time_scaled = _robust_scale(time_matrix)
    dist_scaled = _robust_scale(dist_matrix)
    co2_scaled = _robust_scale(co2_matrix)
    risk_scaled = _robust_scale(risk_matrix)
    composite = (
        w["time"] * time_scaled
        + w["distance"] * dist_scaled
        + w["co2"] * co2_scaled
        + w["risk"] * risk_scaled
    )
    composite[~np.isfinite(composite)] = 1e9
    np.fill_diagonal(composite, 0.0)
    return composite


def _save_mode_matrices(
    mode_mats: dict[str, dict[str, np.ndarray]],
    base_dir: str,
) -> dict[str, dict[str, str]]:
    os.makedirs(base_dir, exist_ok=True)
    saved: dict[str, dict[str, str]] = {}
    for mode, mats in mode_mats.items():
        mode_saved: dict[str, str] = {}
        for metric, matrix in mats.items():
            filename = f"{mode}_{metric}.npy"
            output_path = os.path.join(base_dir, filename)
            np.save(output_path, matrix)
            mode_saved[metric] = output_path
        saved[mode] = mode_saved
    return saved


def _apply_elevation_if_needed(
    time_matrix: np.ndarray,
    dist_matrix: np.ndarray,
    locations: list,
    with_elevation: bool,
    elevation_path: str | None,
) -> dict | None:
    """
    Si with_elevation=True, récupère les altitudes SRTM et ajuste les matrices
    en place (modifie les tableaux numpy passés en argument).
    Sauvegarde les métadonnées dans elevation_path si fourni.
    Retourne le résumé ou None.
    """
    if not with_elevation:
        return None
    try:
        from scripts.elevation_engine import fetch_elevations, apply_slope_to_matrices, elevation_summary
        print(f"🏔️  Récupération altitudes SRTM pour {len(locations)} points...")
        elevations = fetch_elevations(locations)
        time_slope, dist_energy, elev_diff = apply_slope_to_matrices(
            time_matrix, dist_matrix, locations, elevations
        )
        # Modifie en place
        time_matrix[:] = time_slope
        dist_matrix[:] = dist_energy

        meta = elevation_summary(elevations, elev_diff, locations)
        print(
            f"🏔️  Relief intégré : terrain={meta['terrain_type']}, "
            f"alt {meta['min_m']}–{meta['max_m']} m, "
            f"D+ {meta['total_climb_m']} m, surcoût temps ≈+{meta['time_overhead_pct']}%"
        )
        if elevation_path:
            import json as _json
            os.makedirs(os.path.dirname(elevation_path), exist_ok=True)
            with open(elevation_path, "w", encoding="utf-8") as f:
                _json.dump(meta, f, ensure_ascii=False)
        return meta
    except Exception as exc:
        print(f"⚠️  Elevation ignorée : {exc}")
        return None


def generate_new_zone(
    location_name,
    num_clients=30,
    data_path=DATA_PATH,
    graph_path=GRAPH_PATH,
    time_matrix_path=TIME_MATRIX,
    dist_matrix_path=DIST_MATRIX,
    co2_matrix_path=CO2_MATRIX,
    risk_matrix_path=RISK_MATRIX,
    composite_matrix_path=COMPOSITE_MATRIX,
    multimodal_profile_path=MODAL_PROFILE,
    center_lat=None,
    center_lon=None,
    search_radius_km=None,
    departure_hour=None,
    with_elevation=False,
    elevation_path=None,
    transport_mode="drive",
    objective_weights=None,
    use_ademe_co2=False,
    ademe_transport_id=None,
):
    """
    Télécharge une nouvelle zone et génère des points de livraison.

    Retourne:
      - (True, "") si OK
      - (False, "message") si échec (message actionnable pour l'UI)
    """
    print(f"📍 Génération de la zone : {location_name}...")
    
    # 1. Téléchargement du graphe multimodal
    explicit_center = center_lat is not None and center_lon is not None and search_radius_km is not None
    normalized_mode = str(transport_mode or "drive").strip().lower()
    if normalized_mode not in {*SUPPORTED_TRANSPORT_MODES, "multimodal"}:
        normalized_mode = "drive"
    requested_modes = list(SUPPORTED_TRANSPORT_MODES) if normalized_mode == "multimodal" else [normalized_mode]
    objective_weights = _normalize_objective_weights(objective_weights)

    mode_graphs: dict[str, nx.MultiDiGraph] = {}
    try:
        for mode in requested_modes:
            if explicit_center:
                dist_m = max(200, int(float(search_radius_km) * 1000))
                center = (float(center_lat), float(center_lon))
                print(f"📌 Zone cible: centre={center} rayon={search_radius_km} km · mode={mode}")
                graph = ox.graph_from_point(center, dist=dist_m, network_type=mode)
            else:
                graph = ox.graph_from_place(location_name, network_type=mode)
            graph = _prepare_graph(graph, int(num_clients) + 1)
            graph = _annotate_multimodal_edges(graph, mode)
            mode_graphs[mode] = graph
        if not mode_graphs:
            raise RuntimeError("Aucun graphe modal récupéré")
        G = _build_multimodal_union_graph(mode_graphs)
        os.makedirs(os.path.dirname(graph_path), exist_ok=True)
        ox.save_graphml(G, graph_path)
        print(
            f"✅ Graphe multimodal téléchargé pour '{location_name}' "
            f"(modes: {', '.join(sorted(mode_graphs.keys()))})."
        )
    except Exception as e:
        msg = str(e)
        print(f"⚠️ OSM (initial) impossible : {msg}")

        if explicit_center:
            return (
                False,
                "Impossible de charger la zone circulaire demandee. "
                "Essayez un rayon plus grand ou une autre ville.\n"
                f"Detail: {msg}",
            )

        # Cas fréquent: le polygon renvoyé par le géocodeur ne contient aucun nœud "drive"
        # => fallback sur un graphe autour d'un point (plus robuste).
        try:
            center = ox.geocode(location_name)  # (lat, lon)
            dist_m = _fallback_dist_m(int(num_clients))
            for mode in requested_modes:
                print(f"↪️ Fallback: graph_from_point({center}, dist={dist_m}m, mode={mode})")
                graph = ox.graph_from_point(center, dist=dist_m, network_type=mode)
                graph = _prepare_graph(graph, int(num_clients) + 1)
                graph = _annotate_multimodal_edges(graph, mode)
                mode_graphs[mode] = graph
            if not mode_graphs:
                raise RuntimeError("Fallback multimodal vide")
            G = _build_multimodal_union_graph(mode_graphs)
            os.makedirs(os.path.dirname(graph_path), exist_ok=True)
            ox.save_graphml(G, graph_path)
            print(
                f"✅ Graphe multimodal (fallback point) téléchargé pour '{location_name}' "
                f"(modes: {', '.join(sorted(mode_graphs.keys()))})."
            )
        except Exception as e2:
            msg2 = str(e2)
            print(f"❌ Fallback OSM échoué : {msg2}")
            hint = (
                "OSM: aucun axe routier trouvé pour cette zone. "
                "Essayez un nom plus précis (ex: 'Le Plateau-Mont-Royal, Montréal, Québec, Canada') "
                "ou ajoutez le pays."
            )
            return False, f"{hint}\nDétail: {msg}"

    # 2. Sélection des points (Dépôt + Clients)
    # On prend des nœuds aléatoires du graphe pour être sûr qu'ils sont sur la route
    nodes = list(G.nodes(data=True))
    if explicit_center:
        radius_m = float(search_radius_km) * 1000.0
        ref_lat = float(center_lat)
        ref_lon = float(center_lon)
        nodes = [
            node
            for node in nodes
            if _haversine_m(ref_lat, ref_lon, float(node[1]["y"]), float(node[1]["x"])) <= radius_m
        ]
    if len(nodes) < (num_clients + 1):
        if explicit_center:
            return (
                False,
                "Rayon trop petit pour ce nombre de colis. "
                "Augmentez le rayon ou reduisez le nombre de colis.",
            )
        return (
            False,
            "OSM: pas assez de nœuds routiers dans la zone. "
            "Réduisez le nombre de clients ou choisissez une zone plus grande.",
        )
    if explicit_center:
        depot_node, clients_nodes = _select_depot_and_clients(
            nodes,
            int(num_clients),
            center_lat=float(center_lat),
            center_lon=float(center_lon),
        )
    else:
        depot_node, clients_nodes = _select_depot_and_clients(nodes, int(num_clients))
    node_ids = [depot_node[0]] + [n[0] for n in clients_nodes]
    
    data = []
    # Dépôt (ID 0)
    data.append({
        "id": 0,
        "lat": depot_node[1]['y'],
        "lon": depot_node[1]['x'],
        "poids_colis": 0,
        "nom_client": "DEPOT CENTRAL"
    })
    
    # Enrichissement Overpass : noms réels depuis OSM
    center_lat_poi = float(center_lat) if center_lat is not None else float(depot_node[1]["y"])
    center_lon_poi = float(center_lon) if center_lon is not None else float(depot_node[1]["x"])
    radius_poi = max(800, int(float(search_radius_km or 1.5) * 1000))
    poi_names = _fetch_overpass_pois(center_lat_poi, center_lon_poi, radius_poi)
    noms_fictifs = ["Boulangerie", "Pharmacie", "Café de la Gare", "Hôtel de Ville",
                    "Librairie", "Supermarché", "Garage", "École", "Mairie", "Poste"]

    for i, node in enumerate(clients_nodes):
        # Fenêtres de temps sur une nuit complète (8h = 28800s)
        # 30% des clients ont une contrainte plus serrée (début ou milieu de nuit)
        has_constraint = random.random() < 0.3
        tw_start, tw_end = 0, 28800
        if has_constraint:
            if random.random() < 0.5:
                tw_start, tw_end = 0, 7200
            else:
                tw_start, tw_end = 7200, 14400

        # Nom : POI réel si disponible, sinon fictif
        if i < len(poi_names):
            client_name = poi_names[i]
        else:
            client_name = f"{random.choice(noms_fictifs)} {i + 1}"

        # Catégorie de cargaison pondérée
        cargo = random.choices(CARGO_CATEGORIES, weights=_CARGO_WEIGHTS, k=1)[0]
        base_weight = random.randint(5, 50)
        actual_weight = max(1, round(base_weight * cargo["weight_factor"]))

        data.append({
            "id": i + 1,
            "lat": node[1]["y"],
            "lon": node[1]["x"],
            "poids_colis": actual_weight,
            "nom_client": client_name,
            "tw_start": tw_start,
            "tw_end": tw_end,
            "cargo_code": cargo["code"],
            "cargo_label": cargo["label"],
            "cargo_emoji": cargo["emoji"],
            "cargo_constraint": cargo["constraint"],
        })
    
    # Depot a aussi une fenêtre de temps (ouverture/fermeture)
    data[0]["tw_start"] = 0
    data[0]["tw_end"] = 28800 # 8h max pour la journée totale
    
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    df.to_csv(data_path, index=False)
    print(f"✅ {num_clients} clients générés dans {data_path}")

    # 3. Calcul des matrices multimodales (temps/distance/co2/risque + composite)
    _locations_for_elev = [(float(row["lat"]), float(row["lon"])) for _, row in df.iterrows()]
    mode_node_ids: dict[str, list[int]] = {}
    for mode, graph in mode_graphs.items():
        mapped_nodes = []
        for _, row in df.iterrows():
            mapped_nodes.append(int(ox.nearest_nodes(graph, float(row["lon"]), float(row["lat"]))))
        mode_node_ids[mode] = mapped_nodes

    try:
        print("🧮 Calcul des matrices multimodales locales via NetworkX…")
        mode_mats_raw: dict[str, dict[str, np.ndarray]] = {}
        for mode, graph in mode_graphs.items():
            mode_mats_raw[mode] = _compute_matrices_local(graph, mode_node_ids[mode])

        if normalized_mode == "multimodal":
            matrices = _compute_multimodal_matrices(mode_graphs, mode_node_ids)
        else:
            selected_graph = mode_graphs[requested_modes[0]]
            selected_nodes = mode_node_ids[requested_modes[0]]
            matrices = _compute_matrices_local(selected_graph, selected_nodes)

        durations = matrices["travel_time"]
        distances = matrices["length"]
        base_distance_matrix = np.array(distances, copy=True)
        co2_matrix = matrices["co2_g"]
        risk_matrix = matrices["risk_score"]
        mode_mats_processed: dict[str, dict[str, np.ndarray]] = {}

        co2_source_meta = {
            "enabled": bool(use_ademe_co2),
            "provider": "local_factor",
            "mode_factor_g_per_km": float(MODE_CO2_G_PER_KM.get(requested_modes[0], 120.0)),
            "status": "local_default",
        }
        if use_ademe_co2:
            selected_transport_id = _resolve_ademe_transport_id(requested_modes[0], ademe_transport_id)
            ademe_factor, ademe_meta = _fetch_ademe_factor_g_per_km(selected_transport_id)
            if ademe_factor is not None and ademe_factor >= 0.0:
                co2_matrix = _build_co2_matrix_from_distance(base_distance_matrix, ademe_factor)
                co2_source_meta = dict(ademe_meta)
            else:
                fallback_factor = MODE_CO2_G_PER_KM.get(requested_modes[0], 120.0)
                co2_matrix = _build_co2_matrix_from_distance(base_distance_matrix, fallback_factor)
                co2_source_meta = dict(ademe_meta)
                co2_source_meta["fallback_mode_factor_g_per_km"] = float(fallback_factor)

        preloaded_elevations = None
        if with_elevation:
            try:
                from scripts.elevation_engine import fetch_elevations
                preloaded_elevations = fetch_elevations(_locations_for_elev)
            except Exception:
                preloaded_elevations = None

        for mode, mode_mats in mode_mats_raw.items():
            mode_time = np.array(mode_mats["travel_time"], copy=True)
            mode_dist = np.array(mode_mats["length"], copy=True)
            mode_co2 = np.array(mode_mats["co2_g"], copy=True)
            mode_risk = np.array(mode_mats["risk_score"], copy=True)
            if departure_hour is not None:
                mode_time = apply_traffic_factor(mode_time, int(departure_hour))
            if with_elevation:
                try:
                    from scripts.elevation_engine import apply_slope_to_matrices
                    elevations = preloaded_elevations if preloaded_elevations is not None else []
                    if not elevations:
                        raise RuntimeError("elevation unavailable")
                    mode_time, mode_dist, _ = apply_slope_to_matrices(
                        mode_time, mode_dist, _locations_for_elev, elevations
                    )
                except Exception:
                    pass
            mode_composite = _build_composite_cost_matrix(
                mode_time, mode_dist, mode_co2, mode_risk, objective_weights
            )
            mode_mats_processed[mode] = {
                "time": mode_time,
                "distance": mode_dist,
                "co2": mode_co2,
                "risk": mode_risk,
                "composite": mode_composite,
            }

        if departure_hour is not None:
            durations = apply_traffic_factor(durations, int(departure_hour))
            print(f"🚦 Facteur trafic appliqué pour {departure_hour}h : ×{TRAFFIC_PROFILE.get(int(departure_hour), 1.0)}")

        elev_meta = _apply_elevation_if_needed(
            durations, distances, _locations_for_elev, with_elevation, elevation_path
        )
        composite_matrix = _build_composite_cost_matrix(
            durations,
            distances,
            co2_matrix,
            risk_matrix,
            objective_weights,
        )

        np.save(time_matrix_path, durations)
        np.save(dist_matrix_path, distances)
        np.save(co2_matrix_path, co2_matrix)
        np.save(risk_matrix_path, risk_matrix)
        np.save(composite_matrix_path, composite_matrix)
        mode_matrix_dir = os.path.join(os.path.dirname(multimodal_profile_path), "mode_matrices")
        mode_matrix_files = _save_mode_matrices(mode_mats_processed, mode_matrix_dir)

        profile = {
            "transport_mode": normalized_mode,
            "available_modes": list(sorted(mode_graphs.keys())),
            "objective_weights": objective_weights,
            "matrix_files": {
                "time": os.path.basename(time_matrix_path),
                "distance": os.path.basename(dist_matrix_path),
                "co2": os.path.basename(co2_matrix_path),
                "risk": os.path.basename(risk_matrix_path),
                "composite": os.path.basename(composite_matrix_path),
            },
            "traffic_hour": departure_hour,
            "with_elevation": bool(with_elevation),
            "co2_source": co2_source_meta,
            "mode_matrix_files": mode_matrix_files,
        }
        os.makedirs(os.path.dirname(multimodal_profile_path), exist_ok=True)
        with open(multimodal_profile_path, "w", encoding="utf-8") as fp:
            json.dump(profile, fp, indent=2, ensure_ascii=False)

        print(
            f"✅ Matrices multimodales générées ({len(df)}x{len(df)}), "
            f"mode actif={normalized_mode}, poids={objective_weights}."
        )
        note = (
            f"Graphe multimodal ({', '.join(sorted(mode_graphs.keys()))}) "
            f"avec coûts temps/distance/CO2/risque et matrice composite."
        )
        if co2_source_meta.get("provider") == "ademe_impact_co2" and co2_source_meta.get("status") == "ok":
            note += (
                " CO2 via ADEME Impact CO2 "
                f"({co2_source_meta.get('selected_transport_name', 'transport')} : "
                f"{round(float(co2_source_meta.get('factor_g_per_km', 0.0)), 2)} g/km)."
            )
        if elev_meta:
            note += f" Relief SRTM intégré ({elev_meta['terrain_type']}, Δalt {elev_meta['range_m']} m)."
        return True, note
    except Exception as exc:
        msg = str(exc)
        print(f"❌ Calcul multimodal échoué : {msg}")
        return False, f"Erreur calcul matrice multimodale: {msg}"

if __name__ == "__main__":
    ok, msg = generate_new_zone("Le Marais, Paris", 20)
    print(ok, msg)
