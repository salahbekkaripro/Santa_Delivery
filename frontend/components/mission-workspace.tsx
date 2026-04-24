"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  clearSleigh,
  evaluateAiLearning,
  getAdjacentNodes,
  getAiLearningRecommendation,
  getMission,
  getNearestNode,
  getRouteOptions,
  getVersusMatchState,
  resetHumanState,
  solveMission,
  solveMissionLearned,
  suggestNext,
  submitVersusAttempt,
  trainAiLearning,
  undoLastSegment,
  validateSegment
} from "@/lib/api";
import { MapSurface } from "@/components/map-surface";
import { usePlayer } from "@/components/player-provider";
import { getAiProfilePreview } from "@/lib/ai-profiles";
import type {
  AdjacentNode,
  AiLearningEvaluationResponse,
  AiLearningRecommendation,
  HumanState,
  RouteOption,
  RouteSegment
} from "@/lib/types";


function defaultHumanState(numVehicles = 3): HumanState {
  return {
    routes_by_sleigh: Object.fromEntries(Array.from({ length: numVehicles }, (_, index) => [String(index), []])),
    segments_by_sleigh: Object.fromEntries(Array.from({ length: numVehicles }, (_, index) => [String(index), []])),
    assigned_clients: [],
    live_stats: {}
  };
}

function flattenSegments(segmentsBySleigh: Record<string, RouteSegment[]>) {
  return Object.values(segmentsBySleigh).flat();
}

function metricTime(seconds: number | undefined) {
  const minutes = Math.round((seconds ?? 0) / 60);
  return `${minutes} min`;
}

function optionBadgeStyle(badge: string): CSSProperties {
  if (badge === "Sûr") {
    return {
      background: "rgba(31, 143, 95, 0.14)",
      color: "var(--success)",
      border: "1px solid rgba(31, 143, 95, 0.22)"
    };
  }
  if (
    badge.startsWith("Surcharge")
    || badge.startsWith("Retard")
    || badge === "Déjà assigné"
    || badge === "Axe incident"
  ) {
    return {
      background: "rgba(158, 47, 63, 0.12)",
      color: "#69222d",
      border: "1px solid rgba(158, 47, 63, 0.22)"
    };
  }
  return {
    background: "rgba(217, 119, 6, 0.12)",
    color: "var(--warning)",
    border: "1px solid rgba(217, 119, 6, 0.24)"
  };
}

function optionFeasibilityClass(option: RouteOption): string {
  if (option.is_feasible === false) return "is-infeasible";
  const badges = option.feasibility_badges ?? ["Sûr"];
  if (badges.every((b) => b === "Sûr")) return "is-feasible-good";
  return "is-warning-opt";
}

function weatherInfo(key: string): { icon: string; cls: string } {
  const map: Record<string, { icon: string; cls: string }> = {
    Clear:       { icon: "☀️", cls: "weather-clear" },
    Rain:        { icon: "🌧", cls: "weather-rain" },
    Snow:        { icon: "🌨", cls: "weather-snow" },
    Thunderstorm:{ icon: "⛈", cls: "weather-thunderstorm" },
  };
  return map[key] ?? { icon: "🌡", cls: "" };
}

function splitStrategyLabel(strategy?: string): string {
  if (!strategy) return "N/A";
  if (strategy === "stratified_by_context_profile") return "Stratifié contexte+profil";
  if (strategy === "stratified_by_context") return "Stratifié contexte";
  return strategy;
}

type LiveStat = Record<string, unknown> & {
  time_s?: number;
  dist_m?: number;
  over_kg?: number;
  load_kg?: number;
  return_time_s?: number;
  return_arrival_clock?: string | null;
  return_segment?: RouteSegment;
};

const ROUTE_OPTIONS_DEBOUNCE_MS = 180;
const SHOW_FEASIBLE_ONLY_STORAGE_KEY = "mission.show_feasible_only";

export function MissionWorkspace({ missionId }: { missionId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { player } = usePlayer();
  const queryClient = useQueryClient();
  const versusMatchId = searchParams.get("versus_match_id");
  const [numVehicles, setNumVehicles] = useState(3);
  const [vehicleCapacity, setVehicleCapacity] = useState(200);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);
  const [activeSleigh, setActiveSleigh] = useState(0);
  const [humanState, setHumanState] = useState<HumanState>(defaultHumanState());
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [selectedOptionIndex, setSelectedOptionIndex] = useState(0);
  const [routeOptions, setRouteOptions] = useState<RouteOption[]>([]);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [optimizationTarget, setOptimizationTarget] = useState<"time" | "distance">("time");
  const [suggestions, setSuggestions] = useState<Array<{ client_id: number; nom_client: string; arrival_clock: string; is_feasible: boolean }>>([]);
  const [isFreeRouting, setIsFreeRouting] = useState(false);
  const [showFeasibleOnly, setShowFeasibleOnly] = useState(false);
  const [showFeasibleOnlyHydrated, setShowFeasibleOnlyHydrated] = useState(false);
  const [isRouteOptionsDebouncing, setIsRouteOptionsDebouncing] = useState(false);
  const [useLearnedAi, setUseLearnedAi] = useState(false);
  const [learningRecommendation, setLearningRecommendation] = useState<AiLearningRecommendation | null>(null);
  const [learningEvaluation, setLearningEvaluation] = useState<AiLearningEvaluationResponse | null>(null);
  const [learningInfo, setLearningInfo] = useState<string | null>(null);

  const missionQuery = useQuery({
    queryKey: ["mission", missionId],
    queryFn: () => getMission(missionId)
  });
  const missionData = missionQuery.data;

  const versusStateQuery = useQuery({
    queryKey: ["versus-inline", versusMatchId, player?.id],
    queryFn: () => getVersusMatchState(versusMatchId!, player!.id),
    enabled: Boolean(versusMatchId && player?.id),
    refetchInterval: 1500,
  });
  const versusSelfState = versusStateQuery.data?.participants.find((participant) => participant.is_self)?.state;
  const versusLocked = versusSelfState === "submitted" || versusSelfState === "forfeit";

  const currentNodeId = useMemo(() => {
    if (!missionData) return 0;
    const routes = missionData.human_state?.routes_by_sleigh?.[String(activeSleigh)] ?? [];
    return routes.length > 0 ? routes[routes.length - 1] : 0;
  }, [missionData, activeSleigh]);

  const adjacentQuery = useQuery({
    queryKey: ["adjacents", missionId, currentNodeId, speedMultiplier],
    queryFn: () => getAdjacentNodes(missionId, currentNodeId, speedMultiplier),
    enabled: isFreeRouting && !!missionData
  });

  useEffect(() => {
    if (isFreeRouting && adjacentQuery.data?.adjacents) {
      adjacentQuery.data.adjacents.forEach((adj) => {
        queryClient.prefetchQuery({
          queryKey: ["adjacents", missionId, adj.node_id, speedMultiplier],
          queryFn: () => getAdjacentNodes(missionId, adj.node_id, speedMultiplier),
          staleTime: 60000,
        });
      });
    }
  }, [isFreeRouting, adjacentQuery.data, missionId, speedMultiplier, queryClient]);

  useEffect(() => {
    if (!missionData) return;
    const nextState = missionData.human_state ?? defaultHumanState();
    setHumanState(nextState);
    setNumVehicles(nextState.num_vehicles ?? 3);
    setVehicleCapacity(nextState.vehicle_capacity ?? 200);
    setSpeedMultiplier(nextState.speed_multiplier ?? 1);
    if (missionData.mission?.ai_profile) {
      setOptimizationTarget(getAiProfilePreview(missionData.mission.ai_profile).optimizationTarget);
    }
  }, [missionData]);

  useEffect(() => {
    try {
      const savedValue = window.localStorage.getItem(SHOW_FEASIBLE_ONLY_STORAGE_KEY);
      if (savedValue === "1" || savedValue === "true") {
        setShowFeasibleOnly(true);
      } else if (savedValue === "0" || savedValue === "false") {
        setShowFeasibleOnly(false);
      }
    } catch {
      // Ignore persistence errors (private mode, blocked storage, etc.)
    } finally {
      setShowFeasibleOnlyHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!showFeasibleOnlyHydrated) return;
    try {
      window.localStorage.setItem(SHOW_FEASIBLE_ONLY_STORAGE_KEY, showFeasibleOnly ? "1" : "0");
    } catch {
      // Ignore persistence errors (private mode, blocked storage, etc.)
    }
  }, [showFeasibleOnly, showFeasibleOnlyHydrated]);

  const mission = missionData;
  const humanSegments = useMemo(() => flattenSegments(humanState.segments_by_sleigh), [humanState]);
  const activeRoute = humanState.routes_by_sleigh[String(activeSleigh)] ?? [];
  const activeSegments = humanState.segments_by_sleigh[String(activeSleigh)] ?? [];
  const currentFromId = activeRoute.at(-1) ?? 0;
  const displayedRouteOptions = useMemo(
    () => (showFeasibleOnly ? routeOptions.filter((option) => option.is_feasible !== false) : routeOptions),
    [routeOptions, showFeasibleOnly]
  );

  useEffect(() => {
    if (selectedOptionIndex >= displayedRouteOptions.length) {
      setSelectedOptionIndex(0);
    }
  }, [selectedOptionIndex, displayedRouteOptions.length]);

  type RouteOptionsPayload = { from_id: number; to_id: number; sleigh_id: number; speed_multiplier: number; vehicle_capacity: number };

  function routeOptionsQueryKey(payload: RouteOptionsPayload) {
    return [
      "route-options",
      missionId,
      payload.sleigh_id,
      payload.from_id,
      payload.to_id,
      payload.speed_multiplier,
      payload.vehicle_capacity,
    ] as const;
  }

  async function fetchRouteOptionsCached(payload: RouteOptionsPayload) {
    return queryClient.fetchQuery({
      queryKey: routeOptionsQueryKey(payload),
      queryFn: () => getRouteOptions(missionId, payload),
      staleTime: 120_000,
    });
  }

  const optionsMutation = useMutation({
    mutationFn: (payload: RouteOptionsPayload) => fetchRouteOptionsCached(payload),
    onSuccess: (data) => {
      setRouteOptions(data.options);
      const firstFeasibleIndex = data.options.findIndex((option) => option.is_feasible !== false);
      setSelectedOptionIndex(showFeasibleOnly ? 0 : (firstFeasibleIndex >= 0 ? firstFeasibleIndex : 0));
      setRouteError(null);
    },
    onError: (error: Error) => setRouteError(error.message)
  });
  const mutateRouteOptions = optionsMutation.mutate;

  const validateMutation = useMutation({
    mutationFn: (option: RouteOption) =>
      validateSegment(missionId, {
        sleigh_id: activeSleigh,
        from_id: humanState.routes_by_sleigh[String(activeSleigh)]?.at(-1) ?? 0,
        to_id: selectedClientId ?? 0,
        selected_route: option,
        speed_multiplier: speedMultiplier,
        vehicle_capacity: vehicleCapacity,
        num_vehicles: numVehicles
      }),
    onSuccess: (nextState) => {
      setHumanState(nextState);
      setSelectedClientId(null);
      setRouteOptions([]);
      setSelectedOptionIndex(0);
      queryClient.invalidateQueries({ queryKey: ["mission", missionId] });
      queryClient.invalidateQueries({ queryKey: ["adjacents"] });
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const solveMutation = useMutation({
    mutationFn: () =>
      (useLearnedAi ? solveMissionLearned : solveMission)(missionId, {
          num_vehicles: numVehicles,
          vehicle_capacity: vehicleCapacity,
          speed_multiplier: speedMultiplier,
          optimization_target: optimizationTarget
        }),
    onSuccess: () => {
      setRouteError(null);
      queryClient.invalidateQueries({ queryKey: ["mission", missionId] });
      router.push(`/mission/${missionId}/results`);
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const trainLearningMutation = useMutation({
    mutationFn: () => trainAiLearning(1000),
    onSuccess: (summary) => {
      setLearningEvaluation(null);
      setLearningInfo(`Modèle entraîné: ${summary.sample_count} échantillons · ${summary.context_count} contextes`);
      setRouteError(null);
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const recommendationMutation = useMutation({
    mutationFn: () => getAiLearningRecommendation(missionId),
    onSuccess: (payload) => {
      setLearningRecommendation(payload.recommendation);
      setLearningInfo(
        `Profil recommandé: ${payload.recommendation.label} · confiance ${(payload.recommendation.confidence * 100).toFixed(0)}%`
      );
      setRouteError(null);
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const evaluateLearningMutation = useMutation({
    mutationFn: () => evaluateAiLearning(800, 0.25),
    onSuccess: (evaluation) => {
      setLearningEvaluation(evaluation);
      setLearningInfo(
        `Évaluation (${splitStrategyLabel(evaluation.split_strategy)}): top-1 ${(evaluation.context_top1_accuracy * 100).toFixed(0)}% · regret ${evaluation.avg_context_regret.toFixed(1)}`
      );
      setRouteError(null);
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const undoMutation = useMutation({
    mutationFn: () =>
      undoLastSegment(missionId, {
        sleigh_id: activeSleigh,
        speed_multiplier: speedMultiplier,
        vehicle_capacity: vehicleCapacity,
        num_vehicles: numVehicles
      }),
    onSuccess: (nextState) => {
      setHumanState(nextState);
      setRouteError(null);
      setSelectedClientId(null);
      setRouteOptions([]);
      queryClient.invalidateQueries({ queryKey: ["adjacents"] });
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const clearMutation = useMutation({
    mutationFn: () =>
      clearSleigh(missionId, {
        sleigh_id: activeSleigh,
        speed_multiplier: speedMultiplier,
        vehicle_capacity: vehicleCapacity,
        num_vehicles: numVehicles
      }),
    onSuccess: (nextState) => {
      setHumanState(nextState);
      setRouteError(null);
      setSelectedClientId(null);
      setRouteOptions([]);
      queryClient.invalidateQueries({ queryKey: ["adjacents"] });
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const resetMutation = useMutation({
    mutationFn: () =>
      resetHumanState(missionId, {
        speed_multiplier: speedMultiplier,
        vehicle_capacity: vehicleCapacity,
        num_vehicles: numVehicles
      }),
    onSuccess: (nextState) => {
      setHumanState(nextState);
      setRouteError(null);
      setSelectedClientId(null);
      setRouteOptions([]);
      setSuggestions([]);
      setActiveSleigh(0);
      queryClient.invalidateQueries({ queryKey: ["adjacents"] });
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const suggestMutation = useMutation({
    mutationFn: () => suggestNext(missionId, { sleigh_id: activeSleigh }),
    onSuccess: (data) => {
      setSuggestions(data.suggestions);
      const fromId = currentFromId;
      data.suggestions.slice(0, 3).forEach((suggestion) => {
        const payload = {
          from_id: fromId,
          to_id: suggestion.client_id,
          sleigh_id: activeSleigh,
          speed_multiplier: speedMultiplier,
          vehicle_capacity: vehicleCapacity,
        };
        queryClient.prefetchQuery({
          queryKey: routeOptionsQueryKey(payload),
          queryFn: () => getRouteOptions(missionId, payload),
          staleTime: 120_000,
        });
      });
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const nearestNodeMutation = useMutation({
    mutationFn: (coords: { lat: number; lon: number }) => getNearestNode(missionId, coords.lat, coords.lon),
    onSuccess: (data) => {
      setRouteOptions([]);
      setSelectedOptionIndex(0);
      setRouteError(null);
      setSelectedClientId(data.node_id);
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  function handleMapClick(lat: number, lon: number) {
    if (!isFreeRouting || versusLocked) return;
    nearestNodeMutation.mutate({ lat, lon });
  }

  function handleAdjacentNodeSelect(node: AdjacentNode) {
    if (versusLocked) return;
    setSelectedClientId(node.node_id);
    validateMutation.mutate({
      route_nodes: [currentNodeId, node.node_id],
      geometry: node.geometry,
      dist_m: node.dist_m,
      base_time_s: node.time_s,
      time_s: node.time_s,
      label: node.label
    });
  }

  function handleClientSelect(clientId: number) {
    if (!mission || versusLocked) return;
    if (humanState.assigned_clients.includes(clientId)) return;
    setRouteOptions([]);
    setSelectedOptionIndex(0);
    setRouteError(null);
    setSelectedClientId(clientId);
  }

  const routeOptionsPayload = useMemo<RouteOptionsPayload | null>(() => {
    if (selectedClientId === null) return null;
    if (!missionQuery.isSuccess) return null;
    if (humanState.assigned_clients.includes(selectedClientId)) return null;
    return {
      from_id: currentFromId,
      to_id: selectedClientId,
      sleigh_id: activeSleigh,
      speed_multiplier: speedMultiplier,
      vehicle_capacity: vehicleCapacity,
    };
  }, [
    selectedClientId,
    missionQuery.isSuccess,
    humanState.assigned_clients,
    currentFromId,
    activeSleigh,
    speedMultiplier,
    vehicleCapacity,
  ]);

  const versusSubmitMutation = useMutation({
    mutationFn: () => submitVersusAttempt(versusMatchId!, { player_id: player!.id }),
    onSuccess: () => {
      if (versusMatchId) {
        router.push(`/versus/match/${versusMatchId}`);
      }
    },
    onError: (error: Error) => setRouteError(error.message),
  });

  useEffect(() => {
    if (!routeOptionsPayload) {
      setIsRouteOptionsDebouncing(false);
      return;
    }
    setIsRouteOptionsDebouncing(true);
    const timeoutId = window.setTimeout(() => {
      setIsRouteOptionsDebouncing(false);
      mutateRouteOptions(routeOptionsPayload);
    }, ROUTE_OPTIONS_DEBOUNCE_MS);
    return () => window.clearTimeout(timeoutId);
  }, [routeOptionsPayload, mutateRouteOptions]);

  if (missionQuery.isLoading) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="hero" style={{ height: 120 }}>
            <div className="skeleton-bar h-lg w-60" style={{ marginBottom: 12 }} />
            <div className="skeleton-bar h-sm w-80" />
          </div>
          <div className="mission-skeleton">
            <div className="mission-skeleton-side">
              {[...Array(8)].map((_, i) => (
                <div key={i} className={`skeleton-bar h-md ${i % 3 === 0 ? "w-60" : "w-full"}`} style={{ animationDelay: `${i * 0.08}s` }} />
              ))}
            </div>
            <div className="mission-skeleton-map" />
          </div>
        </div>
      </div>
    );
  }

  if (missionQuery.error || !mission) {
    return <div className="page-shell error-box">{String(missionQuery.error instanceof Error ? missionQuery.error.message : "Mission introuvable")}</div>;
  }

  const liveStats = (humanState.live_stats ?? {}) as Record<string, LiveStat>;
  const totalHumanTimeS = Object.values(liveStats).reduce((sum, stats) => sum + Number(stats.time_s ?? 0), 0);
  const totalHumanDistM = Object.values(liveStats).reduce((sum, stats) => sum + Number(stats.dist_m ?? 0), 0);
  const overloadedSleighs = Object.entries(liveStats)
    .filter(([, stats]) => Number(stats.over_kg ?? 0) > 0)
    .map(([key]) => Number(key) + 1);
  const returnSegments = Object.values(liveStats)
    .map((stats) => stats.return_segment)
    .filter((segment): segment is RouteSegment => Boolean(segment));
  const incidentSegments = mission.incidents?.segments ?? [];
  const stopMetaByClient = humanState.stop_meta_by_client ?? {};
  const aiProfilePreview = getAiProfilePreview(mission.mission.ai_profile);
  const aiProfileLocked = Boolean(mission.mission.ai_profile);
  const secondaryObjectives = mission.mission.secondary_objectives ?? [];
  const selectedRouteOption = displayedRouteOptions[selectedOptionIndex];
  const selectedRouteIsFeasible = selectedRouteOption ? selectedRouteOption.is_feasible !== false : false;
  const weather = weatherInfo(String(mission.weather?.desc ?? mission.mission.weather_key));
  const progressPct = mission.clients.length > 0 ? (humanState.assigned_clients.length / mission.clients.length) * 100 : 0;

  return (
    <div className="page-shell">
      <div className="page-stack">

        {/* HERO */}
        <section className="hero">
          <h1>{mission.mission.zone}</h1>
          <div className="hero-badges">
            <span className={`hero-badge ${weather.cls}`}>
              {weather.icon} {String(mission.weather?.desc ?? mission.mission.weather_key)}
            </span>
            <span className="hero-badge">
              {mission.mission.level ? `Niveau ${mission.mission.level}` : "Sandbox"}
            </span>
            <span className="hero-badge">
              IA {aiProfilePreview.label} · +{aiProfilePreview.difficultyBonus} score
            </span>
            <span className="hero-badge">
              {mission.clients.length} clients · {mission.mission.budget} €
            </span>
            {overloadedSleighs.length > 0 && (
              <span className="hero-badge incident-badge">
                ⚠️ Surcharge #{overloadedSleighs.join(", #")}
              </span>
            )}
          </div>
          <div className="hero-progress">
            <div className="hero-progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <p className="hero-progress-label">
            {humanState.assigned_clients.length} / {mission.clients.length} clients assignés
          </p>
        </section>

        {/* METRICS */}
        <div className="grid-4">
          <div className="metric-card">
            <div className="metric-label">Temps estimé</div>
            <div className="metric-value">{metricTime(totalHumanTimeS)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Distance</div>
            <div className="metric-value">{(totalHumanDistM / 1000).toFixed(2)} km</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Clients assignés</div>
            <div className="metric-value">{humanState.assigned_clients.length} / {mission.clients.length}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Budget restant</div>
            <div className="metric-value">{mission.mission.budget} €</div>
          </div>
        </div>

        {mission.incidents && mission.incidents.count > 0 && (
          <div className="error-box">
            ⚠️ Incidents actifs : {mission.incidents.count} axe(s) bloqué(s) — visible sur la carte.
          </div>
        )}

        {versusMatchId && (
          <section className="panel stack">
            <div className="panel-head">
              <strong>⚔️ Duel Versus</strong>
              <span className="tag">Match {versusMatchId}</span>
            </div>
            <span className="muted">
              État duel: {versusSelfState ?? "inconnu"} · Soumission valide requise: tous les clients assignés.
            </span>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                className="primary-button"
                onClick={() => versusSubmitMutation.mutate()}
                disabled={!player || !versusMatchId || versusSubmitMutation.isPending || versusLocked}
              >
                {versusSubmitMutation.isPending ? "Soumission..." : versusLocked ? "Tentative soumise" : "Soumettre ma tentative"}
              </button>
              <Link className="secondary-button" href={`/versus/match/${versusMatchId}`}>
                Retour au match live
              </Link>
            </div>
          </section>
        )}

        <div className="mission-layout">
          {/* SIDEBAR */}
          <aside className="panel stack">

            {/* SECTION : CONFIGURATION */}
            <div>
              <span className="sidebar-section-title">Configuration</span>
            </div>
            <label className="field">
              <span>Traîneaux</span>
              <input type="number" min={1} max={10} value={numVehicles} onChange={(e) => setNumVehicles(Number(e.target.value))} />
            </label>
            <label className="field">
              <span>Capacité (kg)</span>
              <input type="number" min={50} max={500} value={vehicleCapacity} onChange={(e) => setVehicleCapacity(Number(e.target.value))} />
            </label>
            <label className="field">
              <span>Vitesse</span>
              <select value={speedMultiplier} onChange={(e) => setSpeedMultiplier(Number(e.target.value))}>
                <option value={0.7}>🐢 Prudent</option>
                <option value={1}>🚗 Normal</option>
                <option value={1.5}>🚀 Turbo</option>
              </select>
            </label>

            <div className="field">
              <span>Traîneau actif</span>
              <div className="sleigh-tab-group">
                {Array.from({ length: numVehicles }, (_, i) => (
                  <button
                    key={i}
                    className={`sleigh-tab ${activeSleigh === i ? "is-active" : ""}`}
                    onClick={() => setActiveSleigh(i)}
                    disabled={versusLocked}
                  >
                    🎅 #{i + 1}
                  </button>
                ))}
              </div>
            </div>

            <label className="field">
              <span>Objectif IA</span>
              <select
                value={aiProfileLocked ? aiProfilePreview.optimizationTarget : optimizationTarget}
                disabled={aiProfileLocked}
                onChange={(e) => setOptimizationTarget(e.target.value as "time" | "distance")}
              >
                <option value="time">⚡ Express (Temps)</option>
                <option value="distance">🌱 Écolo (Distance)</option>
              </select>
            </label>

            {/* SECTION : PROFIL IA */}
            <div className={`sidebar-section ai-profile-card ${aiProfilePreview.accentClass}`}>
              <span className="sidebar-section-title">Profil IA</span>
              <div className="ai-profile-head">
                <div>
                  <strong>IA {aiProfilePreview.label}</strong>
                  <span className="muted">{aiProfilePreview.signature}</span>
                </div>
                <span className="tag">+{aiProfilePreview.difficultyBonus} score</span>
              </div>
              <p className="muted">{aiProfilePreview.description}</p>
              <div className="ai-profile-meta">
                <span>Cible : {aiProfilePreview.optimizationTarget === "time" ? "temps" : "distance"}</span>
                <span className="muted">{aiProfileLocked ? "Verrouillé" : "Libre"}</span>
              </div>
            </div>

            {secondaryObjectives.length > 0 && (
              <div className="sidebar-section">
                <span className="sidebar-section-title">Objectifs secondaires</span>
                <div className="objective-list">
                  {secondaryObjectives.map((obj) => (
                    <div key={`${obj.code}-${obj.label}`} className="objective-chip">
                      <span className="objective-dot" />
                      <span>{obj.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SECTION : MODE DE SÉLECTION */}
            <div className="sidebar-section">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="sidebar-section-title">Mode de sélection</span>
                <button
                  className={`tag ${isFreeRouting ? "is-selected" : ""}`}
                  style={{ cursor: "pointer", background: isFreeRouting ? "var(--accent)" : "rgba(0,0,0,0.05)", color: isFreeRouting ? "white" : "var(--text)" }}
                  onClick={() => {
                    if (versusLocked) return;
                    setIsFreeRouting(!isFreeRouting);
                    setSelectedClientId(null);
                    setRouteOptions([]);
                  }}
                  disabled={versusLocked}
                >
                  {isFreeRouting ? "🗺️ Tracé Libre" : "📍 Sélection"}
                </button>
              </div>
              <span className="muted" style={{ fontSize: "0.83rem" }}>
                {isFreeRouting
                  ? "Clique n'importe où sur la carte pour tracer ta route segment par segment."
                  : "Clique un client sur la carte pour voir les options de chemins."}
              </span>
              {!isFreeRouting && (
                <button
                  className={`tag ${showFeasibleOnly ? "is-selected" : ""}`}
                  style={{
                    cursor: "pointer",
                    width: "fit-content",
                    background: showFeasibleOnly ? "rgba(31, 143, 95, 0.16)" : "rgba(23, 50, 77, 0.08)",
                    color: showFeasibleOnly ? "var(--success)" : "var(--accent-2)",
                    border: showFeasibleOnly ? "1px solid rgba(31, 143, 95, 0.32)" : "1px solid var(--border)"
                  }}
                  onClick={() => {
                    if (versusLocked) return;
                    setShowFeasibleOnly((previous) => !previous);
                    setSelectedOptionIndex(0);
                  }}
                  disabled={versusLocked}
                >
                  {showFeasibleOnly ? "Faisables uniquement: ON" : "Faisables uniquement: OFF"}
                </button>
              )}
              <button className="secondary-button" onClick={() => suggestMutation.mutate()} disabled={suggestMutation.isPending || versusLocked}>
                {suggestMutation.isPending ? "Calcul..." : "💡 Suggérer le prochain stop"}
              </button>
              {suggestions.length > 0 && (
                <div className="stack" style={{ gap: "6px" }}>
                  {suggestions.map((s) => (
                    <button
                      key={s.client_id}
                      className={`tag ${!s.is_feasible ? "error-box" : ""}`}
                      style={{ cursor: "pointer", border: "1px solid var(--border)", width: "100%", justifyContent: "space-between" }}
                      onClick={() => handleClientSelect(s.client_id)}
                      disabled={!s.is_feasible || versusLocked}
                    >
                      <span>{s.nom_client}</span>
                      <span className="muted">{s.arrival_clock}</span>
                    </button>
                  ))}
                  <button className="secondary-button" style={{ fontSize: "0.78rem", padding: "6px" }} onClick={() => setSuggestions([])}>
                    Effacer suggestions
                  </button>
                </div>
              )}
            </div>

            {/* SECTION : ROUTE COURANTE & ETA */}
            <div className="sidebar-section">
              <span className="sidebar-section-title">Route courante — Traîneau #{activeSleigh + 1}</span>
              <span className="muted" style={{ fontSize: "0.83rem", lineHeight: 1.5 }}>
                {activeRoute.length > 0
                  ? activeRoute.map((id) => mission.clients.find((c) => c.id === id)?.nom_client ?? `#${id}`).join(" → ")
                  : "Aucun stop sur ce traîneau"}
              </span>
              {activeSegments.length > 0 && (
                <div className="stack" style={{ gap: "6px" }}>
                  {activeSegments.map((seg) => {
                    const client = mission.clients.find((c) => c.id === seg.to_id);
                    if (!client) return null;
                    return (
                      <span key={`${seg.from_id}-${seg.to_id}`} className="muted" style={{ fontSize: "0.82rem" }}>
                        Stop {seg.segment_idx} · {client.nom_client} · {seg.arrival_clock ?? "--:--"} · {metricTime(seg.arrival_eta_s)}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Erreurs */}
            {routeError && <div className="error-box">{routeError}</div>}

            {/* SECTION : OPTIONS DE ROUTE */}
            {selectedClientId ? (
              <div className="sidebar-section">
                <span className="sidebar-section-title">
                  Options — Client #{selectedClientId}
                </span>
                {(isRouteOptionsDebouncing || optionsMutation.isPending) && (
                  <span className="muted" style={{ fontSize: "0.83rem" }}>
                    {isRouteOptionsDebouncing ? "Recalcul…" : "Calcul des options…"}
                  </span>
                )}
                {showFeasibleOnly && routeOptions.length > 0 && displayedRouteOptions.length === 0 && (
                  <div className="error-box">Aucune option faisable pour ce client avec les paramètres actuels.</div>
                )}
                {displayedRouteOptions.map((option, index) => (
                  <button
                    key={`${option.route_nodes.join("-")}-${index}`}
                    className={`option-card ${selectedOptionIndex === index ? "is-selected" : ""} ${optionFeasibilityClass(option)}`}
                    onClick={() => setSelectedOptionIndex(index)}
                  >
                    <strong>{option.label}</strong>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
                      {(option.feasibility_badges ?? ["Sûr"]).map((badge) => (
                        <span key={`${option.label}-${badge}`} className="tag" style={optionBadgeStyle(badge)}>
                          {badge}
                        </span>
                      ))}
                    </div>
                    <div className="muted" style={{ fontSize: "0.82rem", marginTop: 6 }}>
                      {option.route_nodes.length} nœuds · Arrivée {option.projected_arrival_clock ?? "--:--"} · {Number(option.projected_load_kg ?? 0).toFixed(0)} kg
                    </div>
                    {Number(option.projected_overload_kg ?? 0) > 0 && (
                      <div style={{ color: "#69222d", fontSize: "0.82rem" }}>
                        Dépassement : +{Number(option.projected_overload_kg ?? 0).toFixed(0)} kg
                      </div>
                    )}
                  </button>
                ))}
                {displayedRouteOptions.length > 0 && (
                  <>
                    {selectedRouteOption && !selectedRouteIsFeasible && (
                      <div className="error-box">
                        Option non faisable : {(selectedRouteOption.feasibility_badges ?? ["Risque"]).join(", ")}.
                      </div>
                    )}
                    <button
                      className="primary-button"
                    onClick={() => { if (!selectedRouteOption || !selectedRouteIsFeasible) return; validateMutation.mutate(selectedRouteOption); }}
                      disabled={validateMutation.isPending || !selectedRouteOption || !selectedRouteIsFeasible || versusLocked}
                    >
                      {validateMutation.isPending ? "Validation…" : "✓ Valider ce segment"}
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => { setSelectedClientId(null); setRouteOptions([]); setSelectedOptionIndex(0); setRouteError(null); }}
                    >
                      Annuler ce choix
                    </button>
                  </>
                )}
              </div>
            ) : (
              <div className="sidebar-section">
                <span className="muted" style={{ fontSize: "0.83rem" }}>Aucun client sélectionné — clique un client sur la carte.</span>
              </div>
            )}

            {/* SECTION : ACTIONS */}
            <div className="sidebar-section">
              <span className="sidebar-section-title">Actions</span>
              <button className="secondary-button" onClick={() => undoMutation.mutate()} disabled={undoMutation.isPending || versusLocked}>
                {undoMutation.isPending ? "Annulation…" : "↩ Annuler dernier segment"}
              </button>
              <button className="secondary-button" onClick={() => clearMutation.mutate()} disabled={clearMutation.isPending || versusLocked}>
                {clearMutation.isPending ? "Vidage…" : "🗑 Vider ce traîneau"}
              </button>
              <button className="secondary-button" onClick={() => resetMutation.mutate()} disabled={resetMutation.isPending || versusLocked}>
                {resetMutation.isPending ? "Reset…" : "↺ Réinitialiser tout"}
              </button>
            </div>

            {/* SOLVE ZONE */}
            <div className="solve-zone">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
                <div>
                  <strong style={{ color: "var(--accent-2)" }}>Lancer l&apos;IA</strong>
                  <p className="muted" style={{ fontSize: "0.8rem", margin: "4px 0 0" }}>
                    {aiProfileLocked
                      ? `Profil ${aiProfilePreview.label} imposé · ${aiProfilePreview.signature}`
                      : aiProfilePreview.optimizationTarget === "time"
                        ? "L'IA cherchera à finir le plus vite possible."
                        : "L'IA parcourra le moins de km possible."}
                  </p>
                </div>
                <span className="tag">+{aiProfilePreview.difficultyBonus}</span>
              </div>
              <label
                className="tag"
                style={{
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  width: "fit-content",
                  border: "1px solid var(--border)",
                  background: useLearnedAi ? "rgba(23, 50, 77, 0.10)" : "rgba(0, 0, 0, 0.04)"
                }}
              >
                <input
                  type="checkbox"
                  checked={useLearnedAi}
                  onChange={(event) => setUseLearnedAi(event.target.checked)}
                  style={{ accentColor: "var(--accent-2)" }}
                  disabled={versusLocked}
                />
                IA apprenante (profil auto)
              </label>
              {useLearnedAi && (
                <div className="stack" style={{ gap: 8 }}>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <button
                      className="secondary-button"
                      onClick={() => trainLearningMutation.mutate()}
                      disabled={trainLearningMutation.isPending || versusLocked}
                    >
                      {trainLearningMutation.isPending ? "Entraînement..." : "🧠 Entraîner le modèle"}
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => recommendationMutation.mutate()}
                      disabled={recommendationMutation.isPending || versusLocked}
                    >
                      {recommendationMutation.isPending ? "Calcul..." : "📊 Recommander un profil"}
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => evaluateLearningMutation.mutate()}
                      disabled={evaluateLearningMutation.isPending || versusLocked}
                    >
                      {evaluateLearningMutation.isPending ? "Évaluation..." : "🧪 Évaluer le modèle"}
                    </button>
                  </div>
                  {learningInfo && (
                    <span className="muted" style={{ fontSize: "0.8rem" }}>
                      {learningInfo}
                    </span>
                  )}
                  {learningEvaluation && (
                    <>
                      <span className="muted" style={{ fontSize: "0.8rem" }}>
                        Split: {splitStrategyLabel(learningEvaluation.split_strategy)} · Holdout: {learningEvaluation.sample_count_holdout} · Match sample: {(learningEvaluation.sample_match_rate * 100).toFixed(0)}%
                      </span>
                      <span className="muted" style={{ fontSize: "0.8rem" }}>
                        Top-1 contexte: {(learningEvaluation.context_top1_accuracy * 100).toFixed(0)}% · Regret: {learningEvaluation.avg_context_regret.toFixed(1)}
                      </span>
                    </>
                  )}
                  {learningRecommendation && (
                    <span className="muted" style={{ fontSize: "0.8rem" }}>
                      Top 3: {learningRecommendation.top_candidates.map((candidate) => candidate.label).join(" · ")}
                    </span>
                  )}
                </div>
              )}
              <button className="primary-button" onClick={() => solveMutation.mutate()} disabled={solveMutation.isPending || versusLocked}>
                {solveMutation.isPending
                  ? "Optimisation en cours…"
                  : useLearnedAi
                    ? "🤖 Lancer IA apprenante"
                    : "🤖 Lancer la solution IA"}
              </button>
              {mission.results_available && (
                <Link className="secondary-button" href={`/mission/${missionId}/results`}>
                  Voir les derniers résultats
                </Link>
              )}
            </div>
          </aside>

          {/* CARTE */}
          <section className="panel map-card">
            <div className="legend" style={{ marginBottom: 14 }}>
              <span className="legend-chip">
                <span className="line-dot is-dashed" style={{ color: "#9e2f3f" }} />
                Votre trace
              </span>
              <span className="legend-chip">
                <span className="line-dot is-dashed" style={{ color: "#0f766e" }} />
                Retour dépôt
              </span>
              {incidentSegments.length > 0 && (
                <span className="legend-chip">
                  <span className="line-dot is-dashed" style={{ color: "#991b1b" }} />
                  Incidents
                </span>
              )}
              {displayedRouteOptions.length > 0 && (
                <span className="legend-chip">
                  <span className="line-dot" style={{ color: "#b8892f" }} />
                  Option sélectionnée
                </span>
              )}
            </div>
            <MapSurface
              depot={mission.depot}
              clients={mission.clients}
              humanSegments={humanSegments}
              returnSegments={returnSegments}
              incidentSegments={incidentSegments}
              previewOptions={displayedRouteOptions.map((o) => ({
                geometry: o.geometry,
                label: o.label,
                dist_m: o.dist_m,
                time_s: o.time_s
              }))}
              selectedPreviewIndex={selectedOptionIndex}
              assignedClientIds={humanState.assigned_clients}
              humanStopMetaByClient={stopMetaByClient}
              onClientSelect={handleClientSelect}
              onMapClick={handleMapClick}
              adjacentOptions={isFreeRouting ? adjacentQuery.data?.adjacents : []}
              futureOptions={isFreeRouting ? adjacentQuery.data?.future_adjacents : []}
              onAdjacentSelect={handleAdjacentNodeSelect}
              selectedClientId={selectedClientId}
              showAi={false}
            />
          </section>
        </div>

        {/* VEHICLE STATS */}
        <section className="grid-3">
          {Array.from({ length: numVehicles }, (_, index) => {
            const stats = liveStats[String(index)] ?? {};
            const routeNames = (humanState.routes_by_sleigh[String(index)] ?? [])
              .map((id) => mission.clients.find((c) => c.id === id)?.nom_client ?? `#${id}`)
              .join(" → ");
            const isActive = index === activeSleigh;
            const loadPct = Math.min((Number(stats.load_kg ?? 0) / vehicleCapacity) * 100, 100);
            const isOverloaded = Number(stats.over_kg ?? 0) > 0;

            return (
              <div
                key={index}
                className={`panel stack vehicle-card ${isActive ? "is-active" : ""}`}
                style={{ cursor: "pointer" }}
                onClick={() => setActiveSleigh(index)}
              >
                <div className="vehicle-card-header">
                  <strong>🎅 Traîneau #{index + 1}</strong>
                  {isActive && <span className="vehicle-active-badge">ACTIF</span>}
                  {isOverloaded && <span className="vehicle-active-badge" style={{ background: "rgba(158, 47, 63,0.15)", color: "var(--accent)", borderColor: "rgba(158, 47, 63,0.3)" }}>⚠️ Surcharge</span>}
                </div>
                <div className="capacity-bar-container" title={`Charge : ${Number(stats.load_kg ?? 0).toFixed(0)} / ${vehicleCapacity} kg`}>
                  <div
                    className={`capacity-bar-fill ${isOverloaded ? "is-overloaded" : ""}`}
                    style={{ width: `${loadPct}%` }}
                  />
                </div>
                <div className="vehicle-grid-stats">
                  <span className="vehicle-stat"><strong>Stops</strong> {humanState.routes_by_sleigh[String(index)]?.length ?? 0}</span>
                  <span className="vehicle-stat"><strong>Charge</strong> {Number(stats.load_kg ?? 0).toFixed(0)} kg</span>
                  <span className="vehicle-stat"><strong>Temps</strong> {metricTime(Number(stats.time_s ?? 0))}</span>
                  <span className="vehicle-stat"><strong>Distance</strong> {(Number(stats.dist_m ?? 0) / 1000).toFixed(2)} km</span>
                  <span className="vehicle-stat" style={{ gridColumn: "1 / -1" }}>
                    <strong>Retour</strong> {metricTime(Number(stats.return_time_s ?? 0))}
                    {stats.return_arrival_clock ? ` · ${String(stats.return_arrival_clock)}` : ""}
                  </span>
                </div>
                {routeNames && <span className="muted" style={{ fontSize: "0.78rem", lineHeight: 1.45 }}>{routeNames}</span>}
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}
