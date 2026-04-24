"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import {
  acceptVersusInvite,
  createVersusInvite,
  createVersusMatch,
  declineVersusInvite,
  enterVersusQueue,
  getVersusInvites,
  getVersusTemplates,
  joinVersusMatch,
  leaveVersusQueue,
} from "@/lib/api";
import type { VersusInvite, VersusWinnerRule } from "@/lib/types";

const WINNER_RULE_OPTIONS: Array<{ value: VersusWinnerRule; label: string; description: string }> = [
  { value: "score_time", label: "Score puis temps", description: "Priorité au score final puis au chrono." },
  { value: "time", label: "Temps uniquement", description: "Le plus rapide gagne (tentative valide requise)." },
  { value: "objectives", label: "Objectifs", description: "Le plus d'objectifs secondaires, puis chrono." },
];

function ruleLabel(rule: string) {
  if (rule === "time") return "Temps";
  if (rule === "objectives") return "Objectifs";
  return "Score + temps";
}

export default function VersusPage() {
  const router = useRouter();
  const { player, isReady } = usePlayer();
  const [templateId, setTemplateId] = useState("paris_duel");
  const [winnerRule, setWinnerRule] = useState<VersusWinnerRule>("score_time");
  const [joinCode, setJoinCode] = useState("");
  const [inviteePlayerId, setInviteePlayerId] = useState("");
  const [queueActive, setQueueActive] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const templatesQuery = useQuery({
    queryKey: ["versus-templates"],
    queryFn: getVersusTemplates,
  });

  const invitesQuery = useQuery({
    queryKey: ["versus-invites", player?.id],
    queryFn: () => getVersusInvites(player!.id),
    enabled: Boolean(player?.id),
    refetchInterval: 3000,
  });

  const selectedTemplate = useMemo(
    () => templatesQuery.data?.templates.find((template) => template.template_id === templateId),
    [templatesQuery.data?.templates, templateId],
  );

  const privateMatchMutation = useMutation({
    mutationFn: () =>
      createVersusMatch({
        player_id: player!.id,
        mode: "private",
        template_id: templateId,
        winner_rule: winnerRule,
      }),
    onSuccess: (match) => {
      setError(null);
      setFeedback(`Partie créée. Code: ${match.join_code ?? "--"}`);
      router.push(`/versus/match/${match.match_id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const joinMatchMutation = useMutation({
    mutationFn: () =>
      joinVersusMatch({
        player_id: player!.id,
        join_code: joinCode.trim().toUpperCase(),
      }),
    onSuccess: (match) => {
      setError(null);
      setFeedback("Partie rejointe.");
      router.push(`/versus/match/${match.match_id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const queueMutation = useMutation({
    mutationFn: () =>
      enterVersusQueue({
        player_id: player!.id,
        template_id: templateId,
        winner_rule: winnerRule,
      }),
    onSuccess: (payload) => {
      setError(null);
      if (payload.status === "matched" && payload.match) {
        setQueueActive(false);
        setFeedback("Adversaire trouvé. Ouverture du duel...");
        router.push(`/versus/match/${payload.match.match_id}`);
        return;
      }
      setQueueActive(true);
      setFeedback("En file d'attente. On cherche un adversaire...");
    },
    onError: (err: Error) => setError(err.message),
  });

  const leaveQueueMutation = useMutation({
    mutationFn: () => leaveVersusQueue({ player_id: player!.id }),
    onSuccess: () => {
      setQueueActive(false);
      setError(null);
      setFeedback("Vous avez quitté la file.");
    },
    onError: (err: Error) => setError(err.message),
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      createVersusInvite({
        player_id: player!.id,
        invitee_player_id: inviteePlayerId.trim(),
        template_id: templateId,
        winner_rule: winnerRule,
      }),
    onSuccess: () => {
      setError(null);
      setFeedback("Invitation envoyée.");
      setInviteePlayerId("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const acceptInviteMutation = useMutation({
    mutationFn: (inviteId: string) => acceptVersusInvite(inviteId, { player_id: player!.id }),
    onSuccess: ({ match }) => {
      setError(null);
      setFeedback("Invitation acceptée.");
      invitesQuery.refetch();
      router.push(`/versus/match/${match.match_id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const declineInviteMutation = useMutation({
    mutationFn: (inviteId: string) => declineVersusInvite(inviteId, { player_id: player!.id }),
    onSuccess: () => {
      setError(null);
      setFeedback("Invitation refusée.");
      invitesQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  useEffect(() => {
    if (!queueActive || !player?.id) {
      return;
    }
    const timer = window.setInterval(() => {
      if (!queueMutation.isPending) {
        queueMutation.mutate();
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [queueActive, player?.id, queueMutation, templateId, winnerRule]);

  if (!isReady) {
    return <div className="page-shell"><div className="page-stack"><div className="panel">Chargement...</div></div></div>;
  }

  if (!player) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="hero">
            <h1>Mode Versus</h1>
            <p>Connexion obligatoire pour lancer un duel live.</p>
          </section>
          <section className="panel stack">
            <Link className="primary-button" href="/login?redirect=%2Fversus">Se connecter</Link>
            <Link className="secondary-button" href="/">← Retour à l&apos;accueil</Link>
          </section>
        </div>
      </div>
    );
  }

  const invites: VersusInvite[] = invitesQuery.data?.invites ?? [];

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Mode Versus Live</h1>
          <p>Duel en direct, chrono partagé, même seed pour les deux joueurs.</p>
        </section>

        <section className="panel stack">
          <strong>Configuration du duel</strong>
          <label className="field">
            <span>Template</span>
            <select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
              {(templatesQuery.data?.templates ?? []).map((template) => (
                <option key={template.template_id} value={template.template_id}>
                  {template.label}
                </option>
              ))}
            </select>
          </label>
          <span className="muted">{selectedTemplate?.description ?? "Chargement des templates..."}</span>
          <label className="field">
            <span>Règle de victoire</span>
            <select value={winnerRule} onChange={(event) => setWinnerRule(event.target.value as VersusWinnerRule)}>
              {WINNER_RULE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <span className="muted">{WINNER_RULE_OPTIONS.find((option) => option.value === winnerRule)?.description}</span>
        </section>

        <section className="grid-3">
          <div className="panel stack">
            <strong>Code privé</strong>
            <span className="muted">Crée une room, partage le code et attends ton adversaire.</span>
            <button className="primary-button" onClick={() => privateMatchMutation.mutate()} disabled={privateMatchMutation.isPending}>
              {privateMatchMutation.isPending ? "Création..." : "Créer la partie"}
            </button>
            <label className="field">
              <span>Rejoindre avec un code</span>
              <input
                type="text"
                value={joinCode}
                onChange={(event) => setJoinCode(event.target.value.toUpperCase())}
                placeholder="ABC123"
              />
            </label>
            <button
              className="secondary-button"
              onClick={() => joinMatchMutation.mutate()}
              disabled={joinMatchMutation.isPending || joinCode.trim().length < 4}
            >
              {joinMatchMutation.isPending ? "Connexion..." : "Rejoindre"}
            </button>
          </div>

          <div className="panel stack">
            <strong>File auto</strong>
            <span className="muted">Matchmaking automatique sur le template et la règle choisis.</span>
            {!queueActive ? (
              <button className="primary-button" onClick={() => queueMutation.mutate()} disabled={queueMutation.isPending}>
                {queueMutation.isPending ? "Recherche..." : "Entrer en file"}
              </button>
            ) : (
              <button className="secondary-button" onClick={() => leaveQueueMutation.mutate()} disabled={leaveQueueMutation.isPending}>
                {leaveQueueMutation.isPending ? "Sortie..." : "Quitter la file"}
              </button>
            )}
          </div>

          <div className="panel stack">
            <strong>Invitation</strong>
            <span className="muted">Invite un joueur connecté par son identifiant joueur.</span>
            <label className="field">
              <span>Identifiant cible</span>
              <input
                type="text"
                value={inviteePlayerId}
                onChange={(event) => setInviteePlayerId(event.target.value)}
                placeholder="player_id"
              />
            </label>
            <button
              className="primary-button"
              onClick={() => inviteMutation.mutate()}
              disabled={inviteMutation.isPending || inviteePlayerId.trim().length < 3}
            >
              {inviteMutation.isPending ? "Envoi..." : "Envoyer l'invitation"}
            </button>
          </div>
        </section>

        <section className="panel stack">
          <div className="panel-head">
            <strong>Invitations reçues</strong>
            <span className="muted">{invites.length} en attente</span>
          </div>
          {invites.length === 0 ? (
            <span className="muted">Aucune invitation en attente.</span>
          ) : (
            <div className="stack" style={{ gap: 10 }}>
              {invites.map((invite) => (
                <div key={invite.invite_id} className="lb-row">
                  <span className="lb-row-avatar">{invite.inviter_avatar ?? "🎅"}</span>
                  <div className="lb-row-meta">
                    <div className="lb-row-name">{invite.inviter_display_name ?? invite.inviter_player_id}</div>
                    <div className="lb-zone">
                      {invite.template_id} · {ruleLabel(invite.winner_rule)}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      className="primary-button"
                      onClick={() => acceptInviteMutation.mutate(invite.invite_id)}
                      disabled={acceptInviteMutation.isPending}
                    >
                      Accepter
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => declineInviteMutation.mutate(invite.invite_id)}
                      disabled={declineInviteMutation.isPending}
                    >
                      Refuser
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {(feedback || error) && (
          <section className={`panel ${error ? "error-box" : ""}`}>
            {error ? error : feedback}
          </section>
        )}
      </div>
    </div>
  );
}
