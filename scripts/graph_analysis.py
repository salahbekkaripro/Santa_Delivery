import osmnx as ox
import networkx as nx
import pandas as pd
import json
import argparse
from pathlib import Path

def analyze_graph_centrality(graph_path: str | Path, top_n: int = 10):
    """
    Analyses the centrality of nodes in a street network graph.
    - Degree Centrality: Number of connections.
    - Betweenness Centrality: How often a node lies on the shortest path between others.
    """
    print(f"📊 Loading graph from {graph_path}...")
    G = ox.load_graphml(graph_path)
    
    # Convert to undirected for some centrality measures if needed, 
    # but street networks are directed. We'll use the directed version.
    
    print("⏳ Calculating Degree Centrality...")
    degree_centrality = nx.degree_centrality(G)
    
    print("⏳ Calculating Betweenness Centrality (this can take a while for large graphs)...")
    # Betweenness is computationally expensive, we use a sample if the graph is too large
    if len(G) > 2000:
        print("⚠️ Large graph detected, using sampling for betweenness centrality.")
        betweenness_centrality = nx.betweenness_centrality(G, k=300, weight="length")
    else:
        betweenness_centrality = nx.betweenness_centrality(G, weight="length")
    
    # Get top nodes
    top_degree = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_betweenness = sorted(betweenness_centrality.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    results = {
        "metadata": {
            "node_count": len(G.nodes),
            "edge_count": len(G.edges),
            "graph_path": str(graph_path)
        },
        "top_degree_nodes": [],
        "top_betweenness_nodes": []
    }
    
    for node_id, score in top_degree:
        node_data = G.nodes[node_id]
        results["top_degree_nodes"].append({
            "id": node_id,
            "score": round(score, 5),
            "lat": node_data.get("y"),
            "lon": node_data.get("x"),
            "street": node_data.get("street_count")
        })
        
    for node_id, score in top_betweenness:
        node_data = G.nodes[node_id]
        results["top_betweenness_nodes"].append({
            "id": node_id,
            "score": round(score, 5),
            "lat": node_data.get("y"),
            "lon": node_data.get("x")
        })
        
    return results

def print_report(results):
    print("\n" + "="*50)
    print("🚀 RAPPORT D'ANALYSE DE GRAPH (TOPOLOGIE)")
    print("="*50)
    print(f"Noeuds : {results['metadata']['node_count']}")
    print(f"Arêtes : {results['metadata']['edge_count']}")
    
    print("\n📍 POINTS LES PLUS CONNECTÉS (Degree Centrality)")
    print("Ce sont les intersections avec le plus de rues sortantes/entrantes.")
    for i, node in enumerate(results["top_degree_nodes"], 1):
        print(f"{i}. Noeud {node['id']} : Score {node['score']} (Lat: {node['lat']}, Lon: {node['lon']})")
        
    print("\n🛣️ POINTS DE PASSAGE CRITIQUES (Betweenness Centrality)")
    print("Ce sont les 'goulots d'étranglement' du réseau.")
    for i, node in enumerate(results["top_betweenness_nodes"], 1):
        print(f"{i}. Noeud {node['id']} : Score {node['score']} (Lat: {node['lat']}, Lon: {node['lon']})")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse de la centralité du graphe routier.")
    parser.add_argument("--graph", type=str, help="Chemin vers le fichier .graphml")
    parser.add_argument("--output", type=str, help="Chemin vers le fichier JSON de sortie")
    
    args = parser.parse_args()
    
    if not args.graph:
        # Essayer de trouver un graphe par défaut
        default_graph = "core_data/paris5.graphml"
        if Path(default_graph).exists():
            args.graph = default_graph
        else:
            print("❌ Aucun graphe spécifié et paris5.graphml introuvable.")
            exit(1)
            
    try:
        results = analyze_graph_centrality(args.graph)
        print_report(results)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"✅ Résultats sauvegardés dans {args.output}")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse : {e}")
