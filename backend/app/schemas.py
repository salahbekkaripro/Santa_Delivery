from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MissionCreateRequest(BaseModel):
    zone: str
    num_clients: int = Field(ge=1, le=200)
    budget: int = Field(ge=0)
    sleigh_cost: int = Field(ge=0)
    weather_key: str = "Clear"
    random_incidents: bool = False
    level: int | None = None


class ClientPoint(BaseModel):
    id: int
    lat: float
    lon: float
    nom_client: str
    poids_colis: float


class MissionResponse(BaseModel):
    mission_id: str
    mission: dict
    depot: ClientPoint
    clients: list[ClientPoint]
    graph_available: bool
    weather: dict
    human_state: dict | None = None
    results_available: bool = False
    incidents: dict | None = None


class HumanRouteOptionsRequest(BaseModel):
    from_id: int
    to_id: int
    speed_multiplier: float = Field(default=1.0, gt=0)
    k: int = Field(default=3, ge=1, le=5)


class RouteOption(BaseModel):
    route_nodes: list[int]
    geometry: list[list[float]]
    dist_m: float
    base_time_s: float
    time_s: float
    label: str


class SelectedRoute(BaseModel):
    route_nodes: list[int]
    geometry: list[list[float]] = Field(default_factory=list)
    dist_m: float
    base_time_s: float | None = None
    time_s: float


class HumanValidateSegmentRequest(BaseModel):
    sleigh_id: int = Field(ge=0)
    from_id: int
    to_id: int
    selected_route: SelectedRoute
    speed_multiplier: float = Field(default=1.0, gt=0)
    vehicle_capacity: int = Field(default=200, ge=1)
    num_vehicles: int = Field(default=3, ge=1, le=20)


class RouteSegment(BaseModel):
    variant: Literal["human", "ai", "human-return", "incident"]
    sleigh_id: int
    from_id: int
    to_id: int
    route_nodes: list[int] = Field(default_factory=list)
    geometry: list[list[float]]
    dist_m: float
    time_s: float
    arrival_eta_s: float | None = None
    arrival_clock: str | None = None
    title: str | None = None
    segment_idx: int | None = None
    segment_count: int | None = None


class SolveMissionRequest(BaseModel):
    num_vehicles: int = Field(ge=1, le=20)
    vehicle_capacity: int = Field(ge=1)
    speed_multiplier: float = Field(default=1.0, gt=0)


class HumanStateResponse(BaseModel):
    routes_by_sleigh: dict[str, list[int]]
    segments_by_sleigh: dict[str, list[RouteSegment]]
    assigned_clients: list[int]
    live_stats: dict[str, dict]
    stop_meta_by_client: dict[int, dict] | None = None
    speed_multiplier: float | None = None
    vehicle_capacity: int | None = None
    num_vehicles: int | None = None


class HumanStateMutationRequest(BaseModel):
    sleigh_id: int | None = Field(default=None, ge=0)
    speed_multiplier: float = Field(default=1.0, gt=0)
    vehicle_capacity: int = Field(default=200, ge=1)
    num_vehicles: int = Field(default=3, ge=1, le=20)


class SolveMissionResponse(BaseModel):
    results: dict
    benchmark: dict
    ai_tours: list[dict]
    ai_segments: list[RouteSegment]
    ai_stop_meta: dict[int, dict]
    comparison: dict


class ComparisonResponse(BaseModel):
    depot: ClientPoint
    clients: list[ClientPoint]
    human_segments: list[RouteSegment]
    ai_segments: list[RouteSegment]
    human_stop_meta_by_client: dict[int, dict] | None = None
    incidents: dict | None = None
    summary_metrics: dict


class DebriefResponse(BaseModel):
    mission: dict
    results: dict
    benchmark: dict
    score: dict
    human: dict
