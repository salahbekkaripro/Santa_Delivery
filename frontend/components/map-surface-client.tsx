"use client";

import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Pane, Polyline, Popup, TileLayer, Tooltip, Marker } from "react-leaflet";
import L from "leaflet";
import type { ClientPoint, RouteSegment } from "@/lib/types";

type Props = {
  depot: ClientPoint;
  clients: ClientPoint[];
  humanSegments?: RouteSegment[];
  aiSegments?: RouteSegment[];
  returnSegments?: RouteSegment[];
  incidentSegments?: RouteSegment[];
  previewOptions?: Array<{ geometry: [number, number][]; label?: string; dist_m?: number; time_s?: number }>;
  selectedPreviewIndex?: number;
  assignedClientIds?: number[];
  humanStopMetaByClient?: Record<number, { sleigh_id: number; stop_order: number; arrival_eta_s: number; arrival_clock: string }>;
  onClientSelect?: (clientId: number) => void;
  showHuman?: boolean;
  showAi?: boolean;
  selectedClientId?: number | null;
};

function segmentKey(segment: RouteSegment, index: number) {
  return `${segment.variant}-${segment.sleigh_id}-${segment.from_id}-${segment.to_id}-${index}`;
}

function formatMinutes(seconds?: number) {
  const m = Math.round((seconds ?? 0) / 60);
  return `${m} min`;
}

function formatDistance(meters?: number) {
  return `${((meters ?? 0) / 1000).toFixed(2)} km`;
}

const santaIcon = L.divIcon({
  html: '<div style="font-size: 24px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3))">🎅</div>',
  className: "custom-div-icon",
  iconSize: [30, 30],
  iconAnchor: [15, 15]
});

const robotIcon = L.divIcon({
  html: '<div style="font-size: 24px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3))">🤖</div>',
  className: "custom-div-icon",
  iconSize: [30, 30],
  iconAnchor: [15, 15]
});

function getPositionAtTime(segments: RouteSegment[], time: number): [number, number] | null {
  if (segments.length === 0) return null;
  
  // Sort segments by index
  const sorted = [...segments].sort((a, b) => (a.segment_idx ?? 0) - (b.segment_idx ?? 0));
  
  let accumulatedTime = 0;
  for (const seg of sorted) {
    const start = accumulatedTime;
    const end = accumulatedTime + seg.time_s;
    
    if (time >= start && time <= end) {
      const ratio = (time - start) / (seg.time_s || 1);
      const points = seg.geometry;
      if (points.length === 0) return null;
      if (points.length === 1) return points[0];
      
      const pointIdx = Math.floor(ratio * (points.length - 1));
      const nextIdx = Math.min(pointIdx + 1, points.length - 1);
      const localRatio = (ratio * (points.length - 1)) - pointIdx;
      
      const p1 = points[pointIdx];
      const p2 = points[nextIdx];
      
      return [
        p1[0] + (p2[0] - p1[0]) * localRatio,
        p1[1] + (p2[1] - p1[1]) * localRatio
      ];
    }
    accumulatedTime = end;
  }
  
  const lastSeg = sorted[sorted.length - 1];
  return lastSeg.geometry[lastSeg.geometry.length - 1];
}

export default function MapSurfaceClient({
  depot,
  clients,
  humanSegments = [],
  aiSegments = [],
  returnSegments = [],
  incidentSegments = [],
  previewOptions = [],
  selectedPreviewIndex = 0,
  assignedClientIds = [],
  humanStopMetaByClient = {},
  onClientSelect,
  showHuman = true,
  showAi = true,
  selectedClientId
}: Props) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(60); // 1s réelle = 60s simulation

  const assigned = new Set(assignedClientIds);

  // Group segments by sleigh for animation
  const humanSleighPaths = useMemo(() => {
    const groups: Record<number, RouteSegment[]> = {};
    [...humanSegments, ...returnSegments].forEach(s => {
      if (!groups[s.sleigh_id]) groups[s.sleigh_id] = [];
      groups[s.sleigh_id].push(s);
    });
    return groups;
  }, [humanSegments, returnSegments]);

  const aiSleighPaths = useMemo(() => {
    const groups: Record<number, RouteSegment[]> = {};
    aiSegments.forEach(s => {
      if (!groups[s.sleigh_id]) groups[s.sleigh_id] = [];
      groups[s.sleigh_id].push(s);
    });
    return groups;
  }, [aiSegments]);

  const maxTime = useMemo(() => {
    let max = 0;
    Object.values(humanSleighPaths).forEach(segs => {
      const total = segs.reduce((sum, s) => sum + s.time_s, 0);
      if (total > max) max = total;
    });
    Object.values(aiSleighPaths).forEach(segs => {
      const total = segs.reduce((sum, s) => sum + s.time_s, 0);
      if (total > max) max = total;
    });
    return max || 3600;
  }, [humanSleighPaths, aiSleighPaths]);

  useEffect(() => {
    let interval: any;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentTime(t => {
          const next = t + (playbackSpeed / 10); // assuming 100ms interval
          return next > maxTime ? (setIsPlaying(false), maxTime) : next;
        });
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, maxTime]);

  const humanMarkers = useMemo(() => {
    if (!showHuman) return [];
    return Object.entries(humanSleighPaths).map(([id, segs]) => {
      const pos = getPositionAtTime(segs, currentTime);
      return pos ? { id, pos } : null;
    }).filter(m => m !== null);
  }, [humanSleighPaths, currentTime, showHuman]);

  const aiMarkers = useMemo(() => {
    if (!showAi) return [];
    return Object.entries(aiSleighPaths).map(([id, segs]) => {
      const pos = getPositionAtTime(segs, currentTime);
      return pos ? { id, pos } : null;
    }).filter(m => m !== null);
  }, [aiSleighPaths, currentTime, showAi]);

  return (
    <div className="leaflet-shell" style={{ position: "relative" }}>
      <MapContainer center={[depot.lat, depot.lon]} zoom={14} style={{ height: "100%", minHeight: 640, width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />

        <Pane name="ai" style={{ zIndex: 420 }} />
        <Pane name="human" style={{ zIndex: 430 }} />
        <Pane name="points" style={{ zIndex: 460 }} />

        {showAi &&
          aiSegments.map((segment, index) => (
            <Polyline
              key={segmentKey(segment, index)}
              positions={segment.geometry}
              pathOptions={{ color: "#143c5a", weight: 5, opacity: 0.3 }}
              pane="ai"
            />
          ))}

        {showHuman &&
          humanSegments.map((segment, index) => (
            <Polyline
              key={segmentKey(segment, index)}
              positions={segment.geometry}
              pathOptions={{ color: "#c1452f", weight: 6, opacity: 0.3, dashArray: "8 10" }}
              pane="human"
            />
          ))}

        {/* Animated Markers */}
        {humanMarkers.map(m => (
          <Marker key={`h-marker-${m!.id}`} position={m!.pos as [number, number]} icon={santaIcon} zIndexOffset={1000} />
        ))}
        {aiMarkers.map(m => (
          <Marker key={`a-marker-${m!.id}`} position={m!.pos as [number, number]} icon={robotIcon} zIndexOffset={1000} />
        ))}

        {previewOptions.map((option, index) => {
          const isSelected = index === selectedPreviewIndex;
          return (
            <Polyline
              key={`preview-${index}`}
              positions={option.geometry}
              pathOptions={{
                color: isSelected ? "#d97706" : "#6b7280",
                weight: isSelected ? 7 : 4,
                opacity: isSelected ? 0.9 : 0.35,
                dashArray: isSelected ? undefined : "6 10"
              }}
              pane="human"
            >
              <Tooltip sticky>{option.label ?? `Option ${index + 1}`}</Tooltip>
              <Popup>
                <div style={{ display: "grid", gap: 4, minWidth: 190 }}>
                  <strong>{option.label ?? `Option ${index + 1}`}</strong>
                  {option.time_s !== undefined ? <span>Temps: {formatMinutes(option.time_s)}</span> : null}
                  {option.dist_m !== undefined ? <span>Distance: {formatDistance(option.dist_m)}</span> : null}
                </div>
              </Popup>
            </Polyline>
          );
        })}

        {incidentSegments.map((segment, index) => (
          <Polyline
            key={`incident-${segmentKey(segment, index)}`}
            positions={segment.geometry}
            pathOptions={{ color: "#991b1b", weight: 5, opacity: 0.75, dashArray: "3 8" }}
            pane="ai"
          />
        ))}

        <CircleMarker
          center={[depot.lat, depot.lon]}
          radius={11}
          pathOptions={{ color: "#ffffff", weight: 3 }}
          fillColor="#111827"
          fillOpacity={1}
          pane="points"
        />

        {clients.map((client) => {
          const isAssigned = assigned.has(client.id);
          const isSelected = selectedClientId === client.id;
          const stopMeta = humanStopMetaByClient[client.id];
          return (
            <CircleMarker
              key={client.id}
              center={[client.lat, client.lon]}
              radius={isSelected ? 10 : 8}
              pathOptions={{ color: "#ffffff", weight: 2 }}
              fillColor={isAssigned ? "#1f8f5f" : isSelected ? "#d97706" : "#c1452f"}
              fillOpacity={0.92}
              pane="points"
              eventHandlers={onClientSelect ? { click: () => onClientSelect(client.id) } : undefined}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                {isAssigned && stopMeta
                  ? `${client.nom_client} · T${stopMeta.sleigh_id + 1} · Stop ${stopMeta.stop_order} · ${stopMeta.arrival_clock}`
                  : client.nom_client}
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>

      {/* Animation Controls Overlay */}
      <div className="animation-controls panel stack" style={{
        position: "absolute",
        bottom: 20,
        left: 20,
        zIndex: 1000,
        width: 300,
        background: "rgba(255, 255, 255, 0.95)"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong>🏎️ Replay Temporel</strong>
          <span className="muted">{formatMinutes(currentTime)} / {formatMinutes(maxTime)}</span>
        </div>
        
        <input 
          type="range" 
          min={0} 
          max={maxTime} 
          value={currentTime} 
          onChange={(e) => setCurrentTime(Number(e.target.value))}
          style={{ width: "100%" }}
        />

        <div style={{ display: "flex", gap: 10 }}>
          <button className="primary-button" onClick={() => setIsPlaying(!isPlaying)} style={{ flex: 1 }}>
            {isPlaying ? "⏸️ Pause" : "▶️ Play"}
          </button>
          <button className="secondary-button" onClick={() => { setCurrentTime(0); setIsPlaying(false); }} style={{ flex: 0.5 }}>
            🔄 Reset
          </button>
        </div>

        <div className="field">
          <span className="muted" style={{ fontSize: "0.8rem" }}>Vitesse: x{Math.round(playbackSpeed)}</span>
          <input 
            type="range" 
            min={10} 
            max={300} 
            step={10} 
            value={playbackSpeed} 
            onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
          />
        </div>
      </div>
    </div>
  );
}
