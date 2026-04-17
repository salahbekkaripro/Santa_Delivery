import osmnx as ox
import pandas as pd
import random
import os
import json
import math
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


def generate_new_zone(
    location_name,
    num_clients=30,
    data_path=DATA_PATH,
    graph_path=GRAPH_PATH,
    time_matrix_path=TIME_MATRIX,
    dist_matrix_path=DIST_MATRIX,
    center_lat=None,
    center_lon=None,
    search_radius_km=None,
):
    """
    Télécharge une nouvelle zone et génère des points de livraison.

    Retourne:
      - (True, "") si OK
      - (False, "message") si échec (message actionnable pour l'UI)
    """
    print(f"📍 Génération de la zone : {location_name}...")
    
    # 1. Téléchargement du graphe
    explicit_center = center_lat is not None and center_lon is not None and search_radius_km is not None
    try:
        if explicit_center:
            dist_m = max(200, int(float(search_radius_km) * 1000))
            center = (float(center_lat), float(center_lon))
            print(f"📌 Zone cible: centre={center} rayon={search_radius_km} km")
            G = ox.graph_from_point(center, dist=dist_m, network_type="drive")
            G = _prepare_graph(G, int(num_clients) + 1)
            os.makedirs(os.path.dirname(graph_path), exist_ok=True)
            ox.save_graphml(G, graph_path)
            print(f"✅ Graphe circulaire téléchargé autour de '{location_name}'.")
        else:
            G = ox.graph_from_place(location_name, network_type="drive")
            G = _prepare_graph(G, int(num_clients) + 1)
            os.makedirs(os.path.dirname(graph_path), exist_ok=True)
            ox.save_graphml(G, graph_path)
            print(f"✅ Graphe de '{location_name}' téléchargé.")
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
            print(f"↪️ Fallback: graph_from_point({center}, dist={dist_m}m)")
            G = ox.graph_from_point(center, dist=dist_m, network_type="drive")
            G = _prepare_graph(G, int(num_clients) + 1)
            os.makedirs(os.path.dirname(graph_path), exist_ok=True)
            ox.save_graphml(G, graph_path)
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
    
    # Clients
    noms_fictifs = ["Boulangerie", "Pharmacie", "Café de la Gare", "Hôtel de Ville", "Librairie", "Supermarché", "Garage", "École", "Mairie", "Poste"]
    for i, node in enumerate(clients_nodes):
        # Fenêtres de temps aléatoires (sur une base de 2h = 7200s)
        # 30% des clients ont une contrainte forte (matin ou fin de tournée)
        has_constraint = random.random() < 0.3
        tw_start, tw_end = 0, 14400 # Par défaut 4h de large (très large)
        if has_constraint:
            if random.random() < 0.5:
                tw_start, tw_end = 0, 3600 # Livraison impérative dans la 1ère heure
            else:
                tw_start, tw_end = 3600, 7200 # Livraison dans la 2ème heure
        
        data.append({
            "id": i + 1,
            "lat": node[1]['y'],
            "lon": node[1]['x'],
            "poids_colis": random.randint(5, 50),
            "nom_client": f"{random.choice(noms_fictifs)} {i+1}",
            "tw_start": tw_start,
            "tw_end": tw_end
        })
    
    # Depot a aussi une fenêtre de temps (ouverture/fermeture)
    data[0]["tw_start"] = 0
    data[0]["tw_end"] = 28800 # 8h max pour la journée totale
    
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    df.to_csv(data_path, index=False)
    print(f"✅ {num_clients} clients générés dans {data_path}")

    # 3. Calcul de la Matrice (Temps/Distance)
    # OSRM public peut timeouter sur de grosses matrices -> fallback local.
    max_osrm_points = int(os.getenv("OSRM_MAX_POINTS", "40"))
    if len(df) > max_osrm_points:
        durations, distances = _compute_matrices_local(G, node_ids)
        np.save(time_matrix_path, durations)
        np.save(dist_matrix_path, distances)
        print(f"✅ Matrices locales de temps/distance ({len(df)}x{len(df)}) générées.")
        return True, (
            f"OSRM sauté (>{max_osrm_points} points). "
            "Matrice calculée localement (peut être un peu plus lente)."
        )

    # OSRM (fallback local si OSRM down)
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

                np.save(time_matrix_path, np.array(res["durations"]))
                np.save(dist_matrix_path, np.array(res.get("distances", [])))
                print(f"✅ Matrices OSRM de temps/distance ({len(df)}x{len(df)}) générées.")
                return True, ""
            except Exception as e:
                last_exc = e
                print(f"⚠️ OSRM tentative {attempt}/2 échouée : {e}")

        raise last_exc if last_exc else RuntimeError("OSRM inconnu")
    except Exception as e:
        msg = str(e)
        print(f"⚠️ OSRM indisponible : {msg}")

        # Fallback local: calcule la matrice sur le graphe (plus lent mais fiable)
        try:
            print("↪️ Fallback local: calcul des matrices via NetworkX…")
            durations, distances = _compute_matrices_local(G, node_ids)
            np.save(time_matrix_path, durations)
            np.save(dist_matrix_path, distances)
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
