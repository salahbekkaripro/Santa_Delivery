"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { createMission, getGraphMetrics, getMission, simulateIncidentReplan, solveMission } from "@/lib/api";
import { SearchAreaMap } from "@/components/search-area-map";
import type { ClientPoint, GraphMetrics, IncidentReplanResponse, MissionResponse, RouteSegment, SolveResponse } from "@/lib/types";

const RouteMap = dynamic(() => import("@/components/solver-route-map"), { ssr: false });

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";
const DEFAULT_ADDRESS = {
  label: "10 Downing Street, London, United Kingdom",
  lat: 51.5033635,
  lon: -0.1276248,
};
const SEARCH_MIN_RADIUS_KM = 0.5;
const SEARCH_MAX_RADIUS_KM = 30;
const SEARCH_MAX_CLIENTS = 200;
const SEARCH_MIN_CLIENTS = 8;
const SEARCH_CLIENT_DENSITY_PER_KM2 = 2.0;

const SLEIGH_COLORS = ["#1a6fb5", "#9e2f3f", "#1f7a56", "#b8892f", "#6b3fa0", "#c45e00"];

const PROFILES = [
  { key: "express", label: "⚡ Express", desc: "Minimise le temps — vitesse max, GLS", difficultyBonus: 2 },
  { key: "ecolo",   label: "🌱 Écolo",   desc: "Minimise la distance — empreinte carbone réduite", difficultyBonus: 3 },
  { key: "prudent", label: "🛡️ Prudent", desc: "Marge de temps élevée — robuste aux aléas", difficultyBonus: 4 },
];

const RANK_THRESHOLDS = [
  { min: 85, rank: "S", title: "Eco-Livreur Légendaire", color: "#d4a017" },
  { min: 70, rank: "A", title: "Chef Logisticien",       color: "#1a6fb5" },
  { min: 50, rank: "B", title: "Livreur Efficace",       color: "#1f7a56" },
  { min: 30, rank: "C", title: "Apprenti Père Noël",     color: "#b8892f" },
  { min: 0,  rank: "D", title: "En formation",           color: "#9e2f3f" },
];

type AddressSuggestion = { label: string; lat: number; lon: number };
type Step = "form" | "loading" | "result";
type LoadingStep = { label: string; done: boolean };
type Result = { mission: MissionResponse; solve: SolveResponse };
type SegmentExplain = {
  key: string;
  sleighId: number;
  fromLabel: string;
  toLabel: string;
  primaryReason: "Temps" | "Congestion" | "Capacité" | "Fenêtre horaire";
  details: string;
  badges: string[];
};
type SimulationStage = "idle" | "injecting" | "replanning" | "applying";

function computeScore(
  solve: SolveResponse,
  numClients: number,
  profile: string,
  randomIncidents: boolean,
  weatherFactor: number,
) {
  const savings = solve.benchmark.savings;
  const budget  = solve.benchmark.budget;

  const timeScorePct      = Math.max(0, Math.min(100, savings.time_saved_pct * 2.5));
  const co2RefKg          = Math.max(1.0, numClients * 0.1);
  const co2Score          = Math.max(0, Math.min((savings.co2_saved_kg / co2RefKg) * 100, 100));
  const budgetRemainingPct = Math.max(0, Math.min(100, budget?.remaining_pct ?? 50));

  const timeContribution = 0.60 * timeScorePct;
  const co2Contribution = 0.25 * co2Score;
  const budgetContribution = 0.15 * budgetRemainingPct;
  const baseScore = timeContribution + co2Contribution + budgetContribution;
  const diffBonus      = PROFILES.find((p) => p.key === profile)?.difficultyBonus ?? 2;
  const incidentBonus  = randomIncidents ? 10 : 0;
  const weatherBonus   = Math.max(0, (weatherFactor - 1) * 8);

  const value = Math.max(0, Math.min(100, baseScore + diffBonus + incidentBonus + weatherBonus));
  const rank  = RANK_THRESHOLDS.find((r) => value >= r.min) ?? RANK_THRESHOLDS[RANK_THRESHOLDS.length - 1];
  return {
    value: Math.round(value * 10) / 10,
    rank: rank.rank,
    title: rank.title,
    color: rank.color,
    breakdown: {
      timeScorePct: Math.round(timeScorePct * 10) / 10,
      co2Score: Math.round(co2Score * 10) / 10,
      budgetRemainingPct: Math.round(budgetRemainingPct * 10) / 10,
      timeContribution: Math.round(timeContribution * 10) / 10,
      co2Contribution: Math.round(co2Contribution * 10) / 10,
      budgetContribution: Math.round(budgetContribution * 10) / 10,
      diffBonus,
      incidentBonus,
      weatherBonus: Math.round(weatherBonus * 10) / 10,
    },
  };
}

function computeMaxClientsForRadius(radiusKm: number) {
  const areaKm2 = Math.PI * radiusKm * radiusKm;
  return Math.min(SEARCH_MAX_CLIENTS, Math.max(SEARCH_MIN_CLIENTS, Math.floor(areaKm2 * SEARCH_CLIENT_DENSITY_PER_KM2)));
}

function formatMin(s: number) {
  const m = Math.round(s / 60);
  return m < 60 ? `${m} min` : `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}`;
}
function formatKm(m: number) {
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

function formatEta(seconds: number) {
  const safe = Math.max(0, Math.round(seconds));
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  return `${String(h).padStart(2, "0")}h${String(m).padStart(2, "0")}`;
}

function formatDeltaSeconds(seconds: number) {
  const sign = seconds >= 0 ? "+" : "−";
  return `${sign}${formatMin(Math.abs(seconds))}`;
}

function formatDeltaDistance(meters: number) {
  const sign = meters >= 0 ? "+" : "−";
  return `${sign}${formatKm(Math.abs(meters))}`;
}

export default function SolverPage() {
  const [step, setStep] = useState<Step>("form");
  const [loadingSteps, setLoadingSteps] = useState<LoadingStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [profile, setProfile] = useState("express");
  const [incidentCount, setIncidentCount] = useState(1);
  const [simulationBusy, setSimulationBusy] = useState(false);
  const [simulationStage, setSimulationStage] = useState<SimulationStage>("idle");
  const [simulationError, setSimulationError] = useState<string | null>(null);
  const [simulationSummary, setSimulationSummary] = useState<IncidentReplanResponse | null>(null);
  const [liveIncidentSegments, setLiveIncidentSegments] = useState<RouteSegment[]>([]);
  const [graphMetrics, setGraphMetrics] = useState<GraphMetrics | null>(null);
  const [mapRunId, setMapRunId] = useState(0);
  const [liveGainPct, setLiveGainPct] = useState(0);
  const liveGainPctRef = useRef(0);

  // Address autocomplete
  const [addressQuery, setAddressQuery] = useState(DEFAULT_ADDRESS.label);
  const [selectedAddress, setSelectedAddress] = useState<AddressSuggestion | null>(DEFAULT_ADDRESS);
  const [addressSuggestions, setAddressSuggestions] = useState<AddressSuggestion[]>([]);
  const [addressLookupError, setAddressLookupError] = useState<string | null>(null);
  const [isAddressLoading, setIsAddressLoading] = useState(false);
  const [isAddressFocused, setIsAddressFocused] = useState(false);

  // Mission params
  const [sandbox, setSandbox] = useState({
    search_radius_km: 2.0,
    num_clients: 12,
    budget: 3000,
    sleigh_cost: 500,
    weather_key: "real",
    random_incidents: false,
    departure_hour: null as number | null,
    with_elevation: false,
  });

  const canAutocomplete = MAPBOX_TOKEN.trim().length > 0;
  const maxClientsAllowed = useMemo(() => computeMaxClientsForRadius(sandbox.search_radius_km), [sandbox.search_radius_km]);
  const requestedClients = Math.max(1, Math.round(Number(sandbox.num_clients) || 0));
  const requestedBudget = Math.max(0, Math.round(Number(sandbox.budget) || 0));
  const requestedSleighCost = Math.max(0, Math.round(Number(sandbox.sleigh_cost) || 0));
  const exceedsClientsLimit = requestedClients > maxClientsAllowed;
  const hasAddressSelection = selectedAddress !== null;
  const mapCenter = selectedAddress ?? DEFAULT_ADDRESS;
  const areaKm2 = useMemo(() => Math.PI * sandbox.search_radius_km * sandbox.search_radius_km, [sandbox.search_radius_km]);

  const weatherLocation = useMemo(() => {
    if (!selectedAddress) return "";
    const chunks = selectedAddress.label.split(",").map((s) => s.trim()).filter(Boolean);
    return (chunks.length >= 2 ? chunks.slice(-2).join(", ") : chunks[0] ?? selectedAddress.label).slice(0, 120);
  }, [selectedAddress]);

  // Invalidate selection when query is edited manually
  useEffect(() => {
    if (selectedAddress && addressQuery.trim() !== selectedAddress.label) {
      setSelectedAddress(null);
    }
  }, [addressQuery, selectedAddress]);

  // Mapbox autocomplete with 280 ms debounce
  useEffect(() => {
    const query = addressQuery.trim();
    if (!canAutocomplete || query.length < 3) {
      setAddressSuggestions([]);
      setIsAddressLoading(false);
      setAddressLookupError(null);
      return;
    }
    const id = window.setTimeout(async () => {
      setIsAddressLoading(true);
      setAddressLookupError(null);
      try {
        const endpoint = new URL(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json`);
        endpoint.searchParams.set("autocomplete", "true");
        endpoint.searchParams.set("limit", "6");
        endpoint.searchParams.set("language", "fr");
        endpoint.searchParams.set("types", "address,place,locality,neighborhood,poi");
        endpoint.searchParams.set("access_token", MAPBOX_TOKEN);
        const res = await fetch(endpoint.toString(), { cache: "no-store" });
        if (!res.ok) throw new Error("autocomplete_failed");
        const payload = (await res.json()) as { features?: Array<{ place_name?: string; center?: [number, number] }> };
        const suggestions = (payload.features ?? [])
          .map((f) => {
            if (!Array.isArray(f.center) || f.center.length < 2) return null;
            return { label: String(f.place_name ?? query), lon: Number(f.center[0]), lat: Number(f.center[1]) };
          })
          .filter((s): s is AddressSuggestion => s !== null);
        setAddressSuggestions(suggestions);
      } catch {
        setAddressSuggestions([]);
        setAddressLookupError("Impossible de charger les suggestions d'adresse.");
      } finally {
        setIsAddressLoading(false);
      }
    }, 280);
    return () => window.clearTimeout(id);
  }, [addressQuery, canAutocomplete]);

  function selectSuggestion(s: AddressSuggestion) {
    setSelectedAddress(s);
    setAddressQuery(s.label);
    setAddressSuggestions([]);
    setAddressLookupError(null);
    setIsAddressFocused(false);
  }

  function tick(steps: LoadingStep[], idx: number): LoadingStep[] {
    return steps.map((s, i) => (i === idx ? { ...s, done: true } : s));
  }

  async function handleSolve() {
    if (!selectedAddress) return;
    setError(null);
    setResult(null);

    const steps: LoadingStep[] = [
      { label: `Chargement du graphe OSM pour « ${selectedAddress.label} »…`, done: false },
      { label: `Génération de ${requestedClients} points dans un rayon de ${sandbox.search_radius_km.toFixed(1)} km…`, done: false },
      { label: "Calcul de la matrice de coût (A* haversine)…", done: false },
      { label: "Résolution VRPTW avec Google OR-Tools…", done: false },
      { label: "Optimisation locale (ILS + 2-opt + or-opt)…", done: false },
    ];
    setLoadingSteps(steps);
    setStep("loading");

    try {
      const missionRes = await createMission({
        zone: selectedAddress.label,
        city: weatherLocation,
        center_lat: selectedAddress.lat,
        center_lon: selectedAddress.lon,
        search_radius_km: sandbox.search_radius_km,
        max_clients: maxClientsAllowed,
        num_clients: requestedClients,
        budget: requestedBudget,
        sleigh_cost: requestedSleighCost,
        weather_key: sandbox.weather_key,
        random_incidents: sandbox.random_incidents,
        departure_hour: sandbox.departure_hour,
        with_elevation: sandbox.with_elevation,
        ai_profile: profile,
        level: null,
      });
      const missionId = missionRes.mission_id;
      setLoadingSteps((prev) => tick(prev, 0));
      setLoadingSteps((prev) => tick(prev, 1));
      setLoadingSteps((prev) => tick(prev, 2));

      const solveRes = await solveMission(missionId, {
        num_vehicles: Math.max(1, Math.ceil(requestedClients / 3)),
        vehicle_capacity: 200,
        speed_multiplier: 1.0,
        optimization_target: profile === "ecolo" ? "distance" : "time",
      });
      setLoadingSteps((prev) => tick(prev, 3));
      setLoadingSteps((prev) => tick(prev, 4));

      const missionDetail = await getMission(missionId);
      try {
        const metrics = await getGraphMetrics(missionId);
        setGraphMetrics(metrics);
      } catch {
        setGraphMetrics(null);
      }
      setResult({ mission: missionDetail, solve: solveRes });
      setSimulationSummary(null);
      setSimulationError(null);
      setSimulationStage("idle");
      setSimulationBusy(false);
      setLiveIncidentSegments((missionDetail.incidents?.segments as RouteSegment[]) ?? []);
      setMapRunId(0);
      setStep("result");
    } catch (e) {
      setError((e as Error).message ?? "Erreur inconnue");
      setStep("form");
    }
  }

  function reset() {
    setStep("form");
    setResult(null);
    setError(null);
    setLoadingSteps([]);
    setSimulationSummary(null);
    setSimulationError(null);
    setSimulationStage("idle");
    setSimulationBusy(false);
    setLiveIncidentSegments([]);
    setGraphMetrics(null);
    setMapRunId(0);
  }

  async function runIncidentReplan(
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
    if (!result || simulationBusy) return;
    const missionId = result.mission.mission_id;
    if (!missionId) {
      setSimulationError("Mission introuvable: relance un solve complet.");
      return;
    }

    const strategy = result.solve.results.ai_strategy;
    setSimulationBusy(true);
    setSimulationError(null);
    setSimulationStage("injecting");

    try {
      await new Promise((resolve) => window.setTimeout(resolve, 220));
      setSimulationStage("replanning");
      const response = await simulateIncidentReplan(missionId, {
        ...payload,
        num_vehicles: payload.num_vehicles ?? strategy?.num_vehicles ?? Math.max(1, Math.ceil(result.mission.clients.length / 3)),
        vehicle_capacity: payload.vehicle_capacity ?? strategy?.vehicle_capacity ?? 200,
        speed_multiplier: payload.speed_multiplier ?? strategy?.speed_multiplier ?? 1.0,
        optimization_target: payload.optimization_target ?? strategy?.optimization_target ?? "time",
      });

      setSimulationStage("applying");
      const nextMission = {
        ...result.mission,
        incidents: response.incidents,
        results_available: true,
      };
      setLiveIncidentSegments(response.incidents.segments ?? []);
      setResult({ mission: nextMission, solve: response.after });
      setSimulationSummary(response);
      setMapRunId((prev) => prev + 1);
      await new Promise((resolve) => window.setTimeout(resolve, 260));
      setSimulationStage("idle");
    } catch (e) {
      setSimulationError((e as Error).message ?? "Échec de replanification.");
      setSimulationStage("idle");
    } finally {
      setSimulationBusy(false);
    }
  }

  async function handleIncidentReplan() {
    await runIncidentReplan({
      incident_count: Math.max(1, Math.min(incidentCount, 3)),
      strategy: "guided",
    });
  }

  async function handleManualBlock(segment: RouteSegment) {
    await runIncidentReplan({
      incident_count: 1,
      strategy: "guided",
      manual_segments: [
        {
          from_id: intOrZero(segment.from_id),
          to_id: intOrZero(segment.to_id),
          route_nodes: (segment.route_nodes ?? []).map((node) => intOrZero(node)),
          geometry: segment.geometry,
          dist_m: Number(segment.dist_m ?? 0),
          time_s: Number(segment.time_s ?? 0),
          title: `⚠️ Incident manuel · segment bloque #${segment.from_id} -> #${segment.to_id}`,
        },
      ],
    });
  }

  // Result helpers
  const tours = result?.solve.ai_tours ?? [];
  const activeTours = tours.filter((t) => t.route_ids.filter((id) => id !== result?.mission.depot.id).length > 0);
  const totalTimeS = result?.solve.results.total_time_s ?? 0;
  const totalDistM = result?.solve.benchmark.optimized.total_dist_m ?? 0;
  const savings = result?.solve.benchmark.savings;
  const distanceGainTargetPct = useMemo(() => {
    if (!result) return 13.6;
    const greedyDist = Number(result.solve.benchmark.naive.total_dist_m ?? 0);
    const aiDist = Number(result.solve.benchmark.optimized.total_dist_m ?? 0);
    if (greedyDist <= 0) return 13.6;
    return ((greedyDist - aiDist) / greedyDist) * 100;
  }, [result]);
  const distanceSavedMeters = useMemo(() => {
    if (!result) return 0;
    const greedyDist = Number(result.solve.benchmark.naive.total_dist_m ?? 0);
    const aiDist = Number(result.solve.benchmark.optimized.total_dist_m ?? 0);
    return Math.max(0, greedyDist - aiDist);
  }, [result]);
  const dropped = result?.solve.results.dropped_points ?? [];
  const duplicateAssignments = useMemo(() => {
    if (!result) return [] as Array<{ clientId: number; tours: number[]; clientName: string }>;
    const depotId = intOrZero(result.mission.depot.id);
    const seen = new Map<number, number[]>();
    const names = new Map<number, string>();
    for (const client of result.mission.clients) {
      names.set(intOrZero(client.id), client.nom_client || `Client ${client.id}`);
    }
    for (const tour of activeTours) {
      for (const rawId of tour.route_ids ?? []) {
        const clientId = intOrZero(rawId);
        if (clientId === depotId) continue;
        const current = seen.get(clientId) ?? [];
        current.push(tour.vehicle_id + 1);
        seen.set(clientId, current);
      }
    }
    return Array.from(seen.entries())
      .filter(([, toursForClient]) => toursForClient.length > 1)
      .map(([clientId, toursForClient]) => ({
        clientId,
        tours: Array.from(new Set(toursForClient)),
        clientName: names.get(clientId) ?? `Client ${clientId}`,
      }));
  }, [result, activeTours]);
  const segmentExplanations = useMemo<SegmentExplain[]>(() => {
    if (!result) return [];

    const depotId = intOrZero(result.mission.depot.id);
    const clientById = new Map<number, ClientPoint>(result.mission.clients.map((client) => [intOrZero(client.id), client]));
    const stopMeta = result.solve.ai_stop_meta ?? {};
    const weatherFactor = Number(result.solve.results.weather?.factor ?? 1.0);
    const hasCongestionWindow = result.mission.mission.departure_hour !== null && result.mission.mission.departure_hour !== undefined;

    const blockedUndirectedEdges = new Set<string>();
    for (const incident of result.mission.incidents?.segments ?? []) {
      const nodes = (incident.route_nodes ?? []).map((node) => intOrZero(node));
      for (let i = 0; i < nodes.length - 1; i += 1) {
        const a = Math.min(nodes[i], nodes[i + 1]);
        const b = Math.max(nodes[i], nodes[i + 1]);
        blockedUndirectedEdges.add(`${a}-${b}`);
      }
    }

    const loadBySegmentKey = new Map<string, number>();
    for (const tour of activeTours) {
      const route = tour.route_ids ?? [];
      let currentLoad = 0;
      for (let i = 1; i < route.length; i += 1) {
        const toId = intOrZero(route[i]);
        const client = clientById.get(toId);
        if (toId !== depotId && client) {
          currentLoad += Number(client.poids_colis ?? 0);
        }
        loadBySegmentKey.set(`${tour.vehicle_id}-${i}`, currentLoad);
      }
    }
    const vehicleCapacity = Number(result.solve.results.ai_strategy?.vehicle_capacity ?? 200);

    const labels = new Map<number, string>([[depotId, "Dépôt"]]);
    for (const client of result.mission.clients) {
      labels.set(intOrZero(client.id), client.nom_client || `Client ${client.id}`);
    }

    return (result.solve.ai_segments ?? []).map((segment) => {
      const sleighId = intOrZero(segment.sleigh_id);
      const fromId = intOrZero(segment.from_id);
      const toId = intOrZero(segment.to_id);
      const segIdx = intOrZero(segment.segment_idx ?? 0);
      const segmentKey = `${sleighId}-${segIdx}`;
      const loadKg = loadBySegmentKey.get(segmentKey) ?? 0;
      const loadPct = vehicleCapacity > 0 ? loadKg / vehicleCapacity : 0;

      const client = clientById.get(toId);
      const stop = stopMeta[toId];
      const twStart = client?.tw_start;
      const twEnd = client?.tw_end;
      const arrivalEta = stop?.arrival_eta_s;

      const routeNodes = (segment.route_nodes ?? []).map((node) => intOrZero(node));
      let hasIncidentOverlap = false;
      for (let i = 0; i < routeNodes.length - 1; i += 1) {
        const a = Math.min(routeNodes[i], routeNodes[i + 1]);
        const b = Math.max(routeNodes[i], routeNodes[i + 1]);
        if (blockedUndirectedEdges.has(`${a}-${b}`)) {
          hasIncidentOverlap = true;
          break;
        }
      }

      const badges: string[] = [];
      if (hasIncidentOverlap) badges.push("Incident");
      if (hasCongestionWindow || weatherFactor > 1.2) badges.push("Congestion");
      if (toId !== depotId && loadPct >= 0.8) badges.push(`Charge ${Math.round(loadPct * 100)}%`);
      if (toId !== depotId && twEnd !== undefined && arrivalEta !== undefined) badges.push("Fenêtre horaire");

      let primaryReason: SegmentExplain["primaryReason"] = "Temps";
      let details = `Segment court estimé à ${formatMin(Number(segment.time_s ?? 0))} (${formatKm(Number(segment.dist_m ?? 0))}).`;

      if (toId !== depotId && twEnd !== undefined && arrivalEta !== undefined) {
        const slackS = Number(twEnd) - Number(arrivalEta);
        if (slackS <= 1200) {
          primaryReason = "Fenêtre horaire";
          const startLabel = twStart !== undefined ? formatEta(Number(twStart)) : "00h00";
          const endLabel = formatEta(Number(twEnd));
          details = `Arrivée ${stop?.arrival_clock ?? formatEta(Number(arrivalEta))} pour respecter la fenêtre ${startLabel}–${endLabel} (marge ${Math.max(0, Math.round(slackS / 60))} min).`;
        }
      }

      if (primaryReason === "Temps" && toId !== depotId && loadPct >= 0.85) {
        primaryReason = "Capacité";
        details = `Affecté à ce traîneau pour rester faisable côté charge: ${Math.round(loadKg)} / ${Math.round(vehicleCapacity)} kg.`;
      }

      if (primaryReason === "Temps" && (hasIncidentOverlap || hasCongestionWindow || weatherFactor > 1.2)) {
        primaryReason = "Congestion";
        if (hasIncidentOverlap) {
          details = "Choix d’axe tenant compte d’une zone incidentée pour maintenir une tournée faisable.";
        } else if (weatherFactor > 1.2) {
          details = `Arbitrage robuste en conditions météo dégradées (facteur ×${weatherFactor.toFixed(2)}).`;
        } else {
          details = "Ordonnancement optimisé pour limiter l’impact des congestions horaires.";
        }
      }

      return {
        key: `${sleighId}-${segIdx}-${fromId}-${toId}`,
        sleighId,
        fromLabel: labels.get(fromId) ?? `#${fromId}`,
        toLabel: labels.get(toId) ?? `#${toId}`,
        primaryReason,
        details,
        badges,
      };
    });
  }, [result, activeTours]);
  const explanationsBySleigh = useMemo(() => {
    const grouped = new Map<number, SegmentExplain[]>();
    for (const explanation of segmentExplanations) {
      const current = grouped.get(explanation.sleighId) ?? [];
      current.push(explanation);
      grouped.set(explanation.sleighId, current);
    }
    return grouped;
  }, [segmentExplanations]);

  const scoreData = useMemo(() => {
    if (!result) return null;
    const weatherFactor = result.solve.results.weather?.factor ?? 1.0;
    return computeScore(result.solve, result.mission.clients.length, profile, sandbox.random_incidents, weatherFactor);
  }, [result, profile, sandbox.random_incidents]);
  const canRunSimulation = Boolean(result?.mission.mission_id && result?.solve?.ai_segments?.length) && !simulationBusy;
  const simulationStageLabel =
    simulationStage === "injecting"
      ? "Injection de l'incident…"
      : simulationStage === "replanning"
        ? "Replanification OR-Tools…"
        : simulationStage === "applying"
          ? "Application du nouveau plan…"
          : "Prêt";

  useEffect(() => {
    liveGainPctRef.current = liveGainPct;
  }, [liveGainPct]);

  useEffect(() => {
    const target = Number.isFinite(distanceGainTargetPct) ? distanceGainTargetPct : 0;
    let rafId = 0;
    let startTs = 0;
    const startValue = liveGainPctRef.current;
    const duration = 650;
    const step = (ts: number) => {
      if (!startTs) startTs = ts;
      const p = Math.max(0, Math.min(1, (ts - startTs) / duration));
      const eased = 1 - Math.pow(1 - p, 3);
      setLiveGainPct(startValue + (target - startValue) * eased);
      if (p < 1) rafId = window.requestAnimationFrame(step);
    };
    rafId = window.requestAnimationFrame(step);
    return () => window.cancelAnimationFrame(rafId);
  }, [distanceGainTargetPct]);

  return (
    <div className="page-shell">
      <div className="page-stack">

        {/* HERO */}
        <section className="hero">
          <h1>Solveur de tournées</h1>
          <p>
            Choisis une adresse, une zone, un profil IA — le solveur calcule la tournée optimale
            sur le vrai réseau routier OpenStreetMap en quelques secondes.
          </p>
        </section>

        {/* ── FORMULAIRE ── */}
        {step === "form" && (
          <section className="panel stack">
            <strong>Configure ta tournée</strong>

            <div className="grid-2">

              {/* Adresse avec autocomplete */}
              <label className="field" style={{ gridColumn: "1 / -1" }}>
                <span>Adresse ou zone de livraison</span>
                <div className="address-autocomplete">
                  <input
                    value={addressQuery}
                    onChange={(e) => setAddressQuery(e.target.value)}
                    onFocus={() => setIsAddressFocused(true)}
                    onBlur={() => window.setTimeout(() => setIsAddressFocused(false), 120)}
                    placeholder="ex: 10 Downing Street, London · Marais, Paris · Tokyo Station"
                    autoFocus
                  />
                  {isAddressFocused && canAutocomplete ? (
                    <div className="address-suggestions">
                      {isAddressLoading ? (
                        <div className="address-suggestion-muted">Recherche en cours…</div>
                      ) : null}
                      {!isAddressLoading && addressSuggestions.length > 0
                        ? addressSuggestions.map((s) => (
                            <button
                              key={`${s.label}-${s.lat}-${s.lon}`}
                              type="button"
                              className="address-suggestion-item"
                              onMouseDown={(e) => { e.preventDefault(); selectSuggestion(s); }}
                            >
                              {s.label}
                            </button>
                          ))
                        : null}
                      {!isAddressLoading && addressSuggestions.length === 0 && addressQuery.trim().length >= 3 ? (
                        <div className="address-suggestion-muted">Aucune suggestion pour cette saisie.</div>
                      ) : null}
                      {addressLookupError ? (
                        <div className="address-suggestion-error">{addressLookupError}</div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
                {!canAutocomplete && (
                  <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
                    Autocomplétion indisponible (token Mapbox manquant) — saisie libre activée.
                  </span>
                )}
              </label>

              {/* Météo */}
              <label className="field">
                <span>Météo</span>
                <select
                  value={sandbox.weather_key}
                  onChange={(e) => setSandbox((p) => ({ ...p, weather_key: e.target.value }))}
                >
                  <option value="real">🌍 Temps réel</option>
                  <option value="random">Aléatoire</option>
                  <option value="Clear">☀️ Soleil</option>
                  <option value="Rain">🌧️ Pluie</option>
                  <option value="Snow">❄️ Neige</option>
                  <option value="Thunderstorm">⛈️ Tempête</option>
                </select>
              </label>

              {/* Heure de départ */}
              <label className="field">
                <span>Heure de départ (trafic)</span>
                <select
                  value={sandbox.departure_hour ?? ""}
                  onChange={(e) =>
                    setSandbox((p) => ({
                      ...p,
                      departure_hour: e.target.value === "" ? null : Number(e.target.value),
                    }))
                  }
                >
                  <option value="">Sans congestion</option>
                  <option value="7">7h · ×1.4</option>
                  <option value="8">8h · Pointe matin ×1.7</option>
                  <option value="9">9h · ×1.5</option>
                  <option value="12">12h · Méridienne ×1.2</option>
                  <option value="13">13h · ×1.3</option>
                  <option value="17">17h · ×1.6</option>
                  <option value="18">18h · Pointe soir ×1.8</option>
                  <option value="19">19h · ×1.4</option>
                </select>
              </label>

              {/* Rayon de recherche */}
              <label className="field">
                <span>
                  Rayon de recherche&nbsp;
                  <strong style={{ color: "var(--accent-2)" }}>{sandbox.search_radius_km.toFixed(1)} km</strong>
                  &nbsp;· surface {areaKm2.toFixed(1)} km²
                </span>
                <input
                  type="range"
                  min={SEARCH_MIN_RADIUS_KM}
                  max={SEARCH_MAX_RADIUS_KM}
                  step={0.1}
                  value={sandbox.search_radius_km}
                  onChange={(e) => setSandbox((p) => ({ ...p, search_radius_km: Number(e.target.value) }))}
                  style={{ accentColor: "var(--accent)" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", color: "var(--muted)" }}>
                  <span>0.5 km</span><span>30 km</span>
                </div>
              </label>

              {/* Nombre de colis */}
              <label className="field">
                <span>
                  Nombre de colis&nbsp;
                  <strong style={{ color: exceedsClientsLimit ? "var(--accent)" : "var(--accent-2)" }}>
                    {requestedClients}
                  </strong>
                  &nbsp;/ max {maxClientsAllowed}
                </span>
                <input
                  type="number"
                  min={1}
                  max={SEARCH_MAX_CLIENTS}
                  value={requestedClients}
                  onChange={(e) => setSandbox((p) => ({ ...p, num_clients: Number(e.target.value) }))}
                />
                {exceedsClientsLimit && (
                  <span style={{ fontSize: "0.78rem", color: "var(--accent)" }}>
                    Dépasse la capacité de la zone. Augmente le rayon ou réduis le nombre.
                  </span>
                )}
              </label>

              {/* Budget */}
              <label className="field">
                <span>Budget (€)</span>
                <input
                  type="number"
                  min={0}
                  value={requestedBudget}
                  onChange={(e) => setSandbox((p) => ({ ...p, budget: Number(e.target.value) }))}
                />
              </label>

              {/* Coût traîneau */}
              <label className="field">
                <span>Coût par traîneau (€)</span>
                <input
                  type="number"
                  min={0}
                  value={requestedSleighCost}
                  onChange={(e) => setSandbox((p) => ({ ...p, sleigh_cost: Number(e.target.value) }))}
                />
              </label>

            </div>

            {/* Incidents + profil IA */}
            <label className="field">
              <span>Profil IA</span>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {PROFILES.map((p) => (
                  <button
                    key={p.key}
                    className={profile === p.key ? "primary-button" : "secondary-button"}
                    style={{ flex: "1 1 140px", textAlign: "left", lineHeight: 1.4 }}
                    onClick={() => setProfile(p.key)}
                  >
                    <div style={{ fontWeight: 700 }}>{p.label}</div>
                    <div style={{ fontSize: "0.78rem", opacity: 0.8, fontWeight: 400 }}>{p.desc}</div>
                  </button>
                ))}
              </div>
            </label>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <label className="tag" style={{ width: "fit-content" }}>
                <input
                  type="checkbox"
                  checked={sandbox.random_incidents}
                  onChange={(e) => setSandbox((p) => ({ ...p, random_incidents: e.target.checked }))}
                />
                &nbsp;Incidents aléatoires (routes bloquées, retards)
              </label>
              <label className="tag" style={{ width: "fit-content" }}>
                <input
                  type="checkbox"
                  checked={sandbox.with_elevation}
                  onChange={(e) => setSandbox((p) => ({ ...p, with_elevation: e.target.checked }))}
                />
                &nbsp;🏔️ Relief SRTM (pentes ajustent les temps)
              </label>
            </div>

            {/* Aperçu carte */}
            <SearchAreaMap centerLat={mapCenter.lat} centerLon={mapCenter.lon} radiusKm={sandbox.search_radius_km} />

            {/* Validation */}
            {exceedsClientsLimit ? (
              <div className="error-box">
                La zone actuelle autorise au maximum {maxClientsAllowed} colis. Réduis le nombre demandé ou augmente le rayon.
              </div>
            ) : !hasAddressSelection ? (
              <div className="error-box">
                Sélectionne une adresse dans la liste pour verrouiller le point central.
              </div>
            ) : (
              <div className="tag" style={{ width: "fit-content" }}>
                Zone valide · {selectedAddress.label}
              </div>
            )}

            {error && (
              <span style={{ color: "var(--accent)", fontSize: "0.9rem" }}>{error}</span>
            )}

            <button
              className="primary-button"
              style={{ alignSelf: "flex-start", fontSize: "1rem", padding: "14px 28px" }}
              disabled={!hasAddressSelection || exceedsClientsLimit}
              onClick={handleSolve}
            >
              Calculer la tournée optimale →
            </button>
          </section>
        )}

        {/* ── CHARGEMENT ── */}
        {step === "loading" && (
          <section className="panel stack">
            <strong>Le Père Noël prépare sa tournée…</strong>
            <div style={{ display: "grid", gap: 14, marginTop: 4 }}>
              {loadingSteps.map((s, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{
                    width: 24, height: 24, borderRadius: "50%", flexShrink: 0,
                    background: s.done ? "var(--success)" : "rgba(18,50,71,0.1)",
                    display: "grid", placeItems: "center",
                    fontSize: "0.75rem", fontWeight: 700, color: "white",
                    transition: "background 0.3s",
                  }}>
                    {s.done ? "✓" : i + 1}
                  </span>
                  <span style={{ color: s.done ? "var(--text)" : "var(--muted)", transition: "color 0.3s" }}>
                    {s.label}
                  </span>
                </div>
              ))}
            </div>
            <p className="muted" style={{ fontSize: "0.85rem" }}>
              Le graphe OSM est téléchargé depuis OpenStreetMap, la matrice de coût calculée par A*,
              puis OR-Tools résout le VRPTW avec fenêtres horaires.
            </p>
          </section>
        )}

        {/* ── RÉSULTAT ── */}
        {step === "result" && result && (
          <>
            <section
              className="panel"
              style={{
                position: "sticky",
                top: 10,
                zIndex: 20,
                background: "linear-gradient(120deg, rgba(16,46,70,0.96), rgba(31,122,86,0.92))",
                border: "1px solid rgba(255,255,255,0.14)",
                backdropFilter: "blur(10px)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "0.78rem", opacity: 0.78, letterSpacing: "0.06em" }}>PERFORMANCE TRACKER</div>
                  <div style={{ fontSize: "1.55rem", fontWeight: 900, fontFamily: "var(--font-display)" }}>
                    IA vs Glouton: {liveGainPct >= 0 ? "+" : ""}{liveGainPct.toFixed(1)}%
                  </div>
                  <div style={{ fontSize: "0.84rem", opacity: 0.9 }}>
                    Gain distance live: {formatKm(distanceSavedMeters)} économisés
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="tag">Référence soutenance: +13.6%</span>
                  <span className="tag" style={{ background: simulationBusy ? "rgba(255,180,113,0.2)" : "rgba(93,255,183,0.18)" }}>
                    {simulationBusy ? "Replan en cours…" : "Live"}
                  </span>
                </div>
              </div>
            </section>

            <section className="hero" style={{ background: "linear-gradient(135deg, #112b42 0%, #1f7a56 100%)" }}>
              <h2 style={{ fontFamily: "var(--font-display)", fontSize: "clamp(1.4rem,4vw,2.2rem)", margin: 0 }}>
                Tournée optimale calculée ✓
              </h2>
              <p style={{ marginTop: 8 }}>
                {selectedAddress?.label} · {requestedClients} colis · {activeTours.length} traîneau{activeTours.length > 1 ? "x" : ""} utilisé{activeTours.length > 1 ? "s" : ""}
              </p>
            </section>

            {/* ── SCORE ── */}
            {scoreData && (
              <section className="panel stack" style={{ alignItems: "center", textAlign: "center", gap: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap", justifyContent: "center" }}>
                  {/* Rang */}
                  <div style={{
                    width: 100, height: 100, borderRadius: "50%", flexShrink: 0,
                    background: `radial-gradient(circle at 35% 35%, ${scoreData.color}33, ${scoreData.color}99)`,
                    border: `3px solid ${scoreData.color}`,
                    display: "grid", placeItems: "center",
                    boxShadow: `0 0 32px ${scoreData.color}44`,
                  }}>
                    <span style={{ fontSize: "2.8rem", fontWeight: 900, color: scoreData.color, fontFamily: "var(--font-display)" }}>
                      {scoreData.rank}
                    </span>
                  </div>
                  {/* Score + titre */}
                  <div>
                    <div style={{ fontSize: "3.2rem", fontWeight: 900, color: scoreData.color, lineHeight: 1, fontFamily: "var(--font-display)" }}>
                      {scoreData.value}<span style={{ fontSize: "1.4rem", fontWeight: 600 }}>/100</span>
                    </div>
                    <div style={{ fontSize: "1.1rem", fontWeight: 600, marginTop: 4 }}>{scoreData.title}</div>
                  </div>
                </div>

                {/* Détail du score */}
                <div style={{ width: "100%", maxWidth: 480, display: "flex", flexDirection: "column", gap: 8 }}>
                  {[
                    { label: "Temps économisé (max 60 pts)", value: scoreData.breakdown.timeContribution, max: 60, color: "#1a6fb5" },
                    { label: "CO₂ économisé (max 25 pts)", value: scoreData.breakdown.co2Contribution, max: 25, color: "#1f7a56" },
                    { label: "Budget restant (max 15 pts)", value: scoreData.breakdown.budgetContribution, max: 15, color: "#b8892f" },
                  ].map(({ label, value, max, color }) => (
                    <div key={label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: "0.78rem", color: "var(--muted)", minWidth: 170, textAlign: "right" }}>{label}</span>
                      <div style={{ flex: 1, height: 8, borderRadius: 4, background: "rgba(18,50,71,0.1)", overflow: "hidden" }}>
                        <div style={{
                          height: "100%", borderRadius: 4, background: color,
                          width: `${Math.max(0, Math.min(100, (value / max) * 100))}%`,
                          transition: "width 0.6s ease",
                        }} />
                      </div>
                      <span style={{ fontSize: "0.82rem", fontWeight: 600, minWidth: 38 }}>{value.toFixed(0)}</span>
                    </div>
                  ))}
                  {(scoreData.breakdown.diffBonus + scoreData.breakdown.incidentBonus + scoreData.breakdown.weatherBonus) > 0 && (
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", marginTop: 4 }}>
                      {scoreData.breakdown.diffBonus > 0 && (
                        <span className="tag">Profil IA +{scoreData.breakdown.diffBonus} pts</span>
                      )}
                      {scoreData.breakdown.incidentBonus > 0 && (
                        <span className="tag">Incidents +{scoreData.breakdown.incidentBonus} pts</span>
                      )}
                      {scoreData.breakdown.weatherBonus > 0 && (
                        <span className="tag">Météo difficile +{scoreData.breakdown.weatherBonus} pts</span>
                      )}
                    </div>
                  )}
                </div>
              </section>
            )}

            <div className="grid-2" style={{ gap: 12 }}>
              {[
                { label: "Temps total", value: formatMin(totalTimeS), good: true },
                { label: "Distance totale", value: formatKm(totalDistM), good: true },
                { label: "Traîneaux utilisés", value: String(activeTours.length), good: true },
                { label: "Gain vs itinéraire naïf", value: savings ? `${savings.time_saved_pct}%` : "—", good: true },
                { label: "CO₂ économisé", value: savings ? `${savings.co2_saved_kg} kg` : "—", good: true },
                { label: "Colis non livrés", value: dropped.length === 0 ? "Aucun ✓" : String(dropped.length), good: dropped.length === 0 },
              ].map(({ label, value, good }) => (
                <div key={label} className={`metric-card ${good ? "is-good" : "is-bad"}`}>
                  <div className="metric-label">{label}</div>
                  <div className="metric-value">{value}</div>
                </div>
              ))}
            </div>

            {duplicateAssignments.length > 0 ? (
              <section className="panel stack" style={{ gap: 8 }}>
                <strong style={{ color: "var(--accent)" }}>⚠️ Doublons d’affectation détectés</strong>
                <span className="muted" style={{ fontSize: "0.84rem" }}>
                  Certains clients apparaissent dans plusieurs traîneaux: vérifie la mission/replan.
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {duplicateAssignments.map((item) => (
                    <span key={`dup-${item.clientId}`} className="tag">
                      Client #{item.clientId} ({item.clientName}) · Traîneaux {item.tours.join(", ")}
                    </span>
                  ))}
                </div>
              </section>
            ) : (
              <div className="tag" style={{ width: "fit-content" }}>
                Affectation clients cohérente: aucun doublon entre traîneaux.
              </div>
            )}

            <section className="panel stack" style={{ gap: 12 }}>
              <strong>Simulation Live · Incident + Replan</strong>
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                Injecte un incident visible sur la carte puis relance une replanification complète en un clic.
              </span>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                <label className="field" style={{ margin: 0, minWidth: 160 }}>
                  <span>Incidents</span>
                  <input
                    type="number"
                    min={1}
                    max={3}
                    value={incidentCount}
                    onChange={(e) => setIncidentCount(Math.max(1, Math.min(3, Number(e.target.value) || 1)))}
                    disabled={simulationBusy}
                  />
                </label>
                <button
                  className="primary-button"
                  onClick={handleIncidentReplan}
                  disabled={!canRunSimulation}
                  style={{ minHeight: 44 }}
                >
                  {simulationBusy ? "Simulation en cours…" : "Simuler incident + Replan"}
                </button>
                <span className="tag">{simulationStageLabel}</span>
                {!result?.solve?.ai_segments?.length ? (
                  <span className="muted" style={{ fontSize: "0.8rem" }}>
                    Solve initial requis avant la simulation.
                  </span>
                ) : null}
              </div>
              {simulationError ? (
                <div className="error-box">{simulationError}</div>
              ) : null}
              {simulationSummary ? (
                <div className="grid-2" style={{ gap: 8 }}>
                  <div className="metric-card">
                    <div className="metric-label">Temps total (avant → après)</div>
                    <div className="metric-value" style={{ fontSize: "1.05rem" }}>
                      {formatMin(simulationSummary.before.benchmark.optimized.total_time_s)} → {formatMin(simulationSummary.after.benchmark.optimized.total_time_s)}
                    </div>
                    <div className="muted" style={{ fontSize: "0.8rem" }}>
                      Δ {formatDeltaSeconds(simulationSummary.delta_kpi.time_s)} ({simulationSummary.delta_kpi.time_pct >= 0 ? "+" : ""}{simulationSummary.delta_kpi.time_pct.toFixed(1)}%)
                    </div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Distance (avant → après)</div>
                    <div className="metric-value" style={{ fontSize: "1.05rem" }}>
                      {formatKm(simulationSummary.before.benchmark.optimized.total_dist_m)} → {formatKm(simulationSummary.after.benchmark.optimized.total_dist_m)}
                    </div>
                    <div className="muted" style={{ fontSize: "0.8rem" }}>
                      Δ {formatDeltaDistance(simulationSummary.delta_kpi.dist_m)} ({simulationSummary.delta_kpi.dist_pct >= 0 ? "+" : ""}{simulationSummary.delta_kpi.dist_pct.toFixed(1)}%)
                    </div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">CO₂ économisé (avant → après)</div>
                    <div className="metric-value" style={{ fontSize: "1.05rem" }}>
                      {simulationSummary.before.benchmark.savings.co2_saved_kg.toFixed(2)} kg → {simulationSummary.after.benchmark.savings.co2_saved_kg.toFixed(2)} kg
                    </div>
                    <div className="muted" style={{ fontSize: "0.8rem" }}>
                      Δ {simulationSummary.delta_kpi.co2_kg >= 0 ? "+" : ""}{simulationSummary.delta_kpi.co2_kg.toFixed(2)} kg
                    </div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Incidents injectés</div>
                    <div className="metric-value" style={{ fontSize: "1.05rem" }}>
                      {simulationSummary.incidents.count}
                    </div>
                    <div className="muted" style={{ fontSize: "0.8rem" }}>
                      Segments bloqués affichés en rouge sur la carte.
                    </div>
                  </div>
                </div>
              ) : null}
            </section>

            <section className="panel stack">
              <strong>Détail par traîneau</strong>
              {activeTours.map((t) => {
                const stops = t.route_ids.filter((id) => id !== result.mission.depot.id);
                const color = SLEIGH_COLORS[t.vehicle_id % SLEIGH_COLORS.length];
                return (
                  <div key={t.vehicle_id} className="sleigh-row">
                    <span className="sleigh-row-id" style={{ background: color }}>#{t.vehicle_id + 1}</span>
                    <div className="sleigh-row-stats">
                      <span>{stops.length} colis</span>
                      <span>{formatMin(t.duration_s)}</span>
                      <span>{t.weight_kg.toFixed(0)} kg</span>
                    </div>
                  </div>
                );
              })}
            </section>

            <section className="panel" style={{ padding: 8 }}>
              <RouteMap
                key={`${result.mission.mission_id}-${mapRunId}`}
                depot={result.mission.depot}
                clients={result.mission.clients}
                segments={result.solve.ai_segments as RouteSegment[]}
                incidentSegments={liveIncidentSegments}
                autoPlayToken={mapRunId}
                tours={activeTours}
                centralityNodes={graphMetrics?.top_betweenness_nodes ?? []}
                onBlockSegment={handleManualBlock}
                blockBusy={simulationBusy}
              />
              <div style={{ display: "flex", gap: 14, flexWrap: "wrap", padding: "10px 10px 4px", fontSize: "0.82rem" }}>
                {activeTours.map((t) => (
                  <span key={t.vehicle_id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 12, height: 4, borderRadius: 2, background: SLEIGH_COLORS[t.vehicle_id % SLEIGH_COLORS.length], display: "inline-block" }} />
                    Traîneau {t.vehicle_id + 1}
                  </span>
                ))}
                <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--muted)" }}>
                  <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#17324d", display: "inline-block" }} />
                  Dépôt
                </span>
              </div>
            </section>

            <section className="panel stack">
              <strong>Pourquoi cette route ?</strong>
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                Explication segment par segment selon quatre critères: temps, congestion, capacité, fenêtre horaire.
              </span>
              {segmentExplanations.length === 0 && (
                <div className="muted" style={{ fontSize: "0.85rem" }}>
                  Aucune explication segment disponible pour cette tournée (recalcule la mission pour régénérer le détail).
                </div>
              )}
              {activeTours.map((tour) => {
                const sleighExplanations = explanationsBySleigh.get(tour.vehicle_id) ?? [];
                if (!sleighExplanations.length) return null;
                return (
                  <div key={`why-${tour.vehicle_id}`} className="stack" style={{ gap: 8 }}>
                    <span className="tag" style={{ width: "fit-content" }}>Traîneau {tour.vehicle_id + 1}</span>
                    {sleighExplanations.map((item) => (
                      <div key={item.key} className="metric-card sr-visible" style={{ padding: 12 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                          <strong style={{ fontSize: "0.92rem" }}>
                            {item.fromLabel} → {item.toLabel}
                          </strong>
                          <span className="tag">{item.primaryReason}</span>
                        </div>
                        <div className="muted" style={{ fontSize: "0.84rem", marginTop: 6 }}>{item.details}</div>
                        {item.badges.length > 0 && (
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                            {item.badges.map((badge) => (
                              <span key={`${item.key}-${badge}`} className="tag" style={{ fontSize: "0.76rem" }}>
                                {badge}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                );
              })}
            </section>

            {result.mission.elevation && (
              <section className="panel stack">
                <strong>🏔️ Relief SRTM intégré</strong>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {[
                    { label: "Altitude min", value: `${result.mission.elevation.min_m} m` },
                    { label: "Altitude max", value: `${result.mission.elevation.max_m} m` },
                    { label: "Dénivelé positif", value: `+${result.mission.elevation.total_climb_m} m` },
                    { label: "Dénivelé négatif", value: `−${result.mission.elevation.total_descent_m} m` },
                    { label: "Terrain", value: result.mission.elevation.terrain_type },
                    { label: "Surcoût temps pente", value: `+${result.mission.elevation.time_overhead_pct}%` },
                  ].map(({ label, value }) => (
                    <div key={label} className="metric-card" style={{ flex: "1 1 120px", padding: "10px 14px" }}>
                      <div className="metric-label">{label}</div>
                      <div className="metric-value" style={{ fontSize: "1.1rem" }}>{value}</div>
                    </div>
                  ))}
                </div>
                <p style={{ fontSize: "0.82rem", color: "var(--muted)", margin: 0 }}>
                  Source : <strong>SRTM 90 m</strong> (NASA / CGIAR-CSI) via OpenTopoData — données open data, aucune clé requise.
                  Les arêtes du graphe routier ont été pondérées par la pente : montée → +80% de temps max, descente → −20%.
                </p>
              </section>
            )}

            <section className="panel stack">
              <strong>Comment cette tournée a-t-elle été calculée ?</strong>
              <ol style={{ color: "var(--muted)", lineHeight: 2.2, paddingLeft: 22, margin: 0 }}>
                <li>Téléchargement du graphe routier OSM via <code>osmnx</code> autour de <em>{selectedAddress?.label}</em></li>
                <li>Génération aléatoire de {requestedClients} points dans un rayon de {sandbox.search_radius_km.toFixed(1)} km</li>
                {sandbox.with_elevation && <li>Altitudes SRTM récupérées via <strong>OpenTopoData</strong> — poids des arêtes ajustés selon la pente</li>}
                <li>Calcul de la matrice de coût n×n par <strong>A* bidirectionnel avec heuristique haversine</strong></li>
                <li>Résolution <strong>VRPTW</strong> par <strong>OR-Tools</strong> — {activeTours.length} traîneau{activeTours.length > 1 ? "x" : ""} sur {Math.ceil(requestedClients / 3)} autorisé{Math.ceil(requestedClients / 3) > 1 ? "s" : ""}</li>
                <li>Post-traitement <strong>ALNS + ILS + 2-opt + or-opt</strong> pour affiner la solution</li>
              </ol>
              <Link className="secondary-button" href="/explore" style={{ alignSelf: "flex-start" }}>
                Comprendre les algorithmes →
              </Link>
            </section>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button className="primary-button" onClick={reset}>← Nouvelle tournée</button>
              <Link className="secondary-button" href="/">Retour à l&apos;accueil</Link>
            </div>
          </>
        )}

        {step !== "result" && (
          <section className="panel stack">
            <Link className="secondary-button" href="/" style={{ alignSelf: "flex-start" }}>
              ← Retour à l&apos;accueil
            </Link>
          </section>
        )}

      </div>
    </div>
  );
}

function intOrZero(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.round(n) : 0;
}
