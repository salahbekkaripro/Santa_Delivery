import type { VersusMissionConfig, VersusMissionSummary, VersusWinnerRule } from "@/lib/types";

export const WINNER_RULE_OPTIONS: Array<{ value: VersusWinnerRule; label: string; description: string }> = [
  { value: "score_time", label: "Score puis temps", description: "Priorité au score final puis au chrono." },
  { value: "time", label: "Temps uniquement", description: "Le plus rapide gagne (tentative valide requise)." },
  { value: "objectives", label: "Objectifs", description: "Le plus d'objectifs secondaires, puis chrono." },
];

export const WEATHER_OPTIONS = ["Clear", "Rain", "Snow", "Fog", "Windy"];

export const SECONDARY_OBJECTIVE_PRESETS: Array<{ code: string; label: string }> = [
  { code: "assign_all_clients", label: "Affecter tous les clients" },
  { code: "beat_ai", label: "Battre l'IA" },
  { code: "minimize_time", label: "Minimiser le temps total" },
  { code: "no_late_routes", label: "Aucune tournée en retard" },
];

export const DEFAULT_CUSTOM_MISSION_CONFIG: VersusMissionConfig = {
  zone: "Le Marais, Paris",
  city: "Paris",
  center_lat: 48.857,
  center_lon: 2.36,
  search_radius_km: 3,
  num_clients: 24,
  budget: 3200,
  sleigh_cost: 650,
  weather_key: "Clear",
  random_incidents: false,
  ai_profile: "Express",
  secondary_objectives: [
    { code: "assign_all_clients", label: "Affecter tous les clients" },
    { code: "beat_ai", label: "Battre l'IA" },
  ],
};

export function ruleLabel(rule: string) {
  if (rule === "time") return "Temps";
  if (rule === "objectives") return "Objectifs";
  return "Score + temps";
}

export function formatMissionSummary(summary?: VersusMissionSummary | null) {
  if (!summary) {
    return "Carte non disponible";
  }
  const label = summary.template_label ?? summary.template_id ?? "Carte";
  const zone = summary.zone ? ` · ${summary.zone}` : "";
  const clients = typeof summary.num_clients === "number" ? ` · ${summary.num_clients} colis` : "";
  const weather = summary.weather_key ? ` · ${summary.weather_key}` : "";
  return `${label}${zone}${clients}${weather}`;
}
