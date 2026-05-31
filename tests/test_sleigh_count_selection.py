from pathlib import Path

import pandas as pd

from backend.app import services


class _Paths:
    root_dir = Path("/tmp/noel-test")
    dist_matrix_file = Path("/tmp/noel-test/dist.npy")


def test_sleigh_count_respects_capacity_minimum(monkeypatch):
    df = pd.DataFrame(
        [{"id": 0, "poids_colis": 0}]
        + [{"id": i, "poids_colis": 100} for i in range(1, 11)]
    )
    mission = {"num_clients": 10, "sleigh_cost": 0}
    strategy = {
        "num_vehicles": 2,
        "vehicle_capacity": 200,
        "drop_penalty": 1_000_000,
        "solver_time_limit_s": 10,
    }

    def fake_solve(*args, **kwargs):
        return {"total_time_s": int(kwargs.get("ai_strategy", {}).get("num_vehicles", 1)) * 10, "dropped_points": []}

    monkeypatch.setattr(services, "_solve_vrp_from_strategy", fake_solve)
    monkeypatch.setattr(services, "_solution_total_distance_m", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(services, "SLEIGH_SEARCH_MAX_K", 2)

    selected = services._select_sleigh_count_with_halving(
        _Paths(),
        mission,
        df,
        weather={},
        incident_matrix_path=None,
        ai_strategy=strategy,
        compact_budget=True,
    )

    assert selected["num_vehicles"] >= 5
    assert selected["sleigh_search"]["k_min_capacity"] == 5


def test_large_sleigh_count_search_tests_base_above_capacity_minimum(monkeypatch):
    df = pd.DataFrame(
        [{"id": 0, "poids_colis": 0}]
        + [{"id": i, "poids_colis": 10} for i in range(1, 1001)]
    )
    mission = {"num_clients": 1000, "sleigh_cost": 0}
    strategy = {
        "num_vehicles": 334,
        "vehicle_capacity": 100,
        "drop_penalty": 1_000_000,
        "solver_time_limit_s": 10,
    }
    probed: list[int] = []

    def fake_solve(*args, **kwargs):
        probe_strategy = args[4] if len(args) >= 5 else kwargs.get("ai_strategy", {})
        k = int(probe_strategy.get("num_vehicles", 1))
        probed.append(k)
        dropped = list(range(k, 1000))
        return {"total_time_s": 1000 - k, "dropped_points": dropped}

    monkeypatch.setattr(services, "_solve_vrp_from_strategy", fake_solve)
    monkeypatch.setattr(services, "_solution_total_distance_m", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(services, "SLEIGH_SEARCH_MAX_K", 8)

    selected = services._select_sleigh_count_with_halving(
        _Paths(),
        mission,
        df,
        weather={},
        incident_matrix_path=None,
        ai_strategy=strategy,
        compact_budget=True,
    )

    assert selected["sleigh_search"]["k_min_capacity"] == 100
    assert selected["sleigh_search"]["k_max"] == 334
    assert 334 in probed
    assert selected["num_vehicles"] == 334
