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
  departure_hour?: number | null;
  with_elevation?: boolean;
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

export type SocialPlayer = {
  player_id: string;
  display_name: string;
  callsign?: string | null;
  avatar?: string | null;
};

export type SocialFriendship = {
  peer_player_id: string;
  peer_display_name?: string | null;
  peer_callsign?: string | null;
  peer_avatar?: string | null;
  status: "pending" | "accepted" | "declined";
  requester_player_id: string;
  addressee_player_id: string;
  created_at?: string | null;
  updated_at?: string | null;
  responded_at?: string | null;
};

export type SocialDirectMessage = {
  message_id: string;
  conversation_key: string;
  sender_player_id: string;
  sender_display_name?: string | null;
  sender_avatar?: string | null;
  recipient_player_id: string;
  recipient_display_name?: string | null;
  recipient_avatar?: string | null;
  body: string;
  created_at?: string | null;
  read_at?: string | null;
  is_mine: boolean;
};

export type SocialConversation = {
  conversation_key: string;
  peer_player_id: string;
  peer_display_name?: string | null;
  peer_callsign?: string | null;
  peer_avatar?: string | null;
  unread_count: number;
  last_message_at?: string | null;
  last_message?: SocialDirectMessage | null;
  hidden?: boolean;
  cleared_before_at?: string | null;
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
  tw_start?: number;
  tw_end?: number;
  cargo_code?: string;
  cargo_label?: string;
  cargo_emoji?: string;
  cargo_constraint?: string | null;
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

export type ElevationMeta = {
  min_m: number;
  max_m: number;
  mean_m: number;
  range_m: number;
  total_climb_m: number;
  total_descent_m: number;
  terrain_type: "plat" | "vallonné" | "montagneux";
  time_overhead_pct: number;
  source: string;
  points: Array<{ lat: number; lon: number; elevation_m: number; name: string }>;
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
  elevation?: ElevationMeta | null;
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

export type MapInteractionState = {
  click_to_confirm_enabled: boolean;
  confirming_route_key?: string;
  last_action?: "validated" | "undone" | "error";
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
    weather?: { factor: number; desc: string };
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

export type SolveResponseLite = {
  results: {
    total_time_s: number;
    dropped_points: number[];
    tours: Array<{ vehicle_id: number; route_ids: number[]; duration_s: number; weight_kg: number }>;
  };
  benchmark: {
    optimized: { total_time_s: number; total_dist_m: number };
    savings: { co2_saved_kg: number };
  };
};

export type IncidentReplanResponse = {
  incidents: { count: number; segments: RouteSegment[] };
  before: SolveResponseLite;
  after: SolveResponse;
  delta_kpi: { time_s: number; dist_m: number; co2_kg: number; time_pct: number; dist_pct: number };
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
      weather_bonus: number;
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
    two_opt?: TwoOptResult | null;
    or_opt?: OrOptResult | null;
    nearest_neighbor?: NearestNeighborResult | null;
    optimality_gap?: OptimalityGapResult | null;
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

export type GraphMetrics = {
  num_nodes: number;
  num_edges: number;
  avg_degree: number;
  max_degree: number;
  density: number;
  is_strongly_connected: boolean;
  num_scc: number;
  largest_scc_size: number;
  largest_scc_pct: number;
  avg_clustering: number;
  top_betweenness_nodes: { node: number; score: number; lat: number; lon: number }[];
};

export type DijkstraStep = {
  step: number;
  node: number;
  dist: number;
  lat: number;
  lon: number;
  predecessor: number | null;
};

export type DijkstraResult = {
  from_node: number;
  to_node: number;
  steps: DijkstraStep[];
  steps_count: number;
  path: number[];
  path_length: number;
  total_cost: number;
  reached: boolean;
  truncated: boolean;
};

export type AstarBiDirStep = {
  step: number;
  direction: "forward" | "backward";
  node: number;
  g: number;
  f: number;
  lat: number;
  lon: number;
  predecessor: number | null;
};

export type AstarCompareResult = {
  from_node: number;
  to_node: number;
  steps_forward: AstarBiDirStep[];
  steps_backward: AstarBiDirStep[];
  meeting_node: number | null;
  path: number[];
  path_length: number;
  total_cost: number;
  reached: boolean;
  truncated: boolean;
  nodes_explored_astar_bidir: number;
  nodes_explored_unidir: number;
  reduction_pct: number;
};

export type TwoOptSleighResult = {
  human_time_s: number;
  two_opt_time_s: number;
  improvement_s: number;
  improvement_pct: number;
  optimized_route: number[];
};

export type TwoOptResult = {
  sleighs: Record<string, TwoOptSleighResult>;
  total_human_time_s: number;
  total_two_opt_time_s: number;
  total_improvement_s: number;
  total_improvement_pct: number;
};

export type OrOptSleighResult = {
  human_time_s: number;
  or_opt_time_s: number;
  improvement_s: number;
  improvement_pct: number;
  optimized_route: number[];
};

export type OrOptResult = {
  sleighs: Record<string, OrOptSleighResult>;
  total_human_time_s: number;
  total_or_opt_time_s: number;
  total_improvement_s: number;
  total_improvement_pct: number;
};

export type NearestNeighborStep = {
  step: number;
  from_node: number;
  to_node: number;
  cost_s: number;
  cumulative_s: number;
};

export type NearestNeighborResult = {
  route: number[];
  total_time_s: number;
  steps_count: number;
  steps: NearestNeighborStep[];
};

export type OptimalityGapResult = {
  lower_bound_s: number;
  solution_cost_s: number;
  gap_pct: number | null;
  interpretation: string;
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
  progress?: {
    assigned_clients: number;
    total_clients: number;
    progress_pct: number;
    elapsed_s: number;
    updated_at?: string | null;
  };
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
  countdown_total_s?: number | null;
  countdown_remaining_s?: number | null;
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

// ── Eco / CO2 Analysis ────────────────────────────────────────────────────────

export type Co2RouteProfile = {
  distance_km: number;
  truck_co2_kg: number;
  sleigh_co2_kg: number;
  saved_vs_truck_kg: number;
  trees_month_offset: number;
};

export type EcoAnalysis = {
  terrain: {
    type: "plat" | "vallonné" | "montagneux";
    estimated_climb_m: number;
    zone: string;
    note: string;
  };
  routes: {
    ai: Co2RouteProfile;
    naive: Co2RouteProfile;
    human: Co2RouteProfile | null;
  };
  eco_impact: {
    total_co2_avoided_kg: number;
    route_optimisation_saving_kg: number;
    ai_vs_naive_dist_pct: number;
  };
};

// ── Community Detection / Delivery Sectors ────────────────────────────────────

export type DeliverySector = {
  sector_id: number;
  label: string;
  color: string;
  nodes: (number | string)[];
  node_count: number;
  center_lat: number;
  center_lon: number;
  polygon: [number, number][];  // [[lat, lon], ...]
};

export type DeliverySectorsResult = {
  sector_count: number;
  sectors: DeliverySector[];
  algorithm: string;
  note: string;
};

// ── Topological Validation ────────────────────────────────────────────────────

export type ClientReachability = {
  client_id: number;
  osm_node: number;
  reachable: boolean;
};

export type TopologyCheck = {
  is_valid: boolean;
  depot_node: number;
  num_components: number;
  blocked_edges_count: number;
  incident_count: number;
  unreachable_clients: number[];
  reachability: ClientReachability[];
  status: string;
};
