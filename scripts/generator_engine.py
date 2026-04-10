import osmnx as ox
import pandas as pd
import random
import os
import json
import numpy as np
import requests
import networkx as nx

# Configuration des chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CORE_DATA = os.path.join(BASE_DIR, 'core_data')
DATA_PATH = os.path.join(CORE_DATA, 'livraisons_5eme.csv') # On garde le même nom pour compatibilité ou on change ? On va garder le même pour l'instant mais on pourrait le rendre dynamique
GRAPH_PATH = os.path.join(CORE_DATA, 'paris5.graphml')
TIME_MATRIX = os.path.join(CORE_DATA, 'live_time_matrix.npy')
DIST_MATRIX = os.path.join(CORE_DATA, 'matrix_5eme.npy')

def _fallback_dist_m(num_clients: int) -> int:
    # Distance en mètres pour graph_from_point si la géométrie d'un lieu est
    # trop petite / invalide (ou ne contient aucun axe "drive").
    # Ajusté pour fournir suffisamment de nœuds même à 50-100 clients.
    return int(min(8000, max(1500, 800 + num_clients * 40)))

def _compute_matrices_local(G, node_ids: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """
    Calcule (durations, distances) localement à partir du graphe OSMnx/NetworkX.
    - durations: secondes (via 'travel_time')
    - distances: mètres (via 'length')
    """
    if not node_ids:
        raise ValueError("node_ids vide")

    # S'assure d'avoir 'travel_time' sur les arêtes
    if not any("travel_time" in data for _, _, data in G.edges(data=True)):
        G = ox.add_edge_speeds(G)        # km/h
        G = ox.add_edge_travel_times(G)  # seconds

    n = len(node_ids)
    durations = np.full((n, n), 1e9, dtype=float)
    distances = np.full((n, n), 1e9, dtype=float)

    # Pre-fill diagonal
    np.fill_diagonal(durations, 0.0)
    np.fill_diagonal(distances, 0.0)

    for i, origin in enumerate(node_ids):
        dist_len = nx.single_source_dijkstra_path_length(G, origin, weight="length")
        dist_tt = nx.single_source_dijkstra_path_length(G, origin, weight="travel_time")
        for j, dest in enumerate(node_ids):
            if dest in dist_len:
                distances[i, j] = float(dist_len[dest])
            if dest in dist_tt:
                durations[i, j] = float(dist_tt[dest])

    return durations, distances


def generate_new_zone(location_name, num_clients=30):
    """
    Télécharge une nouvelle zone et génère des points de livraison.

    Retourne:
      - (True, "") si OK
      - (False, "message") si échec (message actionnable pour l'UI)
    """
    print(f"📍 Génération de la zone : {location_name}...")
    
    # 1. Téléchargement du graphe
    try:
        G = ox.graph_from_place(location_name, network_type="drive")
        ox.save_graphml(G, GRAPH_PATH)
        print(f"✅ Graphe de '{location_name}' téléchargé.")
    except Exception as e:
        msg = str(e)
        print(f"❌ Erreur lors du téléchargement d'OSM : {msg}")

        # Cas fréquent: le polygon renvoyé par le géocodeur ne contient aucun nœud "drive"
        # => fallback sur un graphe autour d'un point (plus robuste).
        try:
            center = ox.geocode(location_name)  # (lat, lon)
            dist_m = _fallback_dist_m(int(num_clients))
            print(f"↪️ Fallback: graph_from_point({center}, dist={dist_m}m)")
            G = ox.graph_from_point(center, dist=dist_m, network_type="drive")
            ox.save_graphml(G, GRAPH_PATH)
            print(f"✅ Graphe (fallback point) téléchargé pour '{location_name}'.")
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
    if len(nodes) < (num_clients + 1):
        return (
            False,
            "OSM: pas assez de nœuds routiers dans la zone. "
            "Réduisez le nombre de clients ou choisissez une zone plus grande.",
        )
    selected_nodes = random.sample(nodes, min(len(nodes), num_clients + 1))
    
    # Le premier point est le dépôt
    depot_node = selected_nodes[0]
    clients_nodes = selected_nodes[1:]
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

    # 3. Calcul de la Matrice (Temps/Distance) via OSRM (fallback local si OSRM down)
    coords = [f"{row['lon']},{row['lat']}" for _, row in df.iterrows()]
    coords_str = ";".join(coords)
    url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}"
    params = {"annotations": "duration,distance"}
    
    try:
        timeout_s = int(os.getenv("OSRM_TIMEOUT_S", "90"))
        sess = requests.Session()
        last_exc: Exception | None = None
        for attempt in range(1, 3):
            try:
                r = sess.get(url, params=params, timeout=timeout_s)
                r.raise_for_status()
                res = r.json()
                if "durations" not in res:
                    raise RuntimeError("OSRM: champ 'durations' manquant")

                np.save(TIME_MATRIX, np.array(res["durations"]))
                np.save(DIST_MATRIX, np.array(res.get("distances", [])))
                print(f"✅ Matrices OSRM de temps/distance ({len(df)}x{len(df)}) générées.")
                return True, ""
            except Exception as e:
                last_exc = e
                print(f"⚠️ OSRM tentative {attempt}/2 échouée : {e}")

        raise last_exc if last_exc else RuntimeError("OSRM inconnu")
    except Exception as e:
        msg = str(e)
        print(f"❌ Erreur OSRM : {msg}")

        # Fallback local: calcule la matrice sur le graphe (plus lent mais fiable)
        try:
            print("↪️ Fallback local: calcul des matrices via NetworkX…")
            durations, distances = _compute_matrices_local(G, node_ids)
            np.save(TIME_MATRIX, durations)
            np.save(DIST_MATRIX, distances)
            print(f"✅ Matrices locales de temps/distance ({len(df)}x{len(df)}) générées.")
            return True, (
                "OSRM indisponible (timeout/rate-limit). "
                "Matrice calculée localement (peut être un peu plus lente)."
            )
        except Exception as e2:
            msg2 = str(e2)
            print(f"❌ Fallback local échoué : {msg2}")
            return False, (
                "OSRM: impossible de calculer la matrice (service public down / rate-limit) "
                "et fallback local échoué.\n"
                f"Détail OSRM: {msg}\nDétail local: {msg2}"
            )

if __name__ == "__main__":
    ok, msg = generate_new_zone("Le Marais, Paris", 20)
    print(ok, msg)
