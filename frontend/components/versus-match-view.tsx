"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";
import { usePlayer } from "@/components/player-provider";
import { getVersusMatchState, setVersusReady, submitVersusAttempt } from "@/lib/api";
import { ruleLabel } from "@/lib/versus";

function statusLabel(status: string) {
  if (status === "waiting_opponent") return "En attente adversaire";
  if (status === "waiting_ready") return "Prêt à démarrer";
  if (status === "live") return "En cours";
  if (status === "finished") return "Terminé";
  return status;
}

function asClock(seconds: number | null | undefined) {
  if (!seconds || seconds <= 0) return "00:00";
  const min = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);
  return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export function VersusMatchView({ matchId }: { matchId: string }) {
  const { player, isReady } = usePlayer();

  const stateQuery = useQuery({
    queryKey: ["versus-match", matchId, player?.id],
    queryFn: () => getVersusMatchState(matchId, player!.id),
    enabled: Boolean(player?.id),
    refetchInterval: 1000,
  });

  const readyMutation = useMutation({
    mutationFn: () => setVersusReady(matchId, { player_id: player!.id, ready: true }),
    onSuccess: () => stateQuery.refetch(),
  });

  const submitMutation = useMutation({
    mutationFn: () => submitVersusAttempt(matchId, { player_id: player!.id }),
    onSuccess: () => stateQuery.refetch(),
  });

  const payload = stateQuery.data;
  const selfParticipant = useMemo(
    () => payload?.participants.find((participant) => participant.is_self),
    [payload?.participants],
  );
  const opponent = useMemo(
    () => payload?.participants.find((participant) => !participant.is_self),
    [payload?.participants],
  );

  if (!isReady) {
    return <div className="page-shell"><div className="page-stack"><div className="panel">Chargement...</div></div></div>;
  }

  if (!player) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="panel">
            Connexion requise pour voir ce match.
          </section>
        </div>
      </div>
    );
  }

  if (stateQuery.isLoading || !payload) {
    return <div className="page-shell"><div className="page-stack"><div className="panel">Chargement du duel...</div></div></div>;
  }

  if (stateQuery.error) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="error-box">{String((stateQuery.error as Error).message)}</section>
        </div>
      </div>
    );
  }

  const isLive = payload.status === "live";
  const isFinished = payload.status === "finished";
  const isSelfReady = selfParticipant?.state === "ready" || selfParticipant?.state === "live" || selfParticipant?.state === "submitted";
  const canSubmit = isLive && selfParticipant?.state !== "submitted" && selfParticipant?.state !== "forfeit";
  const mapSummary = payload.mission_summary;

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Duel {payload.template_label ?? payload.template_id}</h1>
          <div className="hero-badges">
            <span className="hero-badge">{statusLabel(payload.status)}</span>
            <span className="hero-badge">Règle: {ruleLabel(payload.winner_rule)}</span>
            <span className="hero-badge">Chrono: {asClock(payload.started_elapsed_s)}</span>
            {payload.join_code && <span className="hero-badge">Code: {payload.join_code}</span>}
          </div>
        </section>

        <section className="panel stack">
          <strong>Carte du match</strong>
          <span>
            Source: {payload.map_source === "custom" ? "Custom" : "Template"} · {mapSummary?.template_label ?? payload.template_id}
          </span>
          <span className="muted">
            Zone: {mapSummary?.zone ?? "--"} · Colis: {mapSummary?.num_clients ?? "--"} · Météo: {mapSummary?.weather_key ?? "--"}
          </span>
          <span className="muted">
            Budget: {mapSummary?.budget ?? "--"} · Coût traîneau: {mapSummary?.sleigh_cost ?? "--"} · IA: {mapSummary?.ai_profile ?? "--"}
          </span>
          {(typeof mapSummary?.center_lat === "number" || typeof mapSummary?.center_lon === "number" || typeof mapSummary?.search_radius_km === "number") && (
            <span className="muted">
              Centre: {mapSummary?.center_lat ?? "--"}, {mapSummary?.center_lon ?? "--"} · Rayon: {mapSummary?.search_radius_km ?? "--"} km
            </span>
          )}
        </section>

        <section className="grid-2">
          <div className="panel stack">
            <strong>Vous</strong>
            <span>{selfParticipant?.avatar ?? "🎅"} {selfParticipant?.display_name ?? player.display_name}</span>
            <span className="muted">Etat: {selfParticipant?.state ?? "joined"}</span>
            {typeof selfParticipant?.score === "number" && <span className="muted">Score: {selfParticipant.score}</span>}
            {typeof selfParticipant?.total_time_s === "number" && <span className="muted">Temps: {Math.round(selfParticipant.total_time_s / 60)} min</span>}
            {selfParticipant?.forfeit_deadline_at && <span className="muted">Deadline AFK: {new Date(selfParticipant.forfeit_deadline_at).toLocaleTimeString("fr-FR")}</span>}
          </div>

          <div className="panel stack">
            <strong>Adversaire</strong>
            <span>{opponent?.avatar ?? "🎄"} {opponent?.display_name ?? opponent?.player_id ?? "En attente"}</span>
            <span className="muted">Etat: {opponent?.state ?? "waiting"}</span>
            {typeof opponent?.score === "number" && <span className="muted">Score: {opponent.score}</span>}
            {typeof opponent?.total_time_s === "number" && <span className="muted">Temps: {Math.round(opponent.total_time_s / 60)} min</span>}
            {opponent?.forfeit_deadline_at && <span className="muted">Deadline AFK: {new Date(opponent.forfeit_deadline_at).toLocaleTimeString("fr-FR")}</span>}
          </div>
        </section>

        <section className="panel stack">
          <strong>Actions match</strong>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              className="primary-button"
              onClick={() => readyMutation.mutate()}
              disabled={readyMutation.isPending || isSelfReady || payload.status !== "waiting_ready"}
            >
              {readyMutation.isPending ? "Validation..." : isSelfReady ? "Prêt" : "Je suis prêt"}
            </button>

            {payload.current_player_mission_id ? (
              <Link className="secondary-button" href={`/mission/${payload.current_player_mission_id}?versus_match_id=${payload.match_id}`}>
                Ouvrir ma mission
              </Link>
            ) : (
              <button className="secondary-button" disabled>
                Mission non assignée
              </button>
            )}

            <button
              className="primary-button"
              onClick={() => submitMutation.mutate()}
              disabled={submitMutation.isPending || !canSubmit}
            >
              {submitMutation.isPending ? "Soumission..." : "Soumettre ma tentative"}
            </button>
          </div>
          {canSubmit && (
            <span className="muted">
              Soumission autorisée uniquement si tous les clients sont assignés sur ta mission.
            </span>
          )}
        </section>

        {isFinished && (
          <section className="panel stack">
            <strong>Résultat</strong>
            <span>
              Gagnant: {payload.participants.find((participant) => participant.player_id === payload.winner_player_id)?.display_name ?? payload.winner_player_id}
            </span>
            <span className="muted">Motif: {payload.result_reason ?? "submitted"}</span>
            <Link className="secondary-button" href="/leaderboard?mode=versus">Voir le classement versus</Link>
          </section>
        )}

        <section className="panel stack">
          <Link className="secondary-button" href="/versus">← Retour choix mode</Link>
        </section>
      </div>
    </div>
  );
}
