"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePlayer } from "@/components/player-provider";
import { getVersusInvites } from "@/lib/api";

export default function VersusPage() {
  const { player, isReady } = usePlayer();

  const invitesQuery = useQuery({
    queryKey: ["versus-invites-counter", player?.id],
    queryFn: () => getVersusInvites(player!.id),
    enabled: Boolean(player?.id),
    refetchInterval: 3000,
  });

  if (!isReady) {
    return <div className="page-shell"><div className="page-stack"><div className="panel">Chargement...</div></div></div>;
  }

  if (!player) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="hero">
            <h1>Mode Versus</h1>
            <p>Connexion obligatoire pour accéder au flow live.</p>
          </section>
          <section className="panel stack">
            <Link className="primary-button" href="/login?redirect=%2Fversus">Se connecter</Link>
            <Link className="secondary-button" href="/">← Retour à l&apos;accueil</Link>
          </section>
        </div>
      </div>
    );
  }

  const inviteCount = invitesQuery.data?.invites.length ?? 0;

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Versus Live</h1>
          <p>Étape 1/3: choisis ton mode de matchmaking.</p>
        </section>

        <section className="grid-3">
          <div className="panel stack">
            <strong>Code privé</strong>
            <span className="muted">Créer une room, choisir template ou map custom, puis partager un code.</span>
            <Link className="primary-button" href="/versus/private">Ouvrir le mode privé</Link>
          </div>

          <div className="panel stack">
            <strong>File auto</strong>
            <span className="muted">Matchmaking rapide sur templates uniquement.</span>
            <Link className="primary-button" href="/versus/queue">Ouvrir la file auto</Link>
          </div>

          <div className="panel stack">
            <strong>Invitation</strong>
            <span className="muted">Inviter un joueur précis avec template ou map custom.</span>
            <Link className="primary-button" href="/versus/invite">Ouvrir les invitations</Link>
            <span className="muted">{inviteCount} invitation{inviteCount > 1 ? "s" : ""} en attente</span>
          </div>
        </section>
      </div>
    </div>
  );
}
