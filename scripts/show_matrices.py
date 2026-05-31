#!/usr/bin/env python3
import argparse
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MISSIONS_DIR = ROOT / "cache" / "api_missions"

MATRICES = {
    "temps": "live_time_matrix.npy",
    "distance": "matrix_5eme.npy",
    "co2": "co2_matrix.npy",
    "risque": "risk_matrix.npy",
    "composite": "composite_cost_matrix.npy",
}


def latest_mission_id() -> str:
    missions = [p for p in MISSIONS_DIR.iterdir() if p.is_dir()]
    if not missions:
        raise SystemExit("Aucune mission trouvee dans cache/api_missions.")
    latest = max(missions, key=lambda p: p.stat().st_mtime)
    return latest.name


def main() -> None:
    parser = argparse.ArgumentParser(description="Affiche un extrait des matrices d'une mission.")
    parser.add_argument("mission_id", nargs="?", help="ID mission. Par defaut: derniere mission du cache.")
    parser.add_argument("--size", type=int, default=5, help="Taille de l'extrait carre affiche. Defaut: 5.")
    args = parser.parse_args()

    mission_id = args.mission_id or latest_mission_id()
    size = max(1, int(args.size))
    core_data = MISSIONS_DIR / mission_id / "core_data"

    if not core_data.exists():
        raise SystemExit(f"Dossier introuvable: {core_data}")

    print(f"Mission: {mission_id}")
    print(f"Dossier: {core_data}")

    for name, filename in MATRICES.items():
        path = core_data / filename
        if not path.exists():
            print(f"\n{name}: fichier manquant ({filename})")
            continue
        matrix = np.load(path)
        print(f"\n{name} | {filename} | shape={matrix.shape}")
        print(matrix[:size, :size])


if __name__ == "__main__":
    main()
