"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useMemo } from "react";
import { GuidedOnboarding, type GuidedOnboardingStep } from "@/components/guided-onboarding";
import { usePlayer } from "@/components/player-provider";
import { getVersusMatchState, setVersusReady, submitVersusAttempt } from "@/lib/api";
import { useVersusLiveState } from "@/lib/versus-live";
import { ruleLabel } from "@/lib/versus";

function statusLabel(status: string) {
  if (status === "waiting_opponent") return "En attente adversaire";
  if (status === "waiting_ready") return "Prêt à démarrer";
  if (status === "live") return "En cours";
  if (status === "finished") return "Terminé";
  return status;
}

function participantChipClass(state: string | undefined) {
  if (state === "live") return "is-live";
  if (state === "ready") return "is-ready";
  if (state === "submitted") return "is-submitted";
  if (state === "forfeit") return "is-forfeit";
  return "is-waiting";
}

function participantStateLabel(state: string | undefined) {
  if (state === "ready") return "Prêt";
  if (state === "live") return "En jeu";
  if (state === "submitted") return "Soumis";
  if (state === "forfeit") return "Forfait";
  return "En attente";
}

function asClock(seconds: number | null | undefined) {
  if (!seconds || seconds <= 0) return "00:00";
  const min = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);
  return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

const MATCH_ONBOARDING_STEPS: GuidedOnboardingStep[] = [
  {
    targetId: "match-overview",
    title: "Lobby live du duel",
    description: "Ici tu suis le statut du match, la règle active et le chrono commun en temps réel.",
  },
  {
    targetId: "match-map",
    title: "Vérifie la carte du match",
    description: "Confirme zone, météo, colis, budget et source de map avant de lancer ta tentative.",
  },
  {
    targetId: "match-participants",
    title: "Compare les statuts des joueurs",
    description: "Tu vois l'état Ready/live/submitted de chaque joueur, plus score et chrono quand disponibles.",
  },
  {
    targetId: "match-ready-action",
    title: "Déclare-toi prêt",
    description: "Le match démarre quand les deux joueurs sont présents et prêts.",
  },
  {
    targetId: "match-open-mission",
    title: "Ouvre ta mission",
    description: "Travaille ta tournée dans la mission assignée, puis reviens ici pour soumettre.",
  },
  {
    targetId: "match-submit-action",
    title: "Soumets ta tentative",
    description: "Soumission valide uniquement si tous les clients sont assignés sur ta mission.",
  },
];

export function VersusMatchView({ matchId }: { matchId: string }) {
  const { player, isReady } = usePlayer();
  const versusLive = useVersusLiveState(matchId, player?.id);
  const liveVersusState = versusLive.liveState;
  const setLiveVersusState = versusLive.setLiveState;

  const stateQuery = useQuery({
    queryKey: ["versus-match", matchId, player?.id],
    queryFn: () => getVersusMatchState(matchId, player!.id),
    enabled: Boolean(player?.id),
  });
  useEffect(() => {
    if (!liveVersusState && stateQuery.data) {
      setLiveVersusState(stateQuery.data);
    }
  }, [liveVersusState, setLiveVersusState, stateQuery.data]);

  const readyMutation = useMutation({
    mutationFn: () => setVersusReady(matchId, { player_id: player!.id, ready: true }),
    onSuccess: () => stateQuery.refetch(),
  });

  const submitMutation = useMutation({
    mutationFn: () => submitVersusAttempt(matchId, { player_id: player!.id }),
    onSuccess: () => stateQuery.refetch(),
  });

  const payload = liveVersusState ?? stateQuery.data;
  const selfParticipant = useMemo(
    () => payload?.participants.find((participant) => participant.is_self),
    [payload?.participants],
  );
  const opponent = useMemo(
    () => payload?.participants.find((participant) => !participant.is_self),
    [payload?.participants],
  );

  if (!isReady || stateQuery.isLoading || !payload) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="panel-loading" style={{ height: 130 }} />
          <div className="panel-loading" style={{ height: 90 }} />
          <div className="panel-loading" style={{ height: 110 }} />
        </div>
      </div>
    );
  }

  if (!player) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="panel">Connexion requise pour voir ce match.</section>
        </div>
      </div>
    );
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
        <section className="hero" data-onboarding-id="match-overview">
          <h1>Duel {payload.template_label ?? payload.template_id}</h1>
          <div className="hero-badges">
            <span className="hero-badge">{statusLabel(payload.status)}</span>
            <span className="hero-badge">Règle: {ruleLabel(payload.winner_rule)}</span>
            <span className="hero-badge">Chrono: {asClock(payload.started_elapsed_s)}</span>
            <span className="hero-badge">Live: {versusLive.connection === "open" ? "connecté" : versusLive.connection}</span>
            {payload.countdown_remaining_s && payload.countdown_remaining_s > 0 && (
              <span className="hero-badge">Départ commun: {payload.countdown_remaining_s}s</span>
            )}
            {payload.join_code && (
              <button
                type="button"
                className="hero-badge"
                style={{ cursor: "pointer" }}
                onClick={() => navigator.clipboard.writeText(payload.join_code!).catch(() => {})}
                title="Copier le code"
              >
                Code: {payload.join_code} · copier
              </button>
            )}
          </div>
          {versusLive.error ? <span className="muted">Canal live: {versusLive.error}</span> : null}
        </section>

        <section className="panel stack" data-onboarding-id="match-map">
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

        <section className="grid-2" data-onboarding-id="match-participants">
          <div className="panel stack">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
              <strong>{selfParticipant?.avatar ?? "🎅"} {selfParticipant?.display_name ?? player.display_name}</strong>
              <span className={`state-chip ${participantChipClass(selfParticipant?.state)}`}>
                <span className={`state-dot ${participantChipClass(selfParticipant?.state)}`} />
                {participantStateLabel(selfParticipant?.state)}
              </span>
            </div>
            {typeof selfParticipant?.score === "number" && <span className="muted">Score : {selfParticipant.score}</span>}
            {typeof selfParticipant?.total_time_s === "number" && <span className="muted">Temps : {Math.round(selfParticipant.total_time_s / 60)} min</span>}
            {selfParticipant?.progress && (
              <div style={{ display: "grid", gap: 4 }}>
                <span className="muted">
                  Progression: {selfParticipant.progress.assigned_clients}/{selfParticipant.progress.total_clients}
                </span>
                <div className="hero-progress" style={{ marginTop: 0 }}>
                  <div className="hero-progress-fill" style={{ width: `${Math.max(0, Math.min(100, selfParticipant.progress.progress_pct))}%` }} />
                </div>
              </div>
            )}
            {selfParticipant?.forfeit_deadline_at && <span className="muted">AFK deadline : {new Date(selfParticipant.forfeit_deadline_at).toLocaleTimeString("fr-FR")}</span>}
          </div>

          <div className="panel stack">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
              <strong>{opponent?.avatar ?? "🎄"} {opponent?.display_name ?? opponent?.player_id ?? "En attente"}</strong>
              <span className={`state-chip ${participantChipClass(opponent?.state)}`}>
                <span className={`state-dot ${participantChipClass(opponent?.state)}`} />
                {participantStateLabel(opponent?.state)}
              </span>
            </div>
            {typeof opponent?.score === "number" && <span className="muted">Score : {opponent.score}</span>}
            {typeof opponent?.total_time_s === "number" && <span className="muted">Temps : {Math.round(opponent.total_time_s / 60)} min</span>}
            {opponent?.progress && (
              <div style={{ display: "grid", gap: 4 }}>
                <span className="muted">
                  Progression: {opponent.progress.assigned_clients}/{opponent.progress.total_clients}
                </span>
                <div className="hero-progress" style={{ marginTop: 0 }}>
                  <div
                    className="hero-progress-fill"
                    style={{ width: `${Math.max(0, Math.min(100, opponent.progress.progress_pct))}%`, background: "var(--accent-2)" }}
                  />
                </div>
              </div>
            )}
            {opponent?.forfeit_deadline_at && <span className="muted">AFK deadline : {new Date(opponent.forfeit_deadline_at).toLocaleTimeString("fr-FR")}</span>}
          </div>
        </section>

        {!isFinished && (
          <section className="panel stack" data-onboarding-id="match-ready-action">
            {payload.status === "waiting_ready" && !isSelfReady && (
              <button
                className="primary-button"
                onClick={() => readyMutation.mutate()}
                disabled={readyMutation.isPending}
              >
                {readyMutation.isPending ? "Validation..." : "✅ Je suis prêt"}
              </button>
            )}
            {isSelfReady && payload.status === "waiting_ready" && (
              <div className="match-ready-wait">
                <span className="state-chip is-ready"><span className="state-dot is-ready" />Prêt — en attente de l&apos;adversaire</span>
              </div>
            )}
            {isLive && (
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {payload.current_player_mission_id ? (
                  <Link
                    className="primary-button"
                    href={`/mission/${payload.current_player_mission_id}?versus_match_id=${payload.match_id}`}
                    data-onboarding-id="match-open-mission"
                  >
                    🗺️ Ouvrir ma mission
                  </Link>
                ) : (
                  <button className="secondary-button" disabled>Mission non assignée</button>
                )}
                <button
                  className="secondary-button"
                  onClick={() => submitMutation.mutate()}
                  disabled={submitMutation.isPending || !canSubmit}
                  data-onboarding-id="match-submit-action"
                >
                  {submitMutation.isPending ? "Soumission..." : "Soumettre ma tentative"}
                </button>
              </div>
            )}
            {canSubmit && (
              <span className="muted" style={{ fontSize: "0.82rem" }}>
                Soumission autorisée uniquement si tous les clients sont assignés.
              </span>
            )}
          </section>
        )}

        {isFinished && (() => {
          const winner = payload.participants.find((p) => p.player_id === payload.winner_player_id);
          const isSelfWinner = winner?.is_self;
          return (
            <section className={`match-result-hero ${isSelfWinner ? "match-result-hero--win" : "match-result-hero--loss"}`}>
              <div className="match-result-icon">{isSelfWinner ? "🏆" : "💀"}</div>
              <div className="match-result-copy">
                <strong>{isSelfWinner ? "Victoire !" : "Défaite"}</strong>
                <span>{winner?.display_name ?? winner?.player_id ?? "—"} remporte le duel</span>
                {typeof winner?.score === "number" && (
                  <span className="match-result-score">{winner.score.toFixed(1)} pts</span>
                )}
                <span className="muted" style={{ fontSize: "0.8rem" }}>{payload.result_reason ?? "submitted"}</span>
              </div>
              <div className="match-result-actions">
                <Link className="primary-button" href="/leaderboard?mode=versus">🏆 Classement versus</Link>
                <Link className="secondary-button" href="/versus">Nouveau duel</Link>
              </div>
            </section>
          );
        })()}

        <section className="panel stack">
          <Link className="secondary-button" href="/versus">← Retour choix mode</Link>
        </section>

        <GuidedOnboarding
          storageKey="operation-noel-onboarding-versus-match-v1"
          tutorialLabel="Versus match"
          steps={MATCH_ONBOARDING_STEPS}
        />
      </div>
    </div>
  );
}
