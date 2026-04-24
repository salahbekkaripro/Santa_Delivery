#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import repository, services
from final_scripts.solve_santa_final import solve_vrp
from scripts.benchmark_engine import calculate_benchmark
from scripts.mission_paths import mission_paths


DEFAULT_ZONES = [
    "Le Marais, Paris",
    "Mitte, Berlin",
    "Vieux Lyon, Lyon",
    "Quartier des Marolles, Bruxelles",
    "Bordeaux Centre",
]
DEFAULT_WEATHER_KEYS = ["Clear", "Rain", "Snow", "Thunderstorm"]

POLICY_LIBRARY: dict[str, dict[str, Any]] = {
    "pca_gls_fast": {
        "label": "PATH_CHEAPEST_ARC + GLS (rapide)",
        "optimization_target": "time",
        "first_solution_strategy": "path_cheapest_arc",
        "local_search_metaheuristic": "guided_local_search",
        "solver_time_limit_s": 12,
        "time_slack_s": 3000,
        "max_route_time_s": 15000,
        "drop_penalty": 900_000,
        "global_span_cost": 80,
    },
    "pca_sa_balanced": {
        "label": "PATH_CHEAPEST_ARC + SA",
        "optimization_target": "time",
        "first_solution_strategy": "path_cheapest_arc",
        "local_search_metaheuristic": "simulated_annealing",
        "solver_time_limit_s": 18,
        "time_slack_s": 3600,
        "max_route_time_s": 15600,
        "drop_penalty": 1_200_000,
        "global_span_cost": 90,
    },
    "pci_gls_deep": {
        "label": "PARALLEL_CHEAPEST_INSERTION + GLS",
        "optimization_target": "time",
        "first_solution_strategy": "parallel_cheapest_insertion",
        "local_search_metaheuristic": "guided_local_search",
        "solver_time_limit_s": 28,
        "time_slack_s": 4200,
        "max_route_time_s": 18000,
        "drop_penalty": 1_300_000,
        "global_span_cost": 140,
    },
    "savings_tabu": {
        "label": "SAVINGS + TABU",
        "optimization_target": "time",
        "first_solution_strategy": "savings",
        "local_search_metaheuristic": "tabu_search",
        "solver_time_limit_s": 22,
        "time_slack_s": 3600,
        "max_route_time_s": 15600,
        "drop_penalty": 1_050_000,
        "global_span_cost": 110,
    },
    "pca_gls_distance": {
        "label": "PATH_CHEAPEST_ARC + GLS (distance)",
        "optimization_target": "distance",
        "first_solution_strategy": "path_cheapest_arc",
        "local_search_metaheuristic": "guided_local_search",
        "solver_time_limit_s": 20,
        "time_slack_s": 3600,
        "max_route_time_s": 16000,
        "drop_penalty": 1_000_000,
        "global_span_cost": 100,
    },
    "pci_gls_distance": {
        "label": "PARALLEL_CHEAPEST_INSERTION + GLS (distance)",
        "optimization_target": "distance",
        "first_solution_strategy": "parallel_cheapest_insertion",
        "local_search_metaheuristic": "guided_local_search",
        "solver_time_limit_s": 28,
        "time_slack_s": 4200,
        "max_route_time_s": 18000,
        "drop_penalty": 1_200_000,
        "global_span_cost": 130,
    },
}


@dataclass
class RunRecord:
    mission_id: str
    context_key: str
    policy_id: str
    policy_label: str
    status: str
    wall_time_s: float | None = None
    composite_cost: float | None = None
    total_time_s: float | None = None
    total_dist_m: float | None = None
    dropped_points: int | None = None
    num_tours: int | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "context_key": self.context_key,
            "policy_id": self.policy_id,
            "policy_label": self.policy_label,
            "status": self.status,
            "wall_time_s": self.wall_time_s,
            "composite_cost": self.composite_cost,
            "total_time_s": self.total_time_s,
            "total_dist_m": self.total_dist_m,
            "dropped_points": self.dropped_points,
            "num_tours": self.num_tours,
            "error": self.error,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a reproducible OR-Tools heuristics experiment on fixed mission instances."
    )
    parser.add_argument("--mode", choices=["existing", "generate"], default="existing")
    parser.add_argument("--instances", type=int, default=6, help="Number of mission instances to evaluate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument(
        "--policies",
        default="pca_gls_fast,pca_sa_balanced,pci_gls_deep,savings_tabu,pca_gls_distance,pci_gls_distance",
        help="Comma-separated policy ids to evaluate.",
    )
    parser.add_argument("--num-vehicles", type=int, default=0, help="Fixed fleet size (0 = auto by mission size).")
    parser.add_argument("--vehicle-capacity", type=int, default=220)
    parser.add_argument("--speed-multiplier", type=float, default=1.0)
    parser.add_argument("--context-mode", choices=["stable", "varied"], default="varied")
    parser.add_argument("--min-clients", type=int, default=10)
    parser.add_argument("--max-clients", type=int, default=42)
    parser.add_argument(
        "--output-json",
        default="daily_reports/ro_heuristics_experiment_summary.json",
        help="Summary report output path.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="daily_reports/ro_heuristics_experiment_runs.jsonl",
        help="Raw run logs output path (one JSON line per run).",
    )
    return parser.parse_args()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _policy_ids_from_arg(raw: str) -> list[str]:
    policy_ids = [part.strip() for part in str(raw).split(",") if part.strip()]
    unknown = [pid for pid in policy_ids if pid not in POLICY_LIBRARY]
    if unknown:
        raise ValueError(f"Unknown policy id(s): {', '.join(unknown)}")
    if not policy_ids:
        raise ValueError("At least one policy id is required.")
    return policy_ids


def _auto_num_vehicles(num_clients: int) -> int:
    # Keep a realistic fleet size while preserving comparability across policies.
    return max(2, min(6, int(round(float(num_clients) / 12.0))))


def _build_create_payload(index: int, *, context_mode: str, min_clients: int, max_clients: int) -> dict[str, Any]:
    zone = DEFAULT_ZONES[index % len(DEFAULT_ZONES)]
    if context_mode == "stable":
        num_clients = min(max(min_clients, 18), max_clients)
        weather_key = "Clear"
        random_incidents = False
        budget = int(num_clients * 110)
        sleigh_cost = 650
    else:
        weather_key = random.choice(DEFAULT_WEATHER_KEYS)
        num_clients = random.randint(min_clients, max_clients)
        random_incidents = (weather_key != "Clear" and random.random() < 0.65) or (
            weather_key == "Clear" and random.random() < 0.2
        )
        budget = int(num_clients * random.randint(90, 140))
        sleigh_cost = random.choice([500, 550, 600, 650, 700, 800])

    return {
        "zone": zone,
        "num_clients": num_clients,
        "budget": budget,
        "sleigh_cost": sleigh_cost,
        "weather_key": weather_key,
        "random_incidents": random_incidents,
    }


def _select_existing_missions(target_count: int) -> list[str]:
    snapshots = repository.list_mission_snapshots(limit=max(target_count * 8, target_count))
    selected: list[str] = []
    for snapshot in snapshots:
        mission_id = str(snapshot.get("mission_id", ""))
        if not mission_id:
            continue
        paths = mission_paths(mission_id)
        required = [
            paths.mission_file,
            paths.data_file,
            paths.time_matrix_file,
            paths.dist_matrix_file,
            paths.weather_file,
        ]
        if not all(path.exists() for path in required):
            continue
        selected.append(mission_id)
        if len(selected) >= target_count:
            break
    if len(selected) < target_count:
        raise ValueError(
            f"Not enough reusable missions with full data ({len(selected)}/{target_count}). "
            "Generate more missions first or lower --instances."
        )
    return selected


def _generate_missions(target_count: int, *, context_mode: str, min_clients: int, max_clients: int) -> list[str]:
    mission_ids: list[str] = []
    for index in range(target_count):
        payload = _build_create_payload(
            index,
            context_mode=context_mode,
            min_clients=min_clients,
            max_clients=max_clients,
        )
        response = services.create_mission(payload)
        mission_ids.append(str(response["mission_id"]))
    return mission_ids


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _run_policy_on_mission(
    mission_id: str,
    policy_id: str,
    policy: dict[str, Any],
    *,
    num_vehicles_override: int,
    vehicle_capacity: int,
    speed_multiplier: float,
) -> RunRecord:
    paths, mission, _ = services.load_mission_bundle(mission_id)
    context_key = services._mission_learning_context(mission)
    num_clients = max(1, int(mission.get("num_clients", 1)))
    num_vehicles = int(num_vehicles_override) if int(num_vehicles_override) > 0 else _auto_num_vehicles(num_clients)
    weather = services.load_weather(paths.weather_file, mission.get("weather_key"))
    incident_matrix_path = services._build_incident_matrix(paths, mission)
    experiment_dir = paths.root_dir / "ro_experiments"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    output_json_path = experiment_dir / f"result_{policy_id}.json"
    benchmark_json_path = experiment_dir / f"benchmark_{policy_id}.json"

    start = time.perf_counter()
    try:
        results = solve_vrp(
            num_vehicles=num_vehicles,
            vehicle_capacity=int(vehicle_capacity),
            speed_multiplier=float(speed_multiplier),
            forced_weather=weather,
            incident_matrix_path=incident_matrix_path,
            data_path=str(paths.data_file),
            time_matrix_path=str(paths.time_matrix_file),
            dist_matrix_path=str(paths.dist_matrix_file),
            weather_file=str(paths.weather_file),
            output_path=str(output_json_path),
            optimization_target=str(policy["optimization_target"]),
            solver_time_limit_s=int(policy["solver_time_limit_s"]),
            first_solution_strategy=str(policy["first_solution_strategy"]),
            local_search_metaheuristic=str(policy["local_search_metaheuristic"]),
            time_slack_s=int(policy["time_slack_s"]),
            max_route_time_s=int(policy["max_route_time_s"]),
            drop_penalty=int(policy["drop_penalty"]),
            global_span_cost=int(policy["global_span_cost"]),
        )
        elapsed = float(time.perf_counter() - start)
        if not isinstance(results, dict):
            return RunRecord(
                mission_id=mission_id,
                context_key=context_key,
                policy_id=policy_id,
                policy_label=str(policy["label"]),
                status="failed",
                wall_time_s=elapsed,
                error="solve_vrp returned no result",
            )

        benchmark = calculate_benchmark(
            num_vehicles=num_vehicles,
            budget_initial=int(mission.get("budget", 0)),
            budget_spent=int(num_vehicles * int(mission.get("sleigh_cost", 0))),
            data_path=str(paths.data_file),
            time_matrix_path=str(paths.time_matrix_file),
            dist_matrix_path=str(paths.dist_matrix_file),
            optimized_json_path=str(output_json_path),
            benchmark_file=str(benchmark_json_path),
        )
        composite_cost = services._compute_training_cost(mission, results, benchmark=benchmark)
        total_time_s = services._safe_float(results.get("total_time_s"))
        total_dist_m = services._safe_float((benchmark.get("optimized") or {}).get("total_dist_m"))
        dropped_points = len(results.get("dropped_points", [])) if isinstance(results.get("dropped_points", []), list) else None
        num_tours = len(results.get("tours", [])) if isinstance(results.get("tours", []), list) else None
        return RunRecord(
            mission_id=mission_id,
            context_key=context_key,
            policy_id=policy_id,
            policy_label=str(policy["label"]),
            status="ok",
            wall_time_s=round(elapsed, 4),
            composite_cost=None if composite_cost is None else round(float(composite_cost), 4),
            total_time_s=None if total_time_s is None else round(float(total_time_s), 4),
            total_dist_m=None if total_dist_m is None else round(float(total_dist_m), 4),
            dropped_points=dropped_points,
            num_tours=num_tours,
        )
    except Exception as exc:
        elapsed = float(time.perf_counter() - start)
        return RunRecord(
            mission_id=mission_id,
            context_key=context_key,
            policy_id=policy_id,
            policy_label=str(policy["label"]),
            status="failed",
            wall_time_s=round(elapsed, 4),
            error=str(exc),
        )


def _mean_std(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "std": None}
    arr = np.array(values, dtype=float)
    return {"mean": round(float(arr.mean()), 4), "std": round(float(arr.std(ddof=0)), 4)}


def _build_summary(
    records: list[RunRecord],
    *,
    policy_ids: list[str],
    policies: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    policy_stats: dict[str, dict[str, Any]] = {}
    winners_by_instance: dict[str, dict[str, Any]] = {}

    for policy_id in policy_ids:
        ok_records = [r for r in records if r.policy_id == policy_id and r.status == "ok"]
        failed_records = [r for r in records if r.policy_id == policy_id and r.status != "ok"]
        policy_stats[policy_id] = {
            "label": str(policies[policy_id]["label"]),
            "run_count": len(ok_records) + len(failed_records),
            "ok_count": len(ok_records),
            "failed_count": len(failed_records),
            "composite_cost": _mean_std([float(r.composite_cost) for r in ok_records if r.composite_cost is not None]),
            "total_time_s": _mean_std([float(r.total_time_s) for r in ok_records if r.total_time_s is not None]),
            "total_dist_m": _mean_std([float(r.total_dist_m) for r in ok_records if r.total_dist_m is not None]),
            "dropped_points": _mean_std([float(r.dropped_points) for r in ok_records if r.dropped_points is not None]),
            "wall_time_s": _mean_std([float(r.wall_time_s) for r in ok_records if r.wall_time_s is not None]),
        }

    by_mission: dict[str, list[RunRecord]] = {}
    for record in records:
        by_mission.setdefault(record.mission_id, []).append(record)
    for mission_id, mission_records in sorted(by_mission.items()):
        feasible = [r for r in mission_records if r.status == "ok" and r.composite_cost is not None]
        if not feasible:
            continue
        best = min(feasible, key=lambda row: float(row.composite_cost))
        winners_by_instance[mission_id] = {
            "best_policy_id": best.policy_id,
            "best_policy_label": best.policy_label,
            "best_composite_cost": best.composite_cost,
        }

    win_counts: dict[str, int] = {policy_id: 0 for policy_id in policy_ids}
    for winner in winners_by_instance.values():
        pid = str(winner["best_policy_id"])
        if pid in win_counts:
            win_counts[pid] += 1

    baseline_id = policy_ids[0]
    baseline_records = {
        record.mission_id: record
        for record in records
        if record.policy_id == baseline_id and record.status == "ok" and record.composite_cost is not None
    }
    deltas_vs_baseline: dict[str, dict[str, float | None]] = {}
    for policy_id in policy_ids[1:]:
        policy_records = {
            record.mission_id: record
            for record in records
            if record.policy_id == policy_id and record.status == "ok" and record.composite_cost is not None
        }
        common_missions = sorted(set(baseline_records.keys()) & set(policy_records.keys()))
        if not common_missions:
            deltas_vs_baseline[policy_id] = {"avg_delta_cost": None, "mission_count": 0}
            continue
        deltas = [
            float(policy_records[mid].composite_cost) - float(baseline_records[mid].composite_cost)
            for mid in common_missions
        ]
        deltas_vs_baseline[policy_id] = {
            "avg_delta_cost": round(float(np.mean(np.array(deltas, dtype=float))), 4),
            "mission_count": len(common_missions),
        }

    return {
        "policies": policy_stats,
        "wins_by_policy": win_counts,
        "winners_by_instance": winners_by_instance,
        "baseline_policy_id": baseline_id,
        "deltas_vs_baseline": deltas_vs_baseline,
    }


def run() -> int:
    args = parse_args()
    if args.instances <= 0:
        raise SystemExit("--instances must be > 0")
    if args.min_clients <= 0:
        raise SystemExit("--min-clients must be > 0")
    if args.max_clients < args.min_clients:
        raise SystemExit("--max-clients must be >= --min-clients")

    random.seed(args.seed)
    policy_ids = _policy_ids_from_arg(args.policies)
    policies = {policy_id: POLICY_LIBRARY[policy_id] for policy_id in policy_ids}

    started_at = _utcnow_iso()
    if args.mode == "existing":
        mission_ids = _select_existing_missions(args.instances)
    else:
        mission_ids = _generate_missions(
            args.instances,
            context_mode=args.context_mode,
            min_clients=args.min_clients,
            max_clients=args.max_clients,
        )

    records: list[RunRecord] = []
    output_jsonl = Path(args.output_jsonl)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_jsonl.write_text("", encoding="utf-8")

    total_runs = len(mission_ids) * len(policy_ids)
    run_index = 0
    print(f"[INFO] Instances={len(mission_ids)} | Policies={len(policy_ids)} | Total runs={total_runs}")

    for mission_id in mission_ids:
        for policy_id in policy_ids:
            run_index += 1
            policy = policies[policy_id]
            print(f"[RUN {run_index}/{total_runs}] mission={mission_id} policy={policy_id}")
            record = _run_policy_on_mission(
                mission_id,
                policy_id,
                policy,
                num_vehicles_override=args.num_vehicles,
                vehicle_capacity=args.vehicle_capacity,
                speed_multiplier=args.speed_multiplier,
            )
            records.append(record)
            _append_jsonl(output_jsonl, record.as_dict())
            if record.status == "ok":
                print(
                    f"[OK] cost={record.composite_cost} time_s={record.total_time_s} "
                    f"dist_m={record.total_dist_m} dropped={record.dropped_points}"
                )
            else:
                print(f"[WARN] {record.error}")

    summary = _build_summary(records, policy_ids=policy_ids, policies=policies)
    ended_at = _utcnow_iso()
    payload = {
        "started_at": started_at,
        "ended_at": ended_at,
        "params": {
            "mode": args.mode,
            "instances": args.instances,
            "seed": args.seed,
            "policy_ids": policy_ids,
            "num_vehicles": args.num_vehicles,
            "vehicle_capacity": args.vehicle_capacity,
            "speed_multiplier": args.speed_multiplier,
            "context_mode": args.context_mode,
            "min_clients": args.min_clients,
            "max_clients": args.max_clients,
            "output_jsonl": str(output_jsonl),
        },
        "mission_ids": mission_ids,
        "run_count": len(records),
        "ok_count": len([record for record in records if record.status == "ok"]),
        "failed_count": len([record for record in records if record.status != "ok"]),
        "summary": summary,
    }
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[INFO] Summary written to {output_json}")
    print(f"[INFO] Raw runs written to {output_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
