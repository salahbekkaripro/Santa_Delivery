"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
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
import type { GuidedOnboardingStep } from "@/components/guided-onboarding";
import { usePlayer } from "@/components/player-provider";
import { getAiProfilePreview } from "@/lib/ai-profiles";
import { useVersusLiveState } from "@/lib/versus-live";
import type {
  AdjacentNode,
  AiLearningEvaluationResponse,
  AiLearningRecommendation,
  HumanState,
  MapInteractionState,
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

function routeOptionKey(option: RouteOption): string {
  return `${option.route_nodes.join("->")}|${Math.round(Number(option.time_s ?? 0))}|${Math.round(Number(option.dist_m ?? 0))}`;
}

function infeasibleRouteMessage(option: RouteOption): string {
  const badges = option.feasibility_badges ?? [];
  if (badges.length === 0) {
    return "Segment non faisable.";
  }
  return `Segment non faisable: ${badges.join(", ")}.`;
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

type ValidateRoutePayload = {
  option: RouteOption;
  fromId: number;
  toId: number;
};

const GuidedOnboarding = dynamic(
  () => import("@/components/guided-onboarding").then((mod) => mod.GuidedOnboarding),
  { ssr: false },
);

const MapSurface = dynamic(
  () => import("@/components/map-surface").then((mod) => mod.MapSurface),
  {
    ssr: false,
    loading: () => (
      <div
        className="panel-loading"
        style={{ height: "100%", minHeight: 520, borderRadius: 22 }}
        aria-label="Chargement de la carte"
      />
    ),
  },
);

const MissionSidebar = dynamic(
  () => import("@/components/mission-sidebar").then((mod) => mod.MissionSidebar),
  {
    ssr: false,
    loading: () => (
      <div className="panel-loading" style={{ minHeight: 720, borderRadius: 22 }} aria-label="Chargement du panneau mission" />
    ),
  },
);

const MissionVehicleStats = dynamic(
  () => import("@/components/mission-vehicle-stats").then((mod) => mod.MissionVehicleStats),
  {
    ssr: false,
    loading: () => (
      <div className="panel-loading" style={{ minHeight: 280, borderRadius: 22 }} aria-label="Chargement des stats véhicules" />
    ),
  },
);

const MissionHeroDuel = dynamic(
  () => import("@/components/mission-hero-duel").then((mod) => mod.MissionHeroDuel),
  {
    ssr: false,
    loading: () => (
      <div className="panel-loading" style={{ minHeight: 360, borderRadius: 22 }} aria-label="Chargement de l'entête mission" />
    ),
  },
);

const ROUTE_OPTIONS_DEBOUNCE_MS = 180;
const SHOW_FEASIBLE_ONLY_STORAGE_KEY = "mission.show_feasible_only";
const VERSUS_MISSION_ONBOARDING_STEPS: GuidedOnboardingStep[] = [
  {
    targetId: "versus-mission-hero",
    title: "Objectif de la mission versus",
    description: "Ta progression indique combien de clients sont déjà assignés. Il faut atteindre 100% avant soumission.",
  },
  {
    targetId: "versus-mission-map",
    title: "Planifie la tournée sur la carte",
    description: "Sélectionne des clients, choisis les segments faisables, puis valide pour construire ta route.",
  },
  {
    targetId: "versus-mission-duel-panel",
    title: "Panel de duel",
    description: "Ce bloc te rappelle l'état de ta tentative dans le match live.",
  },
  {
    targetId: "versus-mission-submit",
    title: "Soumettre ma tentative",
    description: "Envoie ta tentative une fois tous les clients assignés, puis retourne au lobby live.",
  },
  {
    targetId: "versus-mission-back",
    title: "Retour au match live",
    description: "Reviens au lobby pour suivre l'état de l'adversaire et le résultat final.",
  },
];

export function MissionWorkspace({ missionId }: { missionId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { player } = usePlayer();
  const queryClient = useQueryClient();
  const versusMatchId = searchParams.get("versus_match_id");
  const [numVehicles, setNumVehicles] = useState(3);
  const [limitMaxVehicles, setLimitMaxVehicles] = useState(false);
  const [maxVehicles, setMaxVehicles] = useState(3);
  const [vehicleCapacity, setVehicleCapacity] = useState(200);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);
  const [activeSleigh, setActiveSleigh] = useState(0);
  const [humanState, setHumanState] = useState<HumanState>(defaultHumanState());
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [selectedOptionIndex, setSelectedOptionIndex] = useState(0);
  const [routeOptions, setRouteOptions] = useState<RouteOption[]>([]);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [optimizationTarget, setOptimizationTarget] = useState<"time" | "distance" | "composite">("composite");
  const [suggestions, setSuggestions] = useState<Array<{ client_id: number; nom_client: string; arrival_clock: string; is_feasible: boolean }>>([]);
  const [isFreeRouting, setIsFreeRouting] = useState(false);
  const [showFeasibleOnly, setShowFeasibleOnly] = useState(false);
  const [showFeasibleOnlyHydrated, setShowFeasibleOnlyHydrated] = useState(false);
  const [isRouteOptionsDebouncing, setIsRouteOptionsDebouncing] = useState(false);
  const [useLearnedAi, setUseLearnedAi] = useState(false);
  const [learningRecommendation, setLearningRecommendation] = useState<AiLearningRecommendation | null>(null);
  const [learningEvaluation, setLearningEvaluation] = useState<AiLearningEvaluationResponse | null>(null);
  const [learningInfo, setLearningInfo] = useState<string | null>(null);
  const [showVersusReminder, setShowVersusReminder] = useState(false);
  const [dismissedReminderRemaining, setDismissedReminderRemaining] = useState<number | null>(null);
  const [mapInteractionState, setMapInteractionState] = useState<MapInteractionState>({
    click_to_confirm_enabled: true,
  });
  const confirmLockRef = useRef(false);

  useEffect(() => {
    if (!routeError) return;
    const timer = setTimeout(() => setRouteError(null), 5000);
    return () => clearTimeout(timer);
  }, [routeError]);

  const missionQuery = useQuery({
    queryKey: ["mission", missionId],
    queryFn: () => getMission(missionId)
  });
  const missionData = missionQuery.data;
  const versusLive = useVersusLiveState(versusMatchId, player?.id);
  const liveVersusState = versusLive.liveState;
  const setLiveVersusState = versusLive.setLiveState;

  const versusStateQuery = useQuery({
    queryKey: ["versus-inline", versusMatchId, player?.id],
    queryFn: () => getVersusMatchState(versusMatchId!, player!.id),
    enabled: Boolean(versusMatchId && player?.id),
  });
  useEffect(() => {
    if (!liveVersusState && versusStateQuery.data) {
      setLiveVersusState(versusStateQuery.data);
    }
  }, [liveVersusState, setLiveVersusState, versusStateQuery.data]);
  const versusState = liveVersusState ?? versusStateQuery.data;
  const versusSelfState = versusState?.participants.find((participant) => participant.is_self)?.state;
  const versusOpponent = versusState?.participants.find((participant) => !participant.is_self);
  const versusSelf = versusState?.participants.find((participant) => participant.is_self);
  const versusCountdown = versusState?.countdown_remaining_s;
  const versusLocked = versusSelfState === "submitted" || versusSelfState === "forfeit";

  const currentNodeId = useMemo(() => {
    const routes = humanState.routes_by_sleigh?.[String(activeSleigh)] ?? [];
    return routes.length > 0 ? routes[routes.length - 1] : 0;
  }, [humanState, activeSleigh]);

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
    const missionMaxVehiclesRaw = Number(missionData.mission?.max_vehicles);
    if (Number.isFinite(missionMaxVehiclesRaw) && missionMaxVehiclesRaw >= 1) {
      const normalizedCap = Math.max(1, Math.min(20, Math.round(missionMaxVehiclesRaw)));
      setLimitMaxVehicles(true);
      setMaxVehicles(normalizedCap);
    } else {
      setLimitMaxVehicles(false);
      setMaxVehicles(3);
    }
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

  useEffect(() => {
    setMapInteractionState((previous) => ({
      ...previous,
      click_to_confirm_enabled: !isFreeRouting,
      confirming_route_key: undefined,
    }));
    confirmLockRef.current = false;
  }, [isFreeRouting]);

  const mission = missionData;
  const assignedClientsCount = humanState.assigned_clients.length;
  const totalClientsCount = mission?.clients.length ?? 0;
  const remainingClientsCount = Math.max(0, totalClientsCount - assignedClientsCount);
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
    mutationFn: ({ option, fromId, toId }: ValidateRoutePayload) =>
      validateSegment(missionId, {
        sleigh_id: activeSleigh,
        from_id: fromId,
        to_id: toId,
        selected_route: option,
        speed_multiplier: speedMultiplier,
        vehicle_capacity: vehicleCapacity,
        num_vehicles: numVehicles
      }),
    onSuccess: (nextState) => {
      confirmLockRef.current = false;
      setHumanState(nextState);
      setSelectedClientId(null);
      setRouteOptions([]);
      setSelectedOptionIndex(0);
      setMapInteractionState((previous) => ({
        ...previous,
        confirming_route_key: undefined,
        last_action: "validated",
      }));
      setRouteError(null);
      queryClient.invalidateQueries({ queryKey: ["mission", missionId] });
      queryClient.invalidateQueries({ queryKey: ["adjacents"] });
    },
    onError: (error: Error) => {
      confirmLockRef.current = false;
      setMapInteractionState((previous) => ({
        ...previous,
        confirming_route_key: undefined,
        last_action: "error",
      }));
      setRouteError(error.message);
    }
  });

  const solveMutation = useMutation({
    mutationFn: () =>
      (useLearnedAi ? solveMissionLearned : solveMission)(missionId, {
          num_vehicles: numVehicles,
          max_vehicles:
            Number.isFinite(Number(missionData?.mission?.max_vehicles)) && Number(missionData?.mission?.max_vehicles) >= 1
              ? Math.max(1, Math.min(20, Math.round(Number(missionData?.mission?.max_vehicles))))
              : limitMaxVehicles
                ? Math.max(1, Math.min(20, Math.round(Number(maxVehicles) || 1)))
                : undefined,
          vehicle_capacity: vehicleCapacity,
          speed_multiplier: speedMultiplier,
          optimization_target: "composite"
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
      setMapInteractionState((previous) => ({
        ...previous,
        confirming_route_key: undefined,
        last_action: "undone",
      }));
      queryClient.invalidateQueries({ queryKey: ["adjacents"] });
    },
    onError: (error: Error) => {
      setMapInteractionState((previous) => ({
        ...previous,
        confirming_route_key: undefined,
        last_action: "error",
      }));
      setRouteError(error.message);
    }
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
    if (versusLocked || validateMutation.isPending || confirmLockRef.current || mapInteractionState.confirming_route_key) return;
    setSelectedClientId(node.node_id);
    const routeKey = `${currentNodeId}->${node.node_id}|${Math.round(Number(node.time_s ?? 0))}|${Math.round(Number(node.dist_m ?? 0))}`;
    confirmLockRef.current = true;
    setMapInteractionState((previous) => ({
      ...previous,
      confirming_route_key: routeKey,
    }));
    validateMutation.mutate({
      fromId: currentNodeId,
      toId: node.node_id,
      option: {
        route_nodes: [currentNodeId, node.node_id],
        geometry: node.geometry,
        dist_m: node.dist_m,
        base_time_s: node.time_s,
        time_s: node.time_s,
        label: node.label,
      }
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

  function handlePreviewRouteConfirm(optionIndex: number) {
    if (versusLocked || isFreeRouting) return;
    const option = displayedRouteOptions[optionIndex];
    if (!option) return;
    if (selectedClientId === null) return;
    setSelectedOptionIndex(optionIndex);
    if (validateMutation.isPending || confirmLockRef.current || mapInteractionState.confirming_route_key) {
      return;
    }
    if (option.is_feasible === false) {
      setMapInteractionState((previous) => ({
        ...previous,
        last_action: "error",
      }));
      setRouteError(infeasibleRouteMessage(option));
      return;
    }
    const routeKey = routeOptionKey(option);
    confirmLockRef.current = true;
    setMapInteractionState((previous) => ({
      ...previous,
      confirming_route_key: routeKey,
    }));
    setRouteError(null);
    validateMutation.mutate({
      option,
      fromId: currentFromId,
      toId: selectedClientId,
    });
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
    onError: (error: Error) => {
      setRouteError(error.message);
      if (versusMatchId && !versusLocked && remainingClientsCount > 0) {
        setShowVersusReminder(true);
      }
    },
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

  useEffect(() => {
    if (!versusMatchId || versusLocked || remainingClientsCount <= 0) {
      setShowVersusReminder(false);
      setDismissedReminderRemaining(null);
      return;
    }
    if (dismissedReminderRemaining !== null && dismissedReminderRemaining === remainingClientsCount) {
      return;
    }
    setShowVersusReminder(true);
  }, [versusMatchId, versusLocked, remainingClientsCount, dismissedReminderRemaining]);

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
  const missionConfiguredMaxVehicles =
    Number.isFinite(Number(mission.mission.max_vehicles)) && Number(mission.mission.max_vehicles) >= 1
      ? Math.max(1, Math.min(20, Math.round(Number(mission.mission.max_vehicles))))
      : null;
  const maxVehiclesLockedByMission = missionConfiguredMaxVehicles !== null;
  const weather = weatherInfo(String(mission.weather?.desc ?? mission.mission.weather_key));
  const progressPct = mission.clients.length > 0 ? (assignedClientsCount / mission.clients.length) * 100 : 0;
  const selfProgress = versusSelf?.progress;
  const opponentProgress = versusOpponent?.progress;
  const selfProgressPct = selfProgress?.progress_pct ?? 0;
  const opponentProgressPct = opponentProgress?.progress_pct ?? 0;

  return (
    <div className="page-shell">
      <div className="page-stack">

        <MissionHeroDuel
          missionZone={mission.mission.zone}
          weatherLabel={String(mission.weather?.desc ?? mission.mission.weather_key)}
          weatherIcon={weather.icon}
          weatherCls={weather.cls}
          missionLevel={mission.mission.level}
          aiLabel={aiProfilePreview.label}
          aiDifficultyBonus={aiProfilePreview.difficultyBonus}
          clientCount={mission.clients.length}
          budget={mission.mission.budget}
          overloadedSleighs={overloadedSleighs}
          assignedClientsCount={humanState.assigned_clients.length}
          totalClientsCount={mission.clients.length}
          progressPct={progressPct}
          estimatedTimeLabel={metricTime(totalHumanTimeS)}
          estimatedDistanceKm={totalHumanDistM / 1000}
          incidentsCount={mission.incidents?.count ?? 0}
          versusMatchId={versusMatchId}
          versusSelfState={versusSelfState}
          versusConnection={versusLive.connection}
          versusCountdown={versusCountdown}
          selfAssignedClients={selfProgress?.assigned_clients ?? assignedClientsCount}
          selfTotalClients={selfProgress?.total_clients ?? totalClientsCount}
          selfProgressPct={selfProgressPct}
          hasOpponent={Boolean(versusOpponent)}
          opponentDisplayName={versusOpponent?.display_name}
          opponentAssignedClients={opponentProgress?.assigned_clients ?? 0}
          opponentTotalClients={opponentProgress?.total_clients ?? totalClientsCount}
          opponentProgressPct={opponentProgressPct}
          submitPending={versusSubmitMutation.isPending}
          versusLocked={versusLocked}
          canSubmit={Boolean(player && versusMatchId)}
          remainingClientsCount={remainingClientsCount}
          showVersusReminder={showVersusReminder}
          onSubmitAttempt={() => versusSubmitMutation.mutate()}
          onDismissReminder={() => {
            setShowVersusReminder(false);
            setDismissedReminderRemaining(remainingClientsCount);
          }}
        />

        <div className="mission-layout">
          {/* SIDEBAR */}
          <MissionSidebar
            missionId={missionId}
            mission={mission}
            numVehicles={numVehicles}
            limitMaxVehicles={limitMaxVehicles}
            maxVehicles={maxVehicles}
            maxVehiclesLocked={maxVehiclesLockedByMission}
            vehicleCapacity={vehicleCapacity}
            speedMultiplier={speedMultiplier}
            activeSleigh={activeSleigh}
            versusLocked={versusLocked}
            aiProfileLocked={aiProfileLocked}
            aiProfilePreview={aiProfilePreview}
            optimizationTarget={optimizationTarget}
            secondaryObjectives={secondaryObjectives}
            isFreeRouting={isFreeRouting}
            showFeasibleOnly={showFeasibleOnly}
            suggestPending={suggestMutation.isPending}
            suggestions={suggestions}
            activeRoute={activeRoute}
            activeSegments={activeSegments}
            routeError={routeError}
            selectedClientId={selectedClientId}
            isRouteOptionsDebouncing={isRouteOptionsDebouncing}
            optionsPending={optionsMutation.isPending}
            routeOptions={routeOptions}
            displayedRouteOptions={displayedRouteOptions}
            selectedOptionIndex={selectedOptionIndex}
            useLearnedAi={useLearnedAi}
            learningInfo={learningInfo}
            learningEvaluation={learningEvaluation}
            learningRecommendation={learningRecommendation}
            clearPending={clearMutation.isPending}
            resetPending={resetMutation.isPending}
            trainPending={trainLearningMutation.isPending}
            recommendationPending={recommendationMutation.isPending}
            evaluatePending={evaluateLearningMutation.isPending}
            solvePending={solveMutation.isPending}
            resultsAvailable={mission.results_available}
            onNumVehiclesChange={setNumVehicles}
            onLimitMaxVehiclesChange={setLimitMaxVehicles}
            onMaxVehiclesChange={setMaxVehicles}
            onVehicleCapacityChange={setVehicleCapacity}
            onSpeedMultiplierChange={setSpeedMultiplier}
            onActiveSleighChange={setActiveSleigh}
            onOptimizationTargetChange={setOptimizationTarget}
            onToggleFreeRouting={() => {
              if (versusLocked) return;
              setIsFreeRouting(!isFreeRouting);
              setSelectedClientId(null);
              setRouteOptions([]);
            }}
            onToggleShowFeasibleOnly={() => {
              if (versusLocked) return;
              setShowFeasibleOnly((previous) => !previous);
              setSelectedOptionIndex(0);
            }}
            onSuggest={() => suggestMutation.mutate()}
            onSelectSuggestion={handleClientSelect}
            onClearSuggestions={() => setSuggestions([])}
            onSelectOption={setSelectedOptionIndex}
            onCancelClientChoice={() => {
              setSelectedClientId(null);
              setRouteOptions([]);
              setSelectedOptionIndex(0);
              setRouteError(null);
            }}
            onClearSleigh={() => clearMutation.mutate()}
            onResetAll={() => {
              if (!window.confirm("Réinitialiser toutes les routes ? Cette action est irréversible.")) return;
              resetMutation.mutate();
            }}
            onUseLearnedAiChange={setUseLearnedAi}
            onTrainModel={() => trainLearningMutation.mutate()}
            onRecommendProfile={() => recommendationMutation.mutate()}
            onEvaluateModel={() => evaluateLearningMutation.mutate()}
            onSolve={() => solveMutation.mutate()}
          />

          {/* CARTE */}
          <section className="panel map-card" data-onboarding-id="versus-mission-map">
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
                time_s: o.time_s,
                is_feasible: o.is_feasible,
                feasibility_badges: o.feasibility_badges,
                route_key: routeOptionKey(o),
              }))}
              selectedPreviewIndex={selectedOptionIndex}
              onPreviewRouteConfirm={handlePreviewRouteConfirm}
              onUndoLastSegment={() => undoMutation.mutate()}
              undoPending={undoMutation.isPending}
              undoDisabled={undoMutation.isPending || versusLocked}
              overlayMessage={routeError}
              interactionState={mapInteractionState}
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

        <MissionVehicleStats
          numVehicles={numVehicles}
          activeSleigh={activeSleigh}
          vehicleCapacity={vehicleCapacity}
          routesBySleigh={humanState.routes_by_sleigh}
          liveStats={liveStats}
          clients={mission.clients}
          onActiveSleighChange={setActiveSleigh}
        />

        {versusMatchId && (
          <GuidedOnboarding
            storageKey="operation-noel-onboarding-versus-mission-v1"
            tutorialLabel="Mission versus"
            steps={VERSUS_MISSION_ONBOARDING_STEPS}
          />
        )}
      </div>
    </div>
  );
}
