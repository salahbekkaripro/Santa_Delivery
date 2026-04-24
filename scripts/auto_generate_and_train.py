#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_ZONES = [
    "Le Marais, Paris",
    "Mitte, Berlin",
    "Vieux Lyon, Lyon",
    "Quartier des Marolles, Bruxelles",
    "Bordeaux Centre",
]
WEATHER_KEYS = ["Clear", "Rain", "Snow", "Thunderstorm"]
AI_PROFILE_KEYS = ["express", "ecolo", "prudent", "opportuniste", "agressive", "championne"]


@dataclass
class RunStats:
    created: int = 0
    create_failed: int = 0
    solved: int = 0
    solve_failed: int = 0
    solved_preset: int = 0
    solved_learned: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate missions in batch, solve them, then train + evaluate the AI learning model."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend base URL (default: %(default)s)")
    parser.add_argument("--missions", type=int, default=12, help="Number of missions to create (default: %(default)s)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: %(default)s)")
    parser.add_argument(
        "--solve-mode",
        choices=["preset", "learned", "mixed"],
        default="preset",
        help="Solver endpoint selection mode (default: %(default)s)",
    )
    parser.add_argument(
        "--learned-ratio",
        type=float,
        default=0.35,
        help="When solve-mode=mixed, probability of using solve-learned (default: %(default)s)",
    )
    parser.add_argument(
        "--ai-profile-mode",
        choices=["none", "fixed", "random", "cycle"],
        default="cycle",
        help="How to populate mission ai_profile (default: %(default)s)",
    )
    parser.add_argument(
        "--ai-profile",
        default="express",
        help="Profile key when --ai-profile-mode=fixed (default: %(default)s)",
    )
    parser.add_argument(
        "--context-mode",
        choices=["stable", "varied"],
        default="stable",
        help="Mission context generation mode for training/evaluation quality (default: %(default)s)",
    )
    parser.add_argument("--min-clients", type=int, default=10, help="Minimum clients per mission (default: %(default)s)")
    parser.add_argument("--max-clients", type=int, default=48, help="Maximum clients per mission (default: %(default)s)")
    parser.add_argument("--train-limit", type=int, default=2000, help="Train endpoint limit parameter (default: %(default)s)")
    parser.add_argument("--eval-limit", type=int, default=1200, help="Evaluate endpoint limit parameter (default: %(default)s)")
    parser.add_argument(
        "--holdout-ratio",
        type=float,
        default=0.25,
        help="Evaluate endpoint holdout ratio parameter (default: %(default)s)",
    )
    parser.add_argument(
        "--sleep-s",
        type=float,
        default=0.0,
        help="Optional sleep in seconds between missions (default: %(default)s)",
    )
    parser.add_argument(
        "--output-json",
        default="daily_reports/auto_learning_run_summary.json",
        help="Path to write summary JSON (default: %(default)s)",
    )
    return parser.parse_args()


def choose_zone(index: int) -> str:
    return DEFAULT_ZONES[index % len(DEFAULT_ZONES)]


def _pick_ai_profile(index: int, mode: str, fixed_profile: str) -> str | None:
    if mode == "none":
        return None
    if mode == "fixed":
        return fixed_profile
    if mode == "random":
        return random.choice(AI_PROFILE_KEYS)
    return AI_PROFILE_KEYS[index % len(AI_PROFILE_KEYS)]


def build_create_payload(
    index: int,
    min_clients: int,
    max_clients: int,
    *,
    ai_profile_mode: str,
    ai_profile: str,
    context_mode: str,
) -> dict[str, Any]:
    zone = choose_zone(index)
    selected_ai_profile = _pick_ai_profile(index, ai_profile_mode, ai_profile)

    if context_mode == "stable":
        target_clients = min(max(min_clients, 20), max_clients)
        num_clients = target_clients
        weather = "Clear"
        random_incidents = False
        budget = int(num_clients * 110)
        sleigh_cost = 650
    else:
        weather = random.choice(WEATHER_KEYS)
        num_clients = random.randint(min_clients, max_clients)
        random_incidents = (weather != "Clear" and random.random() < 0.65) or (
            weather == "Clear" and random.random() < 0.2
        )
        budget = int(num_clients * random.randint(90, 140))
        sleigh_cost = random.choice([500, 550, 600, 650, 700, 800])

    payload = {
        "zone": zone,
        "num_clients": num_clients,
        "budget": budget,
        "sleigh_cost": sleigh_cost,
        "weather_key": weather,
        "random_incidents": random_incidents,
    }
    if selected_ai_profile:
        payload["ai_profile"] = selected_ai_profile
    return payload


def build_solve_payload() -> dict[str, Any]:
    return {
        "num_vehicles": random.choice([2, 3, 4]),
        "vehicle_capacity": random.choice([180, 200, 220, 240]),
        "speed_multiplier": random.choice([0.9, 1.0, 1.2]),
        "optimization_target": random.choice(["time", "distance"]),
    }


def request_json(client: httpx.Client, method: str, path: str, **kwargs) -> tuple[int, dict[str, Any] | None, str | None]:
    response = client.request(method, path, **kwargs)
    payload: dict[str, Any] | None = None
    message: str | None = None
    try:
        payload = response.json()
    except Exception:
        payload = None
    if response.status_code >= 400:
        if isinstance(payload, dict):
            message = str(payload.get("detail") or payload)
        else:
            message = response.text.strip() or f"HTTP {response.status_code}"
    return response.status_code, payload, message


def pick_solve_path(solve_mode: str, learned_ratio: float) -> str:
    if solve_mode == "preset":
        return "/api/missions/{mission_id}/solve"
    if solve_mode == "learned":
        return "/api/missions/{mission_id}/solve-learned"
    return "/api/missions/{mission_id}/solve-learned" if random.random() < learned_ratio else "/api/missions/{mission_id}/solve"


def run() -> int:
    args = parse_args()
    if args.missions <= 0:
        print("[ERROR] --missions must be > 0")
        return 2
    if args.min_clients <= 0:
        print("[ERROR] --min-clients must be > 0")
        return 2
    if args.max_clients < args.min_clients:
        print("[ERROR] --max-clients must be >= --min-clients")
        return 2
    if args.ai_profile_mode == "fixed" and args.ai_profile not in AI_PROFILE_KEYS:
        print(f"[ERROR] --ai-profile must be one of: {', '.join(AI_PROFILE_KEYS)}")
        return 2
    if not 0.0 <= args.learned_ratio <= 1.0:
        print("[ERROR] --learned-ratio must be between 0 and 1")
        return 2
    if not 0.05 <= args.holdout_ratio <= 0.95:
        print("[ERROR] --holdout-ratio must be between 0.05 and 0.95")
        return 2
    random.seed(args.seed)

    stats = RunStats()
    mission_ids: list[str] = []
    failures: list[dict[str, Any]] = []

    started_at = datetime.now(timezone.utc).isoformat()
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=300.0) as client:
        status, _, error = request_json(client, "GET", "/health")
        if status != 200:
            print(f"[ERROR] Healthcheck failed on {args.base_url}: {error}")
            return 1

        print(f"[INFO] Backend reachable: {args.base_url}")
        print(f"[INFO] Starting batch: missions={args.missions}, solve_mode={args.solve_mode}, seed={args.seed}")

        for i in range(args.missions):
            create_payload = build_create_payload(
                i,
                args.min_clients,
                args.max_clients,
                ai_profile_mode=args.ai_profile_mode,
                ai_profile=args.ai_profile,
                context_mode=args.context_mode,
            )
            status, payload, error = request_json(client, "POST", "/api/missions", json=create_payload)
            if status != 200 or not isinstance(payload, dict):
                stats.create_failed += 1
                failures.append(
                    {
                        "phase": "create",
                        "index": i,
                        "payload": create_payload,
                        "status": status,
                        "error": error,
                    }
                )
                print(f"[WARN] Mission create failed #{i + 1}: {error}")
                continue

            mission_id = str(payload.get("mission_id", ""))
            if not mission_id:
                stats.create_failed += 1
                failures.append(
                    {
                        "phase": "create",
                        "index": i,
                        "payload": create_payload,
                        "status": status,
                        "error": "Missing mission_id in API response",
                    }
                )
                print(f"[WARN] Mission create invalid response #{i + 1}: missing mission_id")
                continue

            stats.created += 1
            mission_ids.append(mission_id)

            solve_payload = build_solve_payload()
            solve_path_template = pick_solve_path(args.solve_mode, args.learned_ratio)
            solve_path = solve_path_template.format(mission_id=mission_id)
            status, _, error = request_json(client, "POST", solve_path, json=solve_payload)
            if status != 200:
                stats.solve_failed += 1
                failures.append(
                    {
                        "phase": "solve",
                        "mission_id": mission_id,
                        "path": solve_path,
                        "payload": solve_payload,
                        "status": status,
                        "error": error,
                    }
                )
                print(f"[WARN] Solve failed for {mission_id}: {error}")
            else:
                stats.solved += 1
                if solve_path.endswith("/solve-learned"):
                    stats.solved_learned += 1
                else:
                    stats.solved_preset += 1
                print(f"[OK] Mission {mission_id} solved via {solve_path.split('/')[-1]}")

            if args.sleep_s > 0:
                time.sleep(args.sleep_s)

        train_result: dict[str, Any] | None = None
        eval_result: dict[str, Any] | None = None

        status, payload, error = request_json(client, "POST", f"/api/ai-learning/train?limit={int(args.train_limit)}")
        if status == 200 and isinstance(payload, dict):
            train_result = payload
            print(
                "[OK] Train complete: "
                f"samples={train_result.get('sample_count')} contexts={train_result.get('context_count')}"
            )
        else:
            failures.append({"phase": "train", "status": status, "error": error})
            print(f"[WARN] Train failed: {error}")

        status, payload, error = request_json(
            client,
            "GET",
            f"/api/ai-learning/evaluate?limit={int(args.eval_limit)}&holdout_ratio={float(args.holdout_ratio)}",
        )
        if status == 200 and isinstance(payload, dict):
            eval_result = payload
            print(
                "[OK] Evaluate complete: "
                f"top1={eval_result.get('context_top1_accuracy')} regret={eval_result.get('avg_context_regret')}"
            )
        else:
            failures.append({"phase": "evaluate", "status": status, "error": error})
            print(f"[WARN] Evaluate failed: {error}")

    ended_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "started_at": started_at,
        "ended_at": ended_at,
        "base_url": args.base_url,
        "params": {
            "missions": args.missions,
            "seed": args.seed,
            "solve_mode": args.solve_mode,
            "learned_ratio": args.learned_ratio,
            "ai_profile_mode": args.ai_profile_mode,
            "ai_profile": args.ai_profile,
            "context_mode": args.context_mode,
            "min_clients": args.min_clients,
            "max_clients": args.max_clients,
            "train_limit": args.train_limit,
            "eval_limit": args.eval_limit,
            "holdout_ratio": args.holdout_ratio,
        },
        "stats": {
            "created": stats.created,
            "create_failed": stats.create_failed,
            "solved": stats.solved,
            "solve_failed": stats.solve_failed,
            "solved_preset": stats.solved_preset,
            "solved_learned": stats.solved_learned,
        },
        "mission_ids": mission_ids,
        "train": train_result,
        "evaluation": eval_result,
        "failures": failures,
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[INFO] Summary written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
