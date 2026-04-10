import json
import os
import numpy as np
import pandas as pd

# Chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(BASE_DIR, 'core_data', 'livraisons_5eme.csv')
TIME_MATRIX = os.path.join(BASE_DIR, 'core_data', 'live_time_matrix.npy')
DIST_MATRIX = os.path.join(BASE_DIR, 'core_data', 'matrix_5eme.npy')
OPTIMIZED_JSON = os.path.join(BASE_DIR, 'production_output', 'resultats_finaux.json')
BENCHMARK_FILE = os.path.join(BASE_DIR, 'core_data', 'benchmark_results.json')

def calculate_benchmark(num_vehicles=3, budget_initial=0, budget_spent=0):
    # 1. Chargement
    df = pd.read_csv(DATA_PATH)
    time_matrix = np.load(TIME_MATRIX)
    dist_matrix = np.load(DIST_MATRIX)
    
    with open(OPTIMIZED_JSON, 'r') as f:
        opt_data = json.load(f)
    
    num_points = len(df)
    
    # 2. Calcul Naïf
    # On livre dans l'ordre 1..N, on ignore la capacité pour le calcul pur
    # Répartition : P1 prend les index 1-16, P2 17-32, P3 le reste.
    naive_tours = []
    chunk = (num_points - 1) // num_vehicles
    
    total_naive_time = 0
    total_naive_dist = 0
    
    for v in range(num_vehicles):
        start_idx = 1 + v * chunk
        end_idx = min(1 + (v + 1) * chunk, num_points)
        
        # Route: 0 -> points -> 0
        route_indices = [0] + list(range(start_idx, end_idx)) + [0]
        v_time = 0
        v_dist = 0
        for i in range(len(route_indices) - 1):
            v_time += time_matrix[route_indices[i]][route_indices[i+1]]
            v_dist += dist_matrix[route_indices[i]][route_indices[i+1]]
        
        total_naive_time += v_time
        total_naive_dist += v_dist
        naive_tours.append({"vehicle_id": v, "route_ids": [int(df.iloc[i]['id']) for i in route_indices]})

    # 3. Calcul Optimisé (Récupéré du JSON)
    total_opt_time = opt_data.get('total_time_s', 0)
    # Calcul de la distance optimisée réelle (on somme les distances sur la matrice dist)
    total_opt_dist = 0
    for tour in opt_data['tours']:
        r_ids = tour['route_ids']
        # Mapping ID -> Index CSV
        id_to_idx = {int(row['id']): i for i, row in df.iterrows()}
        for i in range(len(r_ids) - 1):
            total_opt_dist += dist_matrix[id_to_idx[r_ids[i]]][id_to_idx[r_ids[i+1]]]

    # 4. Économies
    time_saved_sec = total_naive_time - total_opt_time
    time_saved_pct = (time_saved_sec / total_naive_time) * 100 if total_naive_time > 0 else 0
    
    co2_saved_kg = ((total_naive_dist - total_opt_dist) / 1000.0) * 0.120 # 120g/km
    
    benchmark = {
        "naive": {
            "total_time_s": int(total_naive_time),
            "total_dist_m": int(total_naive_dist),
            "tours": naive_tours
        },
        "optimized": {
            "total_time_s": int(total_opt_time),
            "total_dist_m": int(total_opt_dist)
        },
        "savings": {
            "time_saved_min": int(time_saved_sec // 60),
            "time_saved_pct": round(time_saved_pct, 1),
            "co2_saved_kg": round(co2_saved_kg, 2),
            "score": round(time_saved_pct, 1)
        },
        "budget": {
            "initial": budget_initial,
            "spent": budget_spent,
            "remaining": budget_initial - budget_spent,
            "remaining_pct": round(((budget_initial - budget_spent) / budget_initial * 100), 1) if budget_initial > 0 else 0
        }
    }
    
    with open(BENCHMARK_FILE, 'w') as f:
        json.dump(benchmark, f, indent=4)
    
    print(f"📊 Benchmark terminé. Gain : {benchmark['savings']['score']}%")

if __name__ == "__main__":
    calculate_benchmark()
