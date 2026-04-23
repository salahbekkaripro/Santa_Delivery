from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    ComparisonResponse,
    DebriefResponse,
    ForgotPasswordRequest,
    HumanRouteOptionsRequest,
    HumanStateMutationRequest,
    HumanStateResponse,
    HumanValidateSegmentRequest,
    PasswordResetResponse,
    MissionCreateRequest,
    MissionResponse,
    PlayerResponse,
    PlayerUpsertRequest,
    LeaderboardSaveRequest,
    ResetPasswordRequest,
    SolveMissionRequest,
    SolveMissionResponse,
)
from backend.app import services


app = FastAPI(title="Operation Noel API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {"name": "Operation Noel API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.post("/api/missions", response_model=MissionResponse)
def create_mission(payload: MissionCreateRequest) -> dict:
    try:
        return services.create_mission(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/missions")
def list_missions(limit: int = 50) -> dict:
    return services.list_missions(limit=limit)


@app.post("/api/players", response_model=PlayerResponse)
def upsert_player(payload: PlayerUpsertRequest) -> dict:
    try:
        return services.upsert_player(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/players/{player_id}", response_model=PlayerResponse)
def get_player(player_id: str) -> dict:
    try:
        return services.get_player(player_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/auth/register", response_model=PlayerResponse)
def register_player(payload: AuthRegisterRequest) -> dict:
    try:
        return services.register_player(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/login", response_model=PlayerResponse)
def login_player(payload: AuthLoginRequest) -> dict:
    try:
        return services.login_player(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/forgot-password", response_model=PasswordResetResponse)
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    try:
        return services.request_password_reset(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/reset-password", response_model=PlayerResponse)
def reset_password(payload: ResetPasswordRequest) -> dict:
    try:
        return services.reset_password(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/missions/{mission_id}", response_model=MissionResponse)
def get_mission(mission_id: str) -> dict:
    try:
        return services.get_mission(mission_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/missions/{mission_id}/human/route-options")
def get_human_route_options(mission_id: str, payload: HumanRouteOptionsRequest) -> dict:
    try:
        return services.get_human_route_options(
            mission_id,
            from_id=payload.from_id,
            to_id=payload.to_id,
            sleigh_id=payload.sleigh_id,
            speed_multiplier=payload.speed_multiplier,
            k=payload.k,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/missions/{mission_id}/human/validate-segment", response_model=HumanStateResponse)
def validate_human_segment(mission_id: str, payload: HumanValidateSegmentRequest) -> dict:
    try:
        return services.validate_human_segment(mission_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/missions/{mission_id}/human/undo-last", response_model=HumanStateResponse)
def undo_last_human_segment(mission_id: str, payload: HumanStateMutationRequest) -> dict:
    try:
        return services.undo_last_human_segment(mission_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/missions/{mission_id}/human/clear-sleigh", response_model=HumanStateResponse)
def clear_human_sleigh(mission_id: str, payload: HumanStateMutationRequest) -> dict:
    try:
        return services.clear_human_sleigh(mission_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/missions/{mission_id}/human/reset", response_model=HumanStateResponse)
def reset_human_state(mission_id: str, payload: HumanStateMutationRequest) -> dict:
    try:
        return services.reset_human_state(mission_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/missions/{mission_id}/human/suggest-next")
def suggest_next_stops(mission_id: str, payload: dict) -> dict:
    try:
        return services.suggest_next_stops(mission_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/missions/{mission_id}/nearest-node")
def get_nearest_node(mission_id: str, lat: float, lon: float) -> dict:
    try:
        return services.get_nearest_node(mission_id, lat, lon)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/missions/{mission_id}/adjacent-nodes")
def get_adjacent_nodes(mission_id: str, node_id: int, speed_multiplier: float = 1.0) -> dict:
    try:
        return services.get_adjacent_nodes(mission_id, node_id, speed_multiplier)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/missions/{mission_id}/solve", response_model=SolveMissionResponse)
def solve_mission(mission_id: str, payload: SolveMissionRequest) -> dict:
    try:
        return services.solve_mission(mission_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/missions/{mission_id}/comparison", response_model=ComparisonResponse)
def get_comparison(mission_id: str) -> dict:
    try:
        return services.get_comparison(mission_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/missions/{mission_id}/debrief", response_model=DebriefResponse)
def get_debrief(mission_id: str) -> dict:
    try:
        return services.get_debrief(mission_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/missions/{mission_id}/leaderboard")
def save_leaderboard(mission_id: str, payload: LeaderboardSaveRequest) -> dict:
    try:
        return services.save_leaderboard(mission_id, payload.model_dump())
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, FileNotFoundError) else 400, detail=str(exc)) from exc


@app.get("/api/leaderboard")
def list_leaderboard(limit: int = 20) -> dict:
    return services.list_leaderboard(limit=limit)
