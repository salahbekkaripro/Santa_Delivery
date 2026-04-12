import type {
  ComparisonPayload,
  DebriefPayload,
  HumanState,
  LeaderboardEntry,
  MissionConfig,
  MissionResponse,
  RouteOption,
  SolveResponse
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
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

export function getMission(missionId: string) {
  return apiFetch<MissionResponse>(`/api/missions/${missionId}`);
}

export function getRouteOptions(missionId: string, payload: { from_id: number; to_id: number; speed_multiplier: number; k?: number }) {
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

export function saveLeaderboard(missionId: string, payload: { player_name: string }) {
  return apiFetch<{ status: string }>(`/api/missions/${missionId}/leaderboard`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getLeaderboard(limit: number = 20) {
  return apiFetch<{ entries: LeaderboardEntry[] }>(`/api/leaderboard?limit=${limit}`);
}
