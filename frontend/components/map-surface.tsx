import dynamic from "next/dynamic";

export const MapSurface = dynamic(() => import("./map-surface-client"), {
  ssr: false
});

