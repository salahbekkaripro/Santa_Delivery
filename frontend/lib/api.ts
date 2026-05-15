import type {
  AdjacentNode,
  AiLearningEvaluationResponse,
  AiLearningRecommendation,
  AiLearningTrainResponse,
  AstarCompareResult,
  ComparisonPayload,
  DebriefPayload,
  DeliverySectorsResult,
  DijkstraResult,
  EcoAnalysis,
  GraphMetrics,
  HumanState,
  IncidentReplanResponse,
  LeaderboardEntry,
  MissionConfig,
  MissionSnapshot,
  MissionResponse,
  PlayerProfile,
  RouteOption,
  SolveResponse,
  SocialConversation,
  SocialDirectMessage,
  SocialFriendship,
  SocialPlayer,
  TopologyCheck,
  VersusInvite,
  VersusLeaderboardEntry,
  VersusMapSource,
  VersusMatch,
  VersusMissionConfig,
  VersusPlayerStatsEntry,
  VersusTemplate,
  VersusWinnerRule
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const WS_BASE_URL = API_BASE_URL.startsWith("https://")
  ? API_BASE_URL.replace("https://", "wss://")
  : API_BASE_URL.replace("http://", "ws://");

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

export function syncOAuthPlayer(payload: {
  provider: string;
  provider_account_id: string;
  display_name: string;
  email?: string | null;
  callsign?: string | null;
  avatar?: string | null;
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
  }>("/api/auth/oauth-sync", {
    method: "POST",
    body: JSON.stringify(payload),
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

export function searchSocialPlayers(playerId: string, query: string, limit: number = 12) {
  const params = new URLSearchParams({
    player_id: playerId,
    q: query,
    limit: String(limit),
  });
  return apiFetch<{ players: SocialPlayer[] }>(`/api/social/players?${params.toString()}`);
}

export function getSocialFriendships(playerId: string) {
  return apiFetch<{
    friends: SocialFriendship[];
    incoming_requests: SocialFriendship[];
    outgoing_requests: SocialFriendship[];
  }>(`/api/social/friends?player_id=${encodeURIComponent(playerId)}`);
}

export function sendFriendRequest(payload: { player_id: string; friend_player_id: string }) {
  return apiFetch<{ status: string; friendship: SocialFriendship }>("/api/social/friends/request", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function respondFriendRequest(payload: {
  player_id: string;
  friend_player_id: string;
  action: "accept" | "decline";
}) {
  return apiFetch<{ status: string; friendship: SocialFriendship }>("/api/social/friends/respond", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function removeFriendship(payload: { player_id: string; friend_player_id: string }) {
  return apiFetch<{ status: string }>("/api/social/friends/remove", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getDirectConversations(playerId: string, limit: number = 30) {
  const params = new URLSearchParams({
    player_id: playerId,
    limit: String(limit),
  });
  return apiFetch<{ conversations: SocialConversation[] }>(`/api/social/messages/conversations?${params.toString()}`);
}

export function getDirectMessages(payload: {
  player_id: string;
  with_player_id: string;
  limit?: number;
  before?: string;
}) {
  const params = new URLSearchParams({
    player_id: payload.player_id,
    with_player_id: payload.with_player_id,
    limit: String(payload.limit ?? 60),
  });
  if (payload.before) {
    params.set("before", payload.before);
  }
  return apiFetch<{ peer: SocialPlayer; self: SocialPlayer; messages: SocialDirectMessage[] }>(
    `/api/social/messages?${params.toString()}`
  );
}

export function sendDirectMessage(payload: { player_id: string; recipient_player_id: string; body: string }) {
  return apiFetch<{ message: SocialDirectMessage }>("/api/social/messages", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function removeDirectConversation(payload: { player_id: string; with_player_id: string }) {
  return apiFetch<{ status: string; conversation_key: string; cleared_before_at: string }>("/api/social/messages/conversation/remove", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function restoreDirectConversation(payload: { player_id: string; with_player_id: string }) {
  return apiFetch<{ status: string; conversation_key: string; restored: boolean }>("/api/social/messages/conversation/restore", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getBlockedPlayers(playerId: string) {
  return apiFetch<{ blocked: Array<{ player_id: string; display_name?: string | null; callsign?: string | null; avatar?: string | null; blocked_at?: string | null }> }>(
    `/api/social/blocks?player_id=${encodeURIComponent(playerId)}`
  );
}

export function blockPlayer(payload: { player_id: string; blocked_player_id: string }) {
  return apiFetch<{ status: string }>("/api/social/blocks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function unblockPlayer(payload: { player_id: string; blocked_player_id: string }) {
  return apiFetch<{ status: string }>("/api/social/blocks/remove", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSocialWebSocketUrl(playerId: string) {
  return `${WS_BASE_URL}/ws/social/${encodeURIComponent(playerId)}`;
}

export function getMission(missionId: string) {
  return apiFetch<MissionResponse>(`/api/missions/${missionId}`);
}

export function getMissions(limit: number = 50) {
  return apiFetch<{ missions: MissionSnapshot[] }>(`/api/missions?limit=${limit}`);
}

export function getRouteOptions(
  missionId: string,
  payload: { from_id: number; to_id: number; sleigh_id: number; speed_multiplier: number; vehicle_capacity?: number; k?: number }
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

export function solveMissionLearned(
  missionId: string,
  payload: { num_vehicles: number; vehicle_capacity: number; speed_multiplier: number; optimization_target?: string }
) {
  return apiFetch<SolveResponse>(`/api/missions/${missionId}/solve-learned`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function simulateIncidentReplan(
  missionId: string,
  payload: {
    incident_count: number;
    strategy?: "guided" | "random";
    seed?: number;
    num_vehicles?: number;
    vehicle_capacity?: number;
    speed_multiplier?: number;
    optimization_target?: "time" | "distance";
    manual_segments?: Array<{
      from_id: number;
      to_id: number;
      route_nodes?: number[];
      geometry?: [number, number][];
      dist_m?: number;
      time_s?: number;
      title?: string;
    }>;
  }
) {
  return apiFetch<IncidentReplanResponse>(`/api/missions/${missionId}/simulation/incident-replan`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function trainAiLearning(limit: number = 500) {
  return apiFetch<AiLearningTrainResponse>(`/api/ai-learning/train?limit=${limit}`, {
    method: "POST"
  });
}

export function evaluateAiLearning(limit: number = 800, holdoutRatio: number = 0.25) {
  return apiFetch<AiLearningEvaluationResponse>(
    `/api/ai-learning/evaluate?limit=${limit}&holdout_ratio=${holdoutRatio}`
  );
}

export function getAiLearningRecommendation(missionId: string) {
  return apiFetch<{ mission_id: string; recommendation: AiLearningRecommendation }>(
    `/api/missions/${missionId}/ai-learning/recommendation`
  );
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

export function getGraphMetrics(missionId: string) {
  return apiFetch<GraphMetrics>(`/api/missions/${missionId}/graph/metrics`);
}

export function getDijkstraSteps(missionId: string, fromNode: number, toNode: number) {
  return apiFetch<DijkstraResult>(
    `/api/missions/${missionId}/graph/dijkstra-steps?from_node=${fromNode}&to_node=${toNode}`,
  );
}

export function getBidirectionalAstarSteps(missionId: string, fromNode: number, toNode: number) {
  return apiFetch<AstarCompareResult>(
    `/api/missions/${missionId}/graph/bidirectional-astar-steps?from_node=${fromNode}&to_node=${toNode}`,
  );
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

export function getVersusTemplates() {
  return apiFetch<{ templates: VersusTemplate[] }>("/api/versus/templates");
}

export function createVersusMatch(payload: {
  player_id: string;
  mode?: "private";
  map_source?: VersusMapSource;
  template_id?: string;
  mission_config?: VersusMissionConfig;
  winner_rule: VersusWinnerRule;
}) {
  return apiFetch<VersusMatch>("/api/versus/matches", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function joinVersusMatch(payload: { player_id: string; join_code: string }) {
  return apiFetch<VersusMatch>("/api/versus/matches/join", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function enterVersusQueue(payload: {
  player_id: string;
  map_source?: VersusMapSource;
  template_id: string;
  winner_rule: VersusWinnerRule;
}) {
  return apiFetch<{
    status: "queued" | "matched";
    queue_entry?: { player_id: string; template_id: string; winner_rule: string; enqueued_at: string; updated_at: string };
    match?: VersusMatch;
  }>("/api/versus/queue/enter", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function leaveVersusQueue(payload: { player_id: string; template_id?: string; winner_rule?: string }) {
  return apiFetch<{ status: string }>("/api/versus/queue/leave", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getVersusQueueStatus(payload: {
  player_id: string;
  template_id: string;
  winner_rule: VersusWinnerRule;
}) {
  const params = new URLSearchParams({
    player_id: payload.player_id,
    template_id: payload.template_id,
    winner_rule: payload.winner_rule,
  });
  return apiFetch<{
    status: "idle" | "queued" | "matched";
    queue_entry?: { player_id: string; template_id: string; winner_rule: string; enqueued_at: string; updated_at: string };
    match?: VersusMatch;
  }>(`/api/versus/queue/status?${params.toString()}`);
}

export function createVersusInvite(payload: {
  player_id: string;
  invitee_player_id: string;
  map_source?: VersusMapSource;
  template_id?: string;
  mission_config?: VersusMissionConfig;
  winner_rule: VersusWinnerRule;
}) {
  return apiFetch<{ invite: VersusInvite }>("/api/versus/invites", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getVersusInvites(playerId: string) {
  return apiFetch<{ invites: VersusInvite[] }>(`/api/versus/invites?player_id=${encodeURIComponent(playerId)}`);
}

export function acceptVersusInvite(inviteId: string, payload: { player_id: string }) {
  return apiFetch<{ status: string; match: VersusMatch }>(`/api/versus/invites/${inviteId}/accept`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function declineVersusInvite(inviteId: string, payload: { player_id: string }) {
  return apiFetch<{ status: string }>(`/api/versus/invites/${inviteId}/decline`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function setVersusReady(matchId: string, payload: { player_id: string; ready?: boolean }) {
  return apiFetch<VersusMatch>(`/api/versus/matches/${matchId}/ready`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getVersusMatchState(matchId: string, playerId: string) {
  return apiFetch<VersusMatch>(`/api/versus/matches/${matchId}/state?player_id=${encodeURIComponent(playerId)}`);
}

export function submitVersusAttempt(matchId: string, payload: { player_id: string }) {
  return apiFetch<VersusMatch>(`/api/versus/matches/${matchId}/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getVersusLeaderboard(limit: number = 20) {
  return apiFetch<{ entries: VersusLeaderboardEntry[] }>(`/api/versus/leaderboard?limit=${limit}`);
}

export function getVersusPlayerStats(limit: number = 20, maxMatches: number = 500) {
  return apiFetch<{ entries: VersusPlayerStatsEntry[] }>(
    `/api/versus/stats?limit=${limit}&max_matches=${maxMatches}`,
  );
}

export function getVersusWebSocketUrl(matchId: string, playerId: string) {
  const params = new URLSearchParams({ player_id: playerId });
  return `${WS_BASE_URL}/ws/versus/${encodeURIComponent(matchId)}?${params.toString()}`;
}

// ── Eco / CO2 Analysis ────────────────────────────────────────────────────────

export function getEcoAnalysis(missionId: string) {
  return apiFetch<EcoAnalysis>(`/api/missions/${encodeURIComponent(missionId)}/eco/co2-analysis`);
}

// ── Community Detection / Delivery Sectors ────────────────────────────────────

export function getDeliverySectors(missionId: string) {
  return apiFetch<DeliverySectorsResult>(
    `/api/missions/${encodeURIComponent(missionId)}/graph/delivery-sectors`
  );
}

// ── Topological Validation ────────────────────────────────────────────────────

export function validateTopology(missionId: string) {
  return apiFetch<TopologyCheck>(
    `/api/missions/${encodeURIComponent(missionId)}/graph/topology-check`
  );
}
