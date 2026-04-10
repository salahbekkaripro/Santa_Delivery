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

def solve_vrp(num_vehicles=3, vehicle_capacity=200, speed_multiplier=1.0, forced_weather=None):
    # 1. Chargement des données
    if not os.path.exists(DATA_PATH):
        print(f"Erreur : {DATA_PATH} introuvable.")
        return
    df = pd.read_csv(DATA_PATH)
    num_locations = len(df)
    
    # 2. Chargement Météo
    weather_factor = 1.0
    weather_desc = "Inconnue"
    
    if forced_weather:
        weather_factor = forced_weather.get('factor', 1.0)
        weather_desc = forced_weather.get('desc', 'Forcée')
    elif os.path.exists(WEATHER_FILE):
        with open(WEATHER_FILE, 'r', encoding='utf-8') as f:
            w_data = json.load(f)
            weather_factor = w_data.get('factor', 1.0)
            weather_desc = w_data.get('desc', 'Inconnue')
    
    # 3. Chargement et Ajustement Matrice de temps
    if os.path.exists(TIME_MATRIX_PATH):
        # La vitesse réduit le temps : matrix / speed
        # La météo augmente le temps : matrix * factor
        total_factor = weather_factor / speed_multiplier
        print(f"Chargement OSRM | Météo : {weather_desc} | Vitesse x{speed_multiplier} | Total Factor x{total_factor:.2f}")
        matrix = np.load(TIME_MATRIX_PATH) * total_factor
    else:
        print("Erreur : Matrice OSRM manquante.")
        return

    # 4. Configuration Flotte
    print(f"Configuration : {num_vehicles} traîneaux | Capacité : {vehicle_capacity}kg")

    # 5. OR-Tools
    manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        return int(matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Dimension TEMPS (Max 2h de base * weather_factor)
    routing.AddDimension(transit_callback_index, 0, int(7200 * weather_factor), True, 'Time')

    # Dimension CAPACITÉ
    demands = df['poids_colis'].astype(int).tolist()
    def demand_callback(from_index):
        return int(demands[manager.IndexToNode(from_index)])
    
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, [vehicle_capacity]*num_vehicles, True, 'Capacity')

    # Pénalités pour livraison totale
    penalty = 1000000
    for i in range(1, num_locations):
        routing.AddDisjunction([manager.NodeToIndex(i)], penalty)

    # Recherche
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 20

    print("Recherche de la solution optimale...")
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        save_solution(df, manager, routing, solution, num_vehicles, weather_factor, weather_desc)
    else:
        print("Aucune solution trouvée.")

def save_solution(df, manager, routing, solution, num_vehicles, w_factor, w_desc):
    total_time = 0
    total_weight = 0
    all_tours = []

    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route_time = 0
        route_load = 0
        tour_ids = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_load += float(df.iloc[node_index]['poids_colis'])
            tour_ids.append(int(df.iloc[node_index]['id']))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_time += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        tour_ids.append(int(df.iloc[manager.IndexToNode(index)]['id']))
        
        if len(tour_ids) > 2:
            all_tours.append({
                "vehicle_id": vehicle_id,
                "route_ids": tour_ids,
                "duration_s": int(route_time),
                "weight_kg": float(route_load)
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
        "dropped_points": dropped_ids
    }
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(result, f, indent=4, cls=NpEncoder)
    print(f"Optimisation terminée. Résultats dans {OUTPUT_PATH}")

if __name__ == "__main__":
    solve_vrp()
