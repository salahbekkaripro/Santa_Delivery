"use client";

import { useEffect } from "react";
import { Circle, CircleMarker, MapContainer, TileLayer, useMap } from "react-leaflet";

function FitCircleBounds({ centerLat, centerLon, radiusKm }: { centerLat: number; centerLon: number; radiusKm: number }) {
  const map = useMap();
  useEffect(() => {
    const latSpan = radiusKm / 111.0;
    const lonSpan = radiusKm / Math.max(0.2, 111.0 * Math.cos((centerLat * Math.PI) / 180.0));
    map.fitBounds(
      [
        [centerLat - latSpan, centerLon - lonSpan],
        [centerLat + latSpan, centerLon + lonSpan],
      ],
      { padding: [24, 24] }
    );
  }, [centerLat, centerLon, radiusKm, map]);
  return null;
}

export default function SearchAreaMapClient({
  centerLat,
  centerLon,
  radiusKm,
}: {
  centerLat: number;
  centerLon: number;
  radiusKm: number;
}) {
  return (
    <div className="search-area-map-frame">
      <MapContainer
        center={[centerLat, centerLon]}
        zoom={12}
        style={{ width: "100%", height: 280 }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <FitCircleBounds centerLat={centerLat} centerLon={centerLon} radiusKm={radiusKm} />
        <Circle
          center={[centerLat, centerLon]}
          radius={radiusKm * 1000}
          pathOptions={{ color: "#9e2f3f", weight: 2, fillColor: "#9e2f3f", fillOpacity: 0.12 }}
        />
        <CircleMarker
          center={[centerLat, centerLon]}
          radius={7}
          pathOptions={{ color: "#17324d", weight: 2, fillColor: "#17324d", fillOpacity: 0.9 }}
        />
      </MapContainer>
    </div>
  );
}
