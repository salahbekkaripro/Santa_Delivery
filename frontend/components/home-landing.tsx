"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePlayer } from "./player-provider";

const modes = [
  {
    icon: "🗺️",
    label: "Solo",
    title: "Campagne",
    description: "8 missions progressives contre l'IA — du Marais à Stockholm. Score, étoiles et déblocage.",
    href: "/campaign" as Route,
    cta: "Entrer en campagne →",
  },
  {
    icon: "⚔️",
    label: "Compétitif",
    title: "Versus",
    description: "Même seed, même carte. Qui de vous deux bat l'IA avec le meilleur score ?",
    href: "/versus" as Route,
    cta: "Mode versus →",
  },
  {
    icon: "💬",
    label: "Communauté",
    title: "Social",
    description: "Ajoute des amis, gère tes demandes et discute en messages privés 1v1.",
    href: "/social" as Route,
    cta: "Ouvrir le social hub →",
  },
  {
    icon: "🎪",
    label: "Démo live",
    title: "Salon",
    description: "Hub visuel en temps réel : flux de missions, stats live, scénarios express et création libre.",
    href: "/salon" as Route,
    cta: "Ouvrir le salon →",
  },
  {
    icon: "🧮",
    label: "Solveur",
    title: "Solveur libre",
    description: "Saisis n'importe quelle adresse, choisis le nombre de colis — l'IA calcule la tournée optimale sur le vrai réseau routier.",
    href: "/solver" as Route,
    cta: "Lancer le solveur →",
  },
  {
    icon: "🔬",
    label: "Algorithmes",
    title: "Coulisses",
    description: "Graphe OSM, Dijkstra animé, OR-Tools et 2-opt expliqués interactivement.",
    href: "/explore" as Route,
    cta: "Explorer →",
  },
  {
    icon: "📊",
    label: "Données",
    title: "Données & projet",
    description: "Sources ouvertes (OSM, Overpass, OpenWeatherMap), pipeline de traitement et architecture du projet.",
    href: "/data" as Route,
    cta: "Découvrir →",
  },
];

const quickStats = [
  { value: "6", label: "Profils IA" },
  { value: "8", label: "Missions campagne" },
  { value: "∞", label: "Rejouabilité" },
];

const flowSteps = [
  "Choisis une mission",
  "Trace ta tournée",
  "Compare avec l'IA",
  "Optimise ton score",
];

export function HomeLanding() {
  const { player, isReady } = usePlayer();

  return (
    <div className="home-root">

      {/* HERO PLEIN ÉCRAN */}
      <section className="home-hero">
        <div className="home-hero-stars" aria-hidden="true" />
        <div className="home-hero-glow-a" aria-hidden="true" />
        <div className="home-hero-glow-b" aria-hidden="true" />

        <div className="home-hero-inner">
          <span className="home-hero-kicker">🎄 Portail officiel · Saison 2026</span>

          <h1 className="home-hero-title">
            Operation
            <em className="home-hero-title-accent">Noël</em>
          </h1>

          <p className="home-hero-desc">
            Tu es l&apos;agent de livraison du Père Noël.<br />
            Planifie tes tournées, bats l&apos;IA et deviens légende du Pôle Nord.
          </p>

          <div className="home-hero-actions">
            <Link className="home-hero-cta" href="/campaign">
              🚀 Commencer la campagne
            </Link>
            <Link className="home-hero-ghost" href="/salon">
              Démo rapide
            </Link>
          </div>

          <div className="home-hero-metrics">
            {quickStats.map((item) => (
              <div key={item.label} className="home-hero-metric">
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="home-hero-scroll" aria-hidden="true">↓</div>
      </section>

      {/* CONTENU */}
      <div className="page-shell">
        <div className="page-stack">

          {/* MODES */}
          <div className="home-modes-grid">
            {modes.map((mode, index) => (
              <Link
                key={mode.href}
                className={`home-mode-card reveal-lift reveal-delay-${index + 1}`}
                href={mode.href}
              >
                <div className="home-mode-head">
                  <span className="home-mode-icon">{mode.icon}</span>
                  <span className="home-mode-index">{String(index + 1).padStart(2, "0")}</span>
                </div>
                <span className="home-mode-label">{mode.label}</span>
                <h2 className="home-mode-title">{mode.title}</h2>
                <p className="home-mode-desc">{mode.description}</p>
                <span className="home-mode-arrow">{mode.cta}</span>
              </Link>
            ))}
          </div>

          {/* AUTH COMPACT */}
          {!player && isReady && (
            <section className="home-auth-row">
              <div className="home-auth-row-copy">
                <strong>Rejoins le Panthéon</strong>
                <p>
                  Crée un compte pour sauvegarder ta progression, entrer au classement mondial et débloquer
                  l&apos;historique de missions.
                </p>
              </div>
              <div className="home-auth-row-actions">
                <Link className="primary-button" href="/register">
                  S&apos;inscrire gratuitement
                </Link>
                <Link className="secondary-button home-auth-ghost-btn" href="/login">
                  Se connecter
                </Link>
              </div>
            </section>
          )}

          {/* FLOW STRIP */}
          <section className="home-flow-strip">
            <div className="home-flow-copy">
              <strong>Comment ça marche</strong>
              <p>
                Crée ou choisis une mission, pilote tes traîneaux sur la carte, puis compare ton plan avec
                l&apos;IA pour maximiser ton score final.
              </p>
            </div>
            <div className="home-flow-steps">
              {flowSteps.map((step) => (
                <span key={step} className="home-flow-step">{step}</span>
              ))}
            </div>
            <div className="home-flow-stats">
              {[
                { label: "Villes", value: "∞" },
                { label: "Profils IA", value: "6" },
                { label: "Niveaux", value: "8" },
              ].map((stat) => (
                <div key={stat.label} className="home-flow-stat">
                  <div className="home-flow-value">{stat.value}</div>
                  <div className="home-flow-label">{stat.label}</div>
                </div>
              ))}
            </div>
            <div className="home-flow-cta">
              <Link className="secondary-button" href="/campaign">Voir la campagne</Link>
              <Link className="secondary-button" href="/leaderboard">Explorer le Panthéon</Link>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
