import { VersusMatchView } from "@/components/versus-match-view";

export default function VersusMatchPage({ params }: { params: { id: string } }) {
  return <VersusMatchView matchId={params.id} />;
}
