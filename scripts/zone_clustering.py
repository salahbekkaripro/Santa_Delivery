import numpy as np
import pandas as pd
import json
import argparse
import os
from pathlib import Path
import folium

def kmeans_spatial(points, k, max_iters=100):
    """
    Implémentation "maison" de l'algorithme K-Means pour le clustering spatial.
    Prouve la maîtrise algorithmique pour la soutenance.
    """
    # 1. Initialisation aléatoire des centroïdes
    idx = np.random.choice(len(points), k, replace=False)
    centroids = points[idx]
    
    for i in range(max_iters):
        # 2. Attribution : chaque point au centroïde le plus proche
        distances = np.sqrt(((points - centroids[:, np.newaxis])**2).sum(axis=2))
        labels = np.argmin(distances, axis=0)
        
        # 3. Mise à jour : les centroïdes deviennent le centre de masse des labels
        new_centroids = np.array([points[labels == j].mean(axis=0) for j in range(k)])
        
        # Vérification convergence
        if np.all(centroids == new_centroids):
            break
        centroids = new_centroids
        
    return labels, centroids

def analyze_mission_clusters(data_path, num_clusters=3, output_json=None):
    print(f"📊 Chargement des données : {data_path}")
    df = pd.read_csv(data_path)
    
    # On ne garde que les clients (pas le dépôt id=0)
    clients_df = df[df['id'] != 0].copy()
    coords = clients_df[['lat', 'lon']].values
    
    print(f"🧩 Calcul de {num_clusters} zones de livraison...")
    labels, centroids = kmeans_spatial(coords, num_clusters)
    
    clients_df['zone_id'] = labels
    
    # Calcul des stats par zone
    stats = []
    for j in range(num_clusters):
        zone_clients = clients_df[clients_df['zone_id'] == j]
        stats.append({
            "zone_id": int(j),
            "count": len(zone_clients),
            "center": {"lat": float(centroids[j][0]), "lon": float(centroids[j][1])},
            "avg_weight": round(float(zone_clients['poids_kg'].mean()), 2) if 'poids_kg' in zone_clients else 0
        })
    
    results = {
        "metadata": {"num_clients": len(clients_df), "num_zones": num_clusters},
        "zones": stats,
        "assignments": clients_df[['id', 'zone_id']].to_dict(orient='records')
    }
    
    if output_json:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
    return clients_df, centroids, results

def plot_clusters(df, centroids, title="Répartition par Zones (Clustering K-Means)"):
    # Center map on mean coordinates
    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=14)
    
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
    
    for _, row in df.iterrows():
        color = colors[int(row['zone_id']) % len(colors)]
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=5,
            popup=f"Client {row['id']} (Zone {row['zone_id']})",
            color=color,
            fill=True,
            fill_color=color
        ).add_to(m)
        
    for i, c in enumerate(centroids):
        folium.Marker(
            location=[c[0], c[1]],
            popup=f"Centre Zone {i}",
            icon=folium.Icon(color='black', icon='info-sign')
        ).add_to(m)
        
    output_html = "production_output/clustering_map.html"
    m.save(output_html)
    print(f"🖼️ Carte interactive sauvegardée : {output_html}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clustering spatial des livraisons.")
    parser.add_argument("--data", type=str, default="core_data/livraisons_5eme.csv")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--plot", action="store_true")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data):
        print(f"❌ Erreur : {args.data} introuvable.")
        exit(1)
        
    df_clustered, centers, res = analyze_mission_clusters(args.data, num_clusters=args.k, output_json="core_data/clustering_report.json")
    
    print("\n✅ Analyse de sectorisation terminée :")
    for z in res['zones']:
        print(f" - Zone {z['zone_id']} : {z['count']} clients (Centre: {z['center']['lat']:.4f}, {z['center']['lon']:.4f})")
    
    if args.plot:
        plot_clusters(df_clustered, centers)
