import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

# Ajout du dossier racine au sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app import services
from scripts import ro_improvements
from final_scripts.solve_santa_final import solve_vrp

def calculate_route_distance(tours, dist_matrix):
    total_dist = 0
    for tour in tours:
        route = tour["route_ids"]
        for i in range(len(route) - 1):
            total_dist += dist_matrix[route[i]][route[i+1]]
    return total_dist

def run_benchmark(num_missions=5, num_clients=15):
    print(f"🚀 Lancement du Benchmark (Mode TSP 1 véhicule) : {num_missions} missions, {num_clients} clients.")
    results = []
    zone = "Le Marais, Paris"
    
    for i in range(num_missions):
        print(f"\n📦 Mission {i+1}/{num_missions}...")
        try:
            mission_payload = {
                "zone": zone, "num_clients": num_clients, "weather_key": "Clear",
                "num_vehicles": 1, "vehicle_capacity": 500, "speed_multiplier": 1.0,
                "optimization_target": "time"
            }
            mission_data = services.create_mission(mission_payload)
            mission_id = mission_data["mission_id"]
            paths, mission, _ = services.load_mission_bundle(mission_id)
            
            time_matrix = np.load(paths.time_matrix_file)
            dist_matrix = np.load(paths.dist_matrix_file)
            
            # 1. NN (Humain Glouton)
            nn_result = ro_improvements.nearest_neighbor_tour(num_clients, time_matrix)
            nn_dist = 0
            nn_route = [0] + nn_result["route"] + [0]
            for j in range(len(nn_route) - 1):
                nn_dist += dist_matrix[nn_route[j]][nn_route[j+1]]
            
            # 2. AI (OR-Tools)
            ai_res = solve_vrp(
                num_vehicles=1, vehicle_capacity=500,
                data_path=str(paths.data_file), time_matrix_path=str(paths.time_matrix_file),
                dist_matrix_path=str(paths.dist_matrix_file), weather_file=str(paths.weather_file),
                optimization_target="time", solver_time_limit_s=5,
                first_solution_strategy="parallel_cheapest_insertion",
                local_search_metaheuristic="guided_local_search",
                output_path=str(paths.root_dir / "ai_res.json")
            )
            
            if not ai_res: continue

            ai_dist = calculate_route_distance(ai_res["tours"], dist_matrix)

            results.append({
                "nn": {"time": nn_result["total_time_s"], "dist": nn_dist},
                "ai": {"time": ai_res["total_time_s"], "dist": ai_dist}
            })
            print(f"✅ Mission {i+1} terminée.")

        except Exception as e:
            print(f"❌ Erreur mission {i+1}: {e}")

    generate_report(results)

def generate_report(results):
    if not results: return
    avg_nn_t = np.mean([r["nn"]["time"] for r in results])
    avg_ai_t = np.mean([r["ai"]["time"] for r in results])
    avg_nn_d = np.mean([r["nn"]["dist"] for r in results])
    avg_ai_d = np.mean([r["ai"]["dist"] for r in results])
    
    gain_t = (avg_nn_t - avg_ai_t) / avg_nn_t * 100
    gain_d = (avg_nn_d - avg_ai_d) / avg_nn_d * 100

    report = f"""# 📊 Rapport de Performance IA vs Humain (TSP 1 véhicule)
Généré le {pd.Timestamp.now().strftime('%d/%m/%Y')}

Ce benchmark compare l'algorithme **Google OR-Tools** (IA) à une approche **Gloutonne** (Humain) sur un échantillon de {len(results)} missions de {len(results)} clients.

| Métrique | Humain (Glouton) | IA Optimisée | Gain |
| :--- | :--- | :--- | :--- |
| **Temps de trajet** | {avg_nn_t:.1f}s | **{avg_ai_t:.1f}s** | **{gain_t:.1f}%** |
| **Distance totale** | {avg_nn_d/1000:.2f}km | **{avg_ai_d/1000:.2f}km** | **{gain_d:.1f}%** |

## Analyse des résultats
Contrairement à l'approche gloutonne qui choisit le client le plus proche à chaque étape, l'IA d'OR-Tools utilise des métaheuristiques (Guided Local Search) pour explorer des milliers de combinaisons. Elle évite ainsi les "pièges" topologiques où un humain se retrouverait obligé de faire un long trajet de retour en fin de mission.

## Conclusion pour la soutenance
L'optimisation mathématique permet de réduire les coûts opérationnels de **{gain_t:.1f}%** en moyenne. Sur une flotte logistique réelle, cela représente des économies majeures de carburant et de temps de travail.
"""
    with open("RAPPORT_PERFORMANCES_IA.md", "w") as f: f.write(report)
    print("\n📄 Rapport généré : RAPPORT_PERFORMANCES_IA.md")

if __name__ == "__main__":
    run_benchmark(5, 20) # 20 clients pour bien voir la différence
