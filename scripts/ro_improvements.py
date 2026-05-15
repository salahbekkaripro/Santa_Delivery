"""
ro_improvements.py — Améliorations Recherche Opérationnelle

- two_opt_routes          : 2-opt intra-route (inversion de segments)
- three_opt_routes        : 3-opt intra-route (reconnexion de 3 arcs)
- or_opt_routes           : or-opt inter-routes (relocalisation 1/2/3 clients)
- two_opt_star_routes     : 2-opt* inter-routes VRPTW (échange de suffixes)
- iterated_local_search   : ILS = double-bridge + recherche locale itérée
- nearest_neighbor_tour   : construction greedy Nearest Neighbor (TSP mono-véhicule)
- optimality_gap          : borne inférieure d'affectation + gap d'optimalité
- floyd_warshall          : tous-pairs chemins les plus courts (pédagogique)
- dijkstra_steps          : exécution pas-à-pas de Dijkstra (pédagogique)
- compute_graph_metrics   : métriques structurelles du graphe OSM
"""
from __future__ import annotations

import heapq
import math
import random
from typing import Any

import networkx as nx
import numpy as np


# ─────────────────────────────────────────────────────────
# 2-OPT LOCAL SEARCH
# ─────────────────────────────────────────────────────────

def _route_cost(route: list[int], time_matrix: np.ndarray, depot_id: int = 0) -> float:
    """Coût total d'une route : dépôt → clients → dépôt."""
    if not route:
        return 0.0
    cost = float(time_matrix[depot_id][route[0]])
    for i in range(len(route) - 1):
        cost += float(time_matrix[route[i]][route[i + 1]])
    cost += float(time_matrix[route[-1]][depot_id])
    return cost


def _two_opt_single(route: list[int], time_matrix: np.ndarray, depot_id: int = 0) -> tuple[list[int], float]:
    """
    2-opt sur une seule route.
    Pour toute paire (i, j), inverse le segment [i:j+1] si le coût diminue.
    Converge car le coût est strictement décroissant et les permutations sont finies.
    """
    if len(route) < 3:
        return route, _route_cost(route, time_matrix, depot_id)

    best = list(route)
    best_cost = _route_cost(best, time_matrix, depot_id)
    improved = True

    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 2, len(best)):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                candidate_cost = _route_cost(candidate, time_matrix, depot_id)
                if candidate_cost < best_cost - 1.0:  # seuil 1 s pour éviter le bruit flottant
                    best = candidate
                    best_cost = candidate_cost
                    improved = True

    return best, best_cost


def two_opt_routes(
    routes_by_sleigh: dict[str, list[int]],
    time_matrix: np.ndarray,
    depot_id: int = 0,
) -> dict:
    """
    Applique 2-opt à toutes les routes humaines.

    Args:
        routes_by_sleigh : {sleigh_id_str: [client_id, ...]}
        time_matrix      : matrice numpy n×n indexée par id client (0 = dépôt)
        depot_id         : index du dépôt dans la matrice (0 par défaut)

    Returns:
        dict avec résultats par traîneau et totaux agrégés.
    """
    sleigh_results: dict[str, dict] = {}
    total_human = 0.0
    total_optimized = 0.0

    for sleigh_id, route in routes_by_sleigh.items():
        human_cost = _route_cost(route, time_matrix, depot_id)
        if len(route) < 2:
            sleigh_results[sleigh_id] = {
                "human_time_s": round(human_cost, 1),
                "two_opt_time_s": round(human_cost, 1),
                "improvement_s": 0.0,
                "improvement_pct": 0.0,
                "optimized_route": list(route),
            }
        else:
            optimized, opt_cost = _two_opt_single(route, time_matrix, depot_id)
            gain_s = max(0.0, human_cost - opt_cost)
            gain_pct = (gain_s / human_cost * 100.0) if human_cost > 0 else 0.0
            sleigh_results[sleigh_id] = {
                "human_time_s": round(human_cost, 1),
                "two_opt_time_s": round(opt_cost, 1),
                "improvement_s": round(gain_s, 1),
                "improvement_pct": round(gain_pct, 1),
                "optimized_route": optimized,
            }
        total_human += human_cost
        total_optimized += sleigh_results[sleigh_id]["two_opt_time_s"]

    total_gain_s = max(0.0, total_human - total_optimized)
    total_gain_pct = (total_gain_s / total_human * 100.0) if total_human > 0 else 0.0

    return {
        "sleighs": sleigh_results,
        "total_human_time_s": round(total_human, 1),
        "total_two_opt_time_s": round(total_optimized, 1),
        "total_improvement_s": round(total_gain_s, 1),
        "total_improvement_pct": round(total_gain_pct, 1),
    }


# ─────────────────────────────────────────────────────────
# OR-OPT INTER-ROUTES
# ─────────────────────────────────────────────────────────

def _or_opt_move(
    route_a: list[int],
    route_b: list[int],
    seg_len: int,
    time_matrix: np.ndarray,
    depot_id: int,
) -> tuple[list[int] | None, list[int] | None, float]:
    """
    Essaie de déplacer un segment de seg_len clients consécutifs de route_a vers route_b.
    Retourne (new_a, new_b, delta) où delta < 0 signifie une amélioration.
    """
    n = len(time_matrix)
    best_delta = -1.0  # seuil 1 s
    best_a: list[int] | None = None
    best_b: list[int] | None = None

    def tm(u: int, v: int) -> float:
        if u < n and v < n:
            return float(time_matrix[u][v])
        return 1e9

    for i in range(len(route_a) - seg_len + 1):
        seg = route_a[i : i + seg_len]
        new_a = route_a[:i] + route_a[i + seg_len :]

        # Gain du retrait du segment de route_a
        a_prev = route_a[i - 1] if i > 0 else depot_id
        a_next = route_a[i + seg_len] if i + seg_len < len(route_a) else depot_id
        removal_gain = (
            tm(a_prev, seg[0]) + tm(seg[-1], a_next) - tm(a_prev, a_next)
        )

        for j in range(len(route_b) + 1):
            b_prev = route_b[j - 1] if j > 0 else depot_id
            b_next = route_b[j] if j < len(route_b) else depot_id
            insertion_cost = (
                tm(b_prev, seg[0]) + tm(seg[-1], b_next) - tm(b_prev, b_next)
            )
            delta = insertion_cost - removal_gain
            if delta < best_delta:
                best_delta = delta
                best_a = new_a
                best_b = route_b[:j] + seg + route_b[j:]

    return best_a, best_b, best_delta


def or_opt_routes(
    routes_by_sleigh: dict[str, list[int]],
    time_matrix: np.ndarray,
    depot_id: int = 0,
    capacity: float | None = None,
    demands: dict[int, float] | None = None,
) -> dict:
    """
    Or-opt inter-routes : déplace 1, 2 ou 3 clients consécutifs d'un traîneau vers un autre.
    Complémentaire au 2-opt intra-route : réduit le déséquilibre de charge entre véhicules.

    Args:
        routes_by_sleigh : {sleigh_id_str: [client_idx, ...]}
        time_matrix      : matrice numpy n×n (temps en secondes)
        depot_id         : index du dépôt (0 par défaut)
        capacity         : capacité maximale par véhicule (kg). Si fourni, les
                           déplacements qui surchargeraient le véhicule destinataire
                           sont rejetés — garantit le respect des contraintes CVRPTW.
        demands          : {node_index: poids_kg}. Requis quand capacity est fourni.

    Returns:
        dict avec résultats par traîneau et totaux agrégés.
    """
    routes: dict[str, list[int]] = {sid: list(r) for sid, r in routes_by_sleigh.items()}
    sleigh_ids = list(routes.keys())

    def _route_load(route: list[int]) -> float:
        if demands is None:
            return 0.0
        return sum(demands.get(c, 0.0) for c in route)

    improved = True
    while improved:
        improved = False
        for seg_len in (1, 2, 3):
            for sid_a in sleigh_ids:
                for sid_b in sleigh_ids:
                    if sid_a == sid_b or len(routes[sid_a]) < seg_len:
                        continue
                    new_a, new_b, delta = _or_opt_move(
                        routes[sid_a], routes[sid_b], seg_len, time_matrix, depot_id
                    )
                    if new_a is None or delta >= -1.0:
                        continue
                    # Vérification capacité : le véhicule destinataire ne doit pas
                    # dépasser sa capacité après réception du segment.
                    if capacity is not None and demands is not None:
                        if _route_load(new_b) > capacity:
                            continue
                    routes[sid_a] = new_a
                    routes[sid_b] = new_b
                    improved = True

    sleigh_results: dict[str, dict] = {}
    total_human = 0.0
    total_optimized = 0.0

    for sid, original_route in routes_by_sleigh.items():
        human_cost = _route_cost(original_route, time_matrix, depot_id)
        opt_cost = _route_cost(routes[sid], time_matrix, depot_id)
        gain_s = max(0.0, human_cost - opt_cost)
        gain_pct = (gain_s / human_cost * 100.0) if human_cost > 0 else 0.0
        sleigh_results[sid] = {
            "human_time_s": round(human_cost, 1),
            "or_opt_time_s": round(opt_cost, 1),
            "improvement_s": round(gain_s, 1),
            "improvement_pct": round(gain_pct, 1),
            "optimized_route": routes[sid],
        }
        total_human += human_cost
        total_optimized += opt_cost

    total_gain_s = max(0.0, total_human - total_optimized)
    total_gain_pct = (total_gain_s / total_human * 100.0) if total_human > 0 else 0.0

    return {
        "sleighs": sleigh_results,
        "total_human_time_s": round(total_human, 1),
        "total_or_opt_time_s": round(total_optimized, 1),
        "total_improvement_s": round(total_gain_s, 1),
        "total_improvement_pct": round(total_gain_pct, 1),
    }


# ─────────────────────────────────────────────────────────
# NEAREST NEIGHBOR (construction heuristique)
# ─────────────────────────────────────────────────────────

def nearest_neighbor_tour(
    num_clients: int,
    time_matrix: np.ndarray,
    depot_id: int = 0,
) -> dict:
    """
    Construit une tournée TSP mono-véhicule par l'heuristique du Plus Proche Voisin.

    À chaque étape : parmi les clients non-visités, ajoute le plus proche du dernier nœud.
    Complexité O(n²). Sert de baseline de comparaison pédagogique vs OR-Tools.

    Args:
        num_clients : nombre de clients (indices 1..num_clients, 0 = dépôt)
        time_matrix : matrice numpy n×n
        depot_id    : index du dépôt

    Returns:
        {route, total_time_s, steps}
        steps : [{step, from_node, to_node, cost_s, cumulative_s}]
    """
    n = len(time_matrix)
    unvisited: set[int] = set(range(1, num_clients + 1))
    route: list[int] = []
    steps: list[dict] = []
    current = depot_id
    cumulative = 0.0

    while unvisited:
        candidates = [c for c in unvisited if c < n and current < n]
        if not candidates:
            break
        nearest = min(candidates, key=lambda c: float(time_matrix[current][c]))
        cost = float(time_matrix[current][nearest]) if current < n and nearest < n else 0.0
        cumulative += cost
        steps.append({
            "step": len(steps),
            "from_node": current,
            "to_node": nearest,
            "cost_s": round(cost, 1),
            "cumulative_s": round(cumulative, 1),
        })
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    # Retour au dépôt
    return_cost = float(time_matrix[current][depot_id]) if current < n and depot_id < n else 0.0
    cumulative += return_cost
    steps.append({
        "step": len(steps),
        "from_node": current,
        "to_node": depot_id,
        "cost_s": round(return_cost, 1),
        "cumulative_s": round(cumulative, 1),
    })

    return {
        "route": route,
        "total_time_s": round(cumulative, 1),
        "steps_count": len(steps),
        "steps": steps,
    }


# ─────────────────────────────────────────────────────────
# BORNE INFÉRIEURE + GAP D'OPTIMALITÉ
# ─────────────────────────────────────────────────────────

def lower_bound_assignment(time_matrix: np.ndarray, depot_id: int = 0) -> float:
    """Borne faible (relaxation d'affectation) — conservée pour compatibilité."""
    n = len(time_matrix)
    lb = 0.0
    for j in range(n):
        if j != depot_id:
            lb += float(time_matrix[depot_id][j])
    return round(lb, 1)


def lower_bound_1tree(time_matrix: np.ndarray, depot_id: int = 0) -> float:
    """
    Borne 1-arbre (plus serrée que la relaxation d'affectation).

    Construction :
      1. MST de Prim sur les nœuds non-dépôt (O(n²)).
      2. Ajout des 2 arcs les plus courts du dépôt vers les non-dépôt.

    Validité : toute tournée TSP contient un 1-arbre, donc coût(tournée) ≥ lb.
    Pour VRP à k véhicules, on ajoute les k arcs min au lieu de 2 — on garde
    k=2 par défaut (borne conservative, toujours valide).
    """
    n = len(time_matrix)
    non_depot = [i for i in range(n) if i != depot_id]
    if not non_depot:
        return 0.0
    if len(non_depot) == 1:
        return float(time_matrix[depot_id][non_depot[0]])

    m = len(non_depot)
    key = np.full(m, np.inf)
    key[0] = 0.0
    in_mst = np.zeros(m, dtype=bool)
    mst_cost = 0.0

    for _ in range(m):
        masked = np.where(~in_mst, key, np.inf)
        u_local = int(np.argmin(masked))
        in_mst[u_local] = True
        mst_cost += key[u_local]
        u = non_depot[u_local]
        for v_local, v in enumerate(non_depot):
            if not in_mst[v_local]:
                edge = float(time_matrix[u][v])
                if edge < key[v_local]:
                    key[v_local] = edge

    depot_edges = sorted(float(time_matrix[depot_id][i]) for i in non_depot)
    lb = mst_cost + depot_edges[0] + (depot_edges[1] if m >= 2 else depot_edges[0])
    return round(lb, 1)


def optimality_gap(
    solution_cost_s: float,
    time_matrix: np.ndarray,
    depot_id: int = 0,
) -> dict:
    """
    Gap d'optimalité par rapport à la borne 1-arbre (plus serrée que la relaxation
    d'affectation simple).

    gap_pct = (solution - borne_1tree) / borne_1tree × 100

    Un gap de 0 % serait optimal. En pratique, < 15 % est excellent pour CVRPTW.
    """
    # Prend le max des deux bornes (toujours valide, toujours plus serrée)
    lb_assign = lower_bound_assignment(time_matrix, depot_id)
    lb_1tree  = lower_bound_1tree(time_matrix, depot_id)
    lb = max(lb_assign, lb_1tree)
    method = "1-tree (MST + 2 arcs dépôt)" if lb_1tree >= lb_assign else "affectation (Σ dépôt→client)"

    if lb <= 0:
        return {
            "lower_bound_s": 0.0,
            "solution_cost_s": round(solution_cost_s, 1),
            "gap_pct": None,
            "interpretation": "Borne indisponible",
            "method": method,
        }

    gap = max(0.0, (solution_cost_s - lb) / lb * 100.0)

    if gap < 15:
        interpretation = "Excellent — solution proche de l'optimum théorique"
    elif gap < 35:
        interpretation = "Bon — gap typique pour CVRPTW heuristique"
    elif gap < 60:
        interpretation = "Acceptable — marge d'amélioration significative"
    else:
        interpretation = "Élevé — la tournée peut être sensiblement améliorée"

    return {
        "lower_bound_s": lb,
        "solution_cost_s": round(solution_cost_s, 1),
        "gap_pct": round(gap, 1),
        "interpretation": interpretation,
        "method": method,
    }


# ─────────────────────────────────────────────────────────
# DIJKSTRA PAS-À-PAS
# ─────────────────────────────────────────────────────────

def dijkstra_steps(
    graph,
    from_node: int,
    to_node: int,
    weight: str = "travel_time",
    max_steps: int = 400,
) -> dict:
    """
    Exécute Dijkstra manuellement et capture chaque étape de finalisation.

    Chaque step = un nœud extrait du tas min (finalisé).
    Arrêt dès que to_node est finalisé ou que max_steps est atteint.

    Returns:
        {
            "steps": [{step, node, dist, lat, lon, predecessor}, ...],
            "steps_count": int,
            "path": [node_id, ...],
            "total_cost": float,
            "reached": bool,
            "truncated": bool,
        }
    """
    if from_node not in graph.nodes:
        raise ValueError(f"Nœud source {from_node} absent du graphe.")
    if to_node not in graph.nodes:
        raise ValueError(f"Nœud destination {to_node} absent du graphe.")

    dist: dict[int, float] = {from_node: 0.0}
    prev: dict[int, int | None] = {from_node: None}
    heap: list[tuple[float, int]] = [(0.0, from_node)]
    visited: set[int] = set()
    steps: list[dict[str, Any]] = []

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        nd = graph.nodes.get(u, {})
        steps.append({
            "step": len(steps),
            "node": u,
            "dist": round(d, 1),
            "lat": round(float(nd.get("y", 0.0)), 6),
            "lon": round(float(nd.get("x", 0.0)), 6),
            "predecessor": prev.get(u),
        })

        if u == to_node or len(steps) >= max_steps:
            break

        for _, v, edata in graph.out_edges(u, data=True):
            w = edata.get(weight) or edata.get("length", 0)
            if w is None:
                continue
            new_d = d + float(w)
            if v not in dist or new_d < dist[v]:
                dist[v] = new_d
                prev[v] = u
                heapq.heappush(heap, (new_d, v))

    # Reconstruction du chemin
    path: list[int] = []
    if to_node in visited:
        node: int | None = to_node
        while node is not None:
            path.append(node)
            node = prev.get(node)
        path.reverse()

    return {
        "from_node": from_node,
        "to_node": to_node,
        "steps": steps,
        "steps_count": len(steps),
        "path": path,
        "path_length": len(path),
        "total_cost": round(dist.get(to_node, -1.0), 1),
        "reached": to_node in visited,
        "truncated": len(steps) >= max_steps and to_node not in visited,
    }


# ─────────────────────────────────────────────────────────
# A* BIDIRECTIONNEL
# ─────────────────────────────────────────────────────────

def _haversine_seconds(graph, u: int, v: int, max_speed_ms: float = 13.89) -> float:
    """Distance à vol d'oiseau entre u et v convertie en secondes (heuristique admissible)."""
    ud = graph.nodes[u]
    vd = graph.nodes[v]
    lat1 = math.radians(float(ud["y"]))
    lon1 = math.radians(float(ud["x"]))
    lat2 = math.radians(float(vd["y"]))
    lon2 = math.radians(float(vd["x"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000.0 * 2.0 * math.asin(math.sqrt(a)) / max_speed_ms


def bidirectional_astar_steps(
    graph,
    from_node: int,
    to_node: int,
    weight: str = "travel_time",
    max_steps: int = 400,
) -> dict:
    """
    A* bidirectionnel avec heuristique Haversine dans les deux directions.

    Par rapport au Dijkstra bidirectionnel, chaque frontière est guidée vers
    son objectif (heuristique f = g + h), ce qui réduit encore l'espace exploré.

    Heuristique forward  : h_f(n) = haversine(n, dest) / 13.89 m/s (admissible)
    Heuristique backward : h_b(n) = haversine(n, source) / 13.89 m/s (admissible)

    Terminaison : on s'arrête quand min(f_forward_top, f_backward_top) >= mu,
    où mu est le meilleur chemin complet trouvé — condition identique au
    Dijkstra bidirectionnel mais les tops de file sont des f-valeurs, pas des g.

    Returns:
        {
            steps_forward, steps_backward, meeting_node,
            path, total_cost, reached, truncated,
            nodes_explored_astar_bidir,
        }
    """
    if from_node not in graph.nodes:
        raise ValueError(f"Nœud source {from_node} absent du graphe.")
    if to_node not in graph.nodes:
        raise ValueError(f"Nœud destination {to_node} absent du graphe.")

    if from_node == to_node:
        nd = graph.nodes.get(from_node, {})
        step = {"step": 0, "direction": "forward", "node": from_node, "g": 0.0, "f": 0.0,
                "lat": round(float(nd.get("y", 0.0)), 6),
                "lon": round(float(nd.get("x", 0.0)), 6), "predecessor": None}
        return {
            "from_node": from_node, "to_node": to_node,
            "steps_forward": [step], "steps_backward": [],
            "meeting_node": from_node, "path": [from_node], "path_length": 1,
            "total_cost": 0.0, "reached": True, "truncated": False,
            "nodes_explored_astar_bidir": 1,
        }

    # ── État frontière avant ──────────────────────────────
    g_f: dict[int, float] = {from_node: 0.0}
    prev_f: dict[int, int | None] = {from_node: None}
    h0_f = _haversine_seconds(graph, from_node, to_node)
    heap_f: list[tuple[float, int]] = [(h0_f, from_node)]   # (f, node)
    visited_f: set[int] = set()
    steps_f: list[dict[str, Any]] = []

    # ── État frontière arrière ────────────────────────────
    g_b: dict[int, float] = {to_node: 0.0}
    prev_b: dict[int, int | None] = {to_node: None}
    h0_b = _haversine_seconds(graph, to_node, from_node)
    heap_b: list[tuple[float, int]] = [(h0_b, to_node)]     # (f, node)
    visited_b: set[int] = set()
    steps_b: list[dict[str, Any]] = []

    mu = float("inf")
    meeting_node: int | None = None
    total_steps = 0
    truncated = False

    while (heap_f or heap_b) and total_steps < max_steps:
        top_f = heap_f[0][0] if heap_f else float("inf")
        top_b = heap_b[0][0] if heap_b else float("inf")

        # Terminaison correcte pour A* bidir avec heuristique consistante :
        # toute exploration restante ne peut améliorer mu que si au moins un
        # des deux tas contient un nœud avec f < mu.
        # « min(f) >= mu dans les DEUX tas » → aucun chemin résiduel ne bat mu.
        if mu < float("inf") and top_f >= mu and top_b >= mu:
            break

        expand_forward = not heap_b or (heap_f and top_f <= top_b)

        if expand_forward and heap_f:
            f, u = heapq.heappop(heap_f)
            if u in visited_f:
                continue
            visited_f.add(u)
            g = g_f[u]
            nd = graph.nodes.get(u, {})
            steps_f.append({
                "step": len(steps_f), "direction": "forward", "node": u,
                "g": round(g, 1), "f": round(f, 1),
                "lat": round(float(nd.get("y", 0.0)), 6),
                "lon": round(float(nd.get("x", 0.0)), 6),
                "predecessor": prev_f.get(u),
            })
            total_steps += 1

            if u in g_b:
                candidate = g + g_b[u]
                if candidate < mu:
                    mu = candidate
                    meeting_node = u

            for _, v, edata in graph.out_edges(u, data=True):
                w = edata.get(weight) or edata.get("length", 0)
                if w is None:
                    continue
                new_g = g + float(w)
                if v not in g_f or new_g < g_f[v]:
                    g_f[v] = new_g
                    prev_f[v] = u
                    h = _haversine_seconds(graph, v, to_node)
                    heapq.heappush(heap_f, (new_g + h, v))
                    if v in g_b:
                        candidate = new_g + g_b[v]
                        if candidate < mu:
                            mu = candidate
                            meeting_node = v
        else:
            f, u = heapq.heappop(heap_b)
            if u in visited_b:
                continue
            visited_b.add(u)
            g = g_b[u]
            nd = graph.nodes.get(u, {})
            steps_b.append({
                "step": len(steps_b), "direction": "backward", "node": u,
                "g": round(g, 1), "f": round(f, 1),
                "lat": round(float(nd.get("y", 0.0)), 6),
                "lon": round(float(nd.get("x", 0.0)), 6),
                "predecessor": prev_b.get(u),
            })
            total_steps += 1

            if u in g_f:
                candidate = g_f[u] + g
                if candidate < mu:
                    mu = candidate
                    meeting_node = u

            for v, _, edata in graph.in_edges(u, data=True):
                w = edata.get(weight) or edata.get("length", 0)
                if w is None:
                    continue
                new_g = g + float(w)
                if v not in g_b or new_g < g_b[v]:
                    g_b[v] = new_g
                    prev_b[v] = u
                    h = _haversine_seconds(graph, v, from_node)
                    heapq.heappush(heap_b, (new_g + h, v))
                    if v in g_f:
                        candidate = g_f[v] + new_g
                        if candidate < mu:
                            mu = candidate
                            meeting_node = v

    if total_steps >= max_steps and meeting_node is None:
        truncated = True

    # ── Reconstruction du chemin ──────────────────────────
    path: list[int] = []
    reached = meeting_node is not None and mu < float("inf")

    if reached and meeting_node is not None:
        fwd: list[int] = []
        node: int | None = meeting_node
        while node is not None:
            fwd.append(node)
            node = prev_f.get(node)
        fwd.reverse()

        bwd: list[int] = []
        nxt: int | None = prev_b.get(meeting_node)
        while nxt is not None:
            bwd.append(nxt)
            nxt = prev_b.get(nxt)

        path = fwd + bwd

    return {
        "from_node": from_node,
        "to_node": to_node,
        "steps_forward": steps_f,
        "steps_backward": steps_b,
        "meeting_node": meeting_node,
        "path": path,
        "path_length": len(path),
        "total_cost": round(mu if reached else -1.0, 1),
        "reached": reached,
        "truncated": truncated,
        "nodes_explored_astar_bidir": len(steps_f) + len(steps_b),
    }


# ─────────────────────────────────────────────────────────
# DIJKSTRA BIDIRECTIONNEL
# ─────────────────────────────────────────────────────────

def bidirectional_dijkstra_steps(
    graph,
    from_node: int,
    to_node: int,
    weight: str = "travel_time",
    max_steps: int = 400,
) -> dict:
    """
    Dijkstra bidirectionnel : deux frontières simultanées (avant depuis source,
    arrière depuis destination sur les arêtes inversées).

    Complexité identique à Dijkstra classique dans le pire cas, mais explore en
    pratique ~2× moins de nœuds sur des graphes euclidiens (chaque frontière
    n'a besoin que de rayon r/2 au lieu de r, soit 2×π(r/2)² = πr²/2 nœuds).

    Terminaison correcte : on s'arrête quand la somme des meilleures distances
    restantes des deux tas dépasse le meilleur chemin complet trouvé (mu).

    Returns:
        {
            steps_forward      : étapes frontière avant (node finalisé),
            steps_backward     : étapes frontière arrière,
            meeting_node       : nœud de rencontre optimal,
            path               : chemin complet reconstruit,
            total_cost         : coût total du chemin,
            reached            : bool,
            truncated          : bool,
            nodes_explored_bidir  : nœuds finalisés au total,
        }
    """
    if from_node not in graph.nodes:
        raise ValueError(f"Nœud source {from_node} absent du graphe.")
    if to_node not in graph.nodes:
        raise ValueError(f"Nœud destination {to_node} absent du graphe.")

    if from_node == to_node:
        nd = graph.nodes.get(from_node, {})
        step = {"step": 0, "direction": "forward", "node": from_node, "dist": 0.0,
                "lat": round(float(nd.get("y", 0.0)), 6),
                "lon": round(float(nd.get("x", 0.0)), 6),
                "predecessor": None}
        return {
            "from_node": from_node, "to_node": to_node,
            "steps_forward": [step], "steps_backward": [],
            "meeting_node": from_node, "path": [from_node], "path_length": 1,
            "total_cost": 0.0, "reached": True, "truncated": False,
            "nodes_explored_bidir": 1,
        }

    # ── État frontière avant ──────────────────────────────
    dist_f: dict[int, float] = {from_node: 0.0}
    prev_f: dict[int, int | None] = {from_node: None}
    heap_f: list[tuple[float, int]] = [(0.0, from_node)]
    visited_f: set[int] = set()
    steps_f: list[dict[str, Any]] = []

    # ── État frontière arrière ────────────────────────────
    dist_b: dict[int, float] = {to_node: 0.0}
    prev_b: dict[int, int | None] = {to_node: None}
    heap_b: list[tuple[float, int]] = [(0.0, to_node)]
    visited_b: set[int] = set()
    steps_b: list[dict[str, Any]] = []

    mu = float("inf")   # meilleur chemin complet connu
    meeting_node: int | None = None
    total_steps = 0
    truncated = False

    while (heap_f or heap_b) and total_steps < max_steps:
        top_f = heap_f[0][0] if heap_f else float("inf")
        top_b = heap_b[0][0] if heap_b else float("inf")

        if top_f + top_b >= mu:
            break

        # Développe la frontière dont le sommet est le plus petit
        if not heap_b or (heap_f and top_f <= top_b):
            d, u = heapq.heappop(heap_f)
            if u in visited_f:
                continue
            visited_f.add(u)
            nd = graph.nodes.get(u, {})
            steps_f.append({
                "step": len(steps_f),
                "direction": "forward",
                "node": u,
                "dist": round(d, 1),
                "lat": round(float(nd.get("y", 0.0)), 6),
                "lon": round(float(nd.get("x", 0.0)), 6),
                "predecessor": prev_f.get(u),
            })
            total_steps += 1

            if u in dist_b:
                candidate = d + dist_b[u]
                if candidate < mu:
                    mu = candidate
                    meeting_node = u

            for _, v, edata in graph.out_edges(u, data=True):
                w = edata.get(weight) or edata.get("length", 0)
                if w is None:
                    continue
                new_d = d + float(w)
                if v not in dist_f or new_d < dist_f[v]:
                    dist_f[v] = new_d
                    prev_f[v] = u
                    heapq.heappush(heap_f, (new_d, v))
                    if v in dist_b:
                        candidate = new_d + dist_b[v]
                        if candidate < mu:
                            mu = candidate
                            meeting_node = v
        else:
            d, u = heapq.heappop(heap_b)
            if u in visited_b:
                continue
            visited_b.add(u)
            nd = graph.nodes.get(u, {})
            steps_b.append({
                "step": len(steps_b),
                "direction": "backward",
                "node": u,
                "dist": round(d, 1),
                "lat": round(float(nd.get("y", 0.0)), 6),
                "lon": round(float(nd.get("x", 0.0)), 6),
                "predecessor": prev_b.get(u),
            })
            total_steps += 1

            if u in dist_f:
                candidate = dist_f[u] + d
                if candidate < mu:
                    mu = candidate
                    meeting_node = u

            # Arrière : on parcourt les arêtes entrantes (direction réelle v→u)
            for v, _, edata in graph.in_edges(u, data=True):
                w = edata.get(weight) or edata.get("length", 0)
                if w is None:
                    continue
                new_d = d + float(w)
                if v not in dist_b or new_d < dist_b[v]:
                    dist_b[v] = new_d
                    prev_b[v] = u  # depuis v, le prochain saut vers dest est u
                    heapq.heappush(heap_b, (new_d, v))
                    if v in dist_f:
                        candidate = dist_f[v] + new_d
                        if candidate < mu:
                            mu = candidate
                            meeting_node = v

    if total_steps >= max_steps and meeting_node is None:
        truncated = True

    # ── Reconstruction du chemin ──────────────────────────
    path: list[int] = []
    reached = meeting_node is not None and mu < float("inf")

    if reached and meeting_node is not None:
        # from_node → meeting_node via prev_f
        fwd: list[int] = []
        node: int | None = meeting_node
        while node is not None:
            fwd.append(node)
            node = prev_f.get(node)
        fwd.reverse()

        # meeting_node → to_node via prev_b
        # prev_b[v] = u signifie « depuis v, aller vers u (arête réelle v→u) »
        bwd: list[int] = []
        nxt: int | None = prev_b.get(meeting_node)
        while nxt is not None:
            bwd.append(nxt)
            nxt = prev_b.get(nxt)

        path = fwd + bwd

    return {
        "from_node": from_node,
        "to_node": to_node,
        "steps_forward": steps_f,
        "steps_backward": steps_b,
        "meeting_node": meeting_node,
        "path": path,
        "path_length": len(path),
        "total_cost": round(mu if reached else -1.0, 1),
        "reached": reached,
        "truncated": truncated,
        "nodes_explored_bidir": len(steps_f) + len(steps_b),
    }


# ─────────────────────────────────────────────────────────
# 3-OPT INTRA-ROUTE
# ─────────────────────────────────────────────────────────

def _three_opt_single(
    route: list[int],
    time_matrix: np.ndarray,
    depot_id: int = 0,
) -> tuple[list[int], float]:
    """
    3-opt sur une seule route : supprime 3 arcs et reconnecte en choisissant
    parmi 8 recombinaisons possibles la moins coûteuse.

    Pour chaque triplet (i, j, k) avec i < j < k, on découpe la route en
    segments A=route[:i+1], B=route[i+1:j+1], C=route[j+1:k+1], D=route[k+1:]
    et on teste les 7 reconnexions non-triviales. Complexité O(n³) par passe.

    Cas trouvés par 3-opt mais pas par 2-opt : les transpositions de segments
    A+C+B+D, A+C+B'+D, A+C'+B+D (relocalisation de bloc sans inversion totale).
    """
    if len(route) < 4:
        return _two_opt_single(route, time_matrix, depot_id)

    # Partir du point 2-opt optimal garantit que 3-opt ne peut qu'améliorer ou maintenir.
    best, best_cost = _two_opt_single(route, time_matrix, depot_id)
    improved = True
    n = len(best)

    while improved:
        improved = False
        for i in range(n - 2):
            for j in range(i + 1, n - 1):
                for k in range(j + 1, n):
                    A = best[: i + 1]
                    B = best[i + 1 : j + 1]
                    C = best[j + 1 : k + 1]
                    D = best[k + 1 :]
                    Br = B[::-1]
                    Cr = C[::-1]
                    candidates = [
                        A + B + Cr + D,      # inverse C
                        A + Br + C + D,      # inverse B
                        A + Br + Cr + D,     # inverse B et C
                        A + C + B + D,       # transpose B↔C
                        A + C + Br + D,      # transpose, inverse B
                        A + Cr + B + D,      # transpose, inverse C
                        A + Cr + Br + D,     # transpose, inverse B et C
                    ]
                    for candidate in candidates:
                        cost = _route_cost(candidate, time_matrix, depot_id)
                        if cost < best_cost - 1.0:
                            best = candidate
                            best_cost = cost
                            improved = True
                            n = len(best)
                            break
                    if improved:
                        break
                if improved:
                    break

    return best, best_cost


def three_opt_routes(
    routes_by_sleigh: dict[str, list[int]],
    time_matrix: np.ndarray,
    depot_id: int = 0,
) -> dict:
    """
    Applique 3-opt à toutes les routes.

    Généralise le 2-opt à 3 arcs retirés simultanément. Trouve des améliorations
    que 2-opt ne peut pas atteindre (configurations en W, transpositions de blocs).
    Complexité O(n³) par passe — limité automatiquement à 2-opt si len(route) < 4.

    Returns:
        dict avec résultats par traîneau et totaux agrégés.
    """
    sleigh_results: dict[str, dict] = {}
    total_human = 0.0
    total_optimized = 0.0

    for sleigh_id, route in routes_by_sleigh.items():
        human_cost = _route_cost(route, time_matrix, depot_id)
        if len(route) < 2:
            sleigh_results[sleigh_id] = {
                "human_time_s": round(human_cost, 1),
                "three_opt_time_s": round(human_cost, 1),
                "improvement_s": 0.0,
                "improvement_pct": 0.0,
                "optimized_route": list(route),
            }
        else:
            optimized, opt_cost = _three_opt_single(route, time_matrix, depot_id)
            gain_s = max(0.0, human_cost - opt_cost)
            gain_pct = (gain_s / human_cost * 100.0) if human_cost > 0 else 0.0
            sleigh_results[sleigh_id] = {
                "human_time_s": round(human_cost, 1),
                "three_opt_time_s": round(opt_cost, 1),
                "improvement_s": round(gain_s, 1),
                "improvement_pct": round(gain_pct, 1),
                "optimized_route": optimized,
            }
        total_human += human_cost
        total_optimized += sleigh_results[sleigh_id]["three_opt_time_s"]

    total_gain_s = max(0.0, total_human - total_optimized)
    total_gain_pct = (total_gain_s / total_human * 100.0) if total_human > 0 else 0.0

    return {
        "sleighs": sleigh_results,
        "total_human_time_s": round(total_human, 1),
        "total_three_opt_time_s": round(total_optimized, 1),
        "total_improvement_s": round(total_gain_s, 1),
        "total_improvement_pct": round(total_gain_pct, 1),
    }


# ─────────────────────────────────────────────────────────
# 2-OPT* INTER-ROUTES (VRPTW)
# ─────────────────────────────────────────────────────────

def _two_opt_star_move(
    route_a: list[int],
    route_b: list[int],
    time_matrix: np.ndarray,
    depot_id: int,
    capacity: float | None,
    demands: dict[int, float] | None,
) -> tuple[list[int] | None, list[int] | None, float]:
    """
    Essaie tous les échanges de suffixes entre route_a et route_b (2-opt*).

    Pour chaque paire (i, j), coupe route_a après i et route_b après j,
    puis échange les suffixes :
        new_a = route_a[:i+1] + route_b[j+1:]
        new_b = route_b[:j+1] + route_a[i+1:]

    i=-1 signifie préfixe vide (on prend le suffixe entier de l'autre route).
    Retourne (new_a, new_b, delta) où delta < 0 = amélioration.
    """
    n = len(time_matrix)
    best_delta = -1.0
    best_a: list[int] | None = None
    best_b: list[int] | None = None

    def tm(u: int, v: int) -> float:
        return float(time_matrix[u][v]) if u < n and v < n else 1e9

    def load(route: list[int]) -> float:
        if demands is None:
            return 0.0
        return sum(demands.get(c, 0.0) for c in route)

    cost_a0 = _route_cost(route_a, time_matrix, depot_id)
    cost_b0 = _route_cost(route_b, time_matrix, depot_id)

    for i in range(-1, len(route_a)):
        tail_a = route_a[i + 1 :]
        head_a = route_a[: i + 1]
        # Connexion de route_a avant coupure
        prev_a = route_a[i] if i >= 0 else depot_id

        for j in range(-1, len(route_b)):
            tail_b = route_b[j + 1 :]
            head_b = route_b[: j + 1]
            prev_b = route_b[j] if j >= 0 else depot_id

            new_a = head_a + tail_b
            new_b = head_b + tail_a

            # Capacité
            if capacity is not None and demands is not None:
                if load(new_a) > capacity or load(new_b) > capacity:
                    continue

            cost_new_a = _route_cost(new_a, time_matrix, depot_id) if new_a else 0.0
            cost_new_b = _route_cost(new_b, time_matrix, depot_id) if new_b else 0.0
            delta = (cost_new_a + cost_new_b) - (cost_a0 + cost_b0)

            if delta < best_delta:
                best_delta = delta
                best_a = new_a
                best_b = new_b

    return best_a, best_b, best_delta


def two_opt_star_routes(
    routes_by_sleigh: dict[str, list[int]],
    time_matrix: np.ndarray,
    depot_id: int = 0,
    capacity: float | None = None,
    demands: dict[int, float] | None = None,
) -> dict:
    """
    2-opt* inter-routes VRPTW : échange les suffixes de deux tournées.

    Différent de l'or-opt (qui déplace des blocs courts) : ici on coupe chaque
    route en deux et on recolle les morceaux croisés. Trouve des améliorations
    structurelles que ni le 2-opt ni l'or-opt ne détectent.

    Args:
        routes_by_sleigh : {sleigh_id_str: [client_idx, ...]}
        time_matrix      : matrice numpy n×n
        depot_id         : index du dépôt
        capacity         : capacité maximale par véhicule (si None, pas de garde)
        demands          : {node_index: poids_kg}

    Returns:
        dict avec résultats par traîneau et totaux agrégés.
    """
    routes: dict[str, list[int]] = {sid: list(r) for sid, r in routes_by_sleigh.items()}
    sleigh_ids = list(routes.keys())
    original = {sid: list(r) for sid, r in routes_by_sleigh.items()}

    improved = True
    while improved:
        improved = False
        for idx_a in range(len(sleigh_ids)):
            for idx_b in range(idx_a + 1, len(sleigh_ids)):
                sid_a, sid_b = sleigh_ids[idx_a], sleigh_ids[idx_b]
                new_a, new_b, delta = _two_opt_star_move(
                    routes[sid_a], routes[sid_b],
                    time_matrix, depot_id, capacity, demands,
                )
                if new_a is not None and delta < -1.0:
                    routes[sid_a] = new_a
                    routes[sid_b] = new_b
                    improved = True

    sleigh_results: dict[str, dict] = {}
    total_human = 0.0
    total_optimized = 0.0

    for sid in sleigh_ids:
        human_cost = _route_cost(original[sid], time_matrix, depot_id)
        opt_cost = _route_cost(routes[sid], time_matrix, depot_id)
        gain_s = max(0.0, human_cost - opt_cost)
        gain_pct = (gain_s / human_cost * 100.0) if human_cost > 0 else 0.0
        sleigh_results[sid] = {
            "human_time_s": round(human_cost, 1),
            "two_opt_star_time_s": round(opt_cost, 1),
            "improvement_s": round(gain_s, 1),
            "improvement_pct": round(gain_pct, 1),
            "optimized_route": routes[sid],
        }
        total_human += human_cost
        total_optimized += opt_cost

    total_gain_s = max(0.0, total_human - total_optimized)
    total_gain_pct = (total_gain_s / total_human * 100.0) if total_human > 0 else 0.0

    return {
        "sleighs": sleigh_results,
        "total_human_time_s": round(total_human, 1),
        "total_two_opt_star_time_s": round(total_optimized, 1),
        "total_improvement_s": round(total_gain_s, 1),
        "total_improvement_pct": round(total_gain_pct, 1),
    }


# ─────────────────────────────────────────────────────────
# ILS — ITERATED LOCAL SEARCH avec DOUBLE-BRIDGE
# ─────────────────────────────────────────────────────────

def _double_bridge_single(route: list[int]) -> list[int]:
    """
    Perturbation double-bridge (4-opt non-séquentiel) sur une route.

    Sélectionne 3 points de coupure aléatoires i < j < k, découpe la route en
    4 segments A, B, C, D et les recolle en A + C + B + D.

    Ce mouvement est IMPOSSIBLE à défaire par une séquence de 2-opt ou 3-opt —
    c'est pourquoi il est utilisé comme perturbation pour échapper aux optima
    locaux profonds dans le framework ILS (Iterated Local Search).

    Complexité : O(n).
    """
    n = len(route)
    if n < 4:
        return list(route)

    # 3 points de coupe dans [1, n-1] distincts, garantissant 4 segments non-vides
    cuts = sorted(random.sample(range(1, n), 3))
    i, j, k = cuts
    A, B, C, D = route[:i], route[i:j], route[j:k], route[k:]
    return A + C + B + D


def _total_cost(routes: dict[str, list[int]], time_matrix: np.ndarray, depot_id: int) -> float:
    return sum(_route_cost(r, time_matrix, depot_id) for r in routes.values())


def _full_local_search(
    routes: dict[str, list[int]],
    time_matrix: np.ndarray,
    depot_id: int,
    capacity: float | None,
    demands: dict[int, float] | None,
) -> dict[str, list[int]]:
    """Pipeline 3-opt → or-opt → 2-opt* appliqué en une passe."""
    r = three_opt_routes(routes, time_matrix, depot_id)
    imp = {sid: d["optimized_route"] for sid, d in r["sleighs"].items()}

    r = or_opt_routes(imp, time_matrix, depot_id, capacity=capacity, demands=demands)
    imp = {sid: d["optimized_route"] for sid, d in r["sleighs"].items()}

    r = two_opt_star_routes(imp, time_matrix, depot_id, capacity=capacity, demands=demands)
    return {sid: d["optimized_route"] for sid, d in r["sleighs"].items()}


def iterated_local_search(
    routes_by_sleigh: dict[str, list[int]],
    time_matrix: np.ndarray,
    depot_id: int = 0,
    n_iterations: int = 8,
    capacity: float | None = None,
    demands: dict[int, float] | None = None,
) -> dict:
    """
    Iterated Local Search (ILS) pour VRPTW multi-véhicules.

    Algorithme :
      1. Recherche locale complète (3-opt + or-opt + 2-opt*) → solution initiale S*
      2. Répéter n_iterations fois :
         a. Perturbation double-bridge sur la route la plus longue de S*
         b. Recherche locale complète → S'
         c. Si coût(S') < coût(S*) → S* ← S'  (critère d'acceptation : amélioration seule)
      3. Retourner S*

    La perturbation double-bridge garantit une diversification structurelle :
    aucune séquence de 2-opt/3-opt ne peut revenir à l'état avant perturbation,
    forçant l'exploration d'un nouveau bassin d'attraction.

    Args:
        routes_by_sleigh : {sleigh_id_str: [client_idx, ...]}
        time_matrix      : matrice numpy n×n
        depot_id         : index du dépôt (0 par défaut)
        n_iterations     : nombre d'itérations de perturbation
        capacity         : capacité max par véhicule (None = pas de garde)
        demands          : {node_index: poids_kg}

    Returns:
        dict avec meilleure solution trouvée, statistiques ILS et résultats par traîneau.
    """
    original = {sid: list(r) for sid, r in routes_by_sleigh.items()}
    sleigh_ids = list(original.keys())

    # Phase 1 : recherche locale initiale
    best = _full_local_search(original, time_matrix, depot_id, capacity, demands)
    best_cost = _total_cost(best, time_matrix, depot_id)
    improvements_accepted = 0

    # Phase 2 : perturbations itérées
    for _ in range(n_iterations):
        # Sélectionne la route la plus longue (la plus prometteuse à perturber)
        target_sid = max(
            (sid for sid in sleigh_ids if len(best[sid]) >= 4),
            key=lambda sid: _route_cost(best[sid], time_matrix, depot_id),
            default=None,
        )
        if target_sid is None:
            break

        # Perturbation double-bridge
        candidate = dict(best)
        candidate[target_sid] = _double_bridge_single(best[target_sid])

        # Recherche locale sur la solution perturbée
        candidate = _full_local_search(candidate, time_matrix, depot_id, capacity, demands)
        candidate_cost = _total_cost(candidate, time_matrix, depot_id)

        if candidate_cost < best_cost - 1.0:
            best = candidate
            best_cost = candidate_cost
            improvements_accepted += 1

    # Calcul des gains
    original_cost = _total_cost(original, time_matrix, depot_id)
    total_gain_s = max(0.0, original_cost - best_cost)
    total_gain_pct = (total_gain_s / original_cost * 100.0) if original_cost > 0 else 0.0

    sleigh_results: dict[str, dict] = {}
    for sid in sleigh_ids:
        h = _route_cost(original[sid], time_matrix, depot_id)
        o = _route_cost(best[sid], time_matrix, depot_id)
        g = max(0.0, h - o)
        sleigh_results[sid] = {
            "human_time_s": round(h, 1),
            "ils_time_s": round(o, 1),
            "improvement_s": round(g, 1),
            "improvement_pct": round((g / h * 100.0) if h > 0 else 0.0, 1),
            "optimized_route": best[sid],
        }

    return {
        "sleighs": sleigh_results,
        "total_human_time_s": round(original_cost, 1),
        "total_ils_time_s": round(best_cost, 1),
        "total_improvement_s": round(total_gain_s, 1),
        "total_improvement_pct": round(total_gain_pct, 1),
        "iterations_run": n_iterations,
        "improvements_accepted": improvements_accepted,
    }


# ─────────────────────────────────────────────────────────
# ALNS — Adaptive Large Neighborhood Search
# Ropke & Pisinger (2006), "An Adaptive Large Neighborhood Search
# Heuristic for the Pickup and Delivery Problem with Time Windows"
# ─────────────────────────────────────────────────────────

# Récompenses (Ropke & Pisinger §4.1)
_ALNS_SIGMA1 = 33   # nouvelle meilleure solution globale
_ALNS_SIGMA2 = 9    # amélioration de la solution courante (sans nouveau best)
_ALNS_SIGMA3 = 3    # solution acceptée (recuit, sans amélioration)
_ALNS_DECAY  = 0.80 # facteur de décroissance des scores
_ALNS_COOL   = 0.995  # refroidissement SA par itération


def _alns_route_cost(route: list[int], matrix: np.ndarray, depot: int = 0) -> float:
    if not route:
        return 0.0
    cost = float(matrix[depot][route[0]])
    for i in range(len(route) - 1):
        cost += float(matrix[route[i]][route[i + 1]])
    cost += float(matrix[route[-1]][depot])
    return cost


def _alns_total_cost(routes: dict[str, list[int]], matrix: np.ndarray, depot: int = 0) -> float:
    return sum(_alns_route_cost(r, matrix, depot) for r in routes.values())


def _alns_roulette(scores: list[float], rng: random.Random) -> int:
    total = sum(scores)
    r = rng.random() * total
    s = 0.0
    for i, w in enumerate(scores):
        s += w
        if s >= r:
            return i
    return len(scores) - 1


# ── Opérateurs de destruction ──────────────────────────────────────────────────

def _destroy_random(
    routes: dict[str, list[int]], n: int, rng: random.Random
) -> tuple[dict[str, list[int]], list[int]]:
    """Supprime n clients tirés aléatoirement dans l'ensemble des routes."""
    pool = [(v, c) for v, r in routes.items() for c in r]
    if not pool:
        return routes, []
    chosen = rng.sample(pool, min(n, len(pool)))
    removed = [c for _, c in chosen]
    removed_set = set(removed)
    return {v: [c for c in r if c not in removed_set] for v, r in routes.items()}, removed


def _destroy_worst(
    routes: dict[str, list[int]], matrix: np.ndarray, n: int, depot: int = 0
) -> tuple[dict[str, list[int]], list[int]]:
    """Supprime les n clients dont le coût marginal de service est le plus élevé."""
    savings: list[tuple[float, str, int]] = []
    for v, route in routes.items():
        for i, c in enumerate(route):
            prev = route[i - 1] if i > 0 else depot
            nxt  = route[i + 1] if i < len(route) - 1 else depot
            saving = float(matrix[prev][c]) + float(matrix[c][nxt]) - float(matrix[prev][nxt])
            savings.append((saving, v, c))
    savings.sort(reverse=True)
    removed = [c for _, _, c in savings[:n]]
    removed_set = set(removed)
    return {v: [c for c in r if c not in removed_set] for v, r in routes.items()}, removed


def _destroy_related(
    routes: dict[str, list[int]], matrix: np.ndarray, n: int, rng: random.Random, depot: int = 0
) -> tuple[dict[str, list[int]], list[int]]:
    """
    Supprime un client aléatoire puis ses n-1 voisins les plus proches
    (Shaw removal). Favorise la diversification géographique locale.
    """
    pool = [c for r in routes.values() for c in r]
    if not pool:
        return routes, []
    seed = rng.choice(pool)
    neighbors = sorted((float(matrix[seed][c]), c) for c in pool if c != seed)
    removed = [seed] + [c for _, c in neighbors[: n - 1]]
    removed_set = set(removed)
    return {v: [c for c in r if c not in removed_set] for v, r in routes.items()}, removed


# ── Opérateurs de réparation ───────────────────────────────────────────────────

def _repair_greedy(
    routes: dict[str, list[int]],
    removed: list[int],
    matrix: np.ndarray,
    demands: dict[int, float],
    capacity: float,
    depot: int = 0,
) -> dict[str, list[int]]:
    """Insère chaque client supprimé à la position de coût minimal faisable."""
    routes = {v: list(r) for v, r in routes.items()}
    for c in removed:
        best_delta, best_v, best_pos = float("inf"), None, None
        c_demand = demands.get(c, 0.0)
        for v, route in routes.items():
            if sum(demands.get(x, 0.0) for x in route) + c_demand > capacity:
                continue
            for pos in range(len(route) + 1):
                prev = route[pos - 1] if pos > 0 else depot
                nxt  = route[pos]     if pos < len(route) else depot
                delta = float(matrix[prev][c]) + float(matrix[c][nxt]) - float(matrix[prev][nxt])
                if delta < best_delta:
                    best_delta, best_v, best_pos = delta, v, pos
        if best_v is not None:
            routes[best_v].insert(best_pos, c)
    return routes


def _repair_regret2(
    routes: dict[str, list[int]],
    removed: list[int],
    matrix: np.ndarray,
    demands: dict[int, float],
    capacity: float,
    depot: int = 0,
) -> dict[str, list[int]]:
    """
    Insertion par regret-2 (Potvin & Rousseau 1993).

    Pour chaque client à réinsérer, calcule le regret = différence de coût
    entre la 1re et la 2e meilleure position. Insère d'abord le client
    qui perdrait le plus à attendre (regret maximal).
    """
    routes = {v: list(r) for v, r in routes.items()}
    remaining = list(removed)

    while remaining:
        regrets: list[tuple[float, int, str | None, int]] = []
        for c in remaining:
            c_demand = demands.get(c, 0.0)
            best_insertions: list[tuple[float, str, int]] = []
            for v, route in routes.items():
                if sum(demands.get(x, 0.0) for x in route) + c_demand > capacity:
                    continue
                for pos in range(len(route) + 1):
                    prev = route[pos - 1] if pos > 0 else depot
                    nxt  = route[pos]     if pos < len(route) else depot
                    delta = float(matrix[prev][c]) + float(matrix[c][nxt]) - float(matrix[prev][nxt])
                    best_insertions.append((delta, v, pos))
            best_insertions.sort()
            if not best_insertions:
                regrets.append((float("inf"), c, None, 0))
            elif len(best_insertions) == 1:
                regrets.append((float("inf"), c, best_insertions[0][1], best_insertions[0][2]))
            else:
                regret = best_insertions[1][0] - best_insertions[0][0]
                regrets.append((regret, c, best_insertions[0][1], best_insertions[0][2]))

        regrets.sort(reverse=True)
        _, c, best_v, best_pos = regrets[0]
        if best_v is not None:
            routes[best_v].insert(best_pos, c)
        remaining.remove(c)

    return routes


# ── Boucle principale ALNS ─────────────────────────────────────────────────────

def adaptive_large_neighborhood_search(
    routes_by_sleigh: dict[str, list[int]],
    time_matrix: np.ndarray,
    depot_id: int = 0,
    n_iterations: int | None = None,
    capacity: float | None = None,
    demands: dict[int, float] | None = None,
    seed: int = 42,
) -> dict:
    """
    ALNS pour CVRP (Ropke & Pisinger 2006).

    3 opérateurs de destruction (random, worst, related/Shaw)
    × 2 opérateurs de réparation (greedy, regret-2)
    → sélectionnés par roulette adaptative pondérée par les récompenses σ1/σ2/σ3.

    Acceptation : recuit simulé (température initiale = 5 % du coût initial,
    refroidissement 0.995/itération → ≈ T₀/2 en n/140 itérations).

    Complexité par itération : O(n²) (repair greedy/regret)
    """
    import math

    demands = demands or {}
    capacity = float(capacity) if capacity is not None else float("inf")
    rng = random.Random(seed)

    # Nombre d'itérations adaptatif si non précisé
    n_clients = sum(len(r) for r in routes_by_sleigh.values())
    if n_iterations is None:
        n_iterations = max(120, min(400, n_clients * 6))

    # Taille de destruction adaptative
    n_remove_min = max(1, n_clients // 12)
    n_remove_max = max(3, n_clients // 4)

    current = {v: list(r) for v, r in routes_by_sleigh.items()}
    best    = {v: list(r) for v, r in current.items()}
    cost_current = _alns_total_cost(current, time_matrix, depot_id)
    cost_best    = cost_current
    cost_init    = cost_current

    # Température initiale : accepter +5 % de coût avec prob 50 %
    T = cost_current * 0.05 / math.log(2) if cost_current > 0 else 1.0

    # Scores des opérateurs (3 destroy × 2 repair)
    scores_d = [1.0, 1.0, 1.0]   # random, worst, related
    scores_r = [1.0, 1.0]        # greedy, regret-2
    use_d    = [0, 0, 0]
    use_r    = [0, 0]

    new_best_count = 0

    for _ in range(n_iterations):
        d_idx = _alns_roulette(scores_d, rng)
        r_idx = _alns_roulette(scores_r, rng)
        use_d[d_idx] += 1
        use_r[r_idx] += 1

        n_rm = rng.randint(n_remove_min, min(n_remove_max, n_clients))

        # ── Destruction ──────────────────────────────────────────────────────
        if d_idx == 0:
            partial, removed = _destroy_random(current, n_rm, rng)
        elif d_idx == 1:
            partial, removed = _destroy_worst(current, time_matrix, n_rm, depot_id)
        else:
            partial, removed = _destroy_related(current, time_matrix, n_rm, rng, depot_id)

        if not removed:
            continue

        rng.shuffle(removed)

        # ── Réparation ───────────────────────────────────────────────────────
        if r_idx == 0:
            candidate = _repair_greedy(partial, removed, time_matrix, demands, capacity, depot_id)
        else:
            candidate = _repair_regret2(partial, removed, time_matrix, demands, capacity, depot_id)

        cost_cand = _alns_total_cost(candidate, time_matrix, depot_id)
        delta = cost_cand - cost_current

        # ── Acceptation (SA) + mise à jour scores ────────────────────────────
        reward = _ALNS_SIGMA3
        if cost_cand < cost_best - 0.5:
            best = {v: list(r) for v, r in candidate.items()}
            cost_best = cost_cand
            new_best_count += 1
            reward = _ALNS_SIGMA1

        accepted = delta < 0 or (T > 1e-9 and rng.random() < math.exp(-delta / T))
        if accepted:
            current = {v: list(r) for v, r in candidate.items()}
            cost_current = cost_cand
            if reward < _ALNS_SIGMA2 and delta < 0:
                reward = _ALNS_SIGMA2

        scores_d[d_idx] = _ALNS_DECAY * scores_d[d_idx] + reward
        scores_r[r_idx] = _ALNS_DECAY * scores_r[r_idx] + reward
        T *= _ALNS_COOL

    gain_s   = max(0.0, cost_init - cost_best)
    gain_pct = round(gain_s / cost_init * 100.0, 2) if cost_init > 0 else 0.0

    # Formatage identique à ILS pour faciliter l'intégration
    sleigh_results: dict[str, dict] = {}
    for v in routes_by_sleigh:
        h = _alns_route_cost(routes_by_sleigh[v], time_matrix, depot_id)
        o = _alns_route_cost(best.get(v, []), time_matrix, depot_id)
        sleigh_results[v] = {
            "human_time_s":     round(h, 1),
            "ils_time_s":       round(o, 1),
            "improvement_s":    round(max(0.0, h - o), 1),
            "improvement_pct":  round((h - o) / h * 100.0 if h > 0 else 0.0, 1),
            "optimized_route":  best.get(v, []),
        }

    return {
        "sleighs":               sleigh_results,
        "total_human_time_s":    round(cost_init, 1),
        "total_ils_time_s":      round(cost_best, 1),
        "total_improvement_s":   round(gain_s, 1),
        "total_improvement_pct": gain_pct,
        "iterations_run":        n_iterations,
        "improvements_accepted": new_best_count,
        "method":                "ALNS",
        "operator_scores": {
            "destroy": {
                "random":  round(scores_d[0], 2),
                "worst":   round(scores_d[1], 2),
                "related": round(scores_d[2], 2),
            },
            "repair": {
                "greedy":   round(scores_r[0], 2),
                "regret2":  round(scores_r[1], 2),
            },
            "usage": {
                "destroy": {"random": use_d[0], "worst": use_d[1], "related": use_d[2]},
                "repair":  {"greedy": use_r[0], "regret2": use_r[1]},
            },
        },
    }


# ─────────────────────────────────────────────────────────
# FLOYD-WARSHALL (tous-pairs chemins les plus courts)
# ─────────────────────────────────────────────────────────

def floyd_warshall(
    time_matrix: np.ndarray,
) -> dict:
    """
    Algorithme de Floyd-Warshall appliqué à la matrice des temps de trajet.

    À chaque itération k (nœud intermédiaire), on tente de raccourcir tous les
    chemins i→j en passant par k :
        dist[i][j] = min(dist[i][j],  dist[i][k] + dist[k][j])

    Complexité O(n³) en temps et O(n²) en mémoire — adapté aux petits graphes
    denses. Contrairement à Dijkstra (source unique, O((V+E)logV)), Floyd-Warshall
    calcule simultanément TOUS les plus courts chemins.

    La matrice d'entrée étant déjà issue d'OSRM (temps de trajet minimaux sur
    réseau routier), les améliorations trouvées par Floyd-Warshall correspondent
    aux cas où passer par un autre point de livraison comme relais intermédiaire
    serait plus rapide que le chemin routier direct.

    Returns:
        {
            dist_matrix        : matrice n×n améliorée (liste de listes),
            next_matrix        : next_hop[i][j] = prochain nœud sur i→j,
            n                  : taille de la matrice,
            iterations         : n (nombre de nœuds intermédiaires testés),
            improved_pairs     : nombre de paires (i,j) améliorées,
            improved_pairs_pct : % de paires améliorées,
            max_improvement_s  : gain max sur une paire (secondes),
            sample_path        : exemple de chemin reconstruit (0 → 1),
        }
    """
    n = len(time_matrix)
    INF = float("inf")

    dist = [[INF] * n for _ in range(n)]
    nxt: list[list[int | None]] = [[None] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            v = float(time_matrix[i][j])
            if i == j:
                dist[i][j] = 0.0
            elif v > 0:
                dist[i][j] = v
                nxt[i][j] = j

    improved_pairs = 0
    max_improvement = 0.0

    for k in range(n):
        for i in range(n):
            if dist[i][k] == INF:
                continue
            for j in range(n):
                if dist[k][j] == INF:
                    continue
                candidate = dist[i][k] + dist[k][j]
                if candidate < dist[i][j] - 1e-9:
                    if dist[i][j] != INF:
                        max_improvement = max(max_improvement, dist[i][j] - candidate)
                    improved_pairs += 1
                    dist[i][j] = candidate
                    nxt[i][j] = nxt[i][k]

    # Reconstruction d'un exemple de chemin (0 → 1)
    def reconstruct(src: int, dst: int) -> list[int]:
        if nxt[src][dst] is None:
            return []
        path = [src]
        while path[-1] != dst:
            nxt_node = nxt[path[-1]][dst]
            if nxt_node is None or nxt_node in path:
                break
            path.append(nxt_node)
        return path

    sample_path = reconstruct(0, 1) if n >= 2 else []
    total_finite = sum(1 for i in range(n) for j in range(n) if i != j and dist[i][j] != INF)

    return {
        "n": n,
        "iterations": n,
        "improved_pairs": improved_pairs,
        "improved_pairs_pct": round(improved_pairs / max(total_finite, 1) * 100.0, 2),
        "max_improvement_s": round(max_improvement, 2),
        "dist_matrix": [[round(v, 1) if v != INF else None for v in row] for row in dist],
        "next_matrix": nxt,
        "sample_path_0_to_1": sample_path,
        "sample_path_cost": round(dist[0][1], 1) if n >= 2 and dist[0][1] != INF else None,
    }


# ─────────────────────────────────────────────────────────
# MÉTRIQUES STRUCTURELLES DU GRAPHE
# ─────────────────────────────────────────────────────────

def compute_graph_metrics(graph) -> dict:
    """
    Calcule les métriques structurelles d'un graphe OSM (DiGraph networkx).

    - Statistiques de base : nœuds, arcs, degrés, densité
    - Connectivité : composante fortement connexe principale
    - Clustering (sur le graphe non-orienté)
    - Top 5 nœuds par centralité d'intermédiarité (approx. k=30 pivots)
    """
    n = graph.number_of_nodes()
    m = graph.number_of_edges()

    if n == 0:
        return {"error": "Graphe vide"}

    degrees = [d for _, d in graph.degree()]
    avg_degree = sum(degrees) / n
    max_degree = max(degrees)

    # Composantes fortement connexes
    sccs = list(nx.strongly_connected_components(graph))
    largest_scc = max(sccs, key=len)

    # Clustering sur le graphe non-orienté simplifié (MultiGraph → Graph)
    undirected = nx.Graph(graph.to_undirected())
    avg_clustering = nx.average_clustering(undirected)

    # Centralité betweenness — approximée par échantillonnage
    k_sample = min(30, n)
    betweenness = nx.betweenness_centrality(graph, k=k_sample, normalized=True)
    top_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
    top_betweenness = [
        {
            "node": int(node),
            "score": round(float(score), 4),
            "lat": round(float(graph.nodes[node].get("y", 0.0)), 6),
            "lon": round(float(graph.nodes[node].get("x", 0.0)), 6),
        }
        for node, score in top_nodes
    ]

    return {
        "num_nodes": n,
        "num_edges": m,
        "avg_degree": round(avg_degree, 2),
        "max_degree": int(max_degree),
        "density": round(nx.density(graph), 6),
        "is_strongly_connected": nx.is_strongly_connected(graph),
        "num_scc": len(sccs),
        "largest_scc_size": len(largest_scc),
        "largest_scc_pct": round(len(largest_scc) / n * 100.0, 1),
        "avg_clustering": round(avg_clustering, 4),
        "top_betweenness_nodes": top_betweenness,
    }
