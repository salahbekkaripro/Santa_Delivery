import { DebriefView } from "@/components/debrief-view";

export default function MissionDebriefPage({ params }: { params: { id: string } }) {
  return <DebriefView missionId={params.id} />;
}
