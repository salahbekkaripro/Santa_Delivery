import osmnx as ox
import networkx as nx
import pandas as pd
import json
import argparse
import random
from pathlib import Path

def analyze_graph_robustness(graph_path: str | Path):
    """
    Analyses how the graph connectivity (Strongly Connected Components) 
    degrades as we remove the most critical nodes.
    """
    print(f"📊 Loading graph from {graph_path}...")
    G_orig = ox.load_graphml(graph_path)
    
    # We use a copy to mutate
    G = G_orig.copy()
    n_initial = len(G.nodes)
    
    # Initial connectivity
    initial_scc = len(max(nx.strongly_connected_components(G), key=len))
    
    # Identify critical nodes by betweenness
    print("⏳ Identifying critical nodes (Betweenness Centrality)...")
    k_sample = min(200, len(G))
    betweenness = nx.betweenness_centrality(G, k=k_sample, weight="length")
    critical_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
    
    # Robustness test: remove top 1%, 2%, 5%, 10% of nodes and check largest SCC size
    removal_steps = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20]
    robustness_results = []
    
    print("⏳ Running robustness simulations...")
    for pct in [0] + removal_steps:
        G_temp = G_orig.copy()
        num_to_remove = int(n_initial * pct)
        nodes_to_remove = [node_id for node_id, _ in critical_nodes[:num_to_remove]]
        
        G_temp.remove_nodes_from(nodes_to_remove)
        
        if len(G_temp.nodes) > 0:
            sccs = list(nx.strongly_connected_components(G_temp))
            largest_scc = len(max(sccs, key=len)) if sccs else 0
        else:
            largest_scc = 0
            
        robustness_results.append({
            "pct_removed": pct * 100,
            "nodes_removed": num_to_remove,
            "largest_scc_size": largest_scc,
            "connectivity_loss_pct": round((1 - largest_scc / initial_scc) * 100, 2) if initial_scc > 0 else 0
        })

    # Compare with random removal (Baseline)
    random_results = []
    all_nodes = list(G_orig.nodes)
    for pct in [0] + removal_steps:
        G_temp = G_orig.copy()
        num_to_remove = int(n_initial * pct)
        nodes_to_remove = random.sample(all_nodes, num_to_remove)
        G_temp.remove_nodes_from(nodes_to_remove)
        
        if len(G_temp.nodes) > 0:
            sccs = list(nx.strongly_connected_components(G_temp))
            largest_scc = len(max(sccs, key=len)) if sccs else 0
        else:
            largest_scc = 0
            
        random_results.append({
            "pct_removed": pct * 100,
            "largest_scc_size": largest_scc,
            "connectivity_loss_pct": round((1 - largest_scc / initial_scc) * 100, 2) if initial_scc > 0 else 0
        })

    return {
        "metadata": {
            "city": Path(graph_path).stem,
            "initial_nodes": n_initial,
            "initial_scc": initial_scc
        },
        "critical_removal": robustness_results,
        "random_removal": random_results
    }

def print_robustness_report(results):
    print("\n" + "="*60)
    print(f"🛡️ RAPPORT DE ROBUSTESSE DU RÉSEAU : {results['metadata']['city'].upper()}")
    print("="*60)
    print(f"Ce rapport analyse la fragilité du graphe face à des pannes ciblées.")
    print(f"Initialement, la plus grande composante contient {results['metadata']['initial_scc']} nœuds.")
    
    print("\n📉 IMPACT DE LA SUPPRESSION DES NŒUDS CRITIQUES (Attaque ciblée)")
    print(f"{'Remov %':<10} | {'SCC size':<10} | {'Loss %':<10}")
    print("-" * 35)
    for r in results['critical_removal']:
        print(f"{r['pct_removed']:>7.0f}% | {r['largest_scc_size']:>9} | {r['connectivity_loss_pct']:>8}%")
        
    print("\n🎲 IMPACT DE LA SUPPRESSION ALÉATOIRE (Panne fortuite)")
    print(f"{'Remov %':<10} | {'SCC size':<10} | {'Loss %':<10}")
    print("-" * 35)
    for r in results['random_removal']:
        print(f"{r['pct_removed']:>7.0f}% | {r['largest_scc_size']:>9} | {r['connectivity_loss_pct']:>8}%")
        
    # Conclusion
    loss_crit = results['critical_removal'][3]['connectivity_loss_pct'] # 10% removal
    loss_rand = results['random_removal'][3]['connectivity_loss_pct']
    
    print("\n📝 CONCLUSION THÉORIQUE")
    if loss_crit > loss_rand * 1.5:
        print(f"Le réseau est très vulnérable aux attaques ciblées.")
        print(f"La perte de connectivité est {loss_crit/max(0.1, loss_rand):.1f}x plus rapide qu'en cas de panne aléatoire.")
    else:
        print("Le réseau présente une robustesse homogène.")
    print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse de robustesse du graphe.")
    parser.add_argument("--graph", type=str, help="Chemin vers le fichier .graphml")
    parser.add_argument("--output", type=str, help="Sortie JSON")
    
    args = parser.parse_args()
    
    if not args.graph:
        default_graph = "core_data/paris5.graphml"
        if Path(default_graph).exists():
            args.graph = default_graph
        else:
            print("❌ Aucun graphe spécifié.")
            exit(1)
            
    results = analyze_graph_robustness(args.graph)
    print_robustness_report(results)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Résultats sauvegardés dans {args.output}")
