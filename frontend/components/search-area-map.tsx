"use client";

import dynamic from "next/dynamic";

const SearchAreaMapClient = dynamic(() => import("./search-area-map-client"), { ssr: false });

export function SearchAreaMap(props: { centerLat: number; centerLon: number; radiusKm: number }) {
  return <SearchAreaMapClient {...props} />;
}
