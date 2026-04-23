"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { clearSleigh, getAdjacentNodes, getMission, getNearestNode, getRouteOptions, resetHumanState, solveMission, suggestNext, undoLastSegment, validateSegment } from "@/lib/api";
import { MapSurface } from "@/components/map-surface";
import { getAiProfilePreview } from "@/lib/ai-profiles";
import type { AdjacentNode, HumanState, RouteOption, RouteSegment } from "@/lib/types";


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
  if (badge === "Surcharge" || badge === "Déjà assigné" || badge === "Axe incident") {
    return {
      background: "rgba(193, 69, 47, 0.12)",
      color: "#7b2418",
      border: "1px solid rgba(193, 69, 47, 0.22)"
    };
  }
  return {
    background: "rgba(217, 119, 6, 0.12)",
    color: "var(--warning)",
    border: "1px solid rgba(217, 119, 6, 0.24)"
  };
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

export function MissionWorkspace({ missionId }: { missionId: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
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

  const missionQuery = useQuery({
    queryKey: ["mission", missionId],
    queryFn: () => getMission(missionId)
  });
  const missionData = missionQuery.data;

  // Calcul du nœud actuel pour le traineau actif
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

  // Prefetching des prochains coups pour zéro latence
  useEffect(() => {
    if (isFreeRouting && adjacentQuery.data?.adjacents) {
      adjacentQuery.data.adjacents.forEach((adj) => {
        queryClient.prefetchQuery({
          queryKey: ["adjacents", missionId, adj.node_id, speedMultiplier],
          queryFn: () => getAdjacentNodes(missionId, adj.node_id, speedMultiplier),
          staleTime: 60000, // Garder en cache 1 min
        });
      });
    }
  }, [isFreeRouting, adjacentQuery.data, missionId, speedMultiplier, queryClient]);

  useEffect(() => {
    if (!missionData) {
      return;
    }
    const nextState = missionData.human_state ?? defaultHumanState();
    setHumanState(nextState);
    setNumVehicles(nextState.num_vehicles ?? 3);
    setVehicleCapacity(nextState.vehicle_capacity ?? 200);
    setSpeedMultiplier(nextState.speed_multiplier ?? 1);
    if (missionData.mission?.ai_profile) {
      setOptimizationTarget(getAiProfilePreview(missionData.mission.ai_profile).optimizationTarget);
    }
  }, [missionData]);

  const mission = missionData;
  const humanSegments = useMemo(() => flattenSegments(humanState.segments_by_sleigh), [humanState]);
  const activeRoute = humanState.routes_by_sleigh[String(activeSleigh)] ?? [];
  const activeSegments = humanState.segments_by_sleigh[String(activeSleigh)] ?? [];
  const currentFromId = activeRoute.at(-1) ?? 0;

  function routeOptionsQueryKey(payload: { from_id: number; to_id: number; sleigh_id: number; speed_multiplier: number }) {
    return ["route-options", missionId, payload.sleigh_id, payload.from_id, payload.to_id, payload.speed_multiplier] as const;
  }

  async function fetchRouteOptionsCached(payload: { from_id: number; to_id: number; sleigh_id: number; speed_multiplier: number }) {
    return queryClient.fetchQuery({
      queryKey: routeOptionsQueryKey(payload),
      queryFn: () => getRouteOptions(missionId, payload),
      staleTime: 120_000,
    });
  }

  const optionsMutation = useMutation({
    mutationFn: (payload: { from_id: number; to_id: number; sleigh_id: number; speed_multiplier: number }) => fetchRouteOptionsCached(payload),
    onSuccess: (data) => {
      setRouteOptions(data.options);
      const firstFeasibleIndex = data.options.findIndex((option) => option.is_feasible !== false);
      setSelectedOptionIndex(firstFeasibleIndex >= 0 ? firstFeasibleIndex : 0);
      setRouteError(null);
    },
    onError: (error: Error) => setRouteError(error.message)
  });

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
      solveMission(missionId, {
        num_vehicles: numVehicles,
        vehicle_capacity: vehicleCapacity,
        speed_multiplier: speedMultiplier,
        optimization_target: optimizationTarget
      }),
    onSuccess: () => {

      queryClient.invalidateQueries({ queryKey: ["mission", missionId] });
      router.push(`/mission/${missionId}/results`);
    }
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
      const fromId = humanState.routes_by_sleigh[String(activeSleigh)]?.at(-1) ?? 0;
      setSelectedClientId(data.node_id);
      optionsMutation.mutate({
        from_id: fromId,
        to_id: data.node_id,
        sleigh_id: activeSleigh,
        speed_multiplier: speedMultiplier
      });
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  function handleMapClick(lat: number, lon: number) {
    if (!isFreeRouting) return;
    nearestNodeMutation.mutate({ lat, lon });
  }

  function handleAdjacentNodeSelect(node: AdjacentNode) {
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
    if (!mission) {
      return;
    }
    if (humanState.assigned_clients.includes(clientId)) {
      return;
    }
    setSelectedClientId(clientId);
    optionsMutation.mutate({
      from_id: currentFromId,
      to_id: clientId,
      sleigh_id: activeSleigh,
      speed_multiplier: speedMultiplier
    });
  }

  if (missionQuery.isLoading) {
    return <div className="page-shell">Chargement de la mission...</div>;
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
  const selectedRouteOption = routeOptions[selectedOptionIndex];
  const selectedRouteIsFeasible = selectedRouteOption ? selectedRouteOption.is_feasible !== false : false;

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>{mission.mission.zone}</h1>
          <p>
            Mission {mission.mission.level ? `niveau ${mission.mission.level}` : "sandbox"} · {mission.clients.length} clients ·{" "}
            meteo {String(mission.weather?.desc ?? mission.mission.weather_key)} · IA {aiProfilePreview.label}
          </p>
        </section>

        <div className="grid-4">
          <div className="metric-card">
            <div className="metric-label">Temps humain estime</div>
            <div className="metric-value">{metricTime(totalHumanTimeS)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Distance actuelle</div>
            <div className="metric-value">{(totalHumanDistM / 1000).toFixed(2)} km</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Clients assignes</div>
            <div className="metric-value">{humanState.assigned_clients.length}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Budget</div>
            <div className="metric-value">{mission.mission.budget} €</div>
          </div>
          <div className={`metric-card ai-profile-metric ${aiProfilePreview.accentClass}`}>
            <div className="metric-label">Profil IA</div>
            <div className="metric-value">{aiProfilePreview.label}</div>
            <span className="muted">Bonus difficulté +{aiProfilePreview.difficultyBonus}</span>
          </div>
        </div>

        {mission.incidents && mission.incidents.count > 0 ? (
          <div className="error-box">Incidents actifs: {mission.incidents.count} axe(s) bloques visibles sur la carte.</div>
        ) : null}

        <div className="mission-layout">
          <aside className="panel stack">
            <strong>Configuration</strong>
            <label className="field">
              <span>Traîneaux</span>
              <input type="number" min={1} max={10} value={numVehicles} onChange={(event) => setNumVehicles(Number(event.target.value))} />
            </label>
            <label className="field">
              <span>Capacite</span>
              <input
                type="number"
                min={50}
                max={500}
                value={vehicleCapacity}
                onChange={(event) => setVehicleCapacity(Number(event.target.value))}
              />
            </label>
            <label className="field">
              <span>Vitesse</span>
              <select value={speedMultiplier} onChange={(event) => setSpeedMultiplier(Number(event.target.value))}>
                <option value={0.7}>Prudent</option>
                <option value={1}>Normal</option>
                <option value={1.5}>Turbo</option>
              </select>
            </label>
            <label className="field">
              <span>Traîneau actif</span>
              <select value={activeSleigh} onChange={(event) => setActiveSleigh(Number(event.target.value))}>
                {Array.from({ length: numVehicles }, (_, index) => (
                  <option key={index} value={index}>
                    Traineau #{index + 1}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Objectif IA</span>
              <select
                value={aiProfileLocked ? aiProfilePreview.optimizationTarget : optimizationTarget}
                disabled={aiProfileLocked}
                onChange={(event) => setOptimizationTarget(event.target.value as "time" | "distance")}
              >
                <option value="time">⚡ Express (Temps)</option>
                <option value="distance">🌱 Écolo (Distance)</option>
              </select>
            </label>

            <div className={`ai-profile-card ${aiProfilePreview.accentClass}`}>
              <div className="ai-profile-head">
                <div>
                  <strong>IA {aiProfilePreview.label}</strong>
                  <span className="muted">{aiProfilePreview.signature}</span>
                </div>
                <span className="tag">+{aiProfilePreview.difficultyBonus} score</span>
              </div>
              <p className="muted">{aiProfilePreview.description}</p>
              <div className="ai-profile-meta">
                <span>Cible {aiProfilePreview.optimizationTarget === "time" ? "temps" : "distance"}</span>
                <span>{aiProfileLocked ? "Profil verrouillé par la mission" : "Mode libre configurable"}</span>
              </div>
            </div>

            {secondaryObjectives.length > 0 ? (
              <div className="ai-profile-card">
                <div className="ai-profile-head">
                  <div>
                    <strong>Objectifs secondaires</strong>
                    <span className="muted">À valider pendant le run et au debrief</span>
                  </div>
                  <span className="tag">{secondaryObjectives.length} objectif(s)</span>
                </div>
                <div className="objective-list">
                  {secondaryObjectives.map((objective) => (
                    <div key={`${objective.code}-${objective.label}`} className="objective-chip">
                      <span className="objective-dot" />
                      <span>{objective.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="stack">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>Choix de chemin</strong>
                <button 
                  className={`tag ${isFreeRouting ? "is-selected" : ""}`}
                  style={{ cursor: "pointer", background: isFreeRouting ? "var(--accent)" : "rgba(0,0,0,0.05)", color: isFreeRouting ? "white" : "var(--text)" }}
                  onClick={() => {
                    setIsFreeRouting(!isFreeRouting);
                    setSelectedClientId(null);
                    setRouteOptions([]);
                  }}
                >
                  {isFreeRouting ? "🗺️ Tracé Libre : ON" : "📍 Sélection : ON"}
                </button>
              </div>
              <span className="muted">
                {isFreeRouting 
                  ? "Clique n'importe où sur la carte pour tracer ta route segment par segment." 
                  : "Clique un client sur la carte pour voir les options de chemins."}
              </span>
              <button 
                className="secondary-button" 
                onClick={() => suggestMutation.mutate()}
                disabled={suggestMutation.isPending}
              >
                {suggestMutation.isPending ? "Calcul..." : "💡 Suggérer le prochain stop"}
              </button>
              {suggestions.length > 0 && (
                <div className="stack" style={{ gap: "8px", marginTop: "8px" }}>
                  {suggestions.map((s) => (
                    <button 
                      key={s.client_id} 
                      className={`tag ${!s.is_feasible ? "error-box" : ""}`}
                      style={{ cursor: "pointer", border: "1px solid var(--border)", width: "100%", justifyContent: "space-between" }}
                      onClick={() => handleClientSelect(s.client_id)}
                      disabled={!s.is_feasible}
                    >
                      <span>{s.nom_client}</span>
                      <span className="muted">{s.arrival_clock}</span>
                    </button>
                  ))}
                  <button className="secondary-button" style={{ fontSize: "0.8rem", padding: "4px" }} onClick={() => setSuggestions([])}>
                    Effacer suggestions
                  </button>
                </div>
              )}
            </div>

            <div className="stack">
              <strong>Route courante</strong>
              <span className="muted">
                {activeRoute.length > 0
                  ? activeRoute
                      .map((clientId) => mission.clients.find((client) => client.id === clientId)?.nom_client ?? `#${clientId}`)
                      .join(" → ")
                  : "Aucun stop sur ce traîneau"}
              </span>
            </div>

            <div className="stack">
              <strong>ETA du traineau actif</strong>
              {activeSegments.length > 0 ? (
                activeSegments.map((segment) => {
                  const client = mission.clients.find((item) => item.id === segment.to_id);
                  if (!client) {
                    return null;
                  }
                  return (
                    <span key={`${segment.from_id}-${segment.to_id}`} className="muted">
                      Stop {segment.segment_idx}: {client.nom_client} · {segment.arrival_clock ?? "--:--"} · {metricTime(segment.arrival_eta_s)}
                    </span>
                  );
                })
              ) : (
                <span className="muted">Aucune ETA tant qu&apos;aucun segment n&apos;est valide.</span>
              )}
            </div>

            {routeError ? <div className="error-box">{routeError}</div> : null}
            {overloadedSleighs.length > 0 ? (
              <div className="error-box">Surcharge sur les traîneaux #{overloadedSleighs.join(", #")}.</div>
            ) : null}

            {selectedClientId ? (
              <div className="stack">
                <span className="tag">Client selectionne #{selectedClientId}</span>
                {optionsMutation.isPending ? <span className="muted">Calcul des options...</span> : null}
                {routeOptions.map((option, index) => (
                  <button
                    key={`${option.route_nodes.join("-")}-${index}`}
                    className={`option-card ${selectedOptionIndex === index ? "is-selected" : ""} ${option.is_feasible === false ? "is-infeasible" : ""}`}
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
                    <div className="muted">Noeuds: {option.route_nodes.length}</div>
                    <div className="muted">
                      Arrivee estimee: {option.projected_arrival_clock ?? "--:--"} · Charge projetee: {Number(option.projected_load_kg ?? 0).toFixed(0)} kg
                    </div>
                    {Number(option.projected_overload_kg ?? 0) > 0 ? (
                      <div className="muted" style={{ color: "#7b2418" }}>
                        Depassement capacite: +{Number(option.projected_overload_kg ?? 0).toFixed(0)} kg
                      </div>
                    ) : null}
                  </button>
                ))}
                {routeOptions.length > 0 ? (
                  <>
                    {selectedRouteOption && !selectedRouteIsFeasible ? (
                      <div className="error-box">
                        Option non faisable: {(selectedRouteOption.feasibility_badges ?? ["Risque"]).join(", ")}.
                      </div>
                    ) : null}
                    <button
                      className="primary-button"
                      onClick={() => {
                        if (!selectedRouteOption || !selectedRouteIsFeasible) {
                          return;
                        }
                        validateMutation.mutate(selectedRouteOption);
                      }}
                      disabled={validateMutation.isPending || !selectedRouteOption || !selectedRouteIsFeasible}
                    >
                      {validateMutation.isPending ? "Validation..." : "Valider ce segment"}
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => {
                        setSelectedClientId(null);
                        setRouteOptions([]);
                        setSelectedOptionIndex(0);
                        setRouteError(null);
                      }}
                    >
                      Annuler ce choix
                    </button>
                  </>
                ) : null}
              </div>
            ) : (
              <div className="muted">Aucun client selectionne.</div>
            )}

            <div className="stack">
              <button className="secondary-button" onClick={() => undoMutation.mutate()}>
                {undoMutation.isPending ? "Annulation..." : "Annuler le dernier segment"}
              </button>
              <button className="secondary-button" onClick={() => clearMutation.mutate()}>
                {clearMutation.isPending ? "Vidage..." : "Vider ce traîneau"}
              </button>
              <button className="secondary-button" onClick={() => resetMutation.mutate()}>
                {resetMutation.isPending ? "Reset..." : "Reinitialiser toutes les routes"}
              </button>
              <div className="error-box" style={{ background: "rgba(23, 50, 77, 0.05)", borderColor: "var(--border)", color: "var(--text)" }}>
                <strong>Mode IA : {aiProfilePreview.label}</strong>
                <p className="muted" style={{ fontSize: "0.8rem", margin: "4px 0 0" }}>
                  {aiProfileLocked
                    ? `Cette mission impose le profil ${aiProfilePreview.label}. Signature: ${aiProfilePreview.signature}.`
                    : aiProfilePreview.optimizationTarget === "time"
                      ? "L'IA cherchera à finir la tournée le plus vite possible."
                      : "L'IA cherchera à parcourir le moins de kilomètres possible."}
                </p>
              </div>
              <button className="primary-button" onClick={() => solveMutation.mutate()}>
                {solveMutation.isPending ? "Optimisation..." : "Lancer la solution IA"}
              </button>
              {mission.results_available ? (
                <Link className="secondary-button" href={`/mission/${missionId}/results`}>
                  Voir les derniers resultats
                </Link>
              ) : null}
            </div>
          </aside>

          <section className="panel map-card">
            <div className="legend" style={{ marginBottom: 14 }}>
              <span className="legend-chip">
                <span className="line-dot is-dashed" style={{ color: "#c1452f" }} />
                Votre trace
              </span>
              <span className="legend-chip">
                <span className="line-dot is-dashed" style={{ color: "#0f766e" }} />
                Retour depot
              </span>
              {incidentSegments.length > 0 ? (
                <span className="legend-chip">
                  <span className="line-dot is-dashed" style={{ color: "#991b1b" }} />
                  Incidents
                </span>
              ) : null}
              {routeOptions.length > 0 ? (
                <span className="legend-chip">
                  <span className="line-dot" style={{ color: "#d97706" }} />
                  Option selectionnee
                </span>
              ) : null}
            </div>
            <MapSurface
              depot={mission.depot}
              clients={mission.clients}
              humanSegments={humanSegments}
              returnSegments={returnSegments}
              incidentSegments={incidentSegments}
              previewOptions={routeOptions.map((option) => ({
                geometry: option.geometry,
                label: option.label,
                dist_m: option.dist_m,
                time_s: option.time_s
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

        <section className="grid-3">
          {Array.from({ length: numVehicles }, (_, index) => {
            const stats = liveStats[String(index)] ?? {};
            const routeNames = (humanState.routes_by_sleigh[String(index)] ?? [])
              .map((clientId) => mission.clients.find((client) => client.id === clientId)?.nom_client ?? `#${clientId}`)
              .join(" → ");
            return (
              <div key={index} className="panel stack">
                <strong>Traineau #{index + 1}</strong>
                <div className="capacity-bar-container" title="Charge utile">
                  <div 
                    className={`capacity-bar-fill ${Number(stats.over_kg ?? 0) > 0 ? "is-overloaded" : ""}`}
                    style={{ width: `${Math.min((Number(stats.load_kg ?? 0) / vehicleCapacity) * 100, 100)}%` }}
                  />
                </div>
                <div className="capacity-bar-container" style={{ background: "rgba(0,0,0,0.03)" }} title="Batterie / Énergie">
                  <div 
                    className="capacity-bar-fill"
                    style={{ 
                      width: `${Math.max(100 - (Number(stats.dist_m ?? 0) / 15000) * 100, 0)}%`,
                      background: "linear-gradient(90deg, #10b981, #34d399)"
                    }}
                  />
                </div>
                <span className="muted">Stops: {humanState.routes_by_sleigh[String(index)]?.length ?? 0}</span>
                <span className="muted">Charge: {Number(stats.load_kg ?? 0).toFixed(0)} / {vehicleCapacity} kg</span>
                <span className="muted">Temps: {metricTime(Number(stats.time_s ?? 0))}</span>
                <span className="muted">Distance: {(Number(stats.dist_m ?? 0) / 1000).toFixed(2)} km</span>
                <span className="muted">
                  Retour depot: {metricTime(Number(stats.return_time_s ?? 0))}
                  {stats.return_arrival_clock ? ` · ${String(stats.return_arrival_clock)}` : ""}
                </span>
                <span className="muted">{routeNames || "Route vide"}</span>
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}
