import type {
  AdjacentNode,
  ComparisonPayload,
  DebriefPayload,
  HumanState,
  LeaderboardEntry,
  MissionConfig,
  MissionSnapshot,
  MissionResponse,
  PlayerProfile,
  RouteOption,
  SolveResponse
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function normalizePlayer(payload: {
  player_id: string;
  display_name: string;
  email?: string | null;
  callsign?: string | null;
  avatar?: string | null;
  last_login_at?: string | null;
  created_at: string;
  updated_at?: string;
}): PlayerProfile {
  return {
    id: payload.player_id,
    display_name: payload.display_name,
    email: payload.email ?? null,
    callsign: payload.callsign ?? null,
    avatar: payload.avatar ?? null,
    last_login_at: payload.last_login_at ?? null,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers ?? undefined);
  const hasBody = init?.body !== undefined && init?.body !== null;
  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method,
    headers,
    cache: "no-store"
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function createMission(payload: MissionConfig) {
  return apiFetch<MissionResponse>("/api/missions", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function upsertPlayer(payload: {
  player_id?: string;
  display_name: string;
  callsign?: string;
  avatar?: string;
}) {
  return apiFetch<{
    player_id: string;
    display_name: string;
    email?: string | null;
    callsign?: string | null;
    avatar?: string | null;
    created_at: string;
    last_login_at?: string | null;
    updated_at: string;
  }>("/api/players", {
    method: "POST",
    body: JSON.stringify(payload)
  }).then(normalizePlayer);
}

export function getPlayer(playerId: string) {
  return apiFetch<{
    player_id: string;
    display_name: string;
    email?: string | null;
    callsign?: string | null;
    avatar?: string | null;
    created_at: string;
    last_login_at?: string | null;
    updated_at: string;
  }>(`/api/players/${playerId}`).then(normalizePlayer);
}

export function registerPlayer(payload: {
  display_name: string;
  email: string;
  password: string;
  callsign?: string;
  avatar?: string;
}) {
  return apiFetch<{
    player_id: string;
    display_name: string;
    email?: string | null;
    callsign?: string | null;
    avatar?: string | null;
    created_at: string;
    last_login_at?: string | null;
    updated_at: string;
  }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  }).then(normalizePlayer);
}

export function loginPlayer(payload: { email: string; password: string }) {
  return apiFetch<{
    player_id: string;
    display_name: string;
    email?: string | null;
    callsign?: string | null;
    avatar?: string | null;
    created_at: string;
    last_login_at?: string | null;
    updated_at: string;
  }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  }).then(normalizePlayer);
}

export function requestPasswordReset(payload: { email: string }) {
  return apiFetch<{
    status: string;
    reset_token?: string | null;
    reset_url?: string | null;
    expires_at?: string | null;
  }>("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function resetPassword(payload: { token: string; password: string }) {
  return apiFetch<{
    player_id: string;
    display_name: string;
    email?: string | null;
    callsign?: string | null;
    avatar?: string | null;
    created_at: string;
    last_login_at?: string | null;
    updated_at: string;
  }>("/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(payload)
  }).then(normalizePlayer);
}

export function getMission(missionId: string) {
  return apiFetch<MissionResponse>(`/api/missions/${missionId}`);
}

export function getMissions(limit: number = 50) {
  return apiFetch<{ missions: MissionSnapshot[] }>(`/api/missions?limit=${limit}`);
}

export function getRouteOptions(
  missionId: string,
  payload: { from_id: number; to_id: number; sleigh_id: number; speed_multiplier: number; k?: number }
) {
  return apiFetch<{ options: RouteOption[] }>(`/api/missions/${missionId}/human/route-options`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function validateSegment(
  missionId: string,
  payload: {
    sleigh_id: number;
    from_id: number;
    to_id: number;
    selected_route: RouteOption;
    speed_multiplier: number;
    vehicle_capacity: number;
    num_vehicles: number;
  }
) {
  return apiFetch<HumanState>(`/api/missions/${missionId}/human/validate-segment`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function solveMission(
  missionId: string,
  payload: { num_vehicles: number; vehicle_capacity: number; speed_multiplier: number; optimization_target?: string }
) {
  return apiFetch<SolveResponse>(`/api/missions/${missionId}/solve`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function undoLastSegment(
  missionId: string,
  payload: { sleigh_id: number; speed_multiplier: number; vehicle_capacity: number; num_vehicles: number }
) {
  return apiFetch<HumanState>(`/api/missions/${missionId}/human/undo-last`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function clearSleigh(
  missionId: string,
  payload: { sleigh_id: number; speed_multiplier: number; vehicle_capacity: number; num_vehicles: number }
) {
  return apiFetch<HumanState>(`/api/missions/${missionId}/human/clear-sleigh`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function resetHumanState(
  missionId: string,
  payload: { speed_multiplier: number; vehicle_capacity: number; num_vehicles: number }
) {
  return apiFetch<HumanState>(`/api/missions/${missionId}/human/reset`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function suggestNext(missionId: string, payload: { sleigh_id: number }) {
  return apiFetch<{ suggestions: Array<{ client_id: number; nom_client: string; arrival_clock: string; is_feasible: boolean }> }>(
    `/api/missions/${missionId}/human/suggest-next`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function getNearestNode(missionId: string, lat: number, lon: number) {
  return apiFetch<{ node_id: number; lat: number; lon: number }>(`/api/missions/${missionId}/nearest-node?lat=${lat}&lon=${lon}`);
}

export function getComparison(missionId: string) {
  return apiFetch<ComparisonPayload>(`/api/missions/${missionId}/comparison`);
}

export function getDebrief(missionId: string) {
  return apiFetch<DebriefPayload>(`/api/missions/${missionId}/debrief`);
}

export function saveLeaderboard(
  missionId: string,
  payload: { player_name: string; player_id?: string; callsign?: string; avatar?: string }
) {
  return apiFetch<{ status: string }>(`/api/missions/${missionId}/leaderboard`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getLeaderboard(limit: number = 20) {
  return apiFetch<{ entries: LeaderboardEntry[] }>(`/api/leaderboard?limit=${limit}`);
}

export function getAdjacentNodes(missionId: string, nodeId: number, speedMultiplier: number) {
  return apiFetch<{ adjacents: AdjacentNode[]; future_adjacents: AdjacentNode[] }>(
    `/api/missions/${missionId}/adjacent-nodes?node_id=${nodeId}&speed_multiplier=${speedMultiplier}`
  );
}
