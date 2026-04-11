import { MissionWorkspace } from "@/components/mission-workspace";

export default function MissionPage({ params }: { params: { id: string } }) {
  return <MissionWorkspace missionId={params.id} />;
}
