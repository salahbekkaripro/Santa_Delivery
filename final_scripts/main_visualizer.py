import pandas as pd
import json
import folium
from folium import plugins
import osmnx as ox
import networkx as nx
import os
import numpy as np

# Définition des chemins relatifs au script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(BASE_DIR, 'core_data', 'livraisons_5eme.csv')
RESULTS_PATH = os.path.join(BASE_DIR, 'production_output', 'resultats_finaux.json')
OUTPUT_HTML = os.path.join(BASE_DIR, 'production_output', 'output_final.html')
GRAPH_PATH = os.path.join(BASE_DIR, 'core_data', 'paris5.graphml')
WEATHER_FILE = os.path.join(BASE_DIR, 'core_data', 'weather_status.json')
BENCHMARK_FILE = os.path.join(BASE_DIR, 'core_data', 'benchmark_results.json')

# Coordonnées exactes du dépôt (Hôtel de Ville)
DEPOT_LAT_LON = (48.8566, 2.3522)

def apply_offset(coords, offset_meters):
    """Applique un décalage géographique aux coordonnées."""
    if offset_meters == 0 or len(coords) < 2: return coords
    lat_factor, lon_factor = 111320.0, 111320.0 * np.cos(np.radians(48.85))
    new_coords = []
    for i in range(len(coords)):
        if i == 0: p1, p2 = np.array(coords[i]), np.array(coords[i+1])
        elif i == len(coords) - 1: p1, p2 = np.array(coords[i-1]), np.array(coords[i])
        else: p1, p2 = np.array(coords[i-1]), np.array(coords[i+1])
        direction = p2 - p1
        mag = np.linalg.norm(direction)
        if mag == 0: new_coords.append(list(coords[i])); continue
        normal = np.array([direction[1], -direction[0]]) / mag
        new_coords.append([coords[i][0] + (normal[0] * offset_meters) / lat_factor,
                           coords[i][1] + (normal[1] * offset_meters) / lon_factor])
    return new_coords

def get_detailed_geometry(G, route_nodes):
    """Extrait la géométrie réelle complète de chaque arête."""
    try:
        gdf_edges = ox.routing.route_to_gdf(G, route_nodes)
        detailed_path = []
        for _, row in gdf_edges.iterrows():
            if 'geometry' in row and row['geometry'] is not None:
                detailed_path.extend([[lat, lon] for lon, lat in row['geometry'].coords])
            else:
                u, v = row['u'], row['v']
                detailed_path.extend([[G.nodes[u]['y'], G.nodes[u]['x']], [G.nodes[v]['y'], G.nodes[v]['x']]])
        if not detailed_path: return [[G.nodes[n]['y'], G.nodes[n]['x']] for n in route_nodes]
        final_path = [detailed_path[0]]
        for pt in detailed_path[1:]:
            if pt != final_path[-1]: final_path.append(pt)
        return final_path
    except: return [[G.nodes[n]['y'], G.nodes[n]['x']] for n in route_nodes]

def generate_map():
    # 1. Chargement
    try:
        df = pd.read_csv(DATA_PATH)
        points_data = df.set_index('id').to_dict('index')
        with open(RESULTS_PATH, 'r') as f: results = json.load(f)
        
        weather_factor, weather_desc = 1.0, "Normale"
        if os.path.exists(WEATHER_FILE):
            with open(WEATHER_FILE, 'r', encoding='utf-8') as f:
                w = json.load(f); weather_factor, weather_desc = w.get('factor', 1.0), w.get('desc', 'Normale')
        
        benchmark = None
        if os.path.exists(BENCHMARK_FILE):
            with open(BENCHMARK_FILE, 'r') as f: benchmark = json.load(f)
    except: print("Erreur chargement données."); return

    # 2. Graphe
    G = ox.load_graphml(GRAPH_PATH)

    # 3. Carte
    tiles = 'cartodbdarkmatter' if weather_factor > 1.2 else 'cartodbpositron'
    m = folium.Map(location=[48.8448, 2.3471], zoom_start=15, tiles=tiles)

    colors = ['#FF0000', '#00FFFF', '#32CD32', '#FF00FF', '#FFFF00']
    offsets = {0: 5, 1: -5, 2: 0}

    # 4. Tracé Naïf (Pointillés Gris)
    if benchmark:
        for tour in benchmark['naive']['tours']:
            naive_coords = []
            for j in range(len(tour['route_ids']) - 1):
                s_id, e_id = tour['route_ids'][j], tour['route_ids'][j+1]
                s_p, e_p = points_data[s_id], points_data[e_id]
                o_n, d_n = ox.nearest_nodes(G, s_p['lon'], s_p['lat']), ox.nearest_nodes(G, e_p['lon'], e_p['lat'])
                try:
                    r_n = nx.shortest_path(G, o_n, d_n, weight='length')
                    naive_coords.extend(get_detailed_geometry(G, r_n))
                except: pass
            if naive_coords:
                folium.PolyLine(naive_coords, color='gray', weight=2, opacity=0.3, dash_array='5, 10').add_to(m)

    # 5. Tracé Optimisé
    for tour in results['tours']:
        v_id, color, offset_m = tour.get('vehicle_id', 0), colors[tour.get('vehicle_id', 0) % len(colors)], offsets.get(tour.get('vehicle_id', 0), 0)
        all_micro_coords = []
        for j in range(len(tour['route_ids']) - 1):
            s_id, e_id = tour['route_ids'][j], tour['route_ids'][j+1]
            s_lat, s_lon = (DEPOT_LAT_LON if s_id == 0 else (points_data[s_id]['lat'], points_data[s_id]['lon']))
            e_lat, e_lon = (DEPOT_LAT_LON if e_id == 0 else (points_data[e_id]['lat'], points_data[e_id]['lon']))
            try:
                r_n = nx.shortest_path(G, ox.nearest_nodes(G, s_lon, s_lat), ox.nearest_nodes(G, e_lon, e_lat), weight='travel_time')
                segment = get_detailed_geometry(G, r_n)
                if segment:
                    segment[0], segment[-1] = [s_lat, s_lon], [e_lat, e_lon]
                    if all_micro_coords and all_micro_coords[-1] == segment[0]: segment = segment[1:]
                    all_micro_coords.extend(segment)
            except: pass
        if offset_m != 0 and all_micro_coords: all_micro_coords = apply_offset(all_micro_coords, offset_m)
        if all_micro_coords:
            plugins.AntPath(locations=all_micro_coords, color=color, weight=4, opacity=0.8, hardwareAcceleration=True).add_to(m)

    # 6. Widgets
    folium.Marker(location=DEPOT_LAT_LON, icon=folium.Icon(color='black', icon='home', prefix='fa')).add_to(m)
    for nid in points_data:
        if nid != 0: folium.CircleMarker(location=[points_data[nid]['lat'], points_data[nid]['lon']], radius=4, color='gray', fill=True, fill_opacity=0.4).add_to(m)

    # Météo (Top Right)
    w_icon = "❄️" if weather_factor >= 2.0 else ("🌧️" if weather_factor >= 1.3 else "☀️")
    folium.Element(f'''<div style="position: fixed; top: 10px; right: 10px; z-index:9999; background: white; padding: 10px; border-radius: 5px; border: 2px solid black;">
    <b>{w_icon} Météo : {weather_desc}</b> | Impact : x{weather_factor}</div>''').add_to(m.get_root().html)

    # Benchmark (Bottom Left)
    if benchmark:
        sav = benchmark['savings']
        folium.Element(f'''<div style="position: fixed; bottom: 50px; left: 50px; z-index:9999; background: white; padding: 10px; border-radius: 8px; border: 2px solid #27ae60; width: 220px;">
        <b style="color:#27ae60;">📊 Rapport d'Efficacité IA</b><br>
        ⏱️ Temps gagné : +{sav['time_saved_min']} min<br>
        🌱 CO2 évité : {sav['co2_saved_kg']} kg<br>
        🚀 Score IA : {sav['score']}%</div>''').add_to(m.get_root().html)

    m.save(OUTPUT_HTML)
    print(f"✅ Carte générée avec benchmark ({benchmark['savings']['score'] if benchmark else 'N/A'}%)")

if __name__ == "__main__":
    generate_map()
