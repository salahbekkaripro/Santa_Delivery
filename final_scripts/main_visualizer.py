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
DEFAULT_DEPARTURE_TIME = "18:00"


def format_minutes(seconds):
    minutes = max(0, int(round(float(seconds) / 60)))
    return f"{minutes} min"


def parse_time_to_seconds(time_str):
    hours, minutes = [int(part) for part in str(time_str).split(":", 1)]
    return hours * 3600 + minutes * 60


def format_clock_time(total_seconds):
    total_seconds = int(round(float(total_seconds)))
    hours = (total_seconds // 3600) % 24
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def route_length_m(G, route_nodes):
    total = 0.0
    for u, v in zip(route_nodes[:-1], route_nodes[1:]):
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue
        total += float(min(data.get("length", 0.0) for data in edge_data.values()))
    return total


def route_travel_time_s(G, route_nodes):
    total = 0.0
    for u, v in zip(route_nodes[:-1], route_nodes[1:]):
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue
        total += float(min(data.get("travel_time", 0.0) for data in edge_data.values()))
    return total


def point_label(points_data, point_id):
    if point_id == 0:
        return "Dépôt"
    data = points_data.get(point_id, {})
    return data.get("nom_client", f"Client #{point_id}")


def route_popup_html(title, duration_s, dist_m, segment_idx, segment_count, arrival_time_str=None):
    html = (
        f"<b>{title}</b><br>"
        f"Segment {segment_idx}/{segment_count}<br>"
        f"⏱️ {format_minutes(duration_s)}<br>"
        f"📏 {dist_m/1000:.2f} km"
    )
    if arrival_time_str:
        html += f"<br>🕒 Arrivée estimée : {arrival_time_str}"
    return html

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

def generate_map(custom_colors=None, line_weight=4, show_names=False, departure_time=DEFAULT_DEPARTURE_TIME):
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
    except Exception as e:
        print(f"Erreur chargement données: {e}")
        return

    # 2. Graphe
    G = ox.load_graphml(GRAPH_PATH)

    # 3. Calcul du centre de la carte
    depot = df[df['id'] == 0].iloc[0]
    map_center = [depot['lat'], depot['lon']]
    depot_coords = (depot['lat'], depot['lon'])

    departure_time_s = parse_time_to_seconds(departure_time)

    # 3. Carte
    tiles = 'cartodbdarkmatter' if weather_factor > 1.2 else 'cartodbpositron'
    m = folium.Map(location=map_center, zoom_start=14, tiles=tiles)

    # Couleurs
    colors = custom_colors if custom_colors else ['#FF0000', '#00FFFF', '#32CD32', '#FF00FF', '#FFFF00']
    
    # Décalages
    offsets = [0, 5, -5, 10, -10, 15, -15, 20, -20, 25]
    ai_stop_meta = {}

    # 4. Tracé Naïf (Pointillés Gris)
    if benchmark:
        for tour in benchmark['naive']['tours']:
            naive_coords = []
            for j in range(len(tour['route_ids']) - 1):
                s_id, e_id = tour['route_ids'][j], tour['route_ids'][j+1]
                s_p = ({"lat": depot_coords[0], "lon": depot_coords[1]} if s_id == 0 else points_data[s_id])
                e_p = ({"lat": depot_coords[0], "lon": depot_coords[1]} if e_id == 0 else points_data[e_id])
                o_n, d_n = ox.nearest_nodes(G, s_p['lon'], s_p['lat']), ox.nearest_nodes(G, e_p['lon'], e_p['lat'])
                try:
                    r_n = nx.shortest_path(G, o_n, d_n, weight='length')
                    naive_coords.extend(get_detailed_geometry(G, r_n))
                except: pass
            if naive_coords:
                folium.PolyLine(naive_coords, color='gray', weight=2, opacity=0.3, dash_array='5, 10').add_to(m)

    # 5. Tracé Optimisé
    for i, tour in enumerate(results['tours']):
        color = colors[i % len(colors)]
        offset_m = offsets[i % len(offsets)]
        vehicle_id = int(tour.get('vehicle_id', i))
        title = f"🛷 Traîneau #{vehicle_id + 1}"
        segment_count = max(0, len(tour['route_ids']) - 1)
        segment_infos = []
        for j in range(len(tour['route_ids']) - 1):
            s_id, e_id = tour['route_ids'][j], tour['route_ids'][j+1]
            s_lat, s_lon = (depot_coords if s_id == 0 else (points_data[s_id]['lat'], points_data[s_id]['lon']))
            e_lat, e_lon = (depot_coords if e_id == 0 else (points_data[e_id]['lat'], points_data[e_id]['lon']))
            try:
                r_n = nx.shortest_path(G, ox.nearest_nodes(G, s_lon, s_lat), ox.nearest_nodes(G, e_lon, e_lat), weight='travel_time')
                segment = get_detailed_geometry(G, r_n)
                if segment:
                    segment[0], segment[-1] = [s_lat, s_lon], [e_lat, e_lon]
                    if offset_m != 0:
                        segment = apply_offset(segment, offset_m)
                    segment_infos.append({
                        "from_id": int(s_id),
                        "to_id": int(e_id),
                        "coords": segment,
                        "dist_m": route_length_m(G, r_n),
                        "base_time_s": route_travel_time_s(G, r_n),
                        "title": f"{title} · {point_label(points_data, s_id)} → {point_label(points_data, e_id)}",
                        "segment_idx": j + 1,
                    })
            except: pass

        total_base_time_s = sum(seg["base_time_s"] for seg in segment_infos)
        target_tour_time_s = float(tour.get("duration_s", total_base_time_s))
        tour_scale = (target_tour_time_s / total_base_time_s) if total_base_time_s > 0 else 1.0
        cumulative_eta_s = 0.0
        stop_order = 0
        for seg in segment_infos:
            seg_time_s = float(seg["base_time_s"]) * tour_scale
            seg_dist_m = float(seg["dist_m"])
            arrival_time_str = format_clock_time(departure_time_s + cumulative_eta_s + seg_time_s)
            plugins.AntPath(
                locations=seg["coords"],
                color=color,
                weight=line_weight,
                opacity=0.8,
                hardwareAcceleration=True,
                tooltip=(
                    f"{seg['title']} · "
                    f"{format_minutes(seg_time_s)} · "
                    f"{seg_dist_m/1000:.2f} km · "
                    f"{arrival_time_str}"
                ),
                popup=folium.Popup(
                    route_popup_html(
                        seg["title"],
                        seg_time_s,
                        seg_dist_m,
                        seg["segment_idx"],
                        segment_count,
                        arrival_time_str=arrival_time_str,
                    ),
                    max_width=300,
                ),
            ).add_to(m)
            cumulative_eta_s += seg_time_s
            if seg["to_id"] != 0:
                stop_order += 1
                ai_stop_meta[int(seg["to_id"])] = {
                    "vehicle_id": vehicle_id,
                    "stop_order": stop_order,
                    "eta_s": cumulative_eta_s,
                    "arrival_time_str": arrival_time_str,
                }

    # 6. Widgets
    folium.Marker(
        location=depot_coords,
        icon=folium.Icon(color='black', icon='home', prefix='fa'),
        tooltip=f"Dépôt Central · Départ {departure_time}",
        popup=folium.Popup(f"<b>Dépôt Central</b><br>🛫 Départ prévu : {departure_time}", max_width=220),
    ).add_to(m)
    
    # Points de livraison
    for nid, data in points_data.items():
        if nid != 0:
            popup_text = f"Colis #{nid}<br>Poids: {data['poids_colis']}kg"
            if show_names and 'nom_client' in data:
                popup_text = f"<b>{data['nom_client']}</b><br>" + popup_text
            stop_meta = ai_stop_meta.get(int(nid))
            if stop_meta:
                popup_text += (
                    f"<br>🛷 Traîneau #{int(stop_meta['vehicle_id']) + 1}"
                    f"<br>📍 Stop #{int(stop_meta['stop_order'])}"
                    f"<br>⏰ Arrivée estimée : {format_minutes(stop_meta['eta_s'])}"
                    f"<br>🕒 Heure d'arrivée : {stop_meta['arrival_time_str']}"
                )
                if show_names and 'nom_client' in data:
                    popup_text = (
                        f"<b>{data['nom_client']}</b><br>"
                        f"⏰ ETA : {format_minutes(stop_meta['eta_s'])}<br>"
                        f"🕒 Arrivée estimée : {stop_meta['arrival_time_str']}<br>"
                        f"🛷 Traîneau #{int(stop_meta['vehicle_id']) + 1} · Stop #{int(stop_meta['stop_order'])}<br>"
                        f"Colis #{nid}<br>Poids: {data['poids_colis']}kg"
                    )
            
            folium.CircleMarker(
                location=[data['lat'], data['lon']],
                radius=4,
                color='gray',
                fill=True,
                fill_opacity=0.6,
                tooltip=popup_text if show_names else None,
                popup=popup_text
            ).add_to(m)

    m.save(OUTPUT_HTML)
    print(f"✅ Carte générée (Épaisseur: {line_weight}, Noms: {show_names})")

if __name__ == "__main__":
    generate_map()
