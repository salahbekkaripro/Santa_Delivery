"use client";

import type { ClientPoint } from "@/lib/types";

type LiveStat = {
  time_s?: number;
  dist_m?: number;
  over_kg?: number;
  load_kg?: number;
  return_time_s?: number;
  return_arrival_clock?: string | null;
};

function metricTime(seconds: number | undefined) {
  const minutes = Math.round((seconds ?? 0) / 60);
  return `${minutes} min`;
}

type MissionVehicleStatsProps = {
  numVehicles: number;
  activeSleigh: number;
  vehicleCapacity: number;
  routesBySleigh: Record<string, number[]>;
  liveStats: Record<string, LiveStat>;
  clients: ClientPoint[];
  onActiveSleighChange: (index: number) => void;
};

export function MissionVehicleStats({
  numVehicles,
  activeSleigh,
  vehicleCapacity,
  routesBySleigh,
  liveStats,
  clients,
  onActiveSleighChange,
}: MissionVehicleStatsProps) {
  return (
    <section className="grid-3">
      {Array.from({ length: numVehicles }, (_, index) => {
        const stats = liveStats[String(index)] ?? {};
        const routeNames = (routesBySleigh[String(index)] ?? [])
          .map((id) => clients.find((c) => c.id === id)?.nom_client ?? `#${id}`)
          .join(" → ");
        const isActive = index === activeSleigh;
        const loadPct = Math.min((Number(stats.load_kg ?? 0) / vehicleCapacity) * 100, 100);
        const isOverloaded = Number(stats.over_kg ?? 0) > 0;

        return (
          <div
            key={index}
            className={`panel stack vehicle-card ${isActive ? "is-active" : ""}`}
            style={{ cursor: "pointer" }}
            onClick={() => onActiveSleighChange(index)}
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
              <span className="vehicle-stat"><strong>Stops</strong> {routesBySleigh[String(index)]?.length ?? 0}</span>
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
  );
}
