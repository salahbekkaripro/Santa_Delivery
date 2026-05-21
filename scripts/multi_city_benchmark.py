#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import services
from scripts.mission_paths import mission_paths
from scripts import ro_heuristics_experiment as ro_exp


DEFAULT_ZONES = [
    "Le Marais, Paris",
    "Mitte, Berlin",
    "Vieux Lyon, Lyon",
    "Quartier des Marolles, Bruxelles",
]


@dataclass
class CityRunRecord:
    phase: int
    mission_id: str
    zone: str
    policy_id: str
    policy_label: str
    status: str
    signature_sha256: str | None
    composite_cost: float | None
    total_time_s: float | None
    total_dist_m: float | None
    dropped_points: int | None
    wall_time_s: float | None
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark multi-city for solver policies with optional reproducibility check."
    )
    parser.add_argument(
        "--zones",
        default="|".join(DEFAULT_ZONES),
        help="Zone list separated with '|' (keeps commas inside city names)",
    )
    parser.add_argument(
        "--zone",
        action="append",
        default=None,
        help="Single zone entry; repeat this flag for multiple zones",
    )
    parser.add_argument("--missions-per-zone", type=int, default=2, help="Generated missions per zone")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--policies",
        default="pca_gls_fast,pca_sa_balanced,pci_gls_deep,savings_tabu,pca_gls_distance,pci_gls_distance",
        help="Comma-separated policy ids",
    )
    parser.add_argument("--repeat-runs", type=int, default=2, help="Re-run same missions this many times")
    parser.add_argument("--num-vehicles", type=int, default=0, help="Fleet size override (0=auto)")
    parser.add_argument("--vehicle-capacity", type=int, default=220)
    parser.add_argument("--speed-multiplier", type=float, default=1.0)
    parser.add_argument("--context-mode", choices=["stable", "varied"], default="stable")
    parser.add_argument("--min-clients", type=int, default=18)
    parser.add_argument("--max-clients", type=int, default=36)
    parser.add_argument(
        "--output-json",
        default="daily_reports/multi_city_benchmark_summary.json",
        help="Summary output path",
    )
    parser.add_argument(
        "--output-jsonl",
        default="daily_reports/multi_city_benchmark_runs.jsonl",
        help="Raw runs output path",
    )
    return parser.parse_args()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_list(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    if "|" in text:
        return [part.strip() for part in text.split("|") if part.strip()]
    return [part.strip() for part in text.split(";") if part.strip()]


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    np.random.seed(int(seed))


def _safe_mean(values: list[float]) -> float | None:
    return round(float(sum(values) / len(values)), 4) if values else None


def _canonical_result_signature(path: Path) -> str | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    tours = payload.get("tours", []) if isinstance(payload, dict) else []
    canonical_tours: list[dict[str, Any]] = []
    for tour in tours:
        if not isinstance(tour, dict):
            continue
        vehicle_id = int(tour.get("vehicle_id", 0))
        route_ids = [int(node_id) for node_id in (tour.get("route_ids") or [])]
        canonical_tours.append({"vehicle_id": vehicle_id, "route_ids": route_ids})
    canonical_tours = sorted(canonical_tours, key=lambda row: int(row["vehicle_id"]))
    canonical = {
        "status": str(payload.get("status", "")),
        "total_time_s": int(payload.get("total_time_s", 0)),
        "dropped_points": sorted(int(point_id) for point_id in (payload.get("dropped_points") or [])),
        "tours": canonical_tours,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    import hashlib

    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _build_create_payload(
    zone: str,
    *,
    zone_index: int,
    mission_index: int,
    seed: int,
    context_mode: str,
    min_clients: int,
    max_clients: int,
) -> dict[str, Any]:
    rng = random.Random(int(seed) + int(zone_index) * 10_000 + int(mission_index))
    if context_mode == "stable":
        num_clients = min(max(min_clients, 18), max_clients)
        weather_key = "Clear"
        random_incidents = False
        budget = int(num_clients * 110)
        sleigh_cost = 650
    else:
        weather_key = rng.choice(ro_exp.DEFAULT_WEATHER_KEYS)
        num_clients = rng.randint(min_clients, max_clients)
        random_incidents = (weather_key != "Clear" and rng.random() < 0.65) or (
            weather_key == "Clear" and rng.random() < 0.2
        )
        budget = int(num_clients * rng.randint(90, 140))
        sleigh_cost = rng.choice([500, 550, 600, 650, 700, 800])

    return {
        "zone": zone,
        "num_clients": int(num_clients),
        "budget": int(budget),
        "sleigh_cost": int(sleigh_cost),
        "weather_key": weather_key,
        "random_incidents": bool(random_incidents),
    }


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_summary(records: list[CityRunRecord], repeat_runs: int) -> dict[str, Any]:
    zone_policy_metrics: dict[str, dict[str, Any]] = {}
    grouped: dict[tuple[str, str], list[CityRunRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.zone, record.policy_id)].append(record)

    for (zone, policy_id), rows in sorted(grouped.items()):
        ok_rows = [row for row in rows if row.status == "ok"]
        zone_policy_metrics[f"{zone}::{policy_id}"] = {
            "zone": zone,
            "policy_id": policy_id,
            "policy_label": rows[0].policy_label if rows else policy_id,
            "run_count": len(rows),
            "ok_count": len(ok_rows),
            "avg_composite_cost": _safe_mean([float(r.composite_cost) for r in ok_rows if r.composite_cost is not None]),
            "avg_total_time_s": _safe_mean([float(r.total_time_s) for r in ok_rows if r.total_time_s is not None]),
            "avg_total_dist_m": _safe_mean([float(r.total_dist_m) for r in ok_rows if r.total_dist_m is not None]),
            "avg_dropped_points": _safe_mean([float(r.dropped_points) for r in ok_rows if r.dropped_points is not None]),
        }

    best_policy_by_zone: dict[str, dict[str, Any]] = {}
    zones = sorted({record.zone for record in records})
    policies = sorted({record.policy_id for record in records})

    for zone in zones:
        candidates: list[tuple[float, str, dict[str, Any]]] = []
        for policy_id in policies:
            key = f"{zone}::{policy_id}"
            row = zone_policy_metrics.get(key)
            if not row:
                continue
            avg_cost = row.get("avg_composite_cost")
            if avg_cost is None:
                continue
            candidates.append((float(avg_cost), policy_id, row))
        if not candidates:
            continue
        candidates.sort(key=lambda item: item[0])
        best = candidates[0][2]
        best_policy_by_zone[zone] = {
            "policy_id": best["policy_id"],
            "policy_label": best["policy_label"],
            "avg_composite_cost": best["avg_composite_cost"],
        }

    reproducibility: dict[str, Any] = {}
    if repeat_runs >= 2:
        signatures: dict[tuple[str, str], dict[int, str | None]] = defaultdict(dict)
        for row in records:
            signatures[(row.mission_id, row.policy_id)][int(row.phase)] = row.signature_sha256

        total_pairs = 0
        identical_pairs = 0
        per_policy = defaultdict(lambda: {"total": 0, "identical": 0})
        for (mission_id, policy_id), phase_map in signatures.items():
            ordered = [phase_map.get(p) for p in sorted(phase_map.keys())]
            if len(ordered) < 2 or any(sig is None for sig in ordered):
                continue
            total_pairs += 1
            per_policy[policy_id]["total"] += 1
            same = all(sig == ordered[0] for sig in ordered[1:])
            if same:
                identical_pairs += 1
                per_policy[policy_id]["identical"] += 1

        reproducibility = {
            "total_mission_policy_pairs": total_pairs,
            "identical_signature_pairs": identical_pairs,
            "global_rate": round(float(identical_pairs) / float(total_pairs), 4) if total_pairs > 0 else None,
            "per_policy": {
                pid: {
                    "identical": meta["identical"],
                    "total": meta["total"],
                    "rate": round(float(meta["identical"]) / float(meta["total"]), 4) if meta["total"] > 0 else None,
                }
                for pid, meta in sorted(per_policy.items())
            },
        }

    return {
        "zone_policy_metrics": zone_policy_metrics,
        "best_policy_by_zone": best_policy_by_zone,
        "reproducibility": reproducibility,
    }


def run() -> int:
    args = parse_args()
    zones = [str(z).strip() for z in (args.zone or []) if str(z).strip()] or _parse_list(args.zones)
    policy_ids = ro_exp._policy_ids_from_arg(args.policies)
    policies = {pid: ro_exp.POLICY_LIBRARY[pid] for pid in policy_ids}

    if not zones:
        raise SystemExit("--zones must contain at least one zone")
    if args.missions_per_zone <= 0:
        raise SystemExit("--missions-per-zone must be > 0")
    if args.repeat_runs <= 0:
        raise SystemExit("--repeat-runs must be > 0")
    if args.min_clients <= 0:
        raise SystemExit("--min-clients must be > 0")
    if args.max_clients < args.min_clients:
        raise SystemExit("--max-clients must be >= --min-clients")

    started_at = _utcnow_iso()
    _seed_everything(args.seed)

    missions: list[dict[str, Any]] = []
    for zone_index, zone in enumerate(zones):
        for mission_index in range(args.missions_per_zone):
            payload = _build_create_payload(
                zone,
                zone_index=zone_index,
                mission_index=mission_index,
                seed=args.seed,
                context_mode=args.context_mode,
                min_clients=args.min_clients,
                max_clients=args.max_clients,
            )
            response = services.create_mission(payload)
            mission_id = str(response.get("mission_id"))
            missions.append(
                {
                    "mission_id": mission_id,
                    "zone": zone,
                    "payload": payload,
                }
            )

    output_jsonl = Path(args.output_jsonl)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_jsonl.write_text("", encoding="utf-8")

    records: list[CityRunRecord] = []
    total_runs = len(missions) * len(policy_ids) * int(args.repeat_runs)
    run_index = 0
    print(f"[INFO] Zones={len(zones)} Missions={len(missions)} Policies={len(policy_ids)} Repeat={args.repeat_runs}")

    for phase in range(1, int(args.repeat_runs) + 1):
        for mission in missions:
            mission_id = str(mission["mission_id"])
            zone = str(mission["zone"])
            for policy_id in policy_ids:
                run_index += 1
                policy = policies[policy_id]
                print(f"[RUN {run_index}/{total_runs}] phase={phase} zone={zone} mission={mission_id} policy={policy_id}")
                result = ro_exp._run_policy_on_mission(
                    mission_id,
                    policy_id,
                    policy,
                    num_vehicles_override=int(args.num_vehicles),
                    vehicle_capacity=int(args.vehicle_capacity),
                    speed_multiplier=float(args.speed_multiplier),
                )
                result_path = mission_paths(mission_id).root_dir / "ro_experiments" / f"result_{policy_id}.json"
                signature = _canonical_result_signature(result_path)

                row = CityRunRecord(
                    phase=phase,
                    mission_id=mission_id,
                    zone=zone,
                    policy_id=policy_id,
                    policy_label=str(policy.get("label", policy_id)),
                    status=result.status,
                    signature_sha256=signature,
                    composite_cost=result.composite_cost,
                    total_time_s=result.total_time_s,
                    total_dist_m=result.total_dist_m,
                    dropped_points=result.dropped_points,
                    wall_time_s=result.wall_time_s,
                    error=result.error,
                )
                records.append(row)
                _append_jsonl(output_jsonl, row.as_dict())

    summary = _build_summary(records, int(args.repeat_runs))

    payload = {
        "started_at": started_at,
        "ended_at": _utcnow_iso(),
        "params": {
            "zones": zones,
            "missions_per_zone": int(args.missions_per_zone),
            "seed": int(args.seed),
            "policy_ids": policy_ids,
            "repeat_runs": int(args.repeat_runs),
            "num_vehicles": int(args.num_vehicles),
            "vehicle_capacity": int(args.vehicle_capacity),
            "speed_multiplier": float(args.speed_multiplier),
            "context_mode": str(args.context_mode),
            "min_clients": int(args.min_clients),
            "max_clients": int(args.max_clients),
            "output_jsonl": str(output_jsonl),
        },
        "missions": missions,
        "run_count": len(records),
        "ok_count": len([r for r in records if r.status == "ok"]),
        "failed_count": len([r for r in records if r.status != "ok"]),
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
