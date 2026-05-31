import pandas as pd
import numpy as np
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
try:
    from ortools.sat.python import cp_model
except Exception:
    cp_model = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(BASE_DIR, 'core_data', 'livraisons_5eme.csv')
TIME_MATRIX_PATH = os.path.join(BASE_DIR, 'core_data', 'live_time_matrix.npy')
DIST_MATRIX_PATH = os.path.join(BASE_DIR, 'core_data', 'matrix_5eme.npy')
CO2_MATRIX_PATH = os.path.join(BASE_DIR, 'core_data', 'co2_matrix.npy')
RISK_MATRIX_PATH = os.path.join(BASE_DIR, 'core_data', 'risk_matrix.npy')
COMPOSITE_MATRIX_PATH = os.path.join(BASE_DIR, 'core_data', 'composite_cost_matrix.npy')
WEATHER_FILE = os.path.join(BASE_DIR, 'core_data', 'weather_status.json')
OUTPUT_PATH = os.path.join(BASE_DIR, 'production_output', 'resultats_finaux.json')
LARGE_SCALE_CLIENT_THRESHOLD = 150


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super(NpEncoder, self).default(obj)


FIRST_SOLUTION_STRATEGIES = {
    "path_cheapest_arc":           routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    "parallel_cheapest_insertion": routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
    "savings":                     routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
    "christofides":                routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES,
    "global_cheapest_arc":         routing_enums_pb2.FirstSolutionStrategy.GLOBAL_CHEAPEST_ARC,
}

LOCAL_SEARCH_METAHEURISTICS = {
    "guided_local_search":  routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    "simulated_annealing":  routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
    "tabu_search":          routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
}


def _load_mode_matrices_from_profile(multimodal_profile_path: str | None) -> dict[str, dict[str, np.ndarray]]:
    if not multimodal_profile_path:
        return {}
    profile_path = Path(multimodal_profile_path)
    if not profile_path.exists():
        return {}
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    raw = payload.get("mode_matrix_files", {})
    if not isinstance(raw, dict):
        return {}
    loaded: dict[str, dict[str, np.ndarray]] = {}
    for mode, files in raw.items():
        if not isinstance(files, dict):
            continue
        mode_loaded: dict[str, np.ndarray] = {}
        for metric, matrix_path in files.items():
            try:
                p = Path(str(matrix_path))
                if p.exists():
                    mode_loaded[str(metric)] = np.load(p)
            except Exception:
                continue
        if mode_loaded:
            loaded[str(mode)] = mode_loaded
    return loaded


def _sanitize_postprocessed_tours(
    tours_raw: dict[int, list[int]],
    improved_tours: dict | None,
    *,
    num_locations: int,
) -> dict[int, list[int]] | None:
    """
    Garantit les invariants VRP après post-traitement:
    - client servi au plus une fois globalement
    - aucun client hors domaine [1, num_locations-1]
    - même couverture client que la solution OR-Tools brute
    Si un invariant casse, on replie sur tours_raw (fiable, unique).
    """
    if not improved_tours:
        return None

    valid_clients = set(range(1, max(1, int(num_locations))))
    raw_clients = {int(c) for route in tours_raw.values() for c in route if int(c) in valid_clients}

    sanitized: dict[int, list[int]] = {}
    seen: set[int] = set()
    has_issue = False

    for vehicle_id in sorted(tours_raw.keys()):
        candidate_route = improved_tours.get(vehicle_id, tours_raw.get(vehicle_id, []))
        normalized: list[int] = []
        for client in candidate_route:
            try:
                cid = int(client)
            except Exception:
                has_issue = True
                continue
            if cid not in valid_clients:
                has_issue = True
                continue
            if cid in seen:
                has_issue = True
                continue
            seen.add(cid)
            normalized.append(cid)
        sanitized[vehicle_id] = normalized

    if seen != raw_clients:
        has_issue = True

    if has_issue:
        print("⚠️ Post-traitement invalide détecté (doublon/perte client). Repli sur solution OR-Tools brute.")
        return {int(k): [int(c) for c in v] for k, v in tours_raw.items()}
    return sanitized


def _resolve_night_horizon_s(night_horizon_s) -> int | None:
    try:
        horizon = int(night_horizon_s)
    except (TypeError, ValueError):
        return None
    if horizon <= 0:
        return None
    return horizon


def _served_priority_drop_penalty(
    *,
    base_drop_penalty: int,
    num_locations: int,
    num_vehicles: int,
    route_horizon_s: int,
) -> int:
    # Priorité: maximiser le nombre de clients servis.
    # On garde une borne int64 raisonnable pour OR-Tools.
    dynamic_floor = int(max(1, route_horizon_s) * max(2, num_locations) * max(1, num_vehicles))
    return int(min(2_000_000_000, max(int(base_drop_penalty), dynamic_floor)))


def _resolve_large_scale_client_threshold() -> int:
    raw_value = os.getenv("NOEL_LARGE_SCALE_CLIENT_THRESHOLD")
    if raw_value is None:
        return int(max(1, LARGE_SCALE_CLIENT_THRESHOLD))
    try:
        return int(max(1, int(raw_value)))
    except (TypeError, ValueError):
        return int(max(1, LARGE_SCALE_CLIENT_THRESHOLD))


def _solve_vrp_classic(
    num_vehicles=3,
    vehicle_capacity=200,
    speed_multiplier=1.0,
    forced_weather=None,
    incident_matrix_path=None,
    data_path=DATA_PATH,
    time_matrix_path=TIME_MATRIX_PATH,
    dist_matrix_path=DIST_MATRIX_PATH,
    co2_matrix_path=CO2_MATRIX_PATH,
    risk_matrix_path=RISK_MATRIX_PATH,
    composite_matrix_path=COMPOSITE_MATRIX_PATH,
    weather_file=WEATHER_FILE,
    output_path=OUTPUT_PATH,
    optimization_target="time",
    transport_mode="drive",
    objective_weights=None,
    solver_time_limit_s=20,
    first_solution_strategy="path_cheapest_arc",
    local_search_metaheuristic="guided_local_search",
    time_slack_s=3600,
    max_route_time_s=14400,
    drop_penalty=1000000,
    global_span_cost=0,
    initial_routes=None,
    vehicle_fixed_cost=0,
    vehicle_modes=None,
    multimodal_profile_path=None,
    random_seed=None,
    night_horizon_s=None,
    prioritize_served_points=False,
):
    if random_seed is not None:
        seed_value = int(random_seed) % (2**32)
        random.seed(seed_value)
        np.random.seed(seed_value)

    # 1. Chargement des données
    if not os.path.exists(data_path):
        print(f"Erreur : {data_path} introuvable.")
        return None
    df = pd.read_csv(data_path)
    num_locations = len(df)

    # 2. Chargement Météo
    weather_factor = 1.0
    weather_desc = "Inconnue"
    weather_cond = "Clear"

    if forced_weather:
        weather_factor = forced_weather.get('factor', 1.0)
        weather_desc = forced_weather.get('desc', 'Forcée')
        weather_cond = forced_weather.get('condition', 'Clear')
    elif os.path.exists(weather_file):
        with open(weather_file, 'r', encoding='utf-8') as f:
            w_data = json.load(f)
            weather_factor = w_data.get('factor', 1.0)
            weather_desc = w_data.get('desc', 'Inconnue')
            weather_cond = w_data.get('condition', 'Clear')

    # 3. Chargement et Ajustement Matrices
    t_matrix_path = incident_matrix_path if (incident_matrix_path and os.path.exists(incident_matrix_path)) else time_matrix_path
    if os.path.exists(t_matrix_path):
        total_factor = weather_factor / speed_multiplier
        matrix_time = np.load(t_matrix_path) * total_factor
        if weather_cond not in ["Clear", "Clouds", "Forcée"] and num_locations > 5:
            stormy_indices = random.sample(range(1, num_locations), max(1, num_locations // 5))
            for idx in stormy_indices:
                matrix_time[idx, :] *= 1.5
                matrix_time[:, idx] *= 1.5
    else:
        print("Erreur : Matrice OSRM (temps) manquante.")
        return None

    matrix_dist = np.load(dist_matrix_path) if (dist_matrix_path and os.path.exists(dist_matrix_path)) else None
    matrix_co2 = np.load(co2_matrix_path) if (co2_matrix_path and os.path.exists(co2_matrix_path)) else None
    matrix_risk = np.load(risk_matrix_path) if (risk_matrix_path and os.path.exists(risk_matrix_path)) else None
    matrix_composite = np.load(composite_matrix_path) if (composite_matrix_path and os.path.exists(composite_matrix_path)) else None
    mode_matrices = _load_mode_matrices_from_profile(multimodal_profile_path)
    valid_mode_matrices: dict[str, dict[str, np.ndarray]] = {}
    for mode, payload in mode_matrices.items():
        mode_payload: dict[str, np.ndarray] = {}
        for metric, matrix in payload.items():
            if isinstance(matrix, np.ndarray) and matrix.shape == (num_locations, num_locations):
                mode_payload[metric] = matrix
        if mode_payload:
            valid_mode_matrices[mode] = mode_payload
    mode_matrices = valid_mode_matrices
    if mode_matrices:
        for mode_payload in mode_matrices.values():
            if "time" in mode_payload:
                mode_payload["time"] = np.array(mode_payload["time"], copy=True) * (weather_factor / speed_multiplier)
            if weather_cond not in ["Clear", "Clouds", "Forcée"] and num_locations > 5 and "time" in mode_payload:
                stormy_indices = random.sample(range(1, num_locations), max(1, num_locations // 5))
                for idx in stormy_indices:
                    mode_payload["time"][idx, :] *= 1.5
                    mode_payload["time"][:, idx] *= 1.5

    if optimization_target == "distance" and matrix_dist is None:
        print("⚠️ Matrice de distance manquante, repli sur le temps.")
        optimization_target = "time"
    if optimization_target == "composite" and matrix_composite is None:
        if matrix_dist is not None and matrix_co2 is not None and matrix_risk is not None:
            weights = objective_weights if isinstance(objective_weights, dict) else {}
            w_time = max(0.0, float(weights.get("time", 0.55)))
            w_dist = max(0.0, float(weights.get("distance", 0.20)))
            w_co2 = max(0.0, float(weights.get("co2", 0.15)))
            w_risk = max(0.0, float(weights.get("risk", 0.10)))
            total_w = max(1e-9, w_time + w_dist + w_co2 + w_risk)
            w_time, w_dist, w_co2, w_risk = w_time / total_w, w_dist / total_w, w_co2 / total_w, w_risk / total_w

            def _scaled(m):
                arr = np.array(m, dtype=float)
                positive = arr[np.isfinite(arr) & (arr > 0)]
                scale = float(np.median(positive)) if positive.size else 1.0
                if scale <= 1e-9:
                    scale = 1.0
                scaled = arr / scale
                scaled[~np.isfinite(scaled)] = 1e9
                return scaled

            matrix_composite = (
                w_time * _scaled(matrix_time)
                + w_dist * _scaled(matrix_dist)
                + w_co2 * _scaled(matrix_co2)
                + w_risk * _scaled(matrix_risk)
            )
            np.fill_diagonal(matrix_composite, 0.0)
        else:
            print("⚠️ Matrice composite indisponible, repli sur le temps.")
            optimization_target = "time"

    # 4. Configuration Flotte
    print(
        f"Configuration : {num_vehicles} traîneaux | Capacité : {vehicle_capacity}kg | "
        f"Cible : {optimization_target} | Mode : {transport_mode} | "
        f"Stratégie : {first_solution_strategy} + {local_search_metaheuristic}"
    )

    available_modes = sorted(mode_matrices.keys())
    if isinstance(vehicle_modes, list) and vehicle_modes:
        normalized_vehicle_modes = [str(mode).strip().lower() for mode in vehicle_modes]
    else:
        fallback_mode = str(transport_mode).strip().lower()
        if fallback_mode == "multimodal" and available_modes:
            fallback_mode = "drive" if "drive" in available_modes else available_modes[0]
        normalized_vehicle_modes = [fallback_mode] * int(num_vehicles)
    if len(normalized_vehicle_modes) < int(num_vehicles):
        normalized_vehicle_modes += [normalized_vehicle_modes[-1]] * (int(num_vehicles) - len(normalized_vehicle_modes))
    normalized_vehicle_modes = normalized_vehicle_modes[: int(num_vehicles)]
    if available_modes:
        default_mode = "drive" if "drive" in available_modes else available_modes[0]
        normalized_vehicle_modes = [mode if mode in available_modes else default_mode for mode in normalized_vehicle_modes]

    # 5. OR-Tools
    manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        return int(matrix_time[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])

    def dist_callback(from_index, to_index):
        return int(matrix_dist[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])

    def composite_callback(from_index, to_index):
        return int(matrix_composite[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])

    def _matrix_for_mode(mode: str, metric: str, fallback: np.ndarray | None) -> np.ndarray | None:
        if mode in mode_matrices and metric in mode_matrices[mode]:
            return mode_matrices[mode][metric]
        return fallback

    transit_time_callback_indices: list[int] = []
    cost_callback_indices: list[int] = []
    for vehicle_id in range(num_vehicles):
        mode = normalized_vehicle_modes[vehicle_id]
        mode_time = _matrix_for_mode(mode, "time", matrix_time)
        mode_dist = _matrix_for_mode(mode, "distance", matrix_dist)
        mode_comp = _matrix_for_mode(mode, "composite", matrix_composite)

        def _make_callback(matrix):
            def _cb(from_index, to_index):
                return int(matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])
            return _cb

        time_cb_idx = routing.RegisterTransitCallback(_make_callback(mode_time))
        transit_time_callback_indices.append(time_cb_idx)
        if optimization_target == "distance" and mode_dist is not None:
            cost_callback_indices.append(routing.RegisterTransitCallback(_make_callback(mode_dist)))
        elif optimization_target == "composite" and mode_comp is not None:
            cost_callback_indices.append(routing.RegisterTransitCallback(_make_callback(mode_comp)))
        else:
            cost_callback_indices.append(time_cb_idx)

    for vehicle_id, cost_idx in enumerate(cost_callback_indices):
        routing.SetArcCostEvaluatorOfVehicle(cost_idx, vehicle_id)

    effective_night_horizon_s = _resolve_night_horizon_s(night_horizon_s)
    effective_route_horizon_s = int(max_route_time_s)
    if effective_night_horizon_s is not None:
        effective_route_horizon_s = min(effective_route_horizon_s, int(effective_night_horizon_s))

    routing.AddDimensionWithVehicleTransits(
        transit_time_callback_indices,
        int(time_slack_s),
        int(effective_route_horizon_s),
        False,
        'Time'
    )
    time_dimension = routing.GetDimensionOrDie('Time')
    if global_span_cost and int(global_span_cost) > 0:
        time_dimension.SetGlobalSpanCostCoefficient(int(global_span_cost))

    if 'tw_start' in df.columns and 'tw_end' in df.columns:
        print("Application des Time Windows (VRPTW)...")
        for i in range(num_locations):
            index = manager.NodeToIndex(i)
            tw_start = int(df.iloc[i]['tw_start'])
            tw_end = int(df.iloc[i]['tw_end'])
            if effective_night_horizon_s is not None:
                tw_end = min(tw_end, int(effective_night_horizon_s))
                tw_start = max(0, min(tw_start, tw_end))
            time_dimension.CumulVar(index).SetRange(tw_start, tw_end)
        depot_tw_end = int(df.iloc[0]['tw_end']) if num_locations > 0 else int(effective_route_horizon_s)
        if effective_night_horizon_s is not None:
            depot_tw_end = min(depot_tw_end, int(effective_night_horizon_s))
            for vehicle_id in range(num_vehicles):
                start_index = routing.Start(vehicle_id)
                time_dimension.CumulVar(start_index).SetRange(0, 0)
        for vehicle_id in range(num_vehicles):
            index = routing.End(vehicle_id)
            time_dimension.CumulVar(index).SetRange(0, depot_tw_end)

    demands = df['poids_colis'].astype(int).tolist()

    def demand_callback(from_index):
        return int(demands[manager.IndexToNode(from_index)])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, [vehicle_capacity] * num_vehicles, True, 'Capacity')

    if vehicle_fixed_cost and int(vehicle_fixed_cost) > 0:
        for v in range(num_vehicles):
            routing.SetFixedCostOfVehicle(int(vehicle_fixed_cost), v)

    penalty = int(drop_penalty)
    if prioritize_served_points:
        penalty = _served_priority_drop_penalty(
            base_drop_penalty=int(drop_penalty),
            num_locations=int(num_locations),
            num_vehicles=int(num_vehicles),
            route_horizon_s=int(effective_route_horizon_s),
        )
    for i in range(1, num_locations):
        routing.AddDisjunction([manager.NodeToIndex(i)], penalty)

    # Recherche
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = FIRST_SOLUTION_STRATEGIES.get(
        str(first_solution_strategy).lower(),
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    )
    search_parameters.local_search_metaheuristic = LOCAL_SEARCH_METAHEURISTICS.get(
        str(local_search_metaheuristic).lower(),
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    )
    search_parameters.time_limit.seconds = int(solver_time_limit_s)

    print("Recherche de la solution optimale...")

    # Warm-start depuis la solution humaine si fournie
    solution = None
    if initial_routes:
        id_to_idx = {int(df.iloc[i]['id']): i for i in range(num_locations)}
        routes_list = []
        for v in range(num_vehicles):
            client_ids = initial_routes.get(str(v), [])
            route_indices = [id_to_idx[cid] for cid in client_ids if cid in id_to_idx]
            routes_list.append(route_indices)
        init_assignment = routing.ReadAssignmentFromRoutes(routes_list, True)
        if init_assignment:
            print(f"Warm-start : {sum(len(r) for r in routes_list)} clients pré-affectés.")
            solution = routing.SolveFromAssignmentWithParameters(init_assignment, search_parameters)
        else:
            print("Warm-start ignoré, repli sur démarrage à froid.")

    if solution is None:
        solution = routing.SolveWithParameters(search_parameters)

    if solution:
        tours_raw: dict[int, list[int]] = {}
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            clients: list[int] = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != 0:
                    clients.append(node)
                index = solution.Value(routing.NextVar(index))
            tours_raw[vehicle_id] = clients

        node_demands = {i: float(df.iloc[i]["poids_colis"]) for i in range(num_locations)}
        use_postprocess = len(set(normalized_vehicle_modes)) <= 1
        if use_postprocess:
            postprocessed_tours = _postprocess_vrp_tours(
                tours_raw, matrix_time,
                demands=node_demands,
                vehicle_capacity=float(vehicle_capacity),
                seed=(int(random_seed) if random_seed is not None else 42),
            )
        else:
            postprocessed_tours = tours_raw
        improved_tours = _sanitize_postprocessed_tours(
            tours_raw,
            postprocessed_tours,
            num_locations=num_locations,
        )

        return save_solution(
            df, manager, routing, solution, num_vehicles,
            weather_factor, weather_desc,
            output_path=output_path,
            matrix_time=matrix_time,
            mode_time_matrices={mode: payload.get("time") for mode, payload in mode_matrices.items()},
            vehicle_modes=normalized_vehicle_modes,
            improved_tours=improved_tours,
            optimization_target=optimization_target,
            transport_mode=transport_mode,
            objective_weights=objective_weights,
            night_horizon_s=effective_night_horizon_s,
            prioritize_served_points=bool(prioritize_served_points),
            effective_drop_penalty=penalty,
        )
    else:
        print("Aucune solution trouvée.")
        return None


def _priority_multiplier(raw_value) -> float:
    if raw_value is None:
        return 1.0
    if isinstance(raw_value, str):
        value = raw_value.strip().lower()
        if value in {"high", "haute", "urgent", "critical", "critique"}:
            return 2.0
        if value in {"medium", "moyenne", "normal"}:
            return 1.4
        if value in {"low", "basse"}:
            return 1.0
        try:
            numeric = float(value)
            return float(max(1.0, min(3.0, 1.0 + 0.25 * numeric)))
        except Exception:
            return 1.0
    try:
        numeric = float(raw_value)
    except Exception:
        return 1.0
    return float(max(1.0, min(3.0, 1.0 + 0.25 * numeric)))


def _client_drop_penalties(df: pd.DataFrame, base_drop_penalty: int) -> dict[int, int]:
    priority_col = None
    for candidate in ["priority", "priorite", "client_priority", "priority_level"]:
        if candidate in df.columns:
            priority_col = candidate
            break
    penalties: dict[int, int] = {}
    for idx in range(1, len(df)):
        mult = _priority_multiplier(df.iloc[idx][priority_col]) if priority_col else 1.0
        penalties[idx] = int(max(1, round(float(base_drop_penalty) * mult)))
    return penalties


def _route_metric_sum(route_clients: list[int], matrix: np.ndarray | None) -> float:
    if matrix is None or not route_clients:
        return 0.0
    total = float(matrix[0][route_clients[0]])
    for src, dst in zip(route_clients[:-1], route_clients[1:]):
        total += float(matrix[src][dst])
    total += float(matrix[route_clients[-1]][0])
    return float(total)


def _evaluate_candidate_route(
    route_clients: list[int],
    *,
    matrix_time: np.ndarray,
    cost_matrix: np.ndarray,
    demands: list[int],
    vehicle_capacity: int,
    max_route_time_s: int,
    tw_start: list[int] | None = None,
    tw_end: list[int] | None = None,
) -> tuple[bool, int, float, float]:
    if not route_clients:
        return False, 0, 0.0, 0.0
    load = float(sum(float(demands[c]) for c in route_clients))
    if load > float(vehicle_capacity):
        return False, 0, 0.0, load

    time_elapsed = 0.0
    current = 0
    for client in route_clients:
        time_elapsed += float(matrix_time[current][client])
        if tw_start is not None and tw_end is not None:
            time_elapsed = max(time_elapsed, float(tw_start[client]))
            if time_elapsed > float(tw_end[client]):
                return False, int(time_elapsed), 0.0, load
        current = client
    time_elapsed += float(matrix_time[current][0])
    if tw_end is not None and time_elapsed > float(tw_end[0]):
        return False, int(time_elapsed), 0.0, load
    if time_elapsed > float(max_route_time_s):
        return False, int(time_elapsed), 0.0, load

    route_cost = _route_metric_sum(route_clients, cost_matrix)
    return True, int(time_elapsed), float(route_cost), load


def _resolve_large_scale_candidate_workers() -> int:
    raw = os.getenv("NOEL_LARGE_SCALE_CANDIDATE_WORKERS", "").strip()
    if raw:
        try:
            parsed = int(raw)
            if parsed > 0:
                return max(1, min(16, parsed))
        except ValueError:
            pass
    return max(1, min(8, os.cpu_count() or 1))


def _build_candidate_routes_chunk(
    *,
    attempts: int,
    seed: int,
    clients: list[int],
    neighbor_k: int,
    matrix_time: np.ndarray,
    cost_matrix: np.ndarray,
    demands: list[int],
    vehicle_capacity: int,
    max_route_time_s: int,
    tw_start: list[int] | None,
    tw_end: list[int] | None,
) -> list[dict]:
    rng = random.Random(int(seed))
    local_candidates: list[dict] = []
    local_signatures: set[tuple[int, ...]] = set()

    for _ in range(max(0, int(attempts))):
        start = int(rng.choice(clients))
        route: list[int] = [start]
        available = [c for c in clients if c != start]
        improved = True
        while improved and available:
            improved = False
            current = route[-1]
            ranked = sorted(available, key=lambda c: float(matrix_time[current][c]))[:neighbor_k]
            rng.shuffle(ranked)
            best_candidate: tuple[float, int] | None = None
            for cand in ranked:
                trial_route = route + [int(cand)]
                feasible, duration_s, route_cost, load_kg = _evaluate_candidate_route(
                    trial_route,
                    matrix_time=matrix_time,
                    cost_matrix=cost_matrix,
                    demands=demands,
                    vehicle_capacity=vehicle_capacity,
                    max_route_time_s=max_route_time_s,
                    tw_start=tw_start,
                    tw_end=tw_end,
                )
                if not feasible:
                    continue
                score = float(route_cost) + float(duration_s) * 0.01 + float(load_kg) * 0.001
                if best_candidate is None or score < best_candidate[0]:
                    best_candidate = (score, int(cand))
            if best_candidate is not None:
                selected = int(best_candidate[1])
                route.append(selected)
                available.remove(selected)
                improved = True

        feasible, duration_s, route_cost, load_kg = _evaluate_candidate_route(
            route,
            matrix_time=matrix_time,
            cost_matrix=cost_matrix,
            demands=demands,
            vehicle_capacity=vehicle_capacity,
            max_route_time_s=max_route_time_s,
            tw_start=tw_start,
            tw_end=tw_end,
        )
        if not feasible:
            continue
        signature = tuple(route)
        if signature in local_signatures:
            continue
        local_signatures.add(signature)
        local_candidates.append(
            {
                "clients": list(route),
                "duration_s": int(duration_s),
                "cost": float(route_cost),
                "load_kg": float(load_kg),
            }
        )
    return local_candidates


def _build_candidate_routes(
    *,
    num_locations: int,
    matrix_time: np.ndarray,
    cost_matrix: np.ndarray,
    demands: list[int],
    vehicle_capacity: int,
    max_route_time_s: int,
    tw_start: list[int] | None = None,
    tw_end: list[int] | None = None,
    random_seed: int | None = None,
) -> list[dict]:
    clients = list(range(1, num_locations))
    if not clients:
        return []

    neighbor_k = max(3, min(12, int(np.sqrt(len(clients))) + 2))
    max_candidates = max(120, min(3000, len(clients) * 10))
    max_attempts = max_candidates * 6
    workers = min(_resolve_large_scale_candidate_workers(), max(1, max_attempts))

    candidates: list[dict] = []
    signatures: set[tuple[int, ...]] = set()
    base_seed = int(random_seed) if random_seed is not None else 42
    chunk_attempts = [max_attempts // workers] * workers
    for idx in range(max_attempts % workers):
        chunk_attempts[idx] += 1

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _build_candidate_routes_chunk,
                attempts=attempts,
                seed=base_seed + worker_idx * 100_003,
                clients=clients,
                neighbor_k=neighbor_k,
                matrix_time=matrix_time,
                cost_matrix=cost_matrix,
                demands=demands,
                vehicle_capacity=vehicle_capacity,
                max_route_time_s=max_route_time_s,
                tw_start=tw_start,
                tw_end=tw_end,
            )
            for worker_idx, attempts in enumerate(chunk_attempts)
            if attempts > 0
        ]
        for future in futures:
            for candidate in future.result():
                signature = tuple(int(c) for c in candidate.get("clients", []))
                if not signature or signature in signatures:
                    continue
                signatures.add(signature)
                candidates.append(candidate)
                if len(candidates) >= max_candidates:
                    break
            if len(candidates) >= max_candidates:
                break

    for client in clients:
        feasible, duration_s, route_cost, load_kg = _evaluate_candidate_route(
            [client],
            matrix_time=matrix_time,
            cost_matrix=cost_matrix,
            demands=demands,
            vehicle_capacity=vehicle_capacity,
            max_route_time_s=max_route_time_s,
            tw_start=tw_start,
            tw_end=tw_end,
        )
        if not feasible:
            continue
        signature = (int(client),)
        if signature in signatures:
            continue
        signatures.add(signature)
        candidates.append(
            {
                "clients": [int(client)],
                "duration_s": int(duration_s),
                "cost": float(route_cost),
                "load_kg": float(load_kg),
            }
        )

    candidates.sort(key=lambda item: (float(item.get("cost", 0.0)), -len(item.get("clients", []))))
    return candidates[:max_candidates]


def _select_routes_cp_sat(
    *,
    candidates: list[dict],
    num_locations: int,
    num_vehicles: int,
    client_penalties: dict[int, int],
    fleet_cost: int,
    solver_time_limit_s: int,
) -> list[int] | None:
    if cp_model is None:
        return None
    if not candidates:
        return []

    model = cp_model.CpModel()
    x_vars = [model.NewBoolVar(f"x_{idx}") for idx in range(len(candidates))]
    y_vars = {
        client: model.NewBoolVar(f"y_{client}")
        for client in range(1, num_locations)
    }

    routes_by_client: dict[int, list[int]] = {client: [] for client in range(1, num_locations)}
    for ridx, route in enumerate(candidates):
        for client in route.get("clients", []):
            if client in routes_by_client:
                routes_by_client[client].append(ridx)

    for client in range(1, num_locations):
        covered_routes = routes_by_client.get(client, [])
        if covered_routes:
            model.Add(sum(x_vars[r] for r in covered_routes) + y_vars[client] == 1)
        else:
            model.Add(y_vars[client] == 1)

    model.Add(sum(x_vars) <= int(num_vehicles))

    scale = 100
    objective_terms = []
    for ridx, route in enumerate(candidates):
        route_cost_scaled = int(round(float(route.get("cost", 0.0)) * scale))
        objective_terms.append((route_cost_scaled + int(max(0, fleet_cost))) * x_vars[ridx])
    for client, y_var in y_vars.items():
        objective_terms.append(int(client_penalties.get(client, 1_000_000)) * y_var)
    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(max(1, int(solver_time_limit_s)))
    solver.parameters.num_search_workers = max(1, min(8, os.cpu_count() or 1))

    status = solver.Solve(model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return None
    return [idx for idx, var in enumerate(x_vars) if solver.Value(var) == 1]


def _select_routes_greedy_fallback(
    *,
    candidates: list[dict],
    num_locations: int,
    num_vehicles: int,
) -> list[int]:
    uncovered = set(range(1, num_locations))
    selected: list[int] = []
    available = set(range(len(candidates)))
    while uncovered and len(selected) < int(num_vehicles):
        best_choice = None
        for ridx in available:
            route = candidates[ridx]
            clients = set(int(c) for c in route.get("clients", []))
            new_clients = clients & uncovered
            if not new_clients:
                continue
            route_cost = max(1e-6, float(route.get("cost", 0.0)))
            score = float(len(new_clients)) / route_cost
            tie_break = (len(new_clients), -route_cost)
            current = (score, tie_break, ridx)
            if best_choice is None or current > best_choice:
                best_choice = current
        if best_choice is None:
            break
        ridx = int(best_choice[2])
        selected.append(ridx)
        uncovered -= set(int(c) for c in candidates[ridx].get("clients", []))
        available.remove(ridx)
    return selected


def solve_large_scale_vrp(
    num_vehicles=3,
    vehicle_capacity=200,
    speed_multiplier=1.0,
    forced_weather=None,
    incident_matrix_path=None,
    data_path=DATA_PATH,
    time_matrix_path=TIME_MATRIX_PATH,
    dist_matrix_path=DIST_MATRIX_PATH,
    co2_matrix_path=CO2_MATRIX_PATH,
    risk_matrix_path=RISK_MATRIX_PATH,
    composite_matrix_path=COMPOSITE_MATRIX_PATH,
    weather_file=WEATHER_FILE,
    output_path=OUTPUT_PATH,
    optimization_target="time",
    transport_mode="drive",
    objective_weights=None,
    solver_time_limit_s=20,
    max_route_time_s=14400,
    drop_penalty=1000000,
    vehicle_fixed_cost=0,
    random_seed=None,
    night_horizon_s=None,
    prioritize_served_points=False,
):
    if random_seed is not None:
        seed_value = int(random_seed) % (2**32)
        random.seed(seed_value)
        np.random.seed(seed_value)

    if not os.path.exists(data_path):
        print(f"Erreur : {data_path} introuvable.")
        return None
    df = pd.read_csv(data_path)
    num_locations = len(df)

    weather_factor = 1.0
    weather_desc = "Inconnue"
    weather_cond = "Clear"
    if forced_weather:
        weather_factor = forced_weather.get('factor', 1.0)
        weather_desc = forced_weather.get('desc', 'Forcée')
        weather_cond = forced_weather.get('condition', 'Clear')
    elif os.path.exists(weather_file):
        with open(weather_file, 'r', encoding='utf-8') as f:
            w_data = json.load(f)
            weather_factor = w_data.get('factor', 1.0)
            weather_desc = w_data.get('desc', 'Inconnue')
            weather_cond = w_data.get('condition', 'Clear')

    t_matrix_path = incident_matrix_path if (incident_matrix_path and os.path.exists(incident_matrix_path)) else time_matrix_path
    if not os.path.exists(t_matrix_path):
        print("Erreur : Matrice OSRM (temps) manquante.")
        return None
    matrix_time = np.load(t_matrix_path) * (weather_factor / speed_multiplier)
    if weather_cond not in ["Clear", "Clouds", "Forcée"] and num_locations > 5:
        stormy_indices = random.sample(range(1, num_locations), max(1, num_locations // 5))
        for idx in stormy_indices:
            matrix_time[idx, :] *= 1.5
            matrix_time[:, idx] *= 1.5

    matrix_dist = np.load(dist_matrix_path) if (dist_matrix_path and os.path.exists(dist_matrix_path)) else None
    matrix_co2 = np.load(co2_matrix_path) if (co2_matrix_path and os.path.exists(co2_matrix_path)) else None
    matrix_risk = np.load(risk_matrix_path) if (risk_matrix_path and os.path.exists(risk_matrix_path)) else None
    matrix_composite = np.load(composite_matrix_path) if (composite_matrix_path and os.path.exists(composite_matrix_path)) else None

    if optimization_target == "distance" and matrix_dist is None:
        optimization_target = "time"
    if optimization_target == "co2" and matrix_co2 is None:
        optimization_target = "time"
    if optimization_target == "risk" and matrix_risk is None:
        optimization_target = "time"
    if optimization_target == "composite" and matrix_composite is None:
        if matrix_dist is not None and matrix_co2 is not None and matrix_risk is not None:
            weights = objective_weights if isinstance(objective_weights, dict) else {}
            w_time = max(0.0, float(weights.get("time", 0.55)))
            w_dist = max(0.0, float(weights.get("distance", 0.20)))
            w_co2 = max(0.0, float(weights.get("co2", 0.15)))
            w_risk = max(0.0, float(weights.get("risk", 0.10)))
            total_w = max(1e-9, w_time + w_dist + w_co2 + w_risk)
            w_time, w_dist, w_co2, w_risk = w_time / total_w, w_dist / total_w, w_co2 / total_w, w_risk / total_w

            def _scaled(m):
                arr = np.array(m, dtype=float)
                positive = arr[np.isfinite(arr) & (arr > 0)]
                scale = float(np.median(positive)) if positive.size else 1.0
                if scale <= 1e-9:
                    scale = 1.0
                scaled = arr / scale
                scaled[~np.isfinite(scaled)] = 1e9
                return scaled

            matrix_composite = (
                w_time * _scaled(matrix_time)
                + w_dist * _scaled(matrix_dist)
                + w_co2 * _scaled(matrix_co2)
                + w_risk * _scaled(matrix_risk)
            )
            np.fill_diagonal(matrix_composite, 0.0)
        else:
            optimization_target = "time"

    if optimization_target == "distance":
        cost_matrix = matrix_dist if matrix_dist is not None else matrix_time
    elif optimization_target == "co2":
        cost_matrix = matrix_co2 if matrix_co2 is not None else matrix_time
    elif optimization_target == "risk":
        cost_matrix = matrix_risk if matrix_risk is not None else matrix_time
    elif optimization_target == "composite":
        cost_matrix = matrix_composite if matrix_composite is not None else matrix_time
    else:
        cost_matrix = matrix_time
        optimization_target = "time"

    effective_night_horizon_s = _resolve_night_horizon_s(night_horizon_s)
    effective_route_horizon_s = int(max_route_time_s)
    if effective_night_horizon_s is not None:
        effective_route_horizon_s = min(effective_route_horizon_s, int(effective_night_horizon_s))

    base_penalty = int(drop_penalty)
    if prioritize_served_points:
        base_penalty = _served_priority_drop_penalty(
            base_drop_penalty=int(drop_penalty),
            num_locations=int(num_locations),
            num_vehicles=int(num_vehicles),
            route_horizon_s=int(effective_route_horizon_s),
        )

    demands = df['poids_colis'].fillna(0).astype(int).tolist()
    tw_start = df['tw_start'].fillna(0).astype(int).tolist() if 'tw_start' in df.columns else None
    tw_end = df['tw_end'].fillna(effective_route_horizon_s).astype(int).tolist() if 'tw_end' in df.columns else None
    if tw_end is not None and effective_night_horizon_s is not None:
        tw_end = [min(int(v), int(effective_night_horizon_s)) for v in tw_end]
    client_penalties = _client_drop_penalties(df, base_penalty)

    print(
        f"Large scale VRP : {num_locations - 1} clients | "
        f"{num_vehicles} traîneaux | cap={vehicle_capacity}kg | horizon={effective_route_horizon_s}s"
    )
    candidates = _build_candidate_routes(
        num_locations=num_locations,
        matrix_time=matrix_time,
        cost_matrix=cost_matrix,
        demands=demands,
        vehicle_capacity=int(vehicle_capacity),
        max_route_time_s=int(effective_route_horizon_s),
        tw_start=tw_start,
        tw_end=tw_end,
        random_seed=random_seed,
    )

    selected_indices = _select_routes_cp_sat(
        candidates=candidates,
        num_locations=num_locations,
        num_vehicles=int(num_vehicles),
        client_penalties=client_penalties,
        fleet_cost=int(max(0, int(vehicle_fixed_cost))),
        solver_time_limit_s=int(solver_time_limit_s),
    )
    method = "candidate_routes_cp_sat"
    if selected_indices is None:
        selected_indices = _select_routes_greedy_fallback(
            candidates=candidates,
            num_locations=num_locations,
            num_vehicles=int(num_vehicles),
        )
        method = "candidate_routes_greedy_fallback"

    selected_routes = [candidates[idx] for idx in selected_indices if 0 <= idx < len(candidates)]
    id_by_index = {idx: int(df.iloc[idx]["id"]) for idx in range(num_locations)}
    tours = []
    served_indices: set[int] = set()
    total_time_s = 0.0
    total_weight_kg = 0.0
    total_dist_m = 0.0
    for vehicle_id, route in enumerate(selected_routes):
        clients = [int(c) for c in route.get("clients", [])]
        if not clients:
            continue
        served_indices.update(clients)
        total_time_s += float(route.get("duration_s", 0.0))
        total_weight_kg += float(route.get("load_kg", 0.0))
        total_dist_m += _route_metric_sum(clients, matrix_dist)
        tours.append(
            {
                "vehicle_id": int(vehicle_id),
                "mode": str(transport_mode),
                "route_ids": [id_by_index[0]] + [id_by_index[c] for c in clients] + [id_by_index[0]],
                "duration_s": int(route.get("duration_s", 0)),
                "weight_kg": float(route.get("load_kg", 0.0)),
            }
        )

    all_client_indices = set(range(1, num_locations))
    dropped_indices = sorted(int(idx) for idx in (all_client_indices - served_indices))
    dropped_points = [id_by_index[idx] for idx in dropped_indices]
    served_points_count = int(len(served_indices))
    total_clients_count = int(len(all_client_indices))
    served_ratio = float(served_points_count) / float(max(1, total_clients_count))

    threshold = _resolve_large_scale_client_threshold()
    result = {
        "status": "Success",
        "weather": {"desc": weather_desc, "factor": weather_factor},
        "objective": {
            "target": optimization_target,
            "transport_mode": transport_mode,
            "vehicle_modes": None,
            "weights": objective_weights if isinstance(objective_weights, dict) else {
                "time": 0.55,
                "distance": 0.20,
                "co2": 0.15,
                "risk": 0.10,
            },
            "night_horizon_s": int(effective_night_horizon_s) if effective_night_horizon_s is not None else None,
            "prioritize_served_points": bool(prioritize_served_points),
            "effective_drop_penalty": int(base_penalty),
        },
        "total_time_s": int(total_time_s),
        "total_dist_m": float(total_dist_m),
        "total_weight_kg": round(float(total_weight_kg), 1),
        "served_points_count": served_points_count,
        "total_clients_count": total_clients_count,
        "served_ratio": round(float(served_ratio), 4),
        "tours": tours,
        "dropped_points": dropped_points,
        "integrity": {
            "client_dedup_applied": False,
            "dedup_removed_count": 0,
        },
        "large_scale": {
            "enabled": True,
            "threshold": int(threshold),
            "num_candidates": int(len(candidates)),
            "candidate_generation_workers": int(_resolve_large_scale_candidate_workers()),
            "selected_routes": int(len(selected_routes)),
            "dropped_count": int(len(dropped_points)),
            "method": method,
        },
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=4, cls=NpEncoder)
    print(f"Optimisation large scale terminée. Résultats dans {output_path}")
    return result


def _postprocess_vrp_tours(
    tours_raw: dict,
    matrix_time: np.ndarray,
    demands: dict | None = None,
    vehicle_capacity: float | None = None,
    seed: int = 42,
) -> dict:
    """
    Pipeline post-traitement : ALNS (grands voisinages) → ILS (raffinement fin).

    ALNS (Ropke & Pisinger 2006) : destroy random/worst/related × repair greedy/regret-2,
    sélection adaptive par roulette, acceptation recuit simulé.
    ILS : double-bridge + 3-opt → or-opt → 2-opt* × 20 itérations.
    """
    try:
        import sys as _sys
        if BASE_DIR not in _sys.path:
            _sys.path.insert(0, BASE_DIR)
        from scripts import ro_improvements

        routes = {str(v): list(c) for v, c in tours_raw.items() if c}
        if not routes:
            return tours_raw

        # Phase 1 : ALNS
        alns = ro_improvements.adaptive_large_neighborhood_search(
            routes, matrix_time, depot_id=0,
            capacity=vehicle_capacity,
            demands=demands,
            seed=int(seed),
        )
        alns_best = {sid: d["optimized_route"] for sid, d in alns["sleighs"].items()}
        print(
            f"ALNS : {alns['total_improvement_pct']}% gain "
            f"({alns['improvements_accepted']} nouveaux best / {alns['iterations_run']} iter) "
            f"| destroy={max(alns['operator_scores']['destroy'], key=alns['operator_scores']['destroy'].get)} "
            f"repair={max(alns['operator_scores']['repair'], key=alns['operator_scores']['repair'].get)}"
        )

        # Phase 2 : ILS (raffinement)
        ils = ro_improvements.iterated_local_search(
            alns_best, matrix_time, depot_id=0,
            n_iterations=20,
            capacity=vehicle_capacity,
            demands=demands,
            seed=int(seed) + 1,
        )
        improved = {sid: d["optimized_route"] for sid, d in ils["sleighs"].items()}
        print(
            f"ILS : {ils['total_improvement_pct']}% gain supplémentaire "
            f"({ils['improvements_accepted']}/{ils['iterations_run']} perturbations acceptées)"
        )
        return {int(k): v for k, v in improved.items()}
    except Exception as exc:
        print(f"⚠️ Post-traitement ignoré : {exc}")
        return tours_raw


def save_solution(
    df, manager, routing, solution, num_vehicles, w_factor, w_desc,
    output_path=OUTPUT_PATH,
    matrix_time: np.ndarray | None = None,
    mode_time_matrices: dict[str, np.ndarray | None] | None = None,
    vehicle_modes: list[str] | None = None,
    improved_tours: dict | None = None,
    optimization_target: str = "time",
    transport_mode: str = "drive",
    objective_weights: dict | None = None,
    night_horizon_s: int | None = None,
    prioritize_served_points: bool = False,
    effective_drop_penalty: int | None = None,
    large_scale_meta: dict | None = None,
):
    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    total_weight = 0
    all_tours = []

    id_to_weight = {int(df.iloc[i]['id']): float(df.iloc[i]['poids_colis']) for i in range(len(df))}

    for vehicle_id in range(num_vehicles):
        vehicle_mode = None
        if isinstance(vehicle_modes, list) and vehicle_id < len(vehicle_modes):
            vehicle_mode = str(vehicle_modes[vehicle_id]).strip().lower()
        vehicle_time_matrix = matrix_time
        if vehicle_mode and isinstance(mode_time_matrices, dict):
            maybe_mode_matrix = mode_time_matrices.get(vehicle_mode)
            if maybe_mode_matrix is not None:
                vehicle_time_matrix = maybe_mode_matrix

        index = routing.Start(vehicle_id)
        route_load = 0
        tour_ids = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_load += float(df.iloc[node_index]['poids_colis'])
            tour_ids.append(int(df.iloc[node_index]['id']))
            index = solution.Value(routing.NextVar(index))

        route_time = solution.Value(time_dimension.CumulVar(index))
        tour_ids.append(int(df.iloc[manager.IndexToNode(index)]['id']))

        if len(tour_ids) <= 2:
            continue

        if improved_tours and vehicle_id in improved_tours and improved_tours[vehicle_id] and vehicle_time_matrix is not None:
            clients = improved_tours[vehicle_id]
            route_time = float(vehicle_time_matrix[0][clients[0]])
            for i in range(len(clients) - 1):
                route_time += float(vehicle_time_matrix[clients[i]][clients[i + 1]])
            route_time += float(vehicle_time_matrix[clients[-1]][0])
            route_time = int(route_time)
            tour_ids = [0] + clients + [0]
            route_load = sum(id_to_weight.get(c, 0.0) for c in clients)

        all_tours.append({
            "vehicle_id": vehicle_id,
            "mode": vehicle_mode if vehicle_mode else str(transport_mode),
            "route_ids": tour_ids,
            "duration_s": int(route_time),
            "weight_kg": float(route_load),
        })
        total_time += route_time
        total_weight += route_load

    # Invariant solveur: un client ne doit apparaître que dans un seul traîneau.
    # On conserve la première affectation rencontrée (vehicle_id croissant),
    # puis on purge les occurrences suivantes et on recalcule temps/charge.
    seen_clients: set[int] = set()
    id_to_idx = {int(df.iloc[i]["id"]): i for i in range(len(df))}
    deduped_tours = []
    dedup_applied = False
    dedup_count = 0
    total_time = 0
    total_weight = 0
    for tour in sorted(all_tours, key=lambda t: int(t.get("vehicle_id", 0))):
        raw_clients = [int(cid) for cid in tour.get("route_ids", []) if int(cid) != 0]
        kept_clients: list[int] = []
        for cid in raw_clients:
            if cid in seen_clients:
                dedup_applied = True
                dedup_count += 1
                continue
            seen_clients.add(cid)
            kept_clients.append(cid)
        if not kept_clients:
            continue

        new_route_ids = [0] + kept_clients + [0]
        mode_name = str(tour.get("mode", transport_mode)).strip().lower()
        tour_time_matrix = matrix_time
        if isinstance(mode_time_matrices, dict) and mode_name in mode_time_matrices and mode_time_matrices[mode_name] is not None:
            tour_time_matrix = mode_time_matrices[mode_name]
        if tour_time_matrix is not None:
            route_time = 0.0
            row_route = [id_to_idx.get(cid) for cid in new_route_ids]
            if any(idx is None for idx in row_route):
                route_time = float(tour.get("duration_s", 0.0))
            else:
                rr = [int(idx) for idx in row_route]
                for src, dst in zip(rr[:-1], rr[1:]):
                    route_time += float(tour_time_matrix[src][dst])
        else:
            route_time = float(tour.get("duration_s", 0.0))
        route_load = sum(id_to_weight.get(cid, 0.0) for cid in kept_clients)

        deduped_tours.append({
            "vehicle_id": int(tour.get("vehicle_id", 0)),
            "mode": str(tour.get("mode", transport_mode)),
            "route_ids": new_route_ids,
            "duration_s": int(route_time),
            "weight_kg": float(route_load),
        })
        total_time += route_time
        total_weight += route_load
    all_tours = deduped_tours
    if dedup_applied:
        print(f"⚠️ Déduplication de sécurité appliquée: {dedup_count} occurrence(s) client supprimée(s).")

    served_client_ids = {
        int(nid)
        for t in all_tours
        for nid in t["route_ids"]
        if int(nid) != 0
    }
    all_client_ids = {int(x) for x in df["id"].tolist() if int(x) != 0}
    dropped_ids = sorted(int(x) for x in (all_client_ids - served_client_ids))
    served_points_count = int(len(served_client_ids))
    total_clients_count = int(len(all_client_ids))
    served_ratio = float(served_points_count) / float(max(1, total_clients_count))

    result = {
        "status": "Success",
        "weather": {"desc": w_desc, "factor": w_factor},
        "objective": {
            "target": optimization_target,
            "transport_mode": transport_mode,
            "vehicle_modes": vehicle_modes if isinstance(vehicle_modes, list) else None,
            "weights": objective_weights if isinstance(objective_weights, dict) else {
                "time": 0.55,
                "distance": 0.20,
                "co2": 0.15,
                "risk": 0.10,
            },
            "night_horizon_s": int(night_horizon_s) if night_horizon_s is not None else None,
            "prioritize_served_points": bool(prioritize_served_points),
            "effective_drop_penalty": int(effective_drop_penalty) if effective_drop_penalty is not None else None,
        },
        "total_time_s": int(total_time),
        "total_weight_kg": round(float(total_weight), 1),
        "served_points_count": served_points_count,
        "total_clients_count": total_clients_count,
        "served_ratio": round(float(served_ratio), 4),
        "tours": all_tours,
        "dropped_points": dropped_ids,
        "integrity": {
            "client_dedup_applied": bool(dedup_applied),
            "dedup_removed_count": int(dedup_count),
        },
        "large_scale": large_scale_meta if isinstance(large_scale_meta, dict) else {
            "enabled": False,
            "threshold": int(_resolve_large_scale_client_threshold()),
        },
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=4, cls=NpEncoder)
    print(f"Optimisation terminée. Résultats dans {output_path}")
    return result


def solve_vrp(
    num_vehicles=3,
    vehicle_capacity=200,
    speed_multiplier=1.0,
    forced_weather=None,
    incident_matrix_path=None,
    data_path=DATA_PATH,
    time_matrix_path=TIME_MATRIX_PATH,
    dist_matrix_path=DIST_MATRIX_PATH,
    co2_matrix_path=CO2_MATRIX_PATH,
    risk_matrix_path=RISK_MATRIX_PATH,
    composite_matrix_path=COMPOSITE_MATRIX_PATH,
    weather_file=WEATHER_FILE,
    output_path=OUTPUT_PATH,
    optimization_target="time",
    transport_mode="drive",
    objective_weights=None,
    solver_time_limit_s=20,
    first_solution_strategy="path_cheapest_arc",
    local_search_metaheuristic="guided_local_search",
    time_slack_s=3600,
    max_route_time_s=14400,
    drop_penalty=1000000,
    global_span_cost=0,
    initial_routes=None,
    vehicle_fixed_cost=0,
    vehicle_modes=None,
    multimodal_profile_path=None,
    random_seed=None,
    night_horizon_s=None,
    prioritize_served_points=False,
):
    if not os.path.exists(data_path):
        print(f"Erreur : {data_path} introuvable.")
        return None
    try:
        num_locations = int(len(pd.read_csv(data_path)))
    except Exception as exc:
        print(f"Erreur lecture données : {exc}")
        return None

    threshold = _resolve_large_scale_client_threshold()
    num_clients = max(0, int(num_locations - 1))
    if num_clients >= int(threshold):
        return solve_large_scale_vrp(
            num_vehicles=num_vehicles,
            vehicle_capacity=vehicle_capacity,
            speed_multiplier=speed_multiplier,
            forced_weather=forced_weather,
            incident_matrix_path=incident_matrix_path,
            data_path=data_path,
            time_matrix_path=time_matrix_path,
            dist_matrix_path=dist_matrix_path,
            co2_matrix_path=co2_matrix_path,
            risk_matrix_path=risk_matrix_path,
            composite_matrix_path=composite_matrix_path,
            weather_file=weather_file,
            output_path=output_path,
            optimization_target=optimization_target,
            transport_mode=transport_mode,
            objective_weights=objective_weights,
            solver_time_limit_s=solver_time_limit_s,
            max_route_time_s=max_route_time_s,
            drop_penalty=drop_penalty,
            vehicle_fixed_cost=vehicle_fixed_cost,
            random_seed=random_seed,
            night_horizon_s=night_horizon_s,
            prioritize_served_points=prioritize_served_points,
        )

    return _solve_vrp_classic(
        num_vehicles=num_vehicles,
        vehicle_capacity=vehicle_capacity,
        speed_multiplier=speed_multiplier,
        forced_weather=forced_weather,
        incident_matrix_path=incident_matrix_path,
        data_path=data_path,
        time_matrix_path=time_matrix_path,
        dist_matrix_path=dist_matrix_path,
        co2_matrix_path=co2_matrix_path,
        risk_matrix_path=risk_matrix_path,
        composite_matrix_path=composite_matrix_path,
        weather_file=weather_file,
        output_path=output_path,
        optimization_target=optimization_target,
        transport_mode=transport_mode,
        objective_weights=objective_weights,
        solver_time_limit_s=solver_time_limit_s,
        first_solution_strategy=first_solution_strategy,
        local_search_metaheuristic=local_search_metaheuristic,
        time_slack_s=time_slack_s,
        max_route_time_s=max_route_time_s,
        drop_penalty=drop_penalty,
        global_span_cost=global_span_cost,
        initial_routes=initial_routes,
        vehicle_fixed_cost=vehicle_fixed_cost,
        vehicle_modes=vehicle_modes,
        multimodal_profile_path=multimodal_profile_path,
        random_seed=random_seed,
        night_horizon_s=night_horizon_s,
        prioritize_served_points=prioritize_served_points,
    )


if __name__ == "__main__":
    solve_vrp()
