"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import { createMission, getLeaderboard, getMissions } from "@/lib/api";
import type { LeaderboardEntry, MissionSnapshot } from "@/lib/types";

const campaigns = [
  {
    level: 1,
    title: "Paris · Le Marais",
    zone: "Le Marais, Paris",
    weather_key: "Clear",
    num_clients: 10,
    budget: 1500,
    sleigh_cost: 500,
    random_incidents: false,
    ai_profile: "Express",
    tone: "Ouverture propre et rapide",
  },
  {
    level: 2,
    title: "Berlin · Mitte",
    zone: "Mitte, Berlin",
    weather_key: "Rain",
    num_clients: 30,
    budget: 2500,
    sleigh_cost: 600,
    random_incidents: false,
    ai_profile: "Prudent",
    tone: "Densité urbaine sous pluie",
  },
  {
    level: 3,
    title: "Montréal · Plateau",
    zone: "Le Plateau-Mont-Royal, Montréal, Québec, Canada",
    weather_key: "Snow",
    num_clients: 50,
    budget: 4000,
    sleigh_cost: 800,
    random_incidents: true,
    ai_profile: "Championne",
    tone: "Mission de salon à haute intensité",
  },
];

function formatTimestamp(value?: string) {
  if (!value) {
    return "--:--";
  }
  return new Date(value).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusLabel(status: string) {
  if (status === "solved") {
    return "Résolue";
  }
  if (status === "in_progress") {
    return "En cours";
  }
  return "Créée";
}

function AnimatedNumber({
  value,
  suffix = "",
  decimals = 0,
}: {
  value: number;
  suffix?: string;
  decimals?: number;
}) {
  const [display, setDisplay] = useState(value);
  const previousValueRef = useRef(value);

  useEffect(() => {
    const from = previousValueRef.current;
    const to = value;
    previousValueRef.current = value;

    if (from === to) {
      setDisplay(value);
      return;
    }

    const durationMs = 900;
    const startedAt = performance.now();
    let frameId = 0;

    const tick = (timestamp: number) => {
      const progress = Math.min((timestamp - startedAt) / durationMs, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(from + (to - from) * eased);
      if (progress < 1) {
        frameId = window.requestAnimationFrame(tick);
      }
    };

    frameId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frameId);
  }, [value]);

  return (
    <span>
      {new Intl.NumberFormat("fr-FR", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(display)}
      {suffix}
    </span>
  );
}

function computeLiveStats(missions: MissionSnapshot[], entries: LeaderboardEntry[]) {
  const solvedCount = missions.filter((mission) => mission.status === "solved").length;
  const incidentCount = missions.filter((mission) => mission.mission.random_incidents).length;
  const totalClients = missions.reduce((sum, mission) => sum + mission.mission.num_clients, 0);
  const avgBudget =
    missions.length > 0
      ? missions.reduce((sum, mission) => sum + mission.mission.budget, 0) / missions.length
      : 0;
  const avgScore = entries.length > 0 ? entries.reduce((sum, entry) => sum + entry.score, 0) / entries.length : 0;
  const uniqueZones = new Set(missions.map((mission) => mission.mission.zone)).size;
  const weatherMix = missions.reduce<Record<string, number>>((acc, mission) => {
    const key = mission.mission.weather_key;
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  return {
    totalMissions: missions.length,
    solvedCount,
    totalClients,
    avgBudget,
    avgScore,
    bestScore: entries[0]?.score ?? 0,
    uniqueZones,
    incidentRate: missions.length > 0 ? Math.round((incidentCount / missions.length) * 100) : 0,
    solveRate: missions.length > 0 ? Math.round((solvedCount / missions.length) * 100) : 0,
    pressureLevel:
      missions.length > 0 ? Math.min(100, Math.round((totalClients / missions.length / 50) * 100)) : 0,
    realWeatherRate:
      missions.length > 0 ? Math.round(((weatherMix.real ?? 0) / missions.length) * 100) : 0,
    lastMission: missions[0] ?? null,
  };
}

export function MissionCreator() {
  const router = useRouter();
  const { player } = usePlayer();
  const [sandbox, setSandbox] = useState({
    zone: "Bordeaux",
    num_clients: 30,
    budget: 3000,
    sleigh_cost: 500,
    weather_key: "real",
    random_incidents: false,
  });

  const createMutation = useMutation({
    mutationFn: createMission,
    onSuccess: (data) => {
      router.push(`/mission/${data.mission_id}`);
    },
  });

  const missionsQuery = useQuery({
    queryKey: ["missions", "salon"],
    queryFn: () => getMissions(24),
    refetchInterval: 15000,
  });

  const leaderboardQuery = useQuery({
    queryKey: ["leaderboard", "salon"],
    queryFn: () => getLeaderboard(5),
    refetchInterval: 15000,
  });

  const recentMissions = useMemo(() => missionsQuery.data?.missions ?? [], [missionsQuery.data?.missions]);
  const topEntries = useMemo(() => leaderboardQuery.data?.entries ?? [], [leaderboardQuery.data?.entries]);
  const liveStats = useMemo(() => computeLiveStats(recentMissions, topEntries), [recentMissions, topEntries]);
  const activityFeed = recentMissions.slice(0, 6);
  const stageBars = recentMissions.slice(0, 10).reverse();

  return (
    <div className="page-shell salon-shell">
      <div className="page-stack salon-stack">
        <section className="salon-hero salon-animate">
          <div className="salon-glow salon-glow-left" />
          <div className="salon-glow salon-glow-right" />
          <div className="salon-hero-grid">
            <div className="stack salon-copy">
              <span className="salon-badge">Mode Salon · écran live</span>
              <h1>
                Operation Noel
                <span className="salon-hero-subtitle">
                  Une façade de démonstration pensée pour tourner en grand écran, avec chiffres en direct et lancement
                  instantané.
                </span>
              </h1>
              <p className="salon-lead">
                Le flux récent des missions, le meilleur score du Panthéon et la pression opérationnelle remontent
                automatiquement. Le hub présente maintenant deux boucles: campagne contre IA et duel live entre
                joueurs.
              </p>
              <div className="salon-action-row">
                <Link href="/campaign" className="primary-button salon-cta">
                  Ouvrir la campagne
                </Link>
                <Link href="/versus" className="secondary-button salon-ghost">
                  Préparer le versus live
                </Link>
                <button
                  className="secondary-button salon-ghost"
                  onClick={() =>
                    createMutation.mutate({
                      zone: campaigns[2].zone,
                      num_clients: campaigns[2].num_clients,
                      budget: campaigns[2].budget,
                      sleigh_cost: campaigns[2].sleigh_cost,
                      weather_key: campaigns[2].weather_key,
                      random_incidents: campaigns[2].random_incidents,
                      ai_profile: campaigns[2].ai_profile,
                      level: campaigns[2].level,
                    })
                  }
                  disabled={createMutation.isPending}
                >
                  {createMutation.isPending ? "Initialisation..." : "Démo instantanée"}
                </button>
              </div>
              <div className="salon-inline-stats">
                <div className="salon-inline-chip">
                  <span>Joueur actif</span>
                  <strong>{player?.display_name ?? "Aucun profil"}</strong>
                </div>
                <div className="salon-inline-chip">
                  <span>Dernière zone</span>
                  <strong>{liveStats.lastMission?.mission.zone ?? "En attente"}</strong>
                </div>
                <div className="salon-inline-chip">
                  <span>Dernière activité</span>
                  <strong>{formatTimestamp(liveStats.lastMission?.updated_at)}</strong>
                </div>
              </div>
            </div>

            <div className="salon-stage salon-animate salon-delay-1">
              <div className="salon-stage-header">
                <div>
                  <span className="salon-stage-kicker">Régie temps réel</span>
                  <strong>Mur de contrôle</strong>
                </div>
                <span className="salon-pulse">Live</span>
              </div>
              <div className="salon-stage-grid">
                <div className="salon-stage-card">
                  <span>Résolution</span>
                  <strong>
                    <AnimatedNumber value={liveStats.solveRate} suffix="%" />
                  </strong>
                </div>
                <div className="salon-stage-card">
                  <span>Pression</span>
                  <strong>
                    <AnimatedNumber value={liveStats.pressureLevel} suffix="/100" />
                  </strong>
                </div>
                <div className="salon-stage-card">
                  <span>Incidents</span>
                  <strong>
                    <AnimatedNumber value={liveStats.incidentRate} suffix="%" />
                  </strong>
                </div>
                <div className="salon-stage-card">
                  <span>Météo réelle</span>
                  <strong>
                    <AnimatedNumber value={liveStats.realWeatherRate} suffix="%" />
                  </strong>
                </div>
              </div>
              <div className="salon-stage-graph">
                {stageBars.length > 0 ? (
                  stageBars.map((mission, index) => (
                    <div key={`${mission.mission_id}-${index}`} className="salon-bar-column">
                      <div
                        className={`salon-bar status-${mission.status}`}
                        style={{ height: `${Math.max(18, Math.min(100, mission.mission.num_clients * 2))}%` }}
                      />
                      <span>{mission.mission.num_clients}</span>
                    </div>
                  ))
                ) : (
                  <div className="salon-stage-empty">Aucune télémétrie disponible pour le moment.</div>
                )}
              </div>
            </div>
          </div>
        </section>

        {createMutation.error ? (
          <div className="error-box salon-animate salon-delay-1">
            {createMutation.error instanceof Error ? createMutation.error.message : "Création impossible"}
          </div>
        ) : null}

        <section className="grid-4 salon-animate salon-delay-1">
          <div className="metric-card salon-metric-card">
            <div className="metric-label">Missions monitorées</div>
            <div className="metric-value">
              <AnimatedNumber value={liveStats.totalMissions} />
            </div>
            <span className="muted">Fenêtre récente de démonstration</span>
          </div>
          <div className="metric-card salon-metric-card">
            <div className="metric-label">Colis simulés</div>
            <div className="metric-value">
              <AnimatedNumber value={liveStats.totalClients} />
            </div>
            <span className="muted">Somme des clients sur le flux affiché</span>
          </div>
          <div className="metric-card salon-metric-card">
            <div className="metric-label">Top score</div>
            <div className="metric-value">
              <AnimatedNumber value={liveStats.bestScore} decimals={1} suffix="/100" />
            </div>
            <span className="muted">Meilleur résultat remonté du Panthéon</span>
          </div>
          <div className="metric-card salon-metric-card">
            <div className="metric-label">Zones actives</div>
            <div className="metric-value">
              <AnimatedNumber value={liveStats.uniqueZones} />
            </div>
            <span className="muted">Villes et quartiers distincts visibles</span>
          </div>
        </section>

        <section className="grid-3 salon-animate salon-delay-2">
          <div className="panel stack">
            <strong>Mode campagne</strong>
            <span className="muted">Progression par niveaux, IA variées, étoiles et meilleure note locale.</span>
            <Link className="secondary-button" href="/campaign">
              Voir la carte de campagne
            </Link>
          </div>
          <div className="panel stack">
            <strong>Mode versus</strong>
            <span className="muted">Même seed, même chrono, comparaison en direct des runs.</span>
            <Link className="secondary-button" href="/versus">
              Voir la feuille de route
            </Link>
          </div>
          <div className="panel stack">
            <strong>Mode salon</strong>
            <span className="muted">Toujours utile pour les démos rapides, les scores live et le lancement express.</span>
            <a href="#launch-grid" className="secondary-button">
              Lancer un scénario vitrine
            </a>
          </div>
        </section>

        <section className="grid-3 salon-animate salon-delay-2">
          <div className="panel stack salon-feed-panel">
            <div className="salon-panel-head">
              <strong>Flux mission</strong>
              <span className="muted">Actualisé toutes les 15 s</span>
            </div>
            {activityFeed.length > 0 ? (
              activityFeed.map((mission) => (
                <div key={mission.mission_id} className="salon-feed-row">
                  <div>
                    <strong>{mission.mission.zone}</strong>
                    <span className="muted">
                      {mission.mission.num_clients} clients · météo {mission.mission.weather_key}
                    </span>
                  </div>
                  <div className="salon-feed-meta">
                    <span className={`tag salon-status-chip status-${mission.status}`}>{statusLabel(mission.status)}</span>
                    <span className="muted">{formatTimestamp(mission.updated_at)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="muted">Aucune mission récente à afficher.</div>
            )}
          </div>

          <div className="panel stack salon-feed-panel">
            <div className="salon-panel-head">
              <strong>Top score live</strong>
              <span className="muted">Classement visible en régie</span>
            </div>
            {topEntries.length > 0 ? (
              topEntries.map((entry, index) => (
                <div key={`${entry.mission_id}-${index}`} className="salon-feed-row">
                  <div>
                    <strong>
                      {index + 1}. {entry.player_name}
                    </strong>
                    <span className="muted">{entry.zone}</span>
                  </div>
                  <div className="salon-feed-meta">
                    <strong>{entry.score.toFixed(1)}/100</strong>
                    <span className="muted">{entry.rank}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="muted">Le Panthéon n&apos;a pas encore d&apos;entrée.</div>
            )}
          </div>

          <div className="panel stack salon-feed-panel">
            <div className="salon-panel-head">
              <strong>Intensité salon</strong>
              <span className="muted">Résumé opérationnel</span>
            </div>
            <div className="salon-meter">
              <div className="salon-meter-head">
                <span>Taux de résolution</span>
                <strong>{liveStats.solveRate}%</strong>
              </div>
              <div className="salon-meter-track">
                <div className="salon-meter-fill fill-primary" style={{ width: `${liveStats.solveRate}%` }} />
              </div>
            </div>
            <div className="salon-meter">
              <div className="salon-meter-head">
                <span>Scénarios incidents</span>
                <strong>{liveStats.incidentRate}%</strong>
              </div>
              <div className="salon-meter-track">
                <div className="salon-meter-fill fill-alert" style={{ width: `${liveStats.incidentRate}%` }} />
              </div>
            </div>
            <div className="salon-meter">
              <div className="salon-meter-head">
                <span>Budget moyen</span>
                <strong>{Math.round(liveStats.avgBudget)} €</strong>
              </div>
              <div className="salon-meter-track">
                <div
                  className="salon-meter-fill fill-secondary"
                  style={{ width: `${Math.min(100, Math.round((liveStats.avgBudget / 4000) * 100))}%` }}
                />
              </div>
            </div>
            <div className="salon-meter">
              <div className="salon-meter-head">
                <span>Score moyen</span>
                <strong>{liveStats.avgScore.toFixed(1)}/100</strong>
              </div>
              <div className="salon-meter-track">
                <div className="salon-meter-fill fill-success" style={{ width: `${Math.min(100, liveStats.avgScore)}%` }} />
              </div>
            </div>
          </div>
        </section>

        <section id="launch-grid" className="stack salon-animate salon-delay-2">
          <div className="salon-section-head">
            <div>
              <strong>Scénarios express</strong>
              <p>Trois entrées prêtes à lancer pour faire tourner la démonstration sans réglage.</p>
            </div>
          </div>
          <div className="grid-3">
            {campaigns.map((campaign) => (
              <button
                key={campaign.level}
                className="panel card-button stack salon-scenario-card"
                onClick={() =>
                  createMutation.mutate({
                    zone: campaign.zone,
                    num_clients: campaign.num_clients,
                    budget: campaign.budget,
                    sleigh_cost: campaign.sleigh_cost,
                    weather_key: campaign.weather_key,
                    random_incidents: campaign.random_incidents,
                    ai_profile: campaign.ai_profile,
                    level: campaign.level,
                  })
                }
                disabled={createMutation.isPending}
              >
                <span className="salon-scenario-level">Niveau {campaign.level}</span>
                <strong>{campaign.title}</strong>
                <span className="muted">{campaign.tone}</span>
                <div className="salon-scenario-metrics">
                  <span>{campaign.num_clients} livraisons</span>
                  <span>{campaign.budget} €</span>
                  <span>{campaign.weather_key}</span>
                  <span>IA {campaign.ai_profile}</span>
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="panel salon-control-panel salon-animate salon-delay-3">
          <div className="salon-control-copy">
            <strong>Partie libre</strong>
            <p>
              Garde la façade spectaculaire, mais laisse aussi un opérateur configurer une zone sur mesure pour une
              démonstration plus guidée.
            </p>
          </div>
          <div className="grid-2">
            <label className="field">
              <span>Zone</span>
              <input
                value={sandbox.zone}
                onChange={(event) => setSandbox((prev) => ({ ...prev, zone: event.target.value }))}
                placeholder="Quartier, ville, pays"
              />
            </label>
            <label className="field">
              <span>Météo</span>
              <select
                value={sandbox.weather_key}
                onChange={(event) => setSandbox((prev) => ({ ...prev, weather_key: event.target.value }))}
              >
                <option value="real">🌍 Temps réel</option>
                <option value="random">Aléatoire</option>
                <option value="Clear">Soleil</option>
                <option value="Rain">Pluie</option>
                <option value="Snow">Neige</option>
                <option value="Thunderstorm">Tempête</option>
              </select>
            </label>
            <label className="field">
              <span>Nombre de clients</span>
              <input
                type="number"
                value={sandbox.num_clients}
                onChange={(event) => setSandbox((prev) => ({ ...prev, num_clients: Number(event.target.value) }))}
              />
            </label>
            <label className="field">
              <span>Budget</span>
              <input
                type="number"
                value={sandbox.budget}
                onChange={(event) => setSandbox((prev) => ({ ...prev, budget: Number(event.target.value) }))}
              />
            </label>
          </div>
          <div className="salon-control-footer">
            <label className="tag" style={{ width: "fit-content" }}>
              <input
                type="checkbox"
                checked={sandbox.random_incidents}
                onChange={(event) => setSandbox((prev) => ({ ...prev, random_incidents: event.target.checked }))}
              />
              Incidents aléatoires
            </label>
            <button className="primary-button" onClick={() => createMutation.mutate({ ...sandbox, level: null })}>
              {createMutation.isPending ? "Création..." : "Créer la mission"}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
