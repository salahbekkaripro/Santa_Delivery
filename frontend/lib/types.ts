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
