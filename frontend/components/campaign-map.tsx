"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import { createMission } from "@/lib/api";
import {
  CAMPAIGN_MISSIONS,
  getCampaignCompletion,
  getDefaultCampaignProgress,
  markCampaignLevelStarted,
  readCampaignProgress,
} from "@/lib/campaign";
import type { CampaignMission, CampaignProgress } from "@/lib/types";

function chapterSummary(progress: CampaignProgress) {
  const stars = Object.values(progress.starsByLevel).reduce((sum, count) => sum + Number(count), 0);
  return {
    completed: progress.completedLevels.length,
    total: CAMPAIGN_MISSIONS.length,
    stars,
  };
}

function missionStatus(mission: CampaignMission, progress: CampaignProgress) {
  if (progress.completedLevels.includes(mission.level)) {
    return "completed";
  }
  if (mission.level <= progress.unlockedLevel) {
    return "unlocked";
  }
  return "locked";
}

export function CampaignMap() {
  const router = useRouter();
  const { player } = usePlayer();
  const [progress, setProgress] = useState<CampaignProgress>(getDefaultCampaignProgress());

  useEffect(() => {
    setProgress(readCampaignProgress());

    const syncProgress = () => setProgress(readCampaignProgress());
    window.addEventListener("storage", syncProgress);
    return () => window.removeEventListener("storage", syncProgress);
  }, [player?.id]);

  const summary = useMemo(() => chapterSummary(progress), [progress]);
  const completion = useMemo(() => getCampaignCompletion(progress), [progress]);

  const launchMutation = useMutation({
    mutationFn: (mission: CampaignMission) => {
      const { title, chapter, briefing, objective, reward_label, ...payload } = mission;
      return createMission(payload);
    },
    onSuccess: (data, variables) => {
      if (variables.level) {
        const nextProgress = markCampaignLevelStarted(variables.level);
        setProgress(nextProgress);
      }
      router.push(`/mission/${data.mission_id}`);
    },
  });

  return (
    <div className="page-shell campaign-shell">
      <div className="page-stack campaign-stack">
        <section className="campaign-hero">
          <div className="campaign-hero-copy">
            <span className="salon-badge">Campagne · Solo contre IA</span>
            <h1>La route vers le Pôle Nord</h1>
            <p>
              Chaque mission oppose ton plan à un profil IA distinct. Termine un niveau pour débloquer le suivant et
              fais grimper ton rang de logisticien.
            </p>
          </div>
          <div className="campaign-hero-stats">
            <div className="campaign-stat-card">
              <span>Missions validées</span>
              <strong>
                {summary.completed}/{summary.total}
              </strong>
            </div>
            <div className="campaign-stat-card">
              <span>Étoiles gagnées</span>
              <strong>{summary.stars}</strong>
            </div>
            <div className="campaign-stat-card">
              <span>Niveau débloqué</span>
              <strong>{progress.unlockedLevel}</strong>
            </div>
          </div>
        </section>

        <section className="grid-3">
          <div className="panel stack">
            <strong>Règles de progression</strong>
            <span className="muted">Un niveau terminé débloque le suivant.</span>
            <span className="muted">1 étoile à 60, 2 étoiles à 75, 3 étoiles à 90.</span>
            <span className="muted">Les missions gardent ton meilleur score localement.</span>
          </div>
          <div className="panel stack">
            <strong>Modes de jeu</strong>
            <Link className="secondary-button" href="/">
              Retour au hub salon
            </Link>
            <Link className="secondary-button" href="/versus">
              Préparer le duel live
            </Link>
          </div>
          <div className="panel stack">
            <strong>Dernière tentative</strong>
            <span className="muted">{player ? `Profil actif: ${player.display_name}` : "Connexion recommandée pour une progression dédiée"}</span>
            <span className="muted">
              {progress.lastPlayedLevel ? `Mission ${progress.lastPlayedLevel}` : "Aucune mission lancée"}
            </span>
            <span className="muted">
              {progress.updatedAt ? new Date(progress.updatedAt).toLocaleString("fr-FR") : "Pas encore d'activité"}
            </span>
            {completion.isCampaignComplete ? (
              <Link className="primary-button" href="/campaign/finale">
                Ouvrir la finale de campagne
              </Link>
            ) : null}
            {!player ? (
              <Link className="secondary-button" href="/login?redirect=/campaign">
                Se connecter
              </Link>
            ) : null}
          </div>
        </section>

        <section className="campaign-path">
          {CAMPAIGN_MISSIONS.map((mission, index) => {
            const status = missionStatus(mission, progress);
            const stars = Number(progress.starsByLevel[mission.level] ?? 0);
            const bestScore = Number(progress.bestScoreByLevel[mission.level] ?? 0);
            const isPending = launchMutation.isPending && launchMutation.variables?.level === mission.level;

            return (
              <div key={mission.level} className={`campaign-row ${index % 2 === 0 ? "is-left" : "is-right"}`}>
                <div className="campaign-node-column">
                  <div className={`campaign-node status-${status}`}>{mission.level}</div>
                  {index < CAMPAIGN_MISSIONS.length - 1 ? <div className="campaign-link" /> : null}
                </div>
                <article className={`campaign-card status-${status}`}>
                  <div className="campaign-card-head">
                    <div>
                      <span className="campaign-chapter">{mission.chapter}</span>
                      <h2>{mission.title}</h2>
                    </div>
                    <span className={`tag salon-status-chip status-${status}`}>
                      {status === "completed" ? "Terminé" : status === "unlocked" ? "Disponible" : "Verrouillé"}
                    </span>
                  </div>
                  <p className="campaign-briefing">{mission.briefing}</p>
                  <div className="campaign-meta-grid">
                    <span>{mission.zone}</span>
                    <span>{mission.num_clients} clients</span>
                    <span>Météo {mission.weather_key}</span>
                    <span>IA {mission.ai_profile}</span>
                  </div>
                  <div className="campaign-objectives">
                    <span>
                      <strong>Objectif</strong> {mission.objective}
                    </span>
                    <span>
                      <strong>Récompense</strong> {mission.reward_label}
                    </span>
                  </div>
                  {mission.secondary_objectives && mission.secondary_objectives.length > 0 ? (
                    <div className="objective-list">
                      {mission.secondary_objectives.map((objective) => (
                        <div key={`${mission.level}-${objective.code}`} className="objective-chip">
                          <span className="objective-dot" />
                          <span>{objective.label}</span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  <div className="campaign-footer">
                    <div className="campaign-stars" aria-label={`${stars} étoiles`}>
                      <span className={stars >= 1 ? "is-lit" : ""}>★</span>
                      <span className={stars >= 2 ? "is-lit" : ""}>★</span>
                      <span className={stars >= 3 ? "is-lit" : ""}>★</span>
                    </div>
                    <span className="muted">{bestScore > 0 ? `Meilleur score ${bestScore.toFixed(1)}/100` : "Pas encore jouée"}</span>
                    <button
                      className="primary-button"
                      disabled={status === "locked" || launchMutation.isPending || !player}
                      onClick={() => launchMutation.mutate(mission)}
                    >
                      {!player ? "Connexion requise" : isPending ? "Initialisation..." : status === "completed" ? "Rejouer" : "Lancer"}
                    </button>
                  </div>
                </article>
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}
