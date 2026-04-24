export type MissionConfig = {
  mission_id?: string;
  zone: string;
  city?: string;
  center_lat?: number;
  center_lon?: number;
  search_radius_km?: number;
  max_clients?: number;
  max_clients_allowed?: number;
  num_clients: number;
  budget: number;
  sleigh_cost: number;
  weather_key: string;
  random_incidents: boolean;
  level?: number | null;
  ai_profile?: string | null;
  secondary_objectives?: SecondaryObjective[] | null;
  generation_message?: string;
};

export type PlayerProfile = {
  id: string;
  display_name: string;
  email?: string | null;
  callsign?: string | null;
  avatar?: string | null;
  last_login_at?: string | null;
  created_at: string;
  updated_at?: string;
};

export type SecondaryObjective = {
  code: string;
  label: string;
  target?: number;
};

export type SecondaryObjectiveResult = SecondaryObjective & {
  completed: boolean;
  progress_label: string;
};

export type AIStrategy = {
  profile: string;
  label: string;
  signature?: string;
  description: string;
  optimization_target: "time" | "distance";
  difficulty_bonus?: number;
  num_vehicles: number;
  vehicle_capacity: number;
  speed_multiplier: number;
  solver_time_limit_s: number;
  first_solution_strategy: string;
  local_search_metaheuristic: string;
  time_slack_s: number;
  max_route_time_s: number;
  drop_penalty: number;
  global_span_cost: number;
  profile_origin?: "learned" | "preset";
  learning?: AiLearningRecommendation;
};

export type AiLearningCandidate = {
  profile: string;
  label: string;
  expected_cost: number;
  support: number;
};

export type AiLearningRecommendation = {
  profile: string;
  label: string;
  context_key: string;
  confidence: number;
  top_candidates: AiLearningCandidate[];
  model: {
    version: string;
    sample_count: number;
    trained_at?: string | null;
  };
};

export type AiLearningTrainResponse = {
  status: string;
  model_version: string;
  model_path: string;
  sample_count: number;
  context_count: number;
  profiles: string[];
  trained_at: string;
};

export type AiLearningEvaluationExample = {
  context_key: string;
  true_best_profile: string;
  predicted_profile: string;
  true_best_cost: number;
  predicted_cost: number;
};

export type AiLearningEvaluationResponse = {
  status: string;
  model_version: string;
  target: string;
  sample_count_total: number;
  sample_count_train: number;
  sample_count_holdout: number;
  holdout_ratio: number;
  split_strategy?: string;
  sample_match_rate: number;
  contexts_evaluated: number;
  context_top1_accuracy: number;
  avg_context_regret: number;
  examples: AiLearningEvaluationExample[];
};

export type ClientPoint = {
  id: number;
  lat: number;
  lon: number;
  nom_client: string;
  poids_colis: number;
};

export type RouteSegment = {
  variant: "human" | "ai" | "human-return" | "incident";
  sleigh_id: number;
  from_id: number;
  to_id: number;
  route_nodes?: number[];
  geometry: [number, number][];
  dist_m: number;
  time_s: number;
  arrival_eta_s?: number;
  arrival_clock?: string;
  title?: string;
  segment_idx?: number;
  segment_count?: number;
  base_time_s?: number;
};

export type HumanSleighStats = {
  time_s: number;
  dist_m: number;
  load_kg: number;
  over_kg: number;
  return_time_s: number;
  return_arrival_clock: string | null;
  return_segment?: RouteSegment;
};

export type HumanState = {
  routes_by_sleigh: Record<string, number[]>;
  segments_by_sleigh: Record<string, RouteSegment[]>;
  assigned_clients: number[];
  live_stats?: Record<string, HumanSleighStats>;
  stop_meta_by_client?: Record<number, { sleigh_id: number; stop_order: number; arrival_eta_s: number; arrival_clock: string }>;
  speed_multiplier?: number;
  vehicle_capacity?: number;
  num_vehicles?: number;
};

export type MissionResponse = {
  mission_id: string;
  mission: MissionConfig;
  depot: ClientPoint;
  clients: ClientPoint[];
  graph_available: boolean;
  weather: { desc: string; factor: number };
  human_state?: HumanState;
  results_available: boolean;
  incidents?: { count: number; segments: RouteSegment[] };
};

export type MissionSnapshot = {
  mission_id: string;
  mission: MissionConfig;
  status: string;
  created_at: string;
  updated_at: string;
};

export type CampaignMission = MissionConfig & {
  level: number;
  title: string;
  chapter: string;
  briefing: string;
  objective: string;
  ai_profile: string;
  reward_label: string;
};

export type CampaignProgress = {
  unlockedLevel: number;
  completedLevels: number[];
  bestScoreByLevel: Record<number, number>;
  starsByLevel: Record<number, number>;
  objectivesCompletedByLevel: Record<number, number>;
  defeatedProfiles: string[];
  lastPlayedLevel: number | null;
  updatedAt: string | null;
};

export type RouteOption = {
  route_nodes: number[];
  geometry: [number, number][];
  dist_m: number;
  base_time_s: number;
  time_s: number;
  label: string;
  is_feasible?: boolean;
  feasibility_badges?: string[];
  projected_arrival_clock?: string;
  projected_load_kg?: number;
  projected_overload_kg?: number;
};

export type SummaryMetrics = {
  total_dist_m: number;
  total_time_s: number;
  segment_count: number;
};

export type AISleighSummary = {
  sleigh_id: number;
  route_ids: number[];
  stop_count: number;
  time_s: number;
  weight_kg: number;
};

export type ComparisonPayload = {
  depot: ClientPoint;
  clients: ClientPoint[];
  human_segments: RouteSegment[];
  ai_segments: RouteSegment[];
  human_stop_meta_by_client?: Record<number, { sleigh_id: number; stop_order: number; arrival_eta_s: number; arrival_clock: string }>;
  incidents?: { count: number; segments: RouteSegment[] };
  summary_metrics: {
    human: SummaryMetrics & { assigned_clients: number; live_stats: Record<string, HumanSleighStats>; sleighs?: HumanSleighSummary[] };
    ai: SummaryMetrics & { sleighs: AISleighSummary[]; dropped_points: number; strategy?: AIStrategy };
  };
};

export type SolveResponse = {
  results: {
    total_time_s: number;
    total_weight_kg: number;
    tours: Array<{ vehicle_id: number; route_ids: number[]; duration_s: number; weight_kg: number }>;
    dropped_points: number[];
    ai_strategy?: AIStrategy;
  };
  benchmark: {
    naive: { total_time_s: number; total_dist_m: number; tours: any[] };
    optimized: { total_time_s: number; total_dist_m: number };
    savings: { time_saved_min: number; time_saved_pct: number; co2_saved_kg: number; score: number };
    budget?: { initial: number; spent: number; remaining: number; remaining_pct: number };
  };
  ai_tours: Array<{ vehicle_id: number; route_ids: number[]; duration_s: number; weight_kg: number }>;
  ai_segments: RouteSegment[];
  ai_stop_meta: Record<number, { vehicle_id: number; stop_order: number; arrival_eta_s: number; arrival_clock: string }>;
  comparison: ComparisonPayload;
  learning?: {
    used_model: boolean;
    model_path: string;
    recommendation: AiLearningRecommendation;
  };
};

export type HumanSleighSummary = {
  sleigh_id: number;
  stop_count: number;
  route_ids: number[];
  load_kg: number;
  over_kg: number;
  dist_m: number;
  time_s: number;
  return_time_s: number;
  return_arrival_clock: string | null;
};

export type DebriefPayload = {
  mission: MissionConfig;
  results: { total_time_s: number; total_weight_kg: number; ai_strategy?: AIStrategy };
  benchmark: {
    savings: { time_saved_min: number; time_saved_pct: number; co2_saved_kg: number };
    optimized: { total_dist_m: number; total_time_s: number };
    budget?: { remaining: number; remaining_pct: number };
  };
  score: {
    value: number;
    rank: string;
    rank_title: string;
    human_beat_ai: boolean;
    breakdown?: {
      base_score: number;
      ai_profile_bonus: number;
      incident_bonus: number;
      human_bonus: number;
      final_score: number;
    };
  };
  human: {
    summary: SummaryMetrics;
    assigned_clients: number[];
    live_stats?: Record<string, HumanSleighStats>;
    sleighs?: HumanSleighSummary[];
  };
  analysis: {
    human_vs_ai_delta_s?: number | null;
    naive_vs_ai_delta_s: number;
    dropped_points: number[];
    ai_sleighs: AISleighSummary[];
    ai_strategy?: AIStrategy;
    secondary_objectives?: SecondaryObjectiveResult[];
    recommendations: string[];
  };
};

export type LeaderboardEntry = {
  mission_id: string;
  zone: string;
  score: number;
  rank: string;
  player_name: string;
  player_id?: string | null;
  callsign?: string | null;
  avatar?: string | null;
  created_at: string;
};

export type AdjacentNode = {
  node_id: number;
  lat: number;
  lon: number;
  geometry: [number, number][];
  dist_m: number;
  time_s: number;
  label: string;
};

export type VersusWinnerRule = "score_time" | "time" | "objectives";
export type VersusMode = "private" | "queue" | "invite";
export type VersusMapSource = "template" | "custom";

export type VersusTemplate = {
  template_id: string;
  label: string;
  description: string;
};

export type VersusMissionConfig = {
  zone: string;
  city?: string | null;
  center_lat?: number | null;
  center_lon?: number | null;
  search_radius_km?: number | null;
  max_clients?: number | null;
  num_clients: number;
  budget: number;
  sleigh_cost: number;
  weather_key: string;
  random_incidents: boolean;
  ai_profile?: string | null;
  secondary_objectives?: Array<{ code: string; label: string; target?: number }> | null;
  level?: null;
};

export type VersusMissionSummary = {
  map_source: VersusMapSource;
  template_id?: string | null;
  template_label?: string | null;
  template_description?: string | null;
  zone?: string | null;
  city?: string | null;
  num_clients?: number;
  weather_key?: string | null;
  random_incidents?: boolean;
  budget?: number;
  sleigh_cost?: number;
  search_radius_km?: number | null;
  center_lat?: number | null;
  center_lon?: number | null;
  ai_profile?: string | null;
  secondary_objectives_count?: number;
};

export type VersusParticipant = {
  player_id: string;
  display_name?: string | null;
  callsign?: string | null;
  avatar?: string | null;
  seat: number;
  state: "joined" | "ready" | "live" | "submitted" | "forfeit";
  mission_id?: string | null;
  ready_at?: string | null;
  submitted_at?: string | null;
  score?: number | null;
  total_time_s?: number | null;
  objectives_completed?: number;
  is_valid_submission?: boolean;
  forfeit_at?: string | null;
  last_seen_at?: string | null;
  forfeit_deadline_at?: string | null;
  is_self: boolean;
};

export type VersusMatch = {
  match_id: string;
  mode: VersusMode;
  template_id: string;
  map_source: VersusMapSource;
  mission_config?: VersusMissionConfig | null;
  mission_summary?: VersusMissionSummary | null;
  template_label?: string | null;
  winner_rule: VersusWinnerRule;
  join_code?: string | null;
  host_player_id: string;
  status: "waiting_opponent" | "waiting_ready" | "live" | "finished";
  reference_mission_id?: string | null;
  started_at?: string | null;
  started_elapsed_s?: number | null;
  completed_at?: string | null;
  winner_player_id?: string | null;
  result_reason?: string | null;
  created_at: string;
  updated_at: string;
  participants: VersusParticipant[];
  current_player_mission_id?: string | null;
};

export type VersusInvite = {
  invite_id: string;
  inviter_player_id: string;
  invitee_player_id: string;
  template_id: string;
  map_source: VersusMapSource;
  mission_config?: VersusMissionConfig | null;
  mission_summary?: VersusMissionSummary | null;
  winner_rule: VersusWinnerRule;
  status: "pending" | "accepted" | "declined";
  match_id?: string | null;
  created_at: string;
  updated_at: string;
  responded_at?: string | null;
  inviter_display_name?: string | null;
  inviter_callsign?: string | null;
  inviter_avatar?: string | null;
};

export type VersusLeaderboardEntry = {
  match_id: string;
  winner_player_id: string;
  winner_display_name?: string | null;
  winner_callsign?: string | null;
  winner_avatar?: string | null;
  loser_player_id?: string | null;
  loser_display_name?: string | null;
  winner_score?: number | null;
  winner_time_s?: number | null;
  winner_rule: VersusWinnerRule;
  template_id: string;
  map_source?: VersusMapSource;
  mission_config?: VersusMissionConfig | null;
  mission_summary?: VersusMissionSummary | null;
  map_label?: string | null;
  created_at: string;
};

export type VersusPlayerStatsEntry = {
  player_id: string;
  display_name?: string | null;
  callsign?: string | null;
  avatar?: string | null;
  matches_played: number;
  wins: number;
  losses: number;
  winrate_pct: number;
  favorite_rule: VersusWinnerRule;
  average_time_s?: number | null;
  last_match_at?: string | null;
};
