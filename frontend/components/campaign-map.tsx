"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { GuidedOnboarding, type GuidedOnboardingStep } from "@/components/guided-onboarding";
import { usePlayer } from "@/components/player-provider";
import { TeleprinterText } from "@/components/teleprinter-text";
import { createMission } from "@/lib/api";
import {
  CAMPAIGN_MISSIONS,
  getCampaignCompletion,
  getDefaultCampaignProgress,
  markCampaignLevelStarted,
  readCampaignProgress,
} from "@/lib/campaign";
import type { CampaignMission, CampaignProgress } from "@/lib/types";

const CITY_ICONS: Record<number, string> = {
  1: "🗼",  // Paris
  2: "🌆",  // Berlin
  3: "🏔",  // Lyon
  4: "🇧🇪",  // Bruxelles
  5: "🍷",  // Bordeaux
  6: "⛄",  // Montréal
  7: "🎡",  // Londres
  8: "❄️",  // Stockholm
};

const WEATHER_ICONS: Record<string, string> = {
  Clear: "☀️",
  Rain: "🌧",
  Snow: "🌨",
  Thunderstorm: "⛈",
  real: "🌡",
};

const SOLO_ONBOARDING_STEPS: GuidedOnboardingStep[] = [
  {
    targetId: "solo-hero",
    title: "Campagne solo en 30 secondes",
    description: "Ici tu suis ta progression, tes étoiles et ton niveau débloqué contre l'IA.",
  },
  {
    targetId: "solo-rules",
    title: "Lis les règles de progression",
    description: "Les paliers de score te donnent jusqu'à 3 étoiles et ouvrent les niveaux suivants.",
  },
  {
    targetId: "solo-missions",
    title: "Choisis une mission et lance",
    description: "Commence par la première mission disponible, trace ta tournée puis compare ton score à l'IA.",
  },
  {
    targetId: "solo-versus-link",
    title: "Ensuite passe en versus",
    description: "Quand tu veux du duel live, passe au mode versus depuis ce raccourci.",
  },
];

function chapterSummary(progress: CampaignProgress) {
  const stars = Object.values(progress.starsByLevel).reduce((sum, count) => sum + Number(count), 0);
  return { completed: progress.completedLevels.length, total: CAMPAIGN_MISSIONS.length, stars };
}

function missionStatus(mission: CampaignMission, progress: CampaignProgress) {
  if (progress.completedLevels.includes(mission.level)) return "completed";
  if (mission.level <= progress.unlockedLevel) return "unlocked";
  return "locked";
}

export function CampaignMap() {
  const router = useRouter();
  const { player } = usePlayer();
  const [progress, setProgress] = useState<CampaignProgress>(getDefaultCampaignProgress());
  const [launchError, setLaunchError] = useState<string | null>(null);

  useEffect(() => {
    setProgress(readCampaignProgress());
    const syncProgress = () => setProgress(readCampaignProgress());
    window.addEventListener("storage", syncProgress);
    return () => window.removeEventListener("storage", syncProgress);
  }, [player?.id]);

  const summary = useMemo(() => chapterSummary(progress), [progress]);
  const completion = useMemo(() => getCampaignCompletion(progress), [progress]);
  const progressPct = summary.total > 0 ? (summary.completed / summary.total) * 100 : 0;

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
    onError: (error: Error) => setLaunchError(error.message),
  });

  return (
    <div className="page-shell campaign-shell">
      <div className="page-stack campaign-stack">

        {/* HERO */}
        <section className="campaign-hero" data-onboarding-id="solo-hero">
          <div className="campaign-hero-copy">
            <span className="salon-badge">🎄 Campagne · Solo contre IA</span>
            <h1>La route vers le Pôle Nord</h1>
            <TeleprinterText
              text="8 villes à travers le monde. 8 profils IA à vaincre. Chaque mission débloque la suivante - bats l'IA et prouve que tu mérites le rang de Maître Livreur."
            />
            <div className="campaign-hero-ribbon">
              <span className="campaign-hero-pill">Progression persistante</span>
              <span className="campaign-hero-pill">IA adaptative</span>
              <span className="campaign-hero-pill">Défi 8 villes</span>
            </div>
            <div className="campaign-progress">
              <div className="campaign-progress-bar">
                <div className="campaign-progress-fill" style={{ width: `${progressPct}%` }} />
              </div>
              <span className="campaign-progress-label">
                {summary.completed} / {summary.total} mission{summary.completed !== 1 ? "s" : ""} · {summary.stars} ⭐
              </span>
            </div>
          </div>
          <div className="campaign-hero-stats">
            <div className="campaign-stat-card">
              <span>Missions validées</span>
              <strong>{summary.completed}/{summary.total}</strong>
            </div>
            <div className="campaign-stat-card">
              <span>Étoiles gagnées</span>
              <strong>{summary.stars} ⭐</strong>
            </div>
            <div className="campaign-stat-card">
              <span>Niveau débloqué</span>
              <strong>{progress.unlockedLevel}</strong>
            </div>
          </div>
        </section>

        {/* INFO PANELS */}
        <section className="grid-3 campaign-info-grid" data-onboarding-id="solo-rules">
          <div className="panel stack">
            <strong>📋 Règles de progression</strong>
            <span className="muted">Un niveau terminé débloque le suivant.</span>
            <span className="muted">⭐ 1 étoile ≥ 60 pts · ⭐⭐ ≥ 75 · ⭐⭐⭐ ≥ 90</span>
            <span className="muted">Les meilleurs scores sont sauvegardés localement.</span>
          </div>
          <div className="panel stack">
            <strong>🎮 Autres modes</strong>
            <Link className="secondary-button" href="/">← Retour au hub</Link>
            <Link className="secondary-button" href="/versus" data-onboarding-id="solo-versus-link">
              ⚔️ Mode Versus
            </Link>
            <Link className="secondary-button" href="/leaderboard">🏆 Panthéon</Link>
          </div>
          <div className="panel stack">
            <strong>👤 Profil joueur</strong>
            {player ? (
              <>
                <span className="muted">{player.avatar ?? "🎅"} {player.display_name}</span>
                <span className="muted">
                  {progress.lastPlayedLevel ? `Dernière mission : niveau ${progress.lastPlayedLevel}` : "Aucune mission lancée"}
                </span>
                <span className="muted">
                  {progress.updatedAt ? new Date(progress.updatedAt).toLocaleString("fr-FR") : "Pas encore d'activité"}
                </span>
                {completion.isCampaignComplete && (
                  <Link className="primary-button" href="/campaign/finale">
                    🎉 Ouvrir la finale
                  </Link>
                )}
              </>
            ) : (
              <>
                <span className="muted">Connexion recommandée pour une progression dédiée.</span>
                <Link className="primary-button" href="/login?redirect=/campaign">
                  🎅 Se connecter
                </Link>
              </>
            )}
          </div>
        </section>

        {/* CARTE DES MISSIONS */}
        <section className="campaign-path" data-onboarding-id="solo-missions">
          {CAMPAIGN_MISSIONS.map((mission, index) => {
            const status = missionStatus(mission, progress);
            const stars = Number(progress.starsByLevel[mission.level] ?? 0);
            const bestScore = Number(progress.bestScoreByLevel[mission.level] ?? 0);
            const isPending = launchMutation.isPending && launchMutation.variables?.level === mission.level;
            const cityIcon = CITY_ICONS[mission.level] ?? "🏙";
            const weatherIcon = WEATHER_ICONS[mission.weather_key] ?? "🌡";

            const isNext = status === "unlocked" && !progress.completedLevels.includes(mission.level);
            return (
              <div key={mission.level} className={`campaign-row ${index % 2 === 0 ? "is-left" : "is-right"} status-${status}${isNext ? " is-next" : ""}`}>
                <div className="campaign-node-column">
                  <div className={`campaign-node status-${status}${isNext ? " is-next" : ""}`}>
                    {status === "completed" ? "✓" : status === "locked" ? "🔒" : mission.level}
                  </div>
                  {index < CAMPAIGN_MISSIONS.length - 1 && <div className="campaign-link" />}
                </div>

                <article className={`campaign-card status-${status}${isNext ? " is-next" : ""}`}>
                  <div className="campaign-card-head">
                    <div>
                      <span className="campaign-chapter">{mission.chapter}</span>
                      <h2>
                        <span className="campaign-city-icon">{cityIcon}</span>
                        {mission.title}
                      </h2>
                    </div>
                    <span className={`tag salon-status-chip status-${status}`}>
                      {status === "completed" ? "✓ Terminé" : isNext ? "▶ Jouer maintenant" : status === "unlocked" ? "Disponible" : "🔒 Verrouillé"}
                    </span>
                  </div>

                  <p className="campaign-briefing">{mission.briefing}</p>

                  <div className="campaign-meta-grid">
                    <span className="campaign-meta-chip">📍 {mission.zone}</span>
                    <span className="campaign-meta-chip">📦 {mission.num_clients} clients</span>
                    <span className="campaign-meta-chip">{weatherIcon} {mission.weather_key}</span>
                    <span className="campaign-meta-chip">🤖 IA {mission.ai_profile}</span>
                  </div>

                  <div className="campaign-objectives">
                    <span><strong>Objectif ·</strong> {mission.objective}</span>
                    <span><strong>Récompense ·</strong> {mission.reward_label}</span>
                  </div>

                  {mission.secondary_objectives && mission.secondary_objectives.length > 0 && (
                    <div className="objective-list">
                      {mission.secondary_objectives.map((obj) => (
                        <div key={`${mission.level}-${obj.code}`} className="objective-chip">
                          <span className="objective-dot" />
                          <span>{obj.label}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="campaign-footer">
                    <div className="campaign-stars" aria-label={`${stars} étoiles`}>
                      <span className={stars >= 1 ? "is-lit" : ""}>★</span>
                      <span className={stars >= 2 ? "is-lit" : ""}>★</span>
                      <span className={stars >= 3 ? "is-lit" : ""}>★</span>
                    </div>
                    <span className="muted">
                      {bestScore > 0 ? `Meilleur score : ${bestScore.toFixed(1)}/100` : "Pas encore jouée"}
                    </span>
                    <button
                      className="primary-button campaign-launch-button"
                      disabled={status === "locked" || launchMutation.isPending || !player}
                      onClick={() => { setLaunchError(null); launchMutation.mutate(mission); }}
                    >
                      {!player
                        ? "🔑 Connexion requise"
                        : isPending
                        ? "Initialisation…"
                        : status === "completed"
                        ? "↺ Rejouer"
                        : "🚀 Lancer"}
                    </button>
                    {launchError && launchMutation.variables?.level === mission.level && (
                      <div className="error-box" style={{ marginTop: 6, fontSize: "0.82rem" }}>{launchError}</div>
                    )}
                  </div>
                </article>
              </div>
            );
          })}
        </section>

        <GuidedOnboarding
          storageKey="operation-noel-onboarding-solo-v1"
          tutorialLabel="Solo"
          steps={SOLO_ONBOARDING_STEPS}
        />

      </div>
    </div>
  );
}
