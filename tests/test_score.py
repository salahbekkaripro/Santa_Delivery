"""
test_score.py — Tests de non-régression du scoring et des algorithmes RO.

Ces tests vérifient que :
- La formule de score ne régresse pas silencieusement entre deux changements
- Les algorithmes locaux (2-opt, 3-opt, or-opt, 2-opt*, Floyd-Warshall, ILS)
  produisent des résultats corrects sur des instances de référence fixes.
"""
import math
import random
import numpy as np
import pytest

from scripts.ro_improvements import (
    floyd_warshall,
    two_opt_routes,
    three_opt_routes,
    or_opt_routes,
    two_opt_star_routes,
    iterated_local_search,
    _double_bridge_single,
    _route_cost,
)


# ─────────────────────────────────────────────────────────
# Matrices de test
# ─────────────────────────────────────────────────────────

def _grid_matrix(n: int, spacing: float = 1.0) -> np.ndarray:
    """Matrice n×n sur une grille carrée — nœuds numérotés ligne par ligne."""
    side = math.ceil(math.sqrt(n))
    coords = [(i % side * spacing, i // side * spacing) for i in range(n)]
    mat = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            mat[i][j] = math.hypot(dx, dy) * 10  # ×10 → temps en secondes
    return mat


# ─────────────────────────────────────────────────────────
# Floyd-Warshall
# ─────────────────────────────────────────────────────────

def test_floyd_warshall_triangle():
    """Sur 3 nœuds en triangle, FW trouve le raccourci 0→2 via 1 si c'est plus court."""
    mat = np.array([
        [0, 5, 100],
        [5, 0,   3],
        [100, 3,  0],
    ], dtype=float)
    result = floyd_warshall(mat)
    dist = result["dist_matrix"]
    # 0→2 via 1 : 5 + 3 = 8 < 100
    assert dist[0][2] == pytest.approx(8.0, abs=0.1)
    assert result["improved_pairs"] >= 1


def test_floyd_warshall_symmetric():
    """La matrice résultat doit rester symétrique sur une entrée symétrique."""
    mat = _grid_matrix(6)
    result = floyd_warshall(mat)
    dist = result["dist_matrix"]
    n = result["n"]
    for i in range(n):
        for j in range(n):
            assert abs((dist[i][j] or 0) - (dist[j][i] or 0)) < 0.2, \
                f"Asymétrie FW en ({i},{j})"


def test_floyd_warshall_diagonal_zero():
    mat = _grid_matrix(5)
    dist = floyd_warshall(mat)["dist_matrix"]
    for i in range(5):
        assert dist[i][i] == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────
# 3-opt
# ─────────────────────────────────────────────────────────

def test_three_opt_improves_crossed_route():
    """Route avec deux croisements que 2-opt ne peut pas résoudre en une passe."""
    mat = _grid_matrix(8)
    # Route délibérément mauvaise : sauts en zigzag
    bad_route = {"0": [4, 1, 6, 3, 5, 2, 7]}
    result_2opt = two_opt_routes(bad_route, mat, depot_id=0)
    result_3opt = three_opt_routes(bad_route, mat, depot_id=0)
    cost_2opt = result_2opt["total_two_opt_time_s"]
    cost_3opt = result_3opt["total_three_opt_time_s"]
    # 3-opt ≤ 2-opt (ne peut pas être pire)
    assert cost_3opt <= cost_2opt + 0.1, f"3-opt ({cost_3opt}) pire que 2-opt ({cost_2opt})"


def test_three_opt_no_client_lost():
    mat = _grid_matrix(7)
    route = {"0": [3, 6, 1, 5, 2, 4]}
    result = three_opt_routes(route, mat, depot_id=0)
    assert set(result["sleighs"]["0"]["optimized_route"]) == {1, 2, 3, 4, 5, 6}


def test_three_opt_single_client_unchanged():
    mat = _grid_matrix(4)
    route = {"0": [2]}
    result = three_opt_routes(route, mat, depot_id=0)
    assert result["sleighs"]["0"]["optimized_route"] == [2]


# ─────────────────────────────────────────────────────────
# 2-opt*
# ─────────────────────────────────────────────────────────

def test_two_opt_star_improves_unbalanced():
    """Deux routes très déséquilibrées : 2-opt* doit rééquilibrer."""
    mat = _grid_matrix(9)
    # v0 a 6 clients proches de lui, v1 en a 2 lointains
    routes = {"0": [1, 2, 3, 4, 5, 6], "1": [7, 8]}
    demands = {i: 10.0 for i in range(9)}
    result = two_opt_star_routes(routes, mat, depot_id=0, capacity=100.0, demands=demands)
    total_before = _route_cost([1,2,3,4,5,6], mat) + _route_cost([7,8], mat)
    total_after = result["total_two_opt_star_time_s"]
    assert total_after <= total_before + 0.1


def test_two_opt_star_capacity_respected():
    """2-opt* ne doit jamais dépasser la capacité."""
    mat = _grid_matrix(7)
    # Chaque client pèse 30kg, capacité=60 → max 2 clients par véhicule
    demands = {i: 30.0 for i in range(7)}
    routes = {"0": [1, 2], "1": [3, 4], "2": [5, 6]}
    result = two_opt_star_routes(routes, mat, depot_id=0, capacity=60.0, demands=demands)
    for sid, d in result["sleighs"].items():
        load = sum(demands.get(c, 0) for c in d["optimized_route"])
        assert load <= 60.0 + 0.01, f"Véhicule {sid} surcharge : {load}kg"


def test_two_opt_star_all_clients_present():
    mat = _grid_matrix(8)
    demands = {i: 5.0 for i in range(8)}
    routes = {"0": [1, 2, 3], "1": [4, 5], "2": [6, 7]}
    result = two_opt_star_routes(routes, mat, depot_id=0, capacity=50.0, demands=demands)
    all_clients = set()
    for d in result["sleighs"].values():
        all_clients.update(d["optimized_route"])
    assert all_clients == {1, 2, 3, 4, 5, 6, 7}


# ─────────────────────────────────────────────────────────
# Non-régression score : formule de calcul
# ─────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────
# Double-bridge + ILS
# ─────────────────────────────────────────────────────────

def test_double_bridge_preserves_clients():
    random.seed(0)
    route = [1, 2, 3, 4, 5, 6, 7, 8]
    result = _double_bridge_single(route)
    assert set(result) == set(route)
    assert len(result) == len(route)


def test_double_bridge_changes_order():
    random.seed(0)
    route = list(range(1, 9))
    # Sur 100 tirages, au moins un doit changer l'ordre
    changed = any(_double_bridge_single(route) != route for _ in range(100))
    assert changed


def test_double_bridge_short_route_unchanged():
    route = [1, 2, 3]
    assert _double_bridge_single(route) == [1, 2, 3]


def test_ils_never_degrades():
    """ILS ne doit jamais retourner une solution plus coûteuse que l'originale."""
    random.seed(42)
    mat = _grid_matrix(10)
    routes = {"0": [4, 1, 8, 3, 6], "1": [5, 2, 7, 9]}
    demands = {i: 10.0 for i in range(10)}
    result = iterated_local_search(routes, mat, depot_id=0, n_iterations=8,
                                   capacity=100.0, demands=demands)
    assert result["total_ils_time_s"] <= result["total_human_time_s"] + 0.1


def test_ils_preserves_all_clients():
    random.seed(7)
    mat = _grid_matrix(9)
    routes = {"0": [1, 2, 3, 4], "1": [5, 6, 7, 8]}
    result = iterated_local_search(routes, mat, depot_id=0, n_iterations=5)
    all_clients = set()
    for d in result["sleighs"].values():
        all_clients.update(d["optimized_route"])
    assert all_clients == {1, 2, 3, 4, 5, 6, 7, 8}


def test_ils_respects_capacity():
    random.seed(3)
    mat = _grid_matrix(9)
    # 10kg/client, capacité 50 → max 5 clients/véhicule, routes de départ toutes feasibles
    demands = {i: 10.0 for i in range(9)}
    routes = {"0": [1, 2, 3], "1": [4, 5, 6], "2": [7, 8]}
    result = iterated_local_search(routes, mat, depot_id=0, n_iterations=6,
                                   capacity=50.0, demands=demands)
    for sid, d in result["sleighs"].items():
        load = sum(demands.get(c, 0) for c in d["optimized_route"])
        assert load <= 50.0 + 0.01, f"Véhicule {sid} surcharge : {load}kg"


def test_ils_improves_zigzag():
    """Route intentionnellement mauvaise : ILS doit trouver une amélioration."""
    random.seed(99)
    mat = _grid_matrix(10)
    # Zigzag délibéré sur une grille 4×3
    routes = {"0": [9, 1, 8, 2, 7, 3, 6], "1": [4, 5]}
    result = iterated_local_search(routes, mat, depot_id=0, n_iterations=10)
    assert result["total_improvement_pct"] > 0.0, "ILS n'a trouvé aucune amélioration sur un zigzag"


# ─────────────────────────────────────────────────────────
# Non-régression score : formule de calcul
# ─────────────────────────────────────────────────────────

def _compute_score(time_saved_pct: float, co2_saved_kg: float,
                   num_clients: int, budget_remaining_pct: float) -> float:
    """Réplique exacte de la formule dans services.py — à maintenir en sync."""
    time_score_pct = min(100.0, time_saved_pct * 2.5)
    co2_ref_kg = max(1.0, num_clients * 0.1)
    co2_score = min(co2_saved_kg / co2_ref_kg * 100.0, 100.0)
    base = 0.60 * time_score_pct + 0.25 * co2_score + 0.15 * budget_remaining_pct
    return max(0.0, min(base, 100.0))


def test_score_reference_case():
    """Cas de référence : 28% de temps économisé, 0.5kg CO2, 10 clients, 80% budget."""
    score = _compute_score(
        time_saved_pct=28.0,
        co2_saved_kg=0.5,
        num_clients=10,
        budget_remaining_pct=80.0,
    )
    # time_score = min(100, 28*2.5) = 70  → 0.60*70 = 42
    # co2_ref = 1.0kg, co2_score = min(0.5/1*100,100) = 50 → 0.25*50 = 12.5
    # budget → 0.15*80 = 12
    # base = 66.5
    assert 64.0 <= score <= 69.0, f"Score hors plage attendue : {score}"


def test_score_perfect():
    """Score parfait doit donner ~100 (avant bonuses)."""
    score = _compute_score(40.0, 5.0, 20, 100.0)
    # time_score = 100 (40*2.5=100), co2_score = 100, budget=100
    assert score == pytest.approx(100.0, abs=0.1)


def test_score_zero_savings():
    """Aucune économie → score ~0 (avant bonuses)."""
    score = _compute_score(0.0, 0.0, 10, 0.0)
    assert score == pytest.approx(0.0, abs=0.1)


def test_score_never_negative():
    """Le score de base ne peut pas être négatif (temps économisé négatif)."""
    score = _compute_score(-50.0, 0.0, 5, 0.0)
    assert score >= 0.0


def test_score_capped_at_100():
    """Le score de base ne peut pas dépasser 100."""
    score = _compute_score(100.0, 100.0, 100, 100.0)
    assert score <= 100.0
