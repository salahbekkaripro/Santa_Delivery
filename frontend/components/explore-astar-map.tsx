"use client";

import { useMemo } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip } from "react-leaflet";
import type { AstarCompareResult } from "@/lib/types";

type Props = {
  result: AstarCompareResult;
  currentStep: number;
};

export default function ExploreAstarMap({ result, currentStep }: Props) {
  const allSteps = useMemo(
    () => [...result.steps_forward, ...result.steps_backward].sort((a, b) => a.step - b.step),
    [result.steps_forward, result.steps_backward],
  );

  const visibleSteps = allSteps.slice(0, currentStep + 1);

  const nodeLatLon = useMemo(() => {
    const map = new Map<number, [number, number]>();
    for (const s of allSteps) map.set(s.node, [s.lat, s.lon]);
    return map;
  }, [allSteps]);

  const center: [number, number] = allSteps[0]
    ? [allSteps[0].lat, allSteps[0].lon]
    : [48.86, 2.35];

  const pathCoords = useMemo<[number, number][]>(() => {
    if (currentStep < allSteps.length - 1) return [];
    return result.path.map((id) => nodeLatLon.get(id)).filter(Boolean) as [number, number][];
  }, [currentStep, allSteps.length, result.path, nodeLatLon]);

  const currentNode = visibleSteps[visibleSteps.length - 1]?.node;

  return (
    <MapContainer center={center} zoom={14} style={{ width: "100%", height: 440, borderRadius: 16 }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="© OpenStreetMap"
      />

      {visibleSteps.map((step) => {
        const isCurrent = step.node === currentNode;
        const isSource = step.node === result.from_node;
        const isDest = step.node === result.to_node;
        const isMeeting = step.node === result.meeting_node;
        const isForward = step.direction === "forward";

        let color: string;
        if (isMeeting) color = "#d4a017";
        else if (isCurrent) color = isForward ? "#1a6fb5" : "#9e2f3f";
        else if (isSource) color = "#17324d";
        else if (isDest) color = "#1f7a56";
        else color = isForward ? "#5b9bd5" : "#c47a85";

        let fillColor: string;
        if (isMeeting) fillColor = "#d4a017";
        else if (isSource) fillColor = "#17324d";
        else if (isDest) fillColor = "#1f7a56";
        else fillColor = isForward ? "#8ab4d8" : "#d4a3ab";

        return (
          <CircleMarker
            key={`${step.direction}-${step.node}`}
            center={[step.lat, step.lon]}
            radius={isCurrent || isMeeting ? 10 : isSource || isDest ? 9 : 5}
            pathOptions={{
              color,
              fillColor,
              fillOpacity: isCurrent || isMeeting ? 1 : 0.75,
              weight: isCurrent || isMeeting ? 3 : 1,
            }}
          >
            <Tooltip>
              {isSource ? "Départ" : isDest ? "Arrivée" : isMeeting ? "Point de rencontre" : `${isForward ? "Avant" : "Arrière"} étape ${step.step}`}
              {" · g="}{step.g.toFixed(0)}s
              {" · f="}{step.f.toFixed(0)}s
            </Tooltip>
          </CircleMarker>
        );
      })}

      {pathCoords.length > 1 && (
        <Polyline
          positions={pathCoords}
          pathOptions={{ color: "#1f7a56", weight: 5, opacity: 0.9 }}
        />
      )}
    </MapContainer>
  );
}
