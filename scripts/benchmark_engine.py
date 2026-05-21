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
CO2_MATRIX = os.path.join(BASE_DIR, 'core_data', 'co2_matrix.npy')
OPTIMIZED_JSON = os.path.join(BASE_DIR, 'production_output', 'resultats_finaux.json')
BENCHMARK_FILE = os.path.join(BASE_DIR, 'core_data', 'benchmark_results.json')

def calculate_benchmark(
    num_vehicles=3,
    budget_initial=0,
    budget_spent=0,
    data_path=DATA_PATH,
    time_matrix_path=TIME_MATRIX,
    dist_matrix_path=DIST_MATRIX,
    co2_matrix_path=CO2_MATRIX,
    optimized_json_path=OPTIMIZED_JSON,
    benchmark_file=BENCHMARK_FILE,
    time_scale_factor=1.0,
):
    # 1. Chargement
    df = pd.read_csv(data_path)
    time_matrix = np.load(time_matrix_path) * float(time_scale_factor)
    dist_matrix = np.load(dist_matrix_path)
    co2_matrix = None
    try:
        if co2_matrix_path and os.path.exists(co2_matrix_path):
            loaded_co2 = np.load(co2_matrix_path)
            if loaded_co2.shape == dist_matrix.shape:
                co2_matrix = loaded_co2
    except Exception:
        co2_matrix = None
    
    with open(optimized_json_path, 'r') as f:
        opt_data = json.load(f)
    
    num_points = len(df)
    default_co2_g_per_km = 120.0

    def _leg_co2_g(from_idx: int, to_idx: int) -> float:
        if co2_matrix is not None:
            value = float(co2_matrix[from_idx][to_idx])
            if np.isfinite(value) and value < 1e8:
                return max(0.0, value)
        dist_m = float(dist_matrix[from_idx][to_idx])
        return max(0.0, dist_m) / 1000.0 * default_co2_g_per_km
    
    # 2. Calcul Naïf
    # On livre dans l'ordre 1..N, on ignore la capacité pour le calcul pur.
    # Répartition équilibrée et exhaustive entre les véhicules.
    naive_tours = []
    client_indices = list(range(1, num_points))
    split_clients = np.array_split(client_indices, max(1, int(num_vehicles)))
    
    total_naive_time = 0
    total_naive_dist = 0
    total_naive_co2_g = 0.0
    
    for v, assigned_clients in enumerate(split_clients):
        route_indices = [0] + assigned_clients.astype(int).tolist() + [0]
        v_time = 0
        v_dist = 0
        for i in range(len(route_indices) - 1):
            v_time += time_matrix[route_indices[i]][route_indices[i+1]]
            v_dist += dist_matrix[route_indices[i]][route_indices[i+1]]
            total_naive_co2_g += _leg_co2_g(route_indices[i], route_indices[i+1])
        
        total_naive_time += v_time
        total_naive_dist += v_dist
        naive_tours.append({"vehicle_id": v, "route_ids": [int(df.iloc[i]['id']) for i in route_indices]})

    # 3. Calcul Optimisé (recalculé sur les mêmes matrices pour comparaison homogène)
    id_to_idx = {int(row['id']): i for i, row in df.iterrows()}
    total_opt_time = 0
    total_opt_dist = 0
    total_opt_co2_g = 0.0
    for tour in opt_data.get('tours', []):
        r_ids = [int(route_id) for route_id in tour.get('route_ids', [])]
        if len(r_ids) < 2:
            continue
        for i in range(len(r_ids) - 1):
            from_idx = id_to_idx.get(r_ids[i])
            to_idx = id_to_idx.get(r_ids[i + 1])
            if from_idx is None or to_idx is None:
                continue
            total_opt_time += time_matrix[from_idx][to_idx]
            total_opt_dist += dist_matrix[from_idx][to_idx]
            total_opt_co2_g += _leg_co2_g(from_idx, to_idx)
    if total_opt_time <= 0 and opt_data.get('total_time_s') is not None:
        total_opt_time = float(opt_data.get('total_time_s', 0))

    # 4. Économies
    # total_opt_time vient de CumulVar OR-Tools (temps cumulé incluant attentes
    # aux fenêtres de temps). Pour comparer équitablement avec le naïf (temps
    # de trajet pur), on borne time_saved_pct à [-100, 100] pour éviter des
    # scores aberrants quand les fenêtres de temps gonflent le cumul OR-Tools.
    time_saved_sec = total_naive_time - total_opt_time
    time_saved_pct = (time_saved_sec / total_naive_time) * 100 if total_naive_time > 0 else 0
    time_saved_pct = max(-100.0, min(100.0, time_saved_pct))

    co2_saved_kg = (total_naive_co2_g - total_opt_co2_g) / 1000.0
    
    benchmark = {
        "naive": {
            "total_time_s": int(total_naive_time),
            "total_dist_m": int(total_naive_dist),
            "total_co2_kg": round(total_naive_co2_g / 1000.0, 3),
            "tours": naive_tours
        },
        "optimized": {
            "total_time_s": int(total_opt_time),
            "total_dist_m": int(total_opt_dist),
            "total_co2_kg": round(total_opt_co2_g / 1000.0, 3),
        },
        "co2_model": {
            "source": "matrix" if co2_matrix is not None else "distance_fallback",
            "fallback_g_per_km": default_co2_g_per_km,
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
    
    os.makedirs(os.path.dirname(benchmark_file), exist_ok=True)
    with open(benchmark_file, 'w') as f:
        json.dump(benchmark, f, indent=4)
    
    print(f"📊 Benchmark terminé. Gain : {benchmark['savings']['score']}%")
    return benchmark

if __name__ == "__main__":
    calculate_benchmark()
