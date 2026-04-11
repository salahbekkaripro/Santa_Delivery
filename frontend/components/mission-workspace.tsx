"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { clearSleigh, getMission, getRouteOptions, resetHumanState, solveMission, undoLastSegment, validateSegment } from "@/lib/api";
import { MapSurface } from "@/components/map-surface";
import type { HumanState, RouteOption, RouteSegment } from "@/lib/types";

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

  const missionQuery = useQuery({
    queryKey: ["mission", missionId],
    queryFn: () => getMission(missionId)
  });
  const missionData = missionQuery.data;

  useEffect(() => {
    if (!missionData) {
      return;
    }
    const nextState = missionData.human_state ?? defaultHumanState();
    setHumanState(nextState);
    setNumVehicles(nextState.num_vehicles ?? 3);
    setVehicleCapacity(nextState.vehicle_capacity ?? 200);
    setSpeedMultiplier(nextState.speed_multiplier ?? 1);
  }, [missionData]);

  const mission = missionData;
  const humanSegments = useMemo(() => flattenSegments(humanState.segments_by_sleigh), [humanState]);
  const activeRoute = humanState.routes_by_sleigh[String(activeSleigh)] ?? [];
  const activeSegments = humanState.segments_by_sleigh[String(activeSleigh)] ?? [];

  const optionsMutation = useMutation({
    mutationFn: (payload: { from_id: number; to_id: number; speed_multiplier: number }) => getRouteOptions(missionId, payload),
    onSuccess: (data) => {
      setRouteOptions(data.options);
      setSelectedOptionIndex(0);
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
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  const solveMutation = useMutation({
    mutationFn: () =>
      solveMission(missionId, {
        num_vehicles: numVehicles,
        vehicle_capacity: vehicleCapacity,
        speed_multiplier: speedMultiplier
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
      setActiveSleigh(0);
    },
    onError: (error: Error) => setRouteError(error.message)
  });

  function handleClientSelect(clientId: number) {
    if (!mission) {
      return;
    }
    if (humanState.assigned_clients.includes(clientId)) {
      return;
    }
    const fromId = humanState.routes_by_sleigh[String(activeSleigh)]?.at(-1) ?? 0;
    setSelectedClientId(clientId);
    optionsMutation.mutate({ from_id: fromId, to_id: clientId, speed_multiplier: speedMultiplier });
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

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>{mission.mission.zone}</h1>
          <p>
            Mission {mission.mission.level ? `niveau ${mission.mission.level}` : "sandbox"} · {mission.clients.length} clients ·{" "}
            meteo {String(mission.weather?.desc ?? mission.mission.weather_key)}
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

            <div className="stack">
              <strong>Choix de chemin</strong>
              <span className="muted">
                Clique un client sur la carte. Le backend calcule ensuite les meilleurs chemins et tu valides celui que tu veux garder.
              </span>
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
                    className={`option-card ${selectedOptionIndex === index ? "is-selected" : ""}`}
                    onClick={() => setSelectedOptionIndex(index)}
                  >
                    <strong>{option.label}</strong>
                    <div className="muted">Noeuds: {option.route_nodes.length}</div>
                  </button>
                ))}
                {routeOptions.length > 0 ? (
                  <>
                    <button className="primary-button" onClick={() => validateMutation.mutate(routeOptions[selectedOptionIndex])}>
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
                <div className="capacity-bar-container">
                  <div 
                    className={`capacity-bar-fill ${Number(stats.over_kg ?? 0) > 0 ? "is-overloaded" : ""}`}
                    style={{ width: `${Math.min((Number(stats.load_kg ?? 0) / vehicleCapacity) * 100, 100)}%` }}
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
