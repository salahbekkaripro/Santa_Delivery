export type MissionConfig = {
  mission_id?: string;
  zone: string;
  num_clients: number;
  budget: number;
  sleigh_cost: number;
  weather_key: string;
  random_incidents: boolean;
  level?: number | null;
  generation_message?: string;
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

export type RouteOption = {
  route_nodes: number[];
  geometry: [number, number][];
  dist_m: number;
  base_time_s: number;
  time_s: number;
  label: string;
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
    ai: SummaryMetrics & { sleighs: AISleighSummary[]; dropped_points: number };
  };
};

export type SolveResponse = {
  results: {
    total_time_s: number;
    total_weight_kg: number;
    tours: Array<{ vehicle_id: number; route_ids: number[]; duration_s: number; weight_kg: number }>;
    dropped_points: number[];
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
  results: { total_time_s: number; total_weight_kg: number };
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
    recommendations: string[];
  };
};

export type LeaderboardEntry = {
  mission_id: string;
  zone: string;
  score: number;
  rank: string;
  player_name: string;
  created_at: string;
};
