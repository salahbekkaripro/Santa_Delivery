import dynamic from "next/dynamic";

const MissionWorkspace = dynamic(
  () => import("@/components/mission-workspace").then((mod) => mod.MissionWorkspace),
  {
    ssr: false,
    loading: () => (
      <div className="page-shell">
        <div className="page-stack">
          <div className="hero" style={{ height: 120 }}>
            <div className="skeleton-bar h-lg w-60" style={{ marginBottom: 12 }} />
            <div className="skeleton-bar h-sm w-80" />
          </div>
          <div className="panel-loading" style={{ height: 560 }} />
        </div>
      </div>
    ),
  },
);

export default function MissionPage({ params }: { params: { id: string } }) {
  return <MissionWorkspace missionId={params.id} />;
}
