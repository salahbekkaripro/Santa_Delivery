import Link from "next/link";
import type { Route } from "next";

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
    icon: "🎪",
    label: "Démo live",
    title: "Salon",
    description: "Hub visuel en temps réel : flux de missions, stats live, scénarios express et création libre.",
    href: "/salon" as Route,
    cta: "Ouvrir le salon →",
  },
  {
    icon: "🏆",
    label: "Classement",
    title: "Panthéon",
    description: "Les meilleurs agents de livraison. Consulte les scores, profils et zones conquises.",
    href: "/leaderboard" as Route,
    cta: "Voir le classement →",
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
  return (
    <div className="page-shell">
      <div className="page-stack">

        {/* HERO */}
        <section className="home-hero reveal-lift">
          <div className="home-hero-copy">
            <span className="home-hero-kicker">🎄 Portail officiel · Saison 2025</span>
            <h1 className="home-hero-title">Operation<br />Noël</h1>
            <p className="home-hero-desc">
              Tu es l&apos;agent de livraison du Père Noël. Planifie tes tournées de traîneaux, bats l&apos;IA et deviens légende du Pôle Nord.
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
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="home-auth-panel">
            <strong>Accès joueur</strong>
            <p className="muted">
              Crée un compte pour sauvegarder ta progression, ton score et entrer au Panthéon.
            </p>
            <div className="home-auth-benefits">
              <span>✓ Progression sauvegardée</span>
              <span>✓ Classement joueur</span>
              <span>✓ Historique des missions</span>
            </div>
            <Link className="primary-button home-auth-link" href="/register">
              S&apos;inscrire gratuitement
            </Link>
            <div className="home-auth-divider">ou</div>
            <Link className="secondary-button home-auth-link" href="/login">
              Se connecter
            </Link>
            <span className="muted home-auth-note">
              Joue sans compte pour tester
            </span>
          </div>
        </section>

        {/* MODES */}
        <div className="home-modes-grid">
          {modes.map((mode, index) => (
            <Link key={mode.href} className={`home-mode-card reveal-lift reveal-delay-${index + 1}`} href={mode.href}>
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

        {/* INFO STRIP */}
        <section className="home-flow-strip">
          <div className="home-flow-copy">
            <strong>Comment ça marche</strong>
            <p>
              Crée ou choisis une mission, pilote tes traîneaux sur la carte, puis compare ton plan avec l&apos;IA pour maximiser ton score final.
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
  );
}
