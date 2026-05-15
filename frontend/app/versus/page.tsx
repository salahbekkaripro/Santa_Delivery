"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { GuidedOnboarding, type GuidedOnboardingStep } from "@/components/guided-onboarding";
import { usePlayer } from "@/components/player-provider";
import { TeleprinterText } from "@/components/teleprinter-text";
import { getVersusInvites } from "@/lib/api";

const VERSUS_ONBOARDING_STEPS: GuidedOnboardingStep[] = [
  {
    targetId: "versus-overview",
    title: "Choisis ton flow de duel",
    description: "Le versus se fait en 3 étapes: mode de matchmaking, configuration, puis lobby live.",
  },
  {
    targetId: "versus-private",
    title: "Code privé",
    description: "Idéal pour un duel ciblé: tu crées la room et partages le code à ton adversaire.",
  },
  {
    targetId: "versus-queue",
    title: "File auto",
    description: "Lance un matchmaking rapide sur templates prédéfinis.",
  },
  {
    targetId: "versus-invite",
    title: "Invitation ciblée",
    description: "Tu envoies une invitation directe à un joueur précis et il accepte ou refuse.",
  },
];

export default function VersusPage() {
  const { player, isReady } = usePlayer();

  const invitesQuery = useQuery({
    queryKey: ["versus-invites-counter", player?.id],
    queryFn: () => getVersusInvites(player!.id),
    enabled: Boolean(player?.id),
    refetchInterval: 3000,
  });

  if (!isReady) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="panel-loading" style={{ height: 110 }} />
          <div className="panel-loading" style={{ height: 140 }} />
        </div>
      </div>
    );
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
        <section className="hero" data-onboarding-id="versus-overview">
          <h1>Versus Live</h1>
          <TeleprinterText text="Étape 1/3: choisis ton mode de matchmaking." />
        </section>

        <div className="versus-hub-grid">
          <Link className="versus-hub-card versus-hub-card--private" href="/versus/private" data-onboarding-id="versus-private">
            <div className="versus-hub-icon">🔐</div>
            <div className="versus-hub-body">
              <strong>Code privé</strong>
              <span>Crée la room, choisis ta carte, partage le code à un ami.</span>
            </div>
            <span className="versus-hub-arrow">→</span>
          </Link>

          <Link className="versus-hub-card versus-hub-card--queue" href="/versus/queue" data-onboarding-id="versus-queue">
            <div className="versus-hub-icon">⚡</div>
            <div className="versus-hub-body">
              <strong>File auto</strong>
              <span>Matchmaking rapide — un adversaire, zéro config.</span>
            </div>
            <span className="versus-hub-arrow">→</span>
          </Link>

          <Link className="versus-hub-card versus-hub-card--invite" href="/versus/invite" data-onboarding-id="versus-invite">
            <div className="versus-hub-icon">📨</div>
            <div className="versus-hub-body">
              <strong>Invitation ciblée</strong>
              <span>Défie un joueur précis avec ta propre configuration.</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginLeft: "auto" }}>
              {inviteCount > 0 && (
                <span className="versus-invite-badge">{inviteCount}</span>
              )}
              <span className="versus-hub-arrow">→</span>
            </div>
          </Link>
        </div>

        <GuidedOnboarding
          storageKey="operation-noel-onboarding-versus-v1"
          tutorialLabel="Versus"
          steps={VERSUS_ONBOARDING_STEPS}
        />
      </div>
    </div>
  );
}
