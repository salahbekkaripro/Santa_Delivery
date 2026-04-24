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
  const topLevels = CAMPAIGN_MISSIONS
    .filter((m) => progress.completedLevels.includes(m.level))
    .slice(-3)
    .reverse();

  const totalStarsPct = completion.maxStars > 0
    ? Math.round((completion.totalStars / completion.maxStars) * 100)
    : 0;

  return (
    <div className="page-shell">
      <div className="page-stack">

        {/* HERO CELEBRATION */}
        <section className="finale-hero">
          <span className="finale-trophy">
            {completion.isCampaignComplete ? "🏆" : "🗺️"}
          </span>
          <h1>
            {completion.isCampaignComplete ? "Le Pôle Nord est sécurisé !" : "Campagne en cours…"}
          </h1>
          <p>
            {completion.isCampaignComplete
              ? "Tu as traversé toute la campagne, battu les profils IA majeurs et accumulé les étoiles de la victoire. Noël est sauvé."
              : "La finale affichera ton palmarès complet dès que toutes les missions de campagne seront terminées."}
          </p>
          {completion.isCampaignComplete && (
            <div className="finale-stars-row">
              {Array.from({ length: Math.min(completion.totalStars, 24) }, (_, i) => (
                <span key={i}>⭐</span>
              ))}
            </div>
          )}
          {player && (
            <span className="hero-badge" style={{ fontSize: "0.9rem", padding: "8px 16px" }}>
              {player.avatar ?? "🎅"} {player.display_name}
            </span>
          )}

          <div className="finale-stat-grid">
            <div className="finale-stat-card">
              <div className="finale-stat-value">
                {progress.completedLevels.length}/{CAMPAIGN_MISSIONS.length}
              </div>
              <span className="finale-stat-label">Missions gagnées</span>
            </div>
            <div className="finale-stat-card">
              <div className="finale-stat-value">
                {completion.completedObjectives}/{completion.totalObjectives}
              </div>
              <span className="finale-stat-label">Objectifs validés</span>
            </div>
            <div className="finale-stat-card">
              <div className="finale-stat-value">
                {completion.totalStars}/{completion.maxStars}
              </div>
              <span className="finale-stat-label">Étoiles totales</span>
            </div>
            <div className="finale-stat-card">
              <div className="finale-stat-value">{progress.defeatedProfiles.length}</div>
              <span className="finale-stat-label">Profils IA vaincus</span>
            </div>
          </div>
        </section>

        {/* DÉTAILS */}
        <section className="grid-2">
          <div className="panel stack">
            <strong>🤖 Profils IA vaincus</strong>
            {progress.defeatedProfiles.length > 0 ? (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {progress.defeatedProfiles.map((profile) => (
                  <span key={profile} className="tag" style={{ background: "rgba(23,50,77,0.1)", fontSize: "0.88rem" }}>
                    ✓ {profile}
                  </span>
                ))}
              </div>
            ) : (
              <span className="muted">Aucun profil enregistré pour le moment.</span>
            )}
          </div>

          <div className="panel stack">
            <strong>🏅 Dernières victoires</strong>
            {topLevels.length > 0 ? (
              topLevels.map((mission) => (
                <div key={mission.level} className="sleigh-row">
                  <span className="sleigh-row-id">#{mission.level}</span>
                  <div className="sleigh-row-stats">
                    <span>{mission.title}</span>
                    <span style={{ marginLeft: "auto" }}>
                      {Number(progress.bestScoreByLevel[mission.level] ?? 0).toFixed(1)}/100
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <span className="muted">Aucune mission terminée.</span>
            )}
          </div>
        </section>

        {/* PROGRESSION GLOBALE */}
        <section className="panel stack">
          <strong>Progression globale — {totalStarsPct}% complété</strong>
          <div className="campaign-progress-bar">
            <div className="campaign-progress-fill" style={{ width: `${totalStarsPct}%` }} />
          </div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <span className="muted">Acte I (1–3) : Prise en main · Paris, Berlin, Lyon</span>
            <span className="muted">Acte II (4–6) : Météo & budget · Bruxelles, Bordeaux, Montréal</span>
            <span className="muted">Acte III (7–8) : Haute intensité · Londres, Stockholm</span>
          </div>
        </section>

        {/* NAVIGATION */}
        <section style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center" }}>
          <Link className="secondary-button" href="/campaign">
            ← Carte de campagne
          </Link>
          <Link className="secondary-button" href="/">
            ← Retour au hub
          </Link>
          <Link className="primary-button" href="/leaderboard">
            🏆 Voir le Panthéon
          </Link>
        </section>

      </div>
    </div>
  );
}
