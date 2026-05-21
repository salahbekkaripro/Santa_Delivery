#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import ro_heuristics_experiment as ro_exp
from scripts.mission_paths import mission_paths


@dataclass
class MissionRunDigest:
    mission_id: str
    phase: int
    run_seed: int
    policy_id: str
    status: str
    signature_sha256: str | None
    composite_cost: float | None
    total_time_s: float | None
    total_dist_m: float | None
    dropped_points: int | None
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a strict reproducibility check on the solver: same missions + same seeds, "
            "run twice, compare solution signatures."
        )
    )
    parser.add_argument("--instances", type=int, default=4, help="Number of generated missions (default: %(default)s)")
    parser.add_argument("--seed", type=int, default=42, help="Global seed (default: %(default)s)")
    parser.add_argument(
        "--policy-id",
        default="pca_gls_fast",
        help="Policy id from scripts/ro_heuristics_experiment.py (default: %(default)s)",
    )
    parser.add_argument("--num-vehicles", type=int, default=0, help="Fleet size override, 0=auto (default: %(default)s)")
    parser.add_argument("--vehicle-capacity", type=int, default=220, help="Vehicle capacity (default: %(default)s)")
    parser.add_argument("--speed-multiplier", type=float, default=1.0, help="Speed multiplier (default: %(default)s)")
    parser.add_argument(
        "--context-mode",
        choices=["stable", "varied"],
        default="stable",
        help="Mission generation mode (default: %(default)s)",
    )
    parser.add_argument("--min-clients", type=int, default=18, help="Minimum clients (default: %(default)s)")
    parser.add_argument("--max-clients", type=int, default=36, help="Maximum clients (default: %(default)s)")
    parser.add_argument(
        "--output-json",
        default="daily_reports/repro_solver_pipeline_summary.json",
        help="Summary output JSON path (default: %(default)s)",
    )
    return parser.parse_args()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    np.random.seed(int(seed))


def _file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _mission_artifact_hashes(mission_id: str) -> dict[str, str | None]:
    paths = mission_paths(mission_id)
    return {
        "mission": _file_sha256(paths.mission_file),
        "data_csv": _file_sha256(paths.data_file),
        "graph": _file_sha256(paths.graph_file),
        "time_matrix": _file_sha256(paths.time_matrix_file),
        "dist_matrix": _file_sha256(paths.dist_matrix_file),
        "weather": _file_sha256(paths.weather_file),
        "incidents": _file_sha256(paths.incidents_file),
    }


def _run_phase(
    mission_ids: list[str],
    *,
    phase: int,
    seed: int,
    policy_id: str,
    num_vehicles: int,
    vehicle_capacity: int,
    speed_multiplier: float,
) -> tuple[list[MissionRunDigest], dict[str, str | None]]:
    policy = ro_exp.POLICY_LIBRARY[policy_id]
    digests: list[MissionRunDigest] = []
    signatures_by_mission: dict[str, str | None] = {}

    for index, mission_id in enumerate(mission_ids):
        run_seed = int(seed) + int(index)
        _seed_everything(run_seed)
        print(f"[PHASE {phase}] mission={mission_id} policy={policy_id} seed={run_seed}")

        record = ro_exp._run_policy_on_mission(
            mission_id,
            policy_id,
            policy,
            num_vehicles_override=num_vehicles,
            vehicle_capacity=vehicle_capacity,
            speed_multiplier=speed_multiplier,
        )

        result_path = mission_paths(mission_id).root_dir / "ro_experiments" / f"result_{policy_id}.json"
        signature = _canonical_result_signature(result_path)
        signatures_by_mission[mission_id] = signature

        digest = MissionRunDigest(
            mission_id=mission_id,
            phase=phase,
            run_seed=run_seed,
            policy_id=policy_id,
            status=record.status,
            signature_sha256=signature,
            composite_cost=record.composite_cost,
            total_time_s=record.total_time_s,
            total_dist_m=record.total_dist_m,
            dropped_points=record.dropped_points,
            error=record.error,
        )
        digests.append(digest)

        if record.status == "ok":
            print(
                f"  -> ok cost={record.composite_cost} time_s={record.total_time_s} "
                f"dist_m={record.total_dist_m} sig={signature}"
            )
        else:
            print(f"  -> failed error={record.error}")

    return digests, signatures_by_mission


def run() -> int:
    args = parse_args()
    if args.instances <= 0:
        raise SystemExit("--instances must be > 0")
    if args.min_clients <= 0:
        raise SystemExit("--min-clients must be > 0")
    if args.max_clients < args.min_clients:
        raise SystemExit("--max-clients must be >= --min-clients")
    if args.policy_id not in ro_exp.POLICY_LIBRARY:
        known = ", ".join(sorted(ro_exp.POLICY_LIBRARY.keys()))
        raise SystemExit(f"Unknown --policy-id '{args.policy_id}'. Available: {known}")

    started_at = _utcnow_iso()
    _seed_everything(args.seed)

    mission_ids = ro_exp._generate_missions(
        args.instances,
        context_mode=args.context_mode,
        min_clients=args.min_clients,
        max_clients=args.max_clients,
    )
    print(f"[INFO] Generated {len(mission_ids)} missions")

    artifact_hashes = {mission_id: _mission_artifact_hashes(mission_id) for mission_id in mission_ids}

    phase1_runs, phase1_signatures = _run_phase(
        mission_ids,
        phase=1,
        seed=args.seed,
        policy_id=args.policy_id,
        num_vehicles=args.num_vehicles,
        vehicle_capacity=args.vehicle_capacity,
        speed_multiplier=args.speed_multiplier,
    )
    phase2_runs, phase2_signatures = _run_phase(
        mission_ids,
        phase=2,
        seed=args.seed,
        policy_id=args.policy_id,
        num_vehicles=args.num_vehicles,
        vehicle_capacity=args.vehicle_capacity,
        speed_multiplier=args.speed_multiplier,
    )

    comparisons: list[dict[str, Any]] = []
    identical_count = 0
    for mission_id in mission_ids:
        sig1 = phase1_signatures.get(mission_id)
        sig2 = phase2_signatures.get(mission_id)
        identical = bool(sig1 and sig2 and sig1 == sig2)
        if identical:
            identical_count += 1
        comparisons.append(
            {
                "mission_id": mission_id,
                "phase1_signature_sha256": sig1,
                "phase2_signature_sha256": sig2,
                "identical": identical,
            }
        )

    total = len(mission_ids)
    reproducibility_rate = round(float(identical_count) / float(total), 4) if total > 0 else 0.0

    payload = {
        "started_at": started_at,
        "ended_at": _utcnow_iso(),
        "params": {
            "instances": args.instances,
            "seed": args.seed,
            "policy_id": args.policy_id,
            "num_vehicles": args.num_vehicles,
            "vehicle_capacity": args.vehicle_capacity,
            "speed_multiplier": args.speed_multiplier,
            "context_mode": args.context_mode,
            "min_clients": args.min_clients,
            "max_clients": args.max_clients,
        },
        "mission_ids": mission_ids,
        "artifact_hashes": artifact_hashes,
        "phase1_runs": [row.as_dict() for row in phase1_runs],
        "phase2_runs": [row.as_dict() for row in phase2_runs],
        "comparisons": comparisons,
        "summary": {
            "missions_total": total,
            "identical_signatures": identical_count,
            "reproducibility_rate": reproducibility_rate,
            "is_fully_reproducible": identical_count == total,
        },
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[INFO] Reproducibility rate: {identical_count}/{total} = {reproducibility_rate}")
    print(f"[INFO] Summary written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
