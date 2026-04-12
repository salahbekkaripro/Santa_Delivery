"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import { CAMPAIGN_MISSIONS, getCampaignCompletion, getDefaultCampaignProgress, readCampaignProgress } from "@/lib/campaign";
import type { CampaignProgress } from "@/lib/types";

export function CampaignFinale() {
  const { player } = usePlayer();
  const [progress, setProgress] = useState<CampaignProgress>(getDefaultCampaignProgress());

  useEffect(() => {
    setProgress(readCampaignProgress());

    const syncProgress = () => setProgress(readCampaignProgress());
    window.addEventListener("storage", syncProgress);
    return () => window.removeEventListener("storage", syncProgress);
  }, [player?.id]);

  const completion = useMemo(() => getCampaignCompletion(progress), [progress]);
  const topLevels = CAMPAIGN_MISSIONS.filter((mission) => progress.completedLevels.includes(mission.level)).slice(-3).reverse();

  return (
    <div className="page-shell campaign-shell">
      <div className="page-stack campaign-stack">
        <section className="campaign-finale-hero">
          <span className="salon-badge">Finale de campagne</span>
          <h1>{completion.isCampaignComplete ? "Le Pôle Nord est sécurisé" : "Campagne encore en cours"}</h1>
          <p>
            {completion.isCampaignComplete
              ? "Tu as traversé toute la campagne, battu les profils IA majeurs et accumulé assez d'étoiles pour clore l'arc principal."
              : "La finale affichera ton palmarès complet dès que toutes les missions de campagne seront terminées."}
          </p>
          <span className="muted" style={{ color: "rgba(255,255,255,0.76)" }}>
            {player ? `Profil actif: ${player.display_name}` : "Aucun joueur connecté"}
          </span>
          <div className="campaign-finale-grid">
            <div className="campaign-stat-card">
              <span>Missions gagnées</span>
              <strong>
                {progress.completedLevels.length}/{CAMPAIGN_MISSIONS.length}
              </strong>
            </div>
            <div className="campaign-stat-card">
              <span>Objectifs validés</span>
              <strong>
                {completion.completedObjectives}/{completion.totalObjectives}
              </strong>
            </div>
            <div className="campaign-stat-card">
              <span>Étoiles totales</span>
              <strong>
                {completion.totalStars}/{completion.maxStars}
              </strong>
            </div>
            <div className="campaign-stat-card">
              <span>Profils vaincus</span>
              <strong>{progress.defeatedProfiles.length}</strong>
            </div>
          </div>
        </section>

        <section className="grid-2">
          <div className="panel stack">
            <strong>Profils IA vaincus</strong>
            {progress.defeatedProfiles.length > 0 ? (
              progress.defeatedProfiles.map((profile) => (
                <span key={profile} className="tag" style={{ width: "fit-content" }}>
                  {profile}
                </span>
              ))
            ) : (
              <span className="muted">Aucun profil enregistré pour le moment.</span>
            )}
          </div>
          <div className="panel stack">
            <strong>Dernières victoires</strong>
            {topLevels.length > 0 ? (
              topLevels.map((mission) => (
                <span key={mission.level} className="muted">
                  Mission {mission.level} · {mission.title} · meilleur score {Number(progress.bestScoreByLevel[mission.level] ?? 0).toFixed(1)}/100
                </span>
              ))
            ) : (
              <span className="muted">Aucune mission terminée.</span>
            )}
          </div>
        </section>

        <section className="panel stack">
          <strong>Lecture de la campagne</strong>
          <span className="muted">Acte I : prise en main et premiers écarts contre l&apos;IA.</span>
          <span className="muted">Acte II : météo, budget et stabilité deviennent centraux.</span>
          <span className="muted">Acte III : profils agressifs et exécution de haut niveau.</span>
        </section>

        <section className="grid-3">
          <Link className="secondary-button" href="/campaign">
            Retour a la carte de campagne
          </Link>
          <Link className="secondary-button" href="/">
            Revenir au hub
          </Link>
          <Link className="primary-button" href="/versus">
            Préparer le mode versus
          </Link>
        </section>
      </div>
    </div>
  );
}
