"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { AdjacentNode, ClientPoint, RouteSegment } from "@/lib/types";

// --- SECURE TOKEN ---
const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";
mapboxgl.accessToken = MAPBOX_TOKEN;

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
  onMapClick?: (lat: number, lon: number) => void;
  adjacentOptions?: AdjacentNode[];
  futureOptions?: AdjacentNode[];
  onAdjacentSelect?: (node: AdjacentNode) => void;
  showHuman?: boolean;
  showAi?: boolean;
  selectedClientId?: number | null;
};

// Helper pour convertir [lat, lon] Leaflet en [lon, lat] Mapbox
const toMapbox = (coords: [number, number][]): [number, number][] => coords.map((c) => [c[1], c[0]]);

export default function MapboxSurfaceClient({
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
  onMapClick,
  adjacentOptions = [],
  futureOptions = [],
  onAdjacentSelect,
  showHuman = true,
  showAi = true,
  selectedClientId
}: Props) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const depotMarker = useRef<mapboxgl.Marker | null>(null);
  const clientMarkers = useRef<Record<number, mapboxgl.Marker>>({});
  const clientMarkerElements = useRef<Record<number, HTMLDivElement>>({});
  const adjacentMarkers = useRef<mapboxgl.Marker[]>([]);
  const sleighMarkers = useRef<Record<string, mapboxgl.Marker>>({});

  const onMapClickRef = useRef(onMapClick);
  const onClientSelectRef = useRef(onClientSelect);
  const onAdjacentSelectRef = useRef(onAdjacentSelect);

  useEffect(() => {
    onMapClickRef.current = onMapClick;
  }, [onMapClick]);
  useEffect(() => {
    onClientSelectRef.current = onClientSelect;
  }, [onClientSelect]);
  useEffect(() => {
    onAdjacentSelectRef.current = onAdjacentSelect;
  }, [onAdjacentSelect]);

  const [isLoaded, setIsLoaded] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(60);

  const assigned = useMemo(() => new Set(assignedClientIds), [assignedClientIds]);

  // --- ANIMATION LOGIC (Simplified for Mapbox) ---
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

  // Initialisation Mapbox
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const m = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: [depot.lon, depot.lat],
      zoom: 15,
      pitch: 60,
      bearing: -17,
      antialias: true
    });

    m.on("load", () => {
      setIsLoaded(true);
      m.resize();
      m.addControl(new mapboxgl.NavigationControl(), "top-left");

      m.addLayer({
        id: "add-3d-buildings",
        source: "composite",
        "source-layer": "building",
        filter: ["==", "extrude", "true"],
        type: "fill-extrusion",
        minzoom: 14,
        paint: {
          "fill-extrusion-color": "#aaa",
          "fill-extrusion-height": ["get", "height"],
          "fill-extrusion-base": ["get", "min_height"],
          "fill-extrusion-opacity": 0.6
        }
      });

      m.addSource("human-routes", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("ai-routes", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("previews", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("incidents", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("adjacents", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addSource("future-adjacents", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

      m.addLayer({ id: "human-layer", type: "line", source: "human-routes", paint: { "line-color": "#9e2f3f", "line-width": 4, "line-dasharray": [2, 2] } });
      m.addLayer({ id: "ai-layer", type: "line", source: "ai-routes", paint: { "line-color": "#143c5a", "line-width": 5, "line-opacity": 0.8 } });
      m.addLayer({ id: "preview-layer", type: "line", source: "previews", paint: { "line-color": "#b8892f", "line-width": 6 } });
      m.addLayer({ id: "incident-layer", type: "line", source: "incidents", paint: { "line-color": "#991b1b", "line-width": 5, "line-dasharray": [1, 2] } });

      m.addLayer({ id: "future-adjacent-layer", type: "line", source: "future-adjacents", paint: { "line-color": "#3b82f6", "line-width": 2, "line-dasharray": [2, 2], "line-opacity": 0.2 } });
      m.addLayer({
        id: "future-adjacent-arrows",
        type: "symbol",
        source: "future-adjacents",
        layout: {
          "symbol-placement": "line",
          "symbol-spacing": 100,
          "text-field": "▶",
          "text-size": 8,
          "text-keep-upright": false,
          "text-allow-overlap": true,
          "text-ignore-placement": true
        },
        paint: {
          "text-color": "#3b82f6",
          "text-opacity": 0.2
        }
      });

      m.addLayer({ id: "adjacent-layer", type: "line", source: "adjacents", paint: { "line-color": "#3b82f6", "line-width": 4, "line-dasharray": [2, 2], "line-opacity": 0.6 } });
      m.addLayer({
        id: "adjacent-arrows",
        type: "symbol",
        source: "adjacents",
        layout: {
          "symbol-placement": "line",
          "symbol-spacing": 50,
          "text-field": "▶",
          "text-size": 12,
          "text-keep-upright": false,
          "text-allow-overlap": true,
          "text-ignore-placement": true
        },
        paint: {
          "text-color": "#3b82f6",
          "text-halo-color": "#ffffff",
          "text-halo-width": 1
        }
      });

      m.on("click", (e) => {
        const layers = ["human-layer", "ai-layer", "preview-layer", "incident-layer", "adjacent-layer", "adjacent-arrows"];
        const features = m.queryRenderedFeatures(e.point, { layers });
        if (features.length === 0) {
          onMapClickRef.current?.(e.lngLat.lat, e.lngLat.lng);
        }
      });
    });

    map.current = m;

    return () => {
      m.remove();
      map.current = null;
      depotMarker.current = null;
      clientMarkers.current = {};
      clientMarkerElements.current = {};
      adjacentMarkers.current = [];
      sleighMarkers.current = {};
      setIsLoaded(false);
    };
  }, [depot.lat, depot.lon]);

  useEffect(() => {
    if (!map.current || !isLoaded) {
      return;
    }
    map.current.easeTo({
      center: [depot.lon, depot.lat],
      duration: 350,
      essential: true
    });
  }, [depot.lat, depot.lon, isLoaded]);

  // Update Routes
  useEffect(() => {
    if (!map.current || !isLoaded || !map.current.isStyleLoaded()) return;

    const updateSource = (id: string, segments: RouteSegment[], visible: boolean) => {
      const source = map.current?.getSource(id) as mapboxgl.GeoJSONSource;
      if (source) {
        source.setData({
          type: 'FeatureCollection',
          features: visible ? segments.map(s => ({
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: toMapbox(s.geometry) },
            properties: {}
          })) : []
        });
      }
    };

    updateSource('human-routes', [...humanSegments, ...returnSegments], showHuman);
    updateSource('ai-routes', aiSegments, showAi);
    updateSource('incidents', incidentSegments, true);
    
    const adjSource = map.current.getSource('adjacents') as mapboxgl.GeoJSONSource;
    if (adjSource) {
      adjSource.setData({
        type: 'FeatureCollection',
        features: adjacentOptions.map(opt => ({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: toMapbox(opt.geometry) },
          properties: {}
        }))
      });
    }

    const futureSource = map.current.getSource('future-adjacents') as mapboxgl.GeoJSONSource;
    if (futureSource) {
      futureSource.setData({
        type: 'FeatureCollection',
        features: futureOptions.map(opt => ({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: toMapbox(opt.geometry) },
          properties: {}
        }))
      });
    }

    const previewSource = map.current.getSource('previews') as mapboxgl.GeoJSONSource;
    if (previewSource) {
      previewSource.setData({
        type: 'FeatureCollection',
        features: previewOptions.map((opt, idx) => ({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: toMapbox(opt.geometry) },
          properties: { selected: idx === selectedPreviewIndex }
        }))
      });
      map.current.setPaintProperty('preview-layer', 'line-opacity', ['case', ['==', ['get', 'selected'], true], 1, 0.3]);
    }
  }, [
    humanSegments,
    aiSegments,
    returnSegments,
    incidentSegments,
    adjacentOptions,
    futureOptions,
    previewOptions,
    selectedPreviewIndex,
    showHuman,
    showAi,
    isLoaded
  ]);

  // Update Markers (Clients & Depot)
  useEffect(() => {
    if (!map.current || !isLoaded) return;
    // Depot
    if (!depotMarker.current) {
      const depotEl = document.createElement("div");
      depotEl.innerHTML = "🏠";
      depotEl.style.fontSize = "24px";
      depotMarker.current = new mapboxgl.Marker(depotEl).setLngLat([depot.lon, depot.lat]).addTo(map.current);
    } else {
      depotMarker.current.setLngLat([depot.lon, depot.lat]);
    }

    // Clients (incremental diff)
    const nextClientIds = new Set<number>();
    clients.forEach((c) => {
      nextClientIds.add(c.id);

      let marker = clientMarkers.current[c.id];
      let el = clientMarkerElements.current[c.id];
      if (!marker || !el) {
        el = document.createElement("div");
        el.style.width = "16px";
        el.style.height = "16px";
        el.style.borderRadius = "50%";
        el.style.border = "2px solid white";
        el.style.cursor = "pointer";
        el.style.boxShadow = "0 2px 4px rgba(0,0,0,0.3)";
        marker = new mapboxgl.Marker(el).setLngLat([c.lon, c.lat]).addTo(map.current!);
        clientMarkers.current[c.id] = marker;
        clientMarkerElements.current[c.id] = el;
      } else {
        marker.setLngLat([c.lon, c.lat]);
      }

      const isAssigned = assigned.has(c.id);
      const isSelected = selectedClientId === c.id;
      const color = isAssigned ? "#1f8f5f" : isSelected ? "#b8892f" : "#9e2f3f";
      if (el.dataset.fill !== color) {
        el.style.backgroundColor = color;
        el.dataset.fill = color;
      }
      if (el.title !== c.nom_client) {
        el.title = c.nom_client;
      }
      el.onclick = () => onClientSelectRef.current?.(c.id);
    });

    Object.keys(clientMarkers.current).forEach((rawId) => {
      const clientId = Number(rawId);
      if (nextClientIds.has(clientId)) {
        return;
      }
      clientMarkers.current[clientId]?.remove();
      delete clientMarkers.current[clientId];
      delete clientMarkerElements.current[clientId];
    });
  }, [clients, depot.lat, depot.lon, assigned, selectedClientId, isLoaded]);

  // Adjacent Navigation Buttons
  useEffect(() => {
    if (!map.current || !isLoaded) return;

    adjacentMarkers.current.forEach(m => m.remove());
    adjacentMarkers.current = [];

    adjacentOptions.forEach(opt => {
      const el = document.createElement('div');
      el.style.width = '12px';
      el.style.height = '12px';
      el.style.borderRadius = '50%';
      el.style.backgroundColor = '#3b82f6';
      el.style.border = '2px solid white';
      el.style.boxShadow = '0 0 8px #3b82f6';
      el.style.cursor = 'pointer';
      el.title = opt.label;
      
      el.onclick = (e) => {
        e.stopPropagation();
        onAdjacentSelectRef.current?.(opt);
      };

      const marker = new mapboxgl.Marker(el)
        .setLngLat([opt.lon, opt.lat])
        .addTo(map.current!);
      adjacentMarkers.current.push(marker);
    });
  }, [adjacentOptions, isLoaded]);

  // Animation Interval
  useEffect(() => {
    let interval: any;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentTime(t => {
          const next = t + (playbackSpeed / 10);
          return next > maxTime ? (setIsPlaying(false), maxTime) : next;
        });
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, maxTime]);

  // Render Sleighs (Santa & Robot)
  useEffect(() => {
    if (!map.current || !isLoaded) return;

    const updateSleigh = (id: string, icon: string, pos: [number, number] | null) => {
      const mid = `sleigh-${id}`;
      if (!pos) {
        sleighMarkers.current[mid]?.remove();
        delete sleighMarkers.current[mid];
        return;
      }
      if (!sleighMarkers.current[mid]) {
        const el = document.createElement("div");
        el.innerHTML = icon;
        el.style.fontSize = "32px";
        el.style.filter = "drop-shadow(0 2px 4px rgba(0,0,0,0.5))";
        sleighMarkers.current[mid] = new mapboxgl.Marker(el).setLngLat(pos).addTo(map.current!);
      } else {
        sleighMarkers.current[mid].setLngLat(pos);
      }
    };

    const activeSleighIds = new Set<string>();

    // Pour chaque traineau humain
    if (showHuman) {
      Object.entries(humanSleighPaths).forEach(([id, segs]) => {
        const key = `sleigh-h-${id}`;
        activeSleighIds.add(key);
        updateSleigh(`h-${id}`, "🎅", getPositionAtTime(segs, currentTime));
      });
    }
    // Pour chaque traineau IA
    if (showAi) {
      Object.entries(aiSleighPaths).forEach(([id, segs]) => {
        const key = `sleigh-a-${id}`;
        activeSleighIds.add(key);
        updateSleigh(`a-${id}`, "🤖", getPositionAtTime(segs, currentTime));
      });
    }

    Object.entries(sleighMarkers.current).forEach(([markerId, marker]) => {
      if (activeSleighIds.has(markerId)) {
        return;
      }
      marker.remove();
      delete sleighMarkers.current[markerId];
    });
  }, [currentTime, showHuman, showAi, humanSleighPaths, aiSleighPaths, isLoaded]);

  return (
    <div className="mapbox-shell" style={{ position: "relative", width: '100%', height: '100%', borderRadius: '22px', overflow: 'hidden' }}>
      <div ref={mapContainer} style={{ width: '100%', height: '640px' }} />
      
      {/* Animation Controls */}
      <div className="animation-controls panel stack" style={{
        position: "absolute",
        bottom: 20,
        left: 20,
        zIndex: 10,
        width: 280,
        background: "rgba(255, 255, 255, 0.95)"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong>🏙️ Replay 3D</strong>
          <span className="muted">{Math.round(currentTime/60)} min</span>
        </div>
        
        <input type="range" min={0} max={maxTime} value={currentTime} onChange={(e) => setCurrentTime(Number(e.target.value))} style={{ width: "100%" }} />

        <div style={{ display: "flex", gap: 10 }}>
          <button className="primary-button" onClick={() => setIsPlaying(!isPlaying)} style={{ flex: 1 }}>
            {isPlaying ? "⏸️ Pause" : "▶️ Play"}
          </button>
          <button className="secondary-button" onClick={() => { setCurrentTime(0); setIsPlaying(false); }} style={{ flex: 0.5 }}>🔄</button>
        </div>
      </div>
    </div>
  );
}

// Re-using the logic from Leaflet for consistency
function getPositionAtTime(segments: RouteSegment[], time: number): [number, number] | null {
  if (segments.length === 0) return null;
  const sorted = [...segments].sort((a, b) => (a.segment_idx ?? 0) - (b.segment_idx ?? 0));
  let accumulatedTime = 0;
  for (const seg of sorted) {
    const start = accumulatedTime;
    const end = accumulatedTime + seg.time_s;
    if (time >= start && time <= end) {
      const ratio = (time - start) / (seg.time_s || 1);
      const points = seg.geometry;
      if (points.length < 2) return points[0] ? [points[0][1], points[0][0]] : null;
      const pointIdx = Math.floor(ratio * (points.length - 1));
      const nextIdx = Math.min(pointIdx + 1, points.length - 1);
      const localRatio = (ratio * (points.length - 1)) - pointIdx;
      const p1 = points[pointIdx];
      const p2 = points[nextIdx];
      return [
        p1[1] + (p2[1] - p1[1]) * localRatio,
        p1[0] + (p2[0] - p1[0]) * localRatio
      ];
    }
    accumulatedTime = end;
  }
  const lastSeg = sorted[sorted.length - 1];
  const lastP = lastSeg.geometry[lastSeg.geometry.length - 1];
  return [lastP[1], lastP[0]];
}
