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
    VersusInviteCreateRequest,
    VersusInviteDecisionRequest,
    VersusMatchCreateRequest,
    VersusMatchJoinRequest,
    VersusQueueRequest,
    VersusReadyRequest,
    VersusSubmitRequest,
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
            vehicle_capacity=payload.vehicle_capacity,
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


@app.post("/api/missions/{mission_id}/solve-learned", response_model=SolveMissionResponse)
def solve_mission_learned(mission_id: str, payload: SolveMissionRequest) -> dict:
    try:
        return services.solve_mission_learned(mission_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/ai-learning/train")
def train_ai_learning(limit: int = 500) -> dict:
    try:
        return services.train_ai_learning_model(limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/ai-learning/evaluate")
def evaluate_ai_learning(limit: int = 800, holdout_ratio: float = 0.25) -> dict:
    try:
        return services.evaluate_ai_learning_model(limit=limit, holdout_ratio=holdout_ratio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/missions/{mission_id}/ai-learning/recommendation")
def get_ai_learning_recommendation(mission_id: str) -> dict:
    try:
        return services.get_ai_learning_recommendation(mission_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/ortools-tuner/train")
def train_ortools_tuner(limit: int = 1500) -> dict:
    try:
        return services.train_ortools_tuner_model(limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/ortools-tuner/evaluate")
def evaluate_ortools_tuner(limit: int = 2000, holdout_ratio: float = 0.25) -> dict:
    try:
        return services.evaluate_ortools_tuner_model(limit=limit, holdout_ratio=holdout_ratio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/missions/{mission_id}/ortools-tuner/recommendation")
def get_ortools_tuner_recommendation(mission_id: str) -> dict:
    try:
        return services.get_ortools_tuner_recommendation(mission_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
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


@app.get("/api/versus/templates")
def list_versus_templates() -> dict:
    return services.list_versus_templates()


@app.post("/api/versus/matches")
def create_versus_match(payload: VersusMatchCreateRequest) -> dict:
    try:
        return services.create_versus_match(payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/versus/matches/join")
def join_versus_match(payload: VersusMatchJoinRequest) -> dict:
    try:
        return services.join_versus_match(payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/versus/queue/enter")
def enter_versus_queue(payload: VersusQueueRequest) -> dict:
    try:
        return services.enter_versus_queue(payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/versus/queue/leave")
def leave_versus_queue(payload: VersusQueueRequest) -> dict:
    try:
        return services.leave_versus_queue(payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/versus/invites")
def create_versus_invite(payload: VersusInviteCreateRequest) -> dict:
    try:
        return services.create_versus_invite(payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/versus/invites")
def list_versus_invites(player_id: str) -> dict:
    try:
        return services.list_versus_invites(player_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/versus/invites/{invite_id}/accept")
def accept_versus_invite(invite_id: str, payload: VersusInviteDecisionRequest) -> dict:
    try:
        return services.accept_versus_invite(invite_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/versus/invites/{invite_id}/decline")
def decline_versus_invite(invite_id: str, payload: VersusInviteDecisionRequest) -> dict:
    try:
        return services.decline_versus_invite(invite_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/versus/matches/{match_id}/ready")
def set_versus_ready(match_id: str, payload: VersusReadyRequest) -> dict:
    try:
        return services.set_versus_ready(match_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/versus/matches/{match_id}/state")
def get_versus_match_state(match_id: str, player_id: str) -> dict:
    try:
        return services.get_versus_match_state(match_id, player_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/versus/matches/{match_id}/submit")
def submit_versus_attempt(match_id: str, payload: VersusSubmitRequest) -> dict:
    try:
        return services.submit_versus_attempt(match_id, payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/versus/leaderboard")
def list_versus_leaderboard(limit: int = 20) -> dict:
    return services.list_versus_leaderboard(limit=limit)


@app.get("/api/versus/stats")
def list_versus_player_stats(limit: int = 20, max_matches: int = 500) -> dict:
    return services.list_versus_player_stats(limit=limit, max_matches=max_matches)
