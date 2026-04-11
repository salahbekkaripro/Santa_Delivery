"use client";

import { CircleMarker, MapContainer, Pane, Polyline, Popup, TileLayer, Tooltip } from "react-leaflet";
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
  return `${Math.round((seconds ?? 0) / 60)} min`;
}

function formatDistance(meters?: number) {
  return `${((meters ?? 0) / 1000).toFixed(2)} km`;
}

function renderSegmentPopup(segment: RouteSegment) {
  return (
    <div style={{ display: "grid", gap: 4, minWidth: 190 }}>
      <strong>{segment.title ?? `Segment ${segment.segment_idx ?? "?"}`}</strong>
      <span>Temps: {formatMinutes(segment.time_s)}</span>
      <span>Distance: {formatDistance(segment.dist_m)}</span>
      {segment.segment_idx ? <span>Ordre: {segment.segment_idx}/{segment.segment_count ?? "?"}</span> : null}
      {segment.arrival_clock ? <span>Arrivee estimee: {segment.arrival_clock}</span> : null}
    </div>
  );
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
  const assigned = new Set(assignedClientIds);

  return (
    <div className="leaflet-shell">
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
              pathOptions={{ color: "#143c5a", weight: 5, opacity: 0.9 }}
              pane="ai"
            >
              <Tooltip sticky>{segment.title ?? `IA · ${Math.round(segment.dist_m)} m`}</Tooltip>
              <Popup>{renderSegmentPopup(segment)}</Popup>
            </Polyline>
          ))}

        {showHuman &&
          humanSegments.map((segment, index) => (
            <Polyline
              key={segmentKey(segment, index)}
              positions={segment.geometry}
              pathOptions={{ color: "#c1452f", weight: 6, opacity: 0.72, dashArray: "8 10" }}
              pane="human"
            >
              <Tooltip sticky>{segment.title ?? `Vous · ${Math.round(segment.dist_m)} m`}</Tooltip>
              <Popup>{renderSegmentPopup(segment)}</Popup>
            </Polyline>
          ))}

        {returnSegments.map((segment, index) => (
          <Polyline
            key={`return-${segmentKey(segment, index)}`}
            positions={segment.geometry}
            pathOptions={{ color: "#0f766e", weight: 4, opacity: 0.45, dashArray: "4 10" }}
            pane="human"
          >
            <Tooltip sticky>{segment.title ?? `Retour depot · ${Math.round(segment.dist_m)} m`}</Tooltip>
            <Popup>{renderSegmentPopup(segment)}</Popup>
          </Polyline>
        ))}

        {incidentSegments.map((segment, index) => (
          <Polyline
            key={`incident-${segmentKey(segment, index)}`}
            positions={segment.geometry}
            pathOptions={{ color: "#991b1b", weight: 5, opacity: 0.75, dashArray: "3 8" }}
            pane="ai"
          >
            <Tooltip sticky>{segment.title ?? `Incident`}</Tooltip>
            <Popup>{renderSegmentPopup(segment)}</Popup>
          </Polyline>
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

        <CircleMarker
          center={[depot.lat, depot.lon]}
          radius={11}
          pathOptions={{ color: "#ffffff", weight: 3 }}
          fillColor="#111827"
          fillOpacity={1}
          pane="points"
        >
          <Tooltip permanent direction="top" offset={[0, -10]}>
            Depot
          </Tooltip>
        </CircleMarker>

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
              eventHandlers={
                onClientSelect
                  ? {
                      click: () => onClientSelect(client.id)
                    }
                  : undefined
              }
            >
              <Tooltip direction="top" offset={[0, -6]}>
                {isAssigned && stopMeta
                  ? `${client.nom_client} · T${stopMeta.sleigh_id + 1} · Stop ${stopMeta.stop_order} · ${stopMeta.arrival_clock}`
                  : client.nom_client}
              </Tooltip>
              <Popup>
                <div style={{ display: "grid", gap: 4, minWidth: 180 }}>
                  <strong>{client.nom_client}</strong>
                  <span>Poids colis: {client.poids_colis} kg</span>
                  {isAssigned && stopMeta ? (
                    <>
                      <span>Traineau: #{stopMeta.sleigh_id + 1}</span>
                      <span>Stop: {stopMeta.stop_order}</span>
                      <span>Arrivee estimee: {stopMeta.arrival_clock}</span>
                    </>
                  ) : (
                    <span>Non assigne</span>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
