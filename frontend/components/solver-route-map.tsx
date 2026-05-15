"use client";

import L from "leaflet";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { ClientPoint, RouteSegment } from "@/lib/types";

// ── Constants ────────────────────────────────────────────────────────────────

const SLEIGH_COLORS = ["#1a6fb5", "#9e2f3f", "#1f7a56", "#b8892f", "#6b3fa0", "#c45e00"];
const SPEEDS = [
  { label: "×30",  value: 30  },
  { label: "×60",  value: 60  },
  { label: "×120", value: 120 },
  { label: "×300", value: 300 },
];

// ── Types ─────────────────────────────────────────────────────────────────────

type Waypoint = { lat: number; lon: number; tAbs: number };
type StopPoint = { clientId: number; arrivalTime: number; lat: number; lon: number };

type SleighRoute = {
  vehicleId: number;
  color: string;
  waypoints: Waypoint[];
  totalTime: number;
  stops: StopPoint[];
};

type Props = {
  depot: ClientPoint;
  clients: ClientPoint[];
  segments: RouteSegment[];
  tours: Array<{ vehicle_id: number; route_ids: number[]; duration_s: number; weight_kg: number }>;
};

// ── Math helpers ──────────────────────────────────────────────────────────────

function getBearing(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const p1 = lat1 * (Math.PI / 180);
  const p2 = lat2 * (Math.PI / 180);
  const y = Math.sin(dLon) * Math.cos(p2);
  const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dLon);
  return (Math.atan2(y, x) * (180 / Math.PI) + 360) % 360;
}

function interpolate(waypoints: Waypoint[], t: number): { lat: number; lon: number; bearing: number } | null {
  if (!waypoints.length) return null;
  if (t <= waypoints[0].tAbs) return { ...waypoints[0], bearing: 0 };
  const last = waypoints[waypoints.length - 1];
  if (t >= last.tAbs) {
    const prev = waypoints[waypoints.length - 2] ?? last;
    return { ...last, bearing: getBearing(prev.lat, prev.lon, last.lat, last.lon) };
  }
  for (let i = 0; i < waypoints.length - 1; i++) {
    const a = waypoints[i], b = waypoints[i + 1];
    if (t >= a.tAbs && t <= b.tAbs) {
      const frac = (t - a.tAbs) / (b.tAbs - a.tAbs || 1);
      return {
        lat: a.lat + frac * (b.lat - a.lat),
        lon: a.lon + frac * (b.lon - a.lon),
        bearing: getBearing(a.lat, a.lon, b.lat, b.lon),
      };
    }
  }
  return null;
}

function buildTrail(waypoints: Waypoint[], t: number): [number, number][] {
  const pts: [number, number][] = [];
  for (let i = 0; i < waypoints.length; i++) {
    if (waypoints[i].tAbs <= t) {
      pts.push([waypoints[i].lat, waypoints[i].lon]);
    } else {
      if (i > 0) {
        const a = waypoints[i - 1], b = waypoints[i];
        const frac = (t - a.tAbs) / (b.tAbs - a.tAbs || 1);
        pts.push([a.lat + frac * (b.lat - a.lat), a.lon + frac * (b.lon - a.lon)]);
      }
      break;
    }
  }
  return pts;
}

// ── Sleigh DivIcon ─────────────────────────────────────────────────────────────

function makeSleighIcon(color: string, bearing: number, done: boolean): L.DivIcon {
  const deg = done ? 0 : bearing - 90;
  const glow = done ? "4px" : "18px";
  const opacity = done ? 0.45 : 1;
  return L.divIcon({
    className: "",
    iconSize: [38, 38],
    iconAnchor: [19, 19],
    html: `<div style="
      width:38px;height:38px;border-radius:50%;
      background:${color};
      border:2.5px solid rgba(255,255,255,0.9);
      display:flex;align-items:center;justify-content:center;
      box-shadow:0 0 ${glow} ${color}cc,0 2px 8px rgba(0,0,0,0.4);
      opacity:${opacity};
    ">
      <span style="font-size:17px;line-height:1;display:block;transform:rotate(${deg}deg)">🛷</span>
    </div>`,
  });
}

// ── AnimatedLayer (imperative Leaflet, no React re-renders per frame) ─────────

type LayerProps = {
  routes: SleighRoute[];
  playing: boolean;
  speed: number;
  externalTime: number;
  maxTime: number;
  onProgress: (t: number) => void;
};

function AnimatedLayer({ routes, playing, speed, externalTime, maxTime, onProgress }: LayerProps) {
  const map = useMap();
  const markersRef  = useRef(new Map<number, L.Marker>());
  const trailsRef   = useRef(new Map<number, L.Polyline>());
  const glowsRef    = useRef(new Map<number, L.Polyline>());
  const simTimeRef  = useRef(externalTime);
  const rafRef      = useRef<number | null>(null);
  const lastTRef    = useRef<number | null>(null);
  const frameRef    = useRef(0);

  // Create / recreate Leaflet objects when routes change
  useEffect(() => {
    markersRef.current.forEach(m => m.remove());
    trailsRef.current.forEach(p => p.remove());
    glowsRef.current.forEach(p => p.remove());
    markersRef.current.clear();
    trailsRef.current.clear();
    glowsRef.current.clear();

    for (const r of routes) {
      if (!r.waypoints.length) continue;
      const w0 = r.waypoints[0];

      // Glow (wider, low opacity) + solid trail
      const glow = L.polyline([], {
        color: r.color, weight: 12, opacity: 0.18, lineCap: "round", lineJoin: "round",
      }).addTo(map);
      const trail = L.polyline([], {
        color: r.color, weight: 4,  opacity: 0.95, lineCap: "round", lineJoin: "round",
      }).addTo(map);
      const marker = L.marker([w0.lat, w0.lon], {
        icon: makeSleighIcon(r.color, 0, false),
        zIndexOffset: 1000,
      }).addTo(map);

      markersRef.current.set(r.vehicleId, marker);
      trailsRef.current.set(r.vehicleId, trail);
      glowsRef.current.set(r.vehicleId, glow);
    }

    return () => {
      markersRef.current.forEach(m => m.remove());
      trailsRef.current.forEach(p => p.remove());
      glowsRef.current.forEach(p => p.remove());
    };
  }, [map, routes]);

  // Imperative update for all objects at time t
  const applyTime = useCallback((t: number) => {
    for (const r of routes) {
      const pos = interpolate(r.waypoints, t);
      if (!pos) continue;
      const done = t >= r.totalTime;
      markersRef.current.get(r.vehicleId)?.setLatLng([pos.lat, pos.lon]);
      markersRef.current.get(r.vehicleId)?.setIcon(makeSleighIcon(r.color, pos.bearing, done));
      const pts = buildTrail(r.waypoints, t) as L.LatLngExpression[];
      trailsRef.current.get(r.vehicleId)?.setLatLngs(pts);
      glowsRef.current.get(r.vehicleId)?.setLatLngs(pts);
    }
  }, [routes]);

  // Scrubber (not playing): update from externalTime prop
  useEffect(() => {
    if (playing) return;
    simTimeRef.current = externalTime;
    applyTime(externalTime);
  }, [playing, externalTime, applyTime]);

  // Playback RAF loop
  useEffect(() => {
    if (!playing) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      lastTRef.current = null;
      return;
    }

    const tick = (now: number) => {
      if (!lastTRef.current) lastTRef.current = now;
      const dtSim = ((now - lastTRef.current) / 1000) * speed;
      lastTRef.current = now;
      simTimeRef.current = Math.min(simTimeRef.current + dtSim, maxTime);

      applyTime(simTimeRef.current);

      frameRef.current++;
      if (frameRef.current % 3 === 0) {
        onProgress(simTimeRef.current);
      }

      if (simTimeRef.current < maxTime) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        onProgress(maxTime);
        rafRef.current = null;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      lastTRef.current = null;
    };
  }, [playing, speed, maxTime, applyTime, onProgress]);

  return null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTime(s: number) {
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SolverRouteMap({ depot, clients, segments, tours }: Props) {
  const center: [number, number] = [depot.lat, depot.lon];

  const [playing, setPlaying]   = useState(false);
  const [speed, setSpeed]       = useState(120);
  const [simulTime, setSimulTime] = useState(0);

  const clientById = useMemo(() => {
    const m = new Map<number, ClientPoint>();
    m.set(depot.id, depot);
    for (const c of clients) m.set(c.id, c);
    return m;
  }, [depot, clients]);

  // Build per-sleigh route data from segments
  const sleighRoutes = useMemo((): SleighRoute[] => {
    const aiSegs = segments.filter(s => s.variant === "ai");
    const byVehicle = new Map<number, RouteSegment[]>();
    for (const seg of aiSegs) {
      const arr = byVehicle.get(seg.sleigh_id) ?? [];
      arr.push(seg);
      byVehicle.set(seg.sleigh_id, arr);
    }

    return Array.from(byVehicle.entries()).map(([vid, segs]) => {
      const sorted = [...segs].sort((a, b) => (a.segment_idx ?? 0) - (b.segment_idx ?? 0));
      const color = SLEIGH_COLORS[vid % SLEIGH_COLORS.length];
      const waypoints: Waypoint[] = [];
      const stops: StopPoint[] = [];

      for (const seg of sorted) {
        const tEnd   = seg.arrival_eta_s ?? 0;
        const tStart = Math.max(0, tEnd - seg.time_s);
        const geom   = seg.geometry;
        const n      = geom.length;
        const startI = waypoints.length === 0 ? 0 : 1; // skip first pt on non-first segments (duplicate)

        for (let i = startI; i < n; i++) {
          const tAbs = n <= 1 ? tStart : tStart + (i / (n - 1)) * seg.time_s;
          waypoints.push({ lat: geom[i][0], lon: geom[i][1], tAbs });
        }

        if (seg.to_id !== depot.id && seg.arrival_eta_s != null) {
          const c = clientById.get(seg.to_id);
          if (c) stops.push({ clientId: seg.to_id, arrivalTime: seg.arrival_eta_s, lat: c.lat, lon: c.lon });
        }
      }

      const totalTime = waypoints.length ? waypoints[waypoints.length - 1].tAbs : 0;
      return { vehicleId: vid, color, waypoints, totalTime, stops };
    });
  }, [segments, depot.id, clientById]);

  const maxSimulTime = useMemo(
    () => Math.max(1, ...sleighRoutes.map(r => r.totalTime)),
    [sleighRoutes]
  );

  const handleProgress = useCallback((t: number) => {
    setSimulTime(t);
    if (t >= maxSimulTime) setPlaying(false);
  }, [maxSimulTime]);

  const progressPct = maxSimulTime > 0 ? (simulTime / maxSimulTime) * 100 : 0;

  function handlePlayPause() {
    if (simulTime >= maxSimulTime) setSimulTime(0);
    setPlaying(p => !p);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>

      {/* ── MAP ── */}
      <div style={{ position: "relative", borderRadius: "18px 18px 0 0", overflow: "hidden" }}>
        <MapContainer className="solver-map-container" center={center} zoom={14} style={{ width: "100%", height: 500 }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            maxZoom={19}
          />

          {/* Ghost routes (full path, faded dashed) */}
          {sleighRoutes.map(r =>
            r.waypoints.length > 1 ? (
              <Polyline
                key={`ghost-${r.vehicleId}`}
                positions={r.waypoints.map(w => [w.lat, w.lon] as [number, number])}
                pathOptions={{ color: r.color, weight: 2, opacity: 0.18, dashArray: "6 5" }}
              />
            ) : null
          )}

          {/* Stop markers — light up when visited */}
          {sleighRoutes.flatMap(r =>
            r.stops.map((stop, i) => {
              const visited = simulTime >= stop.arrivalTime;
              return (
                <CircleMarker
                  key={`stop-${r.vehicleId}-${stop.clientId}`}
                  center={[stop.lat, stop.lon]}
                  radius={visited ? 10 : 6}
                  pathOptions={{
                    color: visited ? "#fff" : r.color,
                    fillColor: visited ? r.color : "rgba(255,255,255,0.15)",
                    fillOpacity: visited ? 1 : 0.6,
                    weight: visited ? 2.5 : 1.5,
                  }}
                >
                  <Tooltip>
                    Stop #{i + 1} · Traîneau {r.vehicleId + 1}
                    {visited ? ` · ✓ ${fmtTime(stop.arrivalTime)}` : ""}
                  </Tooltip>
                </CircleMarker>
              );
            })
          )}

          {/* Depot */}
          <CircleMarker
            center={center}
            radius={18}
            pathOptions={{ color: "#fff", fillColor: "#0d1f2e", fillOpacity: 1, weight: 3 }}
          >
            <Tooltip permanent direction="top" offset={[0, -20]}>🏭 Dépôt</Tooltip>
          </CircleMarker>

          {/* Animated sleighs + trails */}
          <AnimatedLayer
            routes={sleighRoutes}
            playing={playing}
            speed={speed}
            externalTime={simulTime}
            maxTime={maxSimulTime}
            onProgress={handleProgress}
          />
        </MapContainer>

        {/* Legend chip (top-right) */}
        <div style={{
          position: "absolute", top: 12, right: 12, zIndex: 1000,
          background: "rgba(10,22,34,0.82)", backdropFilter: "blur(10px)",
          borderRadius: 12, padding: "10px 14px",
          display: "flex", flexDirection: "column", gap: 7,
          fontSize: "0.78rem", border: "1px solid rgba(255,255,255,0.08)",
        }}>
          {sleighRoutes.map(r => {
            const visited = r.stops.filter(s => simulTime >= s.arrivalTime).length;
            const done = simulTime >= r.totalTime;
            return (
              <div key={r.vehicleId} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{
                  width: 10, height: 10, borderRadius: "50%", background: r.color, flexShrink: 0,
                  boxShadow: done ? "none" : `0 0 7px ${r.color}`,
                }} />
                <span style={{ color: "#fff", fontWeight: 600 }}>Traîneau {r.vehicleId + 1}</span>
                <span style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.72rem" }}>
                  {visited}/{r.stops.length} colis
                  {done ? " · ✓" : ""}
                </span>
              </div>
            );
          })}
          <div style={{ display: "flex", alignItems: "center", gap: 8, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", border: "2px solid #fff", background: "#0d1f2e", flexShrink: 0 }} />
            <span style={{ color: "rgba(255,255,255,0.45)" }}>Dépôt</span>
            <span style={{ color: "rgba(255,255,255,0.2)", marginLeft: 4 }}>·</span>
            <span style={{ color: "rgba(255,255,255,0.45)" }}>Stop ○ / ● livré</span>
          </div>
        </div>

        {/* Simulated clock (top-left) */}
        <div style={{
          position: "absolute", top: 12, left: 12, zIndex: 1000,
          background: "rgba(10,22,34,0.82)", backdropFilter: "blur(10px)",
          borderRadius: 10, padding: "8px 14px",
          border: "1px solid rgba(255,255,255,0.08)",
        }}>
          <div style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.4)", letterSpacing: "0.1em" }}>HORLOGE SIMULÉE</div>
          <div style={{ fontFamily: "monospace", fontSize: "1.2rem", fontWeight: 800, color: "#fff", letterSpacing: "0.06em" }}>
            {fmtTime(simulTime)}
          </div>
        </div>
      </div>

      {/* ── CONTROLS ── */}
      <div style={{
        background: "#0a1622",
        padding: "14px 18px 18px",
        borderRadius: "0 0 18px 18px",
        border: "1px solid rgba(255,255,255,0.07)",
        borderTop: "none",
        display: "flex", flexDirection: "column", gap: 14,
      }}>
        {/* Global scrubber */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontFamily: "monospace", fontSize: "0.78rem", color: "rgba(255,255,255,0.4)", minWidth: 42 }}>
            {fmtTime(simulTime)}
          </span>
          <div style={{ flex: 1, position: "relative" }}>
            <input
              type="range"
              min={0} max={maxSimulTime} step={0.5}
              value={simulTime}
              onChange={e => { setPlaying(false); setSimulTime(Number(e.target.value)); }}
              style={{ width: "100%", accentColor: "#1a6fb5", cursor: "pointer" }}
            />
          </div>
          <span style={{ fontFamily: "monospace", fontSize: "0.78rem", color: "rgba(255,255,255,0.4)", minWidth: 42, textAlign: "right" }}>
            {fmtTime(maxSimulTime)}
          </span>
        </div>

        {/* Buttons row */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button
            onClick={handlePlayPause}
            style={{
              padding: "9px 22px", borderRadius: 10, border: "none", cursor: "pointer",
              background: playing ? "rgba(255,255,255,0.1)" : "#1a6fb5",
              color: "#fff", fontWeight: 700, fontSize: "0.88rem",
              display: "flex", alignItems: "center", gap: 6,
              boxShadow: playing ? "none" : "0 0 16px #1a6fb544",
            }}
          >
            {playing ? "⏸ Pause" : simulTime >= maxSimulTime ? "↺ Rejouer" : "▶ Play"}
          </button>

          <button
            onClick={() => { setPlaying(false); setSimulTime(0); }}
            style={{
              padding: "9px 14px", borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.14)", cursor: "pointer",
              background: "transparent", color: "rgba(255,255,255,0.65)", fontSize: "0.85rem",
            }}
          >
            ⏮ Reset
          </button>

          {/* Speed selector */}
          <div style={{ display: "flex", gap: 4, marginLeft: 4 }}>
            <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.35)", alignSelf: "center", marginRight: 4 }}>Vitesse</span>
            {SPEEDS.map(s => (
              <button
                key={s.value}
                onClick={() => setSpeed(s.value)}
                style={{
                  padding: "6px 12px", borderRadius: 8, border: "none", cursor: "pointer",
                  background: speed === s.value ? "#1a6fb5" : "rgba(255,255,255,0.07)",
                  color: speed === s.value ? "#fff" : "rgba(255,255,255,0.45)",
                  fontSize: "0.75rem", fontWeight: 700,
                }}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Global progress bar */}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 140, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
              <div style={{
                height: "100%", borderRadius: 2, background: "#1a6fb5",
                width: `${progressPct}%`,
                transition: playing ? "none" : "width 0.15s",
              }} />
            </div>
            <span style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.35)", minWidth: 32 }}>
              {Math.round(progressPct)}%
            </span>
          </div>
        </div>

        {/* Per-sleigh progress bars */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {sleighRoutes.map(r => {
            const pct      = r.totalTime > 0 ? Math.min(100, (simulTime / r.totalTime) * 100) : 0;
            const done     = simulTime >= r.totalTime;
            const visited  = r.stops.filter(s => simulTime >= s.arrivalTime).length;
            const remaining = Math.max(0, r.totalTime - simulTime);

            return (
              <div key={r.vehicleId} style={{ display: "flex", alignItems: "center", gap: 10, flex: "1 1 200px" }}>
                <span style={{
                  width: 26, height: 26, borderRadius: "50%", flexShrink: 0,
                  background: r.color, display: "grid", placeItems: "center",
                  fontSize: "0.68rem", fontWeight: 900, color: "#fff",
                  boxShadow: done ? "none" : `0 0 10px ${r.color}88`,
                }}>
                  {r.vehicleId + 1}
                </span>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
                  <div style={{ height: 5, borderRadius: 3, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                    <div style={{
                      height: "100%", borderRadius: 3,
                      background: done ? "#1f7a56" : r.color,
                      width: `${pct}%`,
                      transition: playing ? "none" : "width 0.15s",
                      boxShadow: done ? "none" : `0 0 6px ${r.color}66`,
                    }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: "rgba(255,255,255,0.35)" }}>
                    <span>{visited}/{r.stops.length} stops</span>
                    <span>{done ? "✓ Terminé" : `−${fmtTime(remaining)}`}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
