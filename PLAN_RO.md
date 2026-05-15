# Plan RO — Améliorations Recherche Opérationnelle

## Contexte

Ce projet implémente un VRP (Vehicle Routing Problem) sur des graphes routiers OSM pour simuler
la tournée du Père Noël. Le backend utilise OR-Tools + networkx/osmnx. Ce plan détaille les
améliorations algorithmiques apportées.

---

## 1. A\* avec heuristique haversine

**Fichier :** `scripts/routing_payloads.py`

**Problème :** `ox.routing.shortest_path` utilise Dijkstra — il explore les nœuds sans direction
préférentielle, ce qui est sous-optimal sur des graphes géographiques.

**Solution :** `nx.astar_path` avec une heuristique admissible basée sur la distance de vol à
50 km/h (vitesse max des arcs). L'heuristique est admissible (ne surestime jamais) car la
distance euclidienne est toujours ≤ la distance routière. A\* explore donc strictement moins de
nœuds que Dijkstra tout en garantissant l'optimalité.

**Formule :**
```
h(u, v) = haversine(u, v) / 13.89 m/s   (13.89 = 50 km/h)
```

**Fallback :** si A\* échoue (graphe déconnecté, nœud manquant), repli sur Dijkstra.

---

## 2. 2-opt local search sur la solution humaine

**Fichier :** `scripts/ro_improvements.py`, `backend/app/services.py`

**Problème :** Le debrief compare uniquement la solution humaine brute à la solution IA OR-Tools,
sans montrer le potentiel d'amélioration local de la solution humaine elle-même.

**Solution :** Appliquer 2-opt sur chaque route humaine après la mission. L'algorithme inverse
des sous-segments de la route et accepte l'inversion si elle réduit le coût total :

```
Pour toute paire (i, j) :
  nouvelle_route = route[:i] + route[i:j+1][::-1] + route[j+1:]
  si coût(nouvelle_route) < coût(route) : accepter
```

**Données utilisées :** matrice de temps précalculée (`.npy`) — O(n²) par itération, convergence
garantie car le nombre de permutations est fini et le coût est strictement décroissant.

**Sortie dans le debrief :**
- Gain potentiel en secondes et en % par traîneau
- Gain total sur l'ensemble de la flotte
- Ordre optimal des clients par traîneau

---

## 3. API Dijkstra pas-à-pas (pédagogique)

**Fichier :** `scripts/ro_improvements.py`, `backend/app/services.py`, `backend/app/main.py`

**Endpoint :** `GET /api/missions/{id}/graph/dijkstra-steps?from_node=X&to_node=Y`

**But :** Visualiser l'exécution de Dijkstra nœud par nœud sur le graphe réel de la mission.
Chaque étape correspond à un nœud finalisé (extrait du tas min).

**Réponse :**
```json
{
  "steps": [{"step": 0, "node": 123, "dist": 0, "lat": 48.8, "lon": 2.3, "predecessor": null}, ...],
  "steps_count": 142,
  "path": [123, ..., 456],
  "total_cost": 384.5,
  "reached": true,
  "truncated": false
}
```

**Limite :** max 400 nœuds explorés (configurable) pour éviter les timeout sur grands graphes.

---

## 4. Métriques structurelles du graphe

**Fichier :** `scripts/ro_improvements.py`, `backend/app/services.py`, `backend/app/main.py`

**Endpoint :** `GET /api/missions/{id}/graph/metrics`

**Métriques exposées :**
| Métrique | Description |
|---|---|
| `num_nodes` | Nombre de nœuds du graphe routier |
| `num_edges` | Nombre d'arcs (orientés) |
| `avg_degree` | Degré sortant moyen |
| `max_degree` | Degré maximum (carrefour le plus connecté) |
| `density` | Densité du graphe (arcs / arcs possibles) |
| `is_strongly_connected` | Composante fortement connexe unique |
| `largest_scc_pct` | % du graphe dans la plus grande CFC |
| `avg_clustering` | Coefficient de clustering moyen (non-orienté) |
| `top_betweenness_nodes` | Top 5 nœuds par centralité d'intermédiarité (approx.) |

**Note :** La centralité betweenness est calculée par échantillonnage (k=30 pivots) pour
maintenir des temps de réponse acceptables sur les grands graphes.

---

## Fichiers modifiés

| Fichier | Modification |
|---|---|
| `scripts/ro_improvements.py` | **Nouveau** — 2-opt, Dijkstra steps, graph metrics |
| `scripts/routing_payloads.py` | A\* remplace Dijkstra dans `_collect_candidate_routes` |
| `backend/app/services.py` | `get_graph_metrics`, `get_dijkstra_steps`, 2-opt dans debrief |
| `backend/app/main.py` | 2 nouveaux endpoints GET |
| `frontend/lib/types.ts` | `GraphMetrics`, `DijkstraResult`, `TwoOptResult` |
| `frontend/lib/api.ts` | `getGraphMetrics`, `getDijkstraSteps` |
| `frontend/components/debrief-view.tsx` | Panneaux 2-opt et métriques graphe |
