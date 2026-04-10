import osmnx as ox
import pandas as pd
import random
import os
import json
import numpy as np
import requests

# Configuration des chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CORE_DATA = os.path.join(BASE_DIR, 'core_data')
DATA_PATH = os.path.join(CORE_DATA, 'livraisons_5eme.csv') # On garde le même nom pour compatibilité ou on change ? On va garder le même pour l'instant mais on pourrait le rendre dynamique
GRAPH_PATH = os.path.join(CORE_DATA, 'paris5.graphml')
TIME_MATRIX = os.path.join(CORE_DATA, 'live_time_matrix.npy')
DIST_MATRIX = os.path.join(CORE_DATA, 'matrix_5eme.npy')

def generate_new_zone(location_name, num_clients=30):
    """Télécharge une nouvelle zone et génère des points de livraison."""
    print(f"📍 Génération de la zone : {location_name}...")
    
    # 1. Téléchargement du graphe
    try:
        G = ox.graph_from_place(location_name, network_type='drive')
        ox.save_graphml(G, GRAPH_PATH)
        print(f"✅ Graphe de '{location_name}' téléchargé.")
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement d'OSM : {e}")
        return False

    # 2. Sélection des points (Dépôt + Clients)
    # On prend des nœuds aléatoires du graphe pour être sûr qu'ils sont sur la route
    nodes = list(G.nodes(data=True))
    selected_nodes = random.sample(nodes, min(len(nodes), num_clients + 1))
    
    # Le premier point est le dépôt
    depot_node = selected_nodes[0]
    clients_nodes = selected_nodes[1:]
    
    data = []
    # Dépôt (ID 0)
    data.append({
        "id": 0,
        "lat": depot_node[1]['y'],
        "lon": depot_node[1]['x'],
        "poids_colis": 0,
        "nom_client": "DEPOT CENTRAL"
    })
    
    # Clients
    noms_fictifs = ["Boulangerie", "Pharmacie", "Café de la Gare", "Hôtel de Ville", "Librairie", "Supermarché", "Garage", "École", "Mairie", "Poste"]
    for i, node in enumerate(clients_nodes):
        data.append({
            "id": i + 1,
            "lat": node[1]['y'],
            "lon": node[1]['x'],
            "poids_colis": random.randint(5, 50),
            "nom_client": f"{random.choice(noms_fictifs)} {i+1}"
        })
    
    df = pd.DataFrame(data)
    df.to_csv(DATA_PATH, index=False)
    print(f"✅ {num_clients} clients générés dans {DATA_PATH}")

    # 3. Calcul de la Matrice OSRM (Temps)
    coords = [f"{row['lon']},{row['lat']}" for _, row in df.iterrows()]
    coords_str = ";".join(coords)
    url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}"
    params = {"annotations": "duration,distance"}
    
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        res = r.json()
        
        if "durations" in res:
            np.save(TIME_MATRIX, np.array(res["durations"]))
            np.save(DIST_MATRIX, np.array(res["distances"]))
            print(f"✅ Matrices de temps et distance ({len(df)}x{len(df)}) générées.")
            return True
        else:
            print("❌ OSRM n'a pas renvoyé de données.")
            return False
    except Exception as e:
        print(f"❌ Erreur OSRM : {e}")
        return False

if __name__ == "__main__":
    generate_new_zone("Le Marais, Paris", 20)
