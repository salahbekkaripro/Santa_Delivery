"use client";

import { useMemo } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip } from "react-leaflet";
import type { DijkstraResult } from "@/lib/types";

type Props = {
  result: DijkstraResult;
  currentStep: number;
};

export default function ExploreDijkstraMap({ result, currentStep }: Props) {
  const { steps, path } = result;
  const visibleSteps = steps.slice(0, currentStep + 1);
  const currentStepData = steps[currentStep];

  const nodeLatLon = useMemo(() => {
    const map = new Map<number, [number, number]>();
    for (const s of steps) map.set(s.node, [s.lat, s.lon]);
    return map;
  }, [steps]);

  const center: [number, number] = steps[0] ? [steps[0].lat, steps[0].lon] : [48.86, 2.35];

  const pathCoords = useMemo<[number, number][]>(() => {
    if (currentStep < steps.length - 1) return [];
    return path.map((id) => nodeLatLon.get(id)).filter(Boolean) as [number, number][];
  }, [currentStep, steps.length, path, nodeLatLon]);

  return (
    <MapContainer center={center} zoom={14} style={{ width: "100%", height: 440, borderRadius: 16 }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="© OpenStreetMap"
      />

      {visibleSteps.map((step) => {
        const isCurrent = step.node === currentStepData?.node;
        const isSource = step.node === result.from_node;
        const isDest = step.node === result.to_node;
        return (
          <CircleMarker
            key={step.node}
            center={[step.lat, step.lon]}
            radius={isCurrent ? 11 : isDest || isSource ? 10 : 5}
            pathOptions={{
              color: isCurrent
                ? "#9e2f3f"
                : isSource
                  ? "#17324d"
                  : isDest
                    ? "#1f7a56"
                    : "#7a8fa6",
              fillColor: isCurrent
                ? "#9e2f3f"
                : isSource
                  ? "#17324d"
                  : isDest
                    ? "#1f7a56"
                    : "#aab8c6",
              fillOpacity: isCurrent ? 1 : 0.7,
              weight: isCurrent ? 3 : 1,
            }}
          >
            <Tooltip>
              {isSource ? "Départ" : isDest ? "Arrivée" : `Étape ${step.step}`}
              {" · "}{step.dist.toFixed(0)}s
              {step.predecessor != null ? ` · pred ${step.predecessor}` : ""}
            </Tooltip>
          </CircleMarker>
        );
      })}

      {pathCoords.length > 1 && (
        <Polyline
          positions={pathCoords}
          pathOptions={{ color: "#1f7a56", weight: 5, opacity: 0.85 }}
        />
      )}
    </MapContainer>
  );
}
