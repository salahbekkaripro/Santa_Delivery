import { ResultsView } from "@/components/results-view";

export default function MissionResultsPage({ params }: { params: { id: string } }) {
  return <ResultsView missionId={params.id} />;
}

