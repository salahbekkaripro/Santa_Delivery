import pandas as pd
import numpy as np
import json
import osmnx as ox
import networkx as nx
import os
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# Définition des chemins relatifs au script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(BASE_DIR, 'core_data', 'livraisons_5eme.csv')
TIME_MATRIX_PATH = os.path.join(BASE_DIR, 'core_data', 'live_time_matrix.npy')
WEATHER_FILE = os.path.join(BASE_DIR, 'core_data', 'weather_status.json')
OUTPUT_PATH = os.path.join(BASE_DIR, 'production_output', 'resultats_finaux.json')

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super(NpEncoder, self).default(obj)


FIRST_SOLUTION_STRATEGIES = {
    "path_cheapest_arc": routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    "parallel_cheapest_insertion": routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
    "savings": routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
    "christofides": routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES,
    "global_cheapest_arc": routing_enums_pb2.FirstSolutionStrategy.GLOBAL_CHEAPEST_ARC,
}

LOCAL_SEARCH_METAHEURISTICS = {
    "guided_local_search": routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    "simulated_annealing": routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
    "tabu_search": routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
}

def solve_vrp(
    num_vehicles=3,
    vehicle_capacity=200,
    speed_multiplier=1.0,
    forced_weather=None,
    incident_matrix_path=None,
    data_path=DATA_PATH,
    time_matrix_path=TIME_MATRIX_PATH,
    dist_matrix_path=None,
    weather_file=WEATHER_FILE,
    output_path=OUTPUT_PATH,
    optimization_target="time",
    solver_time_limit_s=20,
    first_solution_strategy="path_cheapest_arc",
    local_search_metaheuristic="guided_local_search",
    time_slack_s=3600,
    max_route_time_s=14400,
    drop_penalty=1000000,
    global_span_cost=0,
    initial_routes=None,
    vehicle_fixed_cost=0,
):
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
    # Matrice de TEMPS (nécessaire pour les Time Windows)
    t_matrix_path = incident_matrix_path if (incident_matrix_path and os.path.exists(incident_matrix_path)) else time_matrix_path
    if os.path.exists(t_matrix_path):
        total_factor = weather_factor / speed_multiplier
        matrix_time = np.load(t_matrix_path) * total_factor
        if weather_cond not in ["Clear", "Clouds", "Forcée"] and num_locations > 5:
            import random
            stormy_indices = random.sample(range(1, num_locations), max(1, num_locations // 5))
            for idx in stormy_indices:
                matrix_time[idx, :] *= 1.5
                matrix_time[:, idx] *= 1.5
    else:
        print("Erreur : Matrice OSRM (temps) manquante.")
        return None

    # Matrice de DISTANCE
    matrix_dist = None
    if optimization_target == "distance":
        if dist_matrix_path and os.path.exists(dist_matrix_path):
            matrix_dist = np.load(dist_matrix_path)
        else:
            print("⚠️ Matrice de distance manquante, repli sur le temps.")
            optimization_target = "time"

    # 4. Configuration Flotte
    print(
        f"Configuration : {num_vehicles} traîneaux | Capacité : {vehicle_capacity}kg | "
        f"Cible : {optimization_target} | Stratégie : {first_solution_strategy} + {local_search_metaheuristic}"
    )

    # 5. OR-Tools
    manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        return int(matrix_time[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])

    def dist_callback(from_index, to_index):
        return int(matrix_dist[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])

    transit_time_callback_index = routing.RegisterTransitCallback(time_callback)
    
    if optimization_target == "distance":
        transit_dist_callback_index = routing.RegisterTransitCallback(dist_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_dist_callback_index)
    else:
        routing.SetArcCostEvaluatorOfAllVehicles(transit_time_callback_index)

    # Dimension TEMPS (Max 4h par traîneau par défaut)
    routing.AddDimension(transit_time_callback_index, int(time_slack_s), int(max_route_time_s), False, 'Time')
    time_dimension = routing.GetDimensionOrDie('Time')
    if global_span_cost and int(global_span_cost) > 0:
        time_dimension.SetGlobalSpanCostCoefficient(int(global_span_cost))

    # Ajout des fenêtres de temps (Time Windows)
    if 'tw_start' in df.columns and 'tw_end' in df.columns:
        print("Application des Time Windows (VRPTW)...")
        for i in range(num_locations):
            index = manager.NodeToIndex(i)
            tw_start = int(df.iloc[i]['tw_start'])
            tw_end = int(df.iloc[i]['tw_end'])
            time_dimension.CumulVar(index).SetRange(tw_start, tw_end)
            
        # Contrainte de retour au dépôt (tous les traîneaux doivent rentrer avant tw_end du dépôt)
        for vehicle_id in range(num_vehicles):
            index = routing.End(vehicle_id)
            depot_end = int(df.iloc[0]['tw_end'])
            time_dimension.CumulVar(index).SetRange(0, depot_end)

    # Dimension CAPACITÉ
    demands = df['poids_colis'].astype(int).tolist()
    def demand_callback(from_index):
        return int(demands[manager.IndexToNode(from_index)])
    
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, [vehicle_capacity]*num_vehicles, True, 'Capacity')

    # Coût fixe par véhicule utilisé — OR-Tools minimise naturellement la flotte
    if vehicle_fixed_cost and int(vehicle_fixed_cost) > 0:
        for v in range(num_vehicles):
            routing.SetFixedCostOfVehicle(int(vehicle_fixed_cost), v)

    # Pénalités pour livraison totale
    penalty = int(drop_penalty)
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

    # Warm-start : si des routes humaines sont fournies, on les passe comme
    # solution initiale. OR-Tools part d'un point déjà "bon" et explore mieux
    # dans le temps imparti plutôt que de reconstruire depuis zéro.
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
            print(f"Warm-start : {sum(len(r) for r in routes_list)} clients pré-affectés depuis la solution humaine.")
            solution = routing.SolveFromAssignmentWithParameters(init_assignment, search_parameters)
        else:
            print("Warm-start ignoré (assignation invalide), repli sur démarrage à froid.")

    if solution is None:
        solution = routing.SolveWithParameters(search_parameters)

    if solution:
        # Extraction des tournées brutes : {vehicle_id: [client_node_indices]}
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

        # Post-traitement local : 2-opt intra-route + or-opt inter-routes (capacité vérifiée)
        node_demands = {i: float(df.iloc[i]["poids_colis"]) for i in range(num_locations)}
        improved_tours = _postprocess_vrp_tours(
            tours_raw, matrix_time,
            demands=node_demands,
            vehicle_capacity=float(vehicle_capacity),
        )

        return save_solution(
            df, manager, routing, solution, num_vehicles,
            weather_factor, weather_desc,
            output_path=output_path,
            matrix_time=matrix_time,
            improved_tours=improved_tours,
        )
    else:
        print("Aucune solution trouvée.")
        return None


def _postprocess_vrp_tours(
    tours_raw: dict,
    matrix_time: np.ndarray,
    demands: dict | None = None,
    vehicle_capacity: float | None = None,
) -> dict:
    """
    Applique 2-opt intra-route puis or-opt inter-routes (avec garde capacité) aux tournées OR-Tools.

    tours_raw        : {vehicle_id_int: [client_node_index, ...]}  — sans dépôt
    demands          : {node_index: poids_kg} pour la vérification de capacité or-opt
    vehicle_capacity : capacité max par véhicule (kg)
    Retourne         : même structure avec routes améliorées.
    Repli silencieux sur tours_raw en cas d'erreur.
    """
    try:
        import sys as _sys
        if BASE_DIR not in _sys.path:
            _sys.path.insert(0, BASE_DIR)
        from scripts import ro_improvements

        routes = {str(v): list(c) for v, c in tours_raw.items() if c}
        if not routes:
            return tours_raw

        # ── Phase 1 : ALNS (grands voisinages, exploration large) ────────────
        alns = ro_improvements.adaptive_large_neighborhood_search(
            routes, matrix_time, depot_id=0,
            capacity=vehicle_capacity,
            demands=demands,
        )
        alns_best = {sid: d["optimized_route"] for sid, d in alns["sleighs"].items()}
        print(
            f"ALNS : {alns['total_improvement_pct']}% gain "
            f"({alns['improvements_accepted']} nouveaux best sur {alns['iterations_run']} iter) "
            f"| opérateurs dominant : destroy={max(alns['operator_scores']['destroy'], key=alns['operator_scores']['destroy'].get)} "
            f"repair={max(alns['operator_scores']['repair'], key=alns['operator_scores']['repair'].get)}"
        )

        # ── Phase 2 : ILS sur la meilleure solution ALNS (raffinement fin) ──
        ils = ro_improvements.iterated_local_search(
            alns_best, matrix_time, depot_id=0,
            n_iterations=20,
            capacity=vehicle_capacity,
            demands=demands,
        )
        improved = {sid: d["optimized_route"] for sid, d in ils["sleighs"].items()}
        print(
            f"ILS : {ils['total_improvement_pct']}% gain supplémentaire "
            f"({ils['improvements_accepted']}/{ils['iterations_run']} perturbations acceptées)"
        )
        return {int(k): v for k, v in improved.items()}
    except Exception as exc:
        print(f"⚠️ Post-traitement local ignoré : {exc}")
        return tours_raw


def save_solution(
    df, manager, routing, solution, num_vehicles, w_factor, w_desc,
    output_path=OUTPUT_PATH,
    matrix_time: np.ndarray | None = None,
    improved_tours: dict | None = None,
):
    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    total_weight = 0
    all_tours = []

    # id → poids lookup pour recalcul des charges sur routes améliorées
    id_to_weight = {int(df.iloc[i]['id']): float(df.iloc[i]['poids_colis']) for i in range(len(df))}

    for vehicle_id in range(num_vehicles):
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

        # Remplace par la tournée post-traitée si disponible
        if improved_tours and vehicle_id in improved_tours and improved_tours[vehicle_id] and matrix_time is not None:
            clients = improved_tours[vehicle_id]
            # Recompute travel time (pure transit, no waiting)
            route_time = float(matrix_time[0][clients[0]])
            for i in range(len(clients) - 1):
                route_time += float(matrix_time[clients[i]][clients[i + 1]])
            route_time += float(matrix_time[clients[-1]][0])
            route_time = int(route_time)
            # Rebuild route_ids [depot, c1, ..., cn, depot]
            tour_ids = [0] + clients + [0]
            route_load = sum(id_to_weight.get(c, 0.0) for c in clients)

        all_tours.append({
            "vehicle_id": vehicle_id,
            "route_ids": tour_ids,
            "duration_s": int(route_time),
            "weight_kg": float(route_load),
        })
        total_time += route_time
        total_weight += route_load

    dropped_ids = [int(x) for x in (set(df['id'].tolist()) - {nid for t in all_tours for nid in t['route_ids']})]

    result = {
        "status": "Success",
        "weather": {"desc": w_desc, "factor": w_factor},
        "total_time_s": int(total_time),
        "total_weight_kg": round(float(total_weight), 1),
        "tours": all_tours,
        "dropped_points": dropped_ids,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=4, cls=NpEncoder)
    print(f"Optimisation terminée. Résultats dans {output_path}")
    return result

if __name__ == "__main__":
    solve_vrp()
