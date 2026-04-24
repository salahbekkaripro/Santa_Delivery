import type { VersusMissionConfig, VersusMissionSummary, VersusWinnerRule } from "@/lib/types";

export const WINNER_RULE_OPTIONS: Array<{ value: VersusWinnerRule; label: string; description: string }> = [
  { value: "score_time", label: "Score puis temps", description: "Priorité au score final puis au chrono." },
  { value: "time", label: "Temps uniquement", description: "Le plus rapide gagne (tentative valide requise)." },
  { value: "objectives", label: "Objectifs", description: "Le plus d'objectifs secondaires, puis chrono." },
];

export const WEATHER_OPTIONS = ["Clear", "Rain", "Snow", "Fog", "Windy"];

export const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";
export const DEFAULT_RADIUS_KM = 3.0;
export const SEARCH_CLIENT_DENSITY_PER_KM2 = 2.0;
export const SEARCH_MIN_CLIENTS = 8;
export const SEARCH_MAX_CLIENTS = 200;
export const VERSUS_MAX_CLIENTS = 60;
export const SEARCH_MIN_RADIUS_KM = 0.5;
export const SEARCH_MAX_RADIUS_KM = 30;

export type AddressSuggestion = {
  label: string;
  lat: number;
  lon: number;
};

export const DEFAULT_DEMO_ADDRESS: AddressSuggestion = {
  label: "10 Downing Street, London, United Kingdom",
  lat: 51.5033635,
  lon: -0.1276248,
};

export const SECONDARY_OBJECTIVE_PRESETS: Array<{ code: string; label: string }> = [
  { code: "assign_all_clients", label: "Affecter tous les clients" },
  { code: "beat_ai", label: "Battre l'IA" },
  { code: "minimize_time", label: "Minimiser le temps total" },
  { code: "no_late_routes", label: "Aucune tournée en retard" },
];

export const DEFAULT_CUSTOM_MISSION_CONFIG: VersusMissionConfig = {
  zone: DEFAULT_DEMO_ADDRESS.label,
  city: "London",
  center_lat: DEFAULT_DEMO_ADDRESS.lat,
  center_lon: DEFAULT_DEMO_ADDRESS.lon,
  search_radius_km: DEFAULT_RADIUS_KM,
  num_clients: 30,
  budget: 3000,
  sleigh_cost: 500,
  weather_key: "Clear",
  random_incidents: false,
  ai_profile: "Express",
  secondary_objectives: [
    { code: "assign_all_clients", label: "Affecter tous les clients" },
    { code: "beat_ai", label: "Battre l'IA" },
  ],
};

export function computeMaxClientsForRadius(radiusKm: number) {
  const areaKm2 = Math.PI * radiusKm * radiusKm;
  const capacity = Math.floor(areaKm2 * SEARCH_CLIENT_DENSITY_PER_KM2);
  return Math.min(SEARCH_MAX_CLIENTS, Math.max(SEARCH_MIN_CLIENTS, capacity));
}

export function computeVersusMaxClientsAllowed(radiusKm: number) {
  return Math.min(VERSUS_MAX_CLIENTS, computeMaxClientsForRadius(radiusKm));
}

export async function fetchAddressSuggestions(query: string): Promise<AddressSuggestion[]> {
  const trimmed = query.trim();
  if (!MAPBOX_TOKEN || trimmed.length < 3) {
    return [];
  }

  const endpoint = new URL(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(trimmed)}.json`,
  );
  endpoint.searchParams.set("autocomplete", "true");
  endpoint.searchParams.set("limit", "6");
  endpoint.searchParams.set("language", "fr");
  endpoint.searchParams.set("types", "address,place,locality,neighborhood,poi");
  endpoint.searchParams.set("access_token", MAPBOX_TOKEN);

  const response = await fetch(endpoint.toString(), { cache: "no-store" });
  if (!response.ok) {
    throw new Error("autocomplete_failed");
  }
  const payload = (await response.json()) as { features?: Array<{ place_name?: string; center?: [number, number] }> };
  return (payload.features ?? [])
    .map((feature) => {
      const center = feature.center;
      if (!Array.isArray(center) || center.length < 2) {
        return null;
      }
      return {
        label: String(feature.place_name ?? trimmed),
        lon: Number(center[0]),
        lat: Number(center[1]),
      };
    })
    .filter((feature): feature is AddressSuggestion => feature !== null);
}

export async function geocodeFirstAddress(query: string): Promise<AddressSuggestion | null> {
  const trimmed = query.trim();
  if (!MAPBOX_TOKEN || trimmed.length < 3) {
    return null;
  }
  const endpoint = new URL(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(trimmed)}.json`,
  );
  endpoint.searchParams.set("autocomplete", "false");
  endpoint.searchParams.set("limit", "1");
  endpoint.searchParams.set("language", "fr");
  endpoint.searchParams.set("types", "address,place,locality,neighborhood,poi");
  endpoint.searchParams.set("access_token", MAPBOX_TOKEN);

  const response = await fetch(endpoint.toString(), { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  const payload = (await response.json()) as { features?: Array<{ place_name?: string; center?: [number, number] }> };
  const first = payload.features?.[0];
  if (!first || !Array.isArray(first.center) || first.center.length < 2) {
    return null;
  }
  return {
    label: String(first.place_name ?? trimmed),
    lon: Number(first.center[0]),
    lat: Number(first.center[1]),
  };
}

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
