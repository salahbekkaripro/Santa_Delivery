"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

const MapboxSurfaceClient = dynamic(() => import("./mapbox-surface-client"), { ssr: false });
const LeafletSurfaceClient = dynamic(() => import("./map-surface-client"), { ssr: false });

export function MapSurface(props: any) {
  const [viewMode, setViewMode] = useState<"3d" | "2d">("3d");

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
      {viewMode === "3d" ? (
        <MapboxSurfaceClient {...props} />
      ) : (
        <LeafletSurfaceClient {...props} />
      )}
    </div>
  );
}

