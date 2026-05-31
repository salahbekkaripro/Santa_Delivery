from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MissionCreateRequest(BaseModel):
    zone: str
    num_clients: int = Field(ge=1, le=2000)
    budget: int = Field(ge=0)
    sleigh_cost: int = Field(ge=0)
    weather_key: str = "Clear"
    random_incidents: bool = False
    level: int | None = None
    ai_profile: str | None = None
    secondary_objectives: list[dict] | None = None
    city: str | None = Field(default=None, max_length=120)
    center_lat: float | None = None
    center_lon: float | None = None
    search_radius_km: float | None = Field(default=None, gt=0, le=30)
    max_clients: int | None = Field(default=None, ge=1, le=2000)
    max_vehicles: int | None = Field(default=None, ge=1, le=20)
    departure_hour: int | None = Field(default=None, ge=0, le=23)
    with_elevation: bool = False
    transport_mode: Literal["drive", "bike", "walk", "multimodal"] = "drive"
    use_ademe_co2: bool = False
    ademe_transport_id: int | None = Field(default=None, ge=1)
    objective_weights: dict | None = None


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


class PlayerUpsertRequest(BaseModel):
    player_id: str | None = None
    display_name: str = Field(min_length=1, max_length=80)
    callsign: str | None = Field(default=None, max_length=80)
    avatar: str | None = Field(default=None, max_length=8)


class PlayerResponse(BaseModel):
    player_id: str
    display_name: str
    email: str | None = None
    callsign: str | None = None
    avatar: str | None = None
    last_login_at: str | None = None
    created_at: str
    updated_at: str


class LeaderboardSaveRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=80)
    player_id: str | None = None
    callsign: str | None = Field(default=None, max_length=80)
    avatar: str | None = Field(default=None, max_length=8)


class AuthRegisterRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=256)
    callsign: str | None = Field(default=None, max_length=80)
    avatar: str | None = Field(default=None, max_length=8)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=256)


class AuthOAuthSyncRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    provider_account_id: str = Field(min_length=2, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)
    email: str | None = Field(default=None, max_length=160)
    avatar: str | None = Field(default=None, max_length=280)
    callsign: str | None = Field(default=None, max_length=80)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=12, max_length=256)
    password: str = Field(min_length=8, max_length=256)


class PasswordResetResponse(BaseModel):
    status: str
    reset_token: str | None = None
    reset_url: str | None = None
    expires_at: str | None = None


class HumanRouteOptionsRequest(BaseModel):
    from_id: int
    to_id: int
    sleigh_id: int = Field(default=0, ge=0)
    speed_multiplier: float = Field(default=1.0, gt=0)
    vehicle_capacity: int | None = Field(default=None, ge=1)
    k: int = Field(default=3, ge=1, le=5)


class RouteOption(BaseModel):
    route_nodes: list[int]
    geometry: list[list[float]]
    dist_m: float
    base_time_s: float
    time_s: float
    label: str
    is_feasible: bool | None = None
    feasibility_badges: list[str] | None = None
    projected_arrival_clock: str | None = None
    projected_load_kg: float | None = None
    projected_overload_kg: float | None = None


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
    num_vehicles: int = Field(ge=1, le=2000)
    max_vehicles: int | None = Field(default=None, ge=1, le=20)
    vehicle_capacity: int = Field(ge=1)
    speed_multiplier: float = Field(default=1.0, gt=0)
    optimization_target: Literal["time", "distance", "composite"] = "time"


class IncidentReplanRequest(BaseModel):
    incident_count: int = Field(default=1, ge=1, le=3)
    strategy: Literal["guided", "random"] = "guided"
    seed: int | None = None
    num_vehicles: int | None = Field(default=None, ge=1, le=20)
    max_vehicles: int | None = Field(default=None, ge=1, le=20)
    vehicle_capacity: int | None = Field(default=None, ge=1)
    speed_multiplier: float | None = Field(default=None, gt=0)
    optimization_target: Literal["time", "distance", "composite"] | None = None
    manual_segments: list[dict] | None = None


class IncidentReplanDeltaKpi(BaseModel):
    time_s: float
    dist_m: float
    co2_kg: float
    time_pct: float
    dist_pct: float


class IncidentReplanResponse(BaseModel):
    incidents: dict
    before: dict
    after: dict
    delta_kpi: IncidentReplanDeltaKpi


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
    analysis: dict


class VersusMissionConfigRequest(BaseModel):
    zone: str
    num_clients: int = Field(ge=1, le=60)
    budget: int = Field(ge=0)
    sleigh_cost: int = Field(ge=0)
    weather_key: str = "Clear"
    random_incidents: bool = False
    level: int | None = None
    ai_profile: str | None = None
    secondary_objectives: list[dict] | None = None
    city: str | None = Field(default=None, max_length=120)
    center_lat: float | None = None
    center_lon: float | None = None
    search_radius_km: float | None = Field(default=None, gt=0, le=30)
    max_clients: int | None = Field(default=None, ge=1, le=200)
    max_vehicles: int | None = Field(default=None, ge=1, le=20)


class VersusMatchCreateRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    mode: Literal["private", "queue", "invite"] = "private"
    map_source: Literal["template", "custom"] = "template"
    template_id: str | None = Field(default=None, min_length=3, max_length=80)
    winner_rule: str = Field(default="score_time", min_length=3, max_length=40)
    mission_config: VersusMissionConfigRequest | None = None


class VersusMatchJoinRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    join_code: str = Field(min_length=4, max_length=16)


class VersusQueueRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    map_source: Literal["template", "custom"] = "template"
    template_id: str = Field(default="paris_duel", min_length=3, max_length=80)
    winner_rule: str = Field(default="score_time", min_length=3, max_length=40)


class VersusInviteCreateRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    invitee_player_id: str = Field(min_length=3, max_length=80)
    map_source: Literal["template", "custom"] = "template"
    template_id: str | None = Field(default=None, min_length=3, max_length=80)
    winner_rule: str = Field(default="score_time", min_length=3, max_length=40)
    mission_config: VersusMissionConfigRequest | None = None


class VersusInviteDecisionRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)


class VersusReadyRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    ready: bool = True


class VersusSubmitRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)


class SocialFriendRequestCreate(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    friend_player_id: str = Field(min_length=3, max_length=80)


class SocialFriendRequestRespond(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    friend_player_id: str = Field(min_length=3, max_length=80)
    action: Literal["accept", "decline"]


class SocialDirectMessageCreate(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    recipient_player_id: str = Field(min_length=3, max_length=80)
    body: str = Field(min_length=1, max_length=1000)


class SocialBlockRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    blocked_player_id: str = Field(min_length=3, max_length=80)


class SocialConversationRemoveRequest(BaseModel):
    player_id: str = Field(min_length=3, max_length=80)
    with_player_id: str = Field(min_length=3, max_length=80)
