"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { MapImmersion } from "@/components/map-immersion";
import type { AdjacentNode, ClientPoint, MapInteractionState, RouteSegment } from "@/lib/types";

const MapboxSurfaceClient = dynamic(() => import("./mapbox-surface-client"), { ssr: false });
const LeafletSurfaceClient = dynamic(() => import("./map-surface-client"), { ssr: false });
const HAS_MAPBOX_TOKEN = Boolean(process.env.NEXT_PUBLIC_MAPBOX_TOKEN?.trim());
const MAP_VIEW_MODE_STORAGE_KEY = "map.surface.view_mode";

type PreviewOption = {
  geometry: [number, number][];
  label?: string;
  dist_m?: number;
  time_s?: number;
  is_feasible?: boolean;
  feasibility_badges?: string[];
  route_key?: string;
};

type MapSurfaceProps = {
  depot: ClientPoint;
  clients: ClientPoint[];
  humanSegments?: RouteSegment[];
  aiSegments?: RouteSegment[];
  returnSegments?: RouteSegment[];
  incidentSegments?: RouteSegment[];
  previewOptions?: PreviewOption[];
  selectedPreviewIndex?: number;
  assignedClientIds?: number[];
  humanStopMetaByClient?: Record<number, { sleigh_id: number; stop_order: number; arrival_eta_s: number; arrival_clock: string }>;
  onClientSelect?: (clientId: number) => void;
  onMapClick?: (lat: number, lon: number) => void;
  adjacentOptions?: AdjacentNode[];
  futureOptions?: AdjacentNode[];
  onAdjacentSelect?: (node: AdjacentNode) => void;
  onPreviewRouteConfirm?: (optionIndex: number) => void;
  onUndoLastSegment?: () => void;
  undoPending?: boolean;
  undoDisabled?: boolean;
  overlayMessage?: string | null;
  interactionState?: MapInteractionState;
  showHuman?: boolean;
  showAi?: boolean;
  selectedClientId?: number | null;
};

export function MapSurface(props: MapSurfaceProps) {
  const [viewMode, setViewMode] = useState<"3d" | "2d">("2d");

  useEffect(() => {
    if (!HAS_MAPBOX_TOKEN) return;
    const saved = window.localStorage.getItem(MAP_VIEW_MODE_STORAGE_KEY);
    if (saved === "2d" || saved === "3d") {
      setViewMode(saved);
    }
  }, []);

  useEffect(() => {
    if (!HAS_MAPBOX_TOKEN) return;
    window.localStorage.setItem(MAP_VIEW_MODE_STORAGE_KEY, viewMode);
  }, [viewMode]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {/* --- Switch de Vue --- */}
      <div style={{ 
        position: "absolute", 
        top: 10, 
        right: 10, 
        zIndex: 1000, 
        display: "flex", 
        gap: "4px",
        background: "rgba(255,255,255,0.9)",
        padding: "4px",
        borderRadius: "12px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        border: "1px solid var(--border)"
      }}>
        {HAS_MAPBOX_TOKEN ? (
          <button 
            onClick={() => setViewMode("3d")}
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
              background: viewMode === "3d" ? "var(--accent)" : "transparent",
              color: viewMode === "3d" ? "white" : "var(--text)",
              fontSize: "0.8rem",
              fontWeight: "bold",
              transition: "all 0.2s"
            }}
          >
            🏙️ 3D (Mapbox)
          </button>
        ) : null}
        <button 
          onClick={() => setViewMode("2d")}
          style={{
            padding: "6px 12px",
            borderRadius: "8px",
            border: "none",
            cursor: "pointer",
            background: viewMode === "2d" ? "var(--accent)" : "transparent",
            color: viewMode === "2d" ? "white" : "var(--text)",
            fontSize: "0.8rem",
            fontWeight: "bold",
            transition: "all 0.2s"
          }}
        >
          🗺️ 2D (Leaflet)
        </button>
      </div>

      {/* --- Affichage conditionnel --- */}
      {viewMode === "3d" && HAS_MAPBOX_TOKEN ? (
        <MapboxSurfaceClient {...props} />
      ) : (
        <LeafletSurfaceClient {...props} />
      )}
      {!HAS_MAPBOX_TOKEN ? (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "absolute",
            top: 64,
            right: 10,
            zIndex: 1001,
            maxWidth: "min(360px, calc(100% - 20px))",
            background: "rgba(255, 245, 236, 0.97)",
            border: "1px solid rgba(184, 137, 47, 0.35)",
            color: "#6d4c08",
            borderRadius: 12,
            padding: "8px 10px",
            boxShadow: "0 8px 18px rgba(18, 50, 71, 0.18)",
            fontSize: "0.8rem",
            lineHeight: 1.35,
          }}
        >
          Vue 3D indisponible: configure <code>NEXT_PUBLIC_MAPBOX_TOKEN</code>.
        </div>
      ) : null}
      <MapImmersion />
      {props.overlayMessage ? (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "absolute",
            top: 64,
            left: 10,
            zIndex: 1001,
            maxWidth: "min(420px, calc(100% - 20px))",
            background: "rgba(255, 245, 236, 0.97)",
            border: "1px solid rgba(158, 47, 63, 0.25)",
            color: "#69222d",
            borderRadius: 12,
            padding: "8px 10px",
            boxShadow: "0 8px 18px rgba(18, 50, 71, 0.18)",
            fontSize: "0.84rem",
            lineHeight: 1.35,
          }}
        >
          {props.overlayMessage}
        </div>
      ) : null}
      {props.onUndoLastSegment ? (
        <button
          type="button"
          className="secondary-button"
          onClick={props.onUndoLastSegment}
          disabled={Boolean(props.undoDisabled) || Boolean(props.undoPending)}
          style={{
            position: "absolute",
            right: 12,
            bottom: 12,
            zIndex: 1001,
            minWidth: 128,
            padding: "10px 14px",
            borderRadius: 12,
            boxShadow: "0 10px 22px rgba(18, 50, 71, 0.22)",
          }}
        >
          {props.undoPending ? "Annulation..." : "↩ Undo"}
        </button>
      ) : null}
    </div>
  );
}
