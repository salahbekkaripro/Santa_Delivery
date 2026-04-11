from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class MissionPaths:
    root_dir: Path
    core_data_dir: Path
    production_output_dir: Path
    data_file: Path
    graph_file: Path
    time_matrix_file: Path
    dist_matrix_file: Path
    weather_file: Path
    benchmark_file: Path
    results_file: Path
    output_html_file: Path
    incident_matrix_file: Path
    incidents_file: Path
    mission_file: Path
    human_state_file: Path

    def as_str_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}

    def ensure_directories(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.core_data_dir.mkdir(parents=True, exist_ok=True)
        self.production_output_dir.mkdir(parents=True, exist_ok=True)


def build_paths(base_dir: str | Path) -> MissionPaths:
    root_dir = Path(base_dir)
    core_data_dir = root_dir / "core_data"
    production_output_dir = root_dir / "production_output"
    return MissionPaths(
        root_dir=root_dir,
        core_data_dir=core_data_dir,
        production_output_dir=production_output_dir,
        data_file=core_data_dir / "livraisons_5eme.csv",
        graph_file=core_data_dir / "paris5.graphml",
        time_matrix_file=core_data_dir / "live_time_matrix.npy",
        dist_matrix_file=core_data_dir / "matrix_5eme.npy",
        weather_file=core_data_dir / "weather_status.json",
        benchmark_file=core_data_dir / "benchmark_results.json",
        results_file=production_output_dir / "resultats_finaux.json",
        output_html_file=production_output_dir / "output_final.html",
        incident_matrix_file=core_data_dir / "live_time_matrix_incident.npy",
        incidents_file=core_data_dir / "incidents.json",
        mission_file=root_dir / "mission.json",
        human_state_file=root_dir / "human_state.json",
    )


def default_paths() -> MissionPaths:
    return build_paths(ROOT_DIR)


def mission_paths(mission_id: str) -> MissionPaths:
    return build_paths(ROOT_DIR / "cache" / "api_missions" / mission_id)
