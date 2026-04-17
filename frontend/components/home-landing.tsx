import Link from "next/link";
import type { Route } from "next";

const sections = [
  {
    title: "Campagne",
    description: "Progression solo contre l'IA, missions verrouillées, score et étoiles.",
    href: "/campaign" as Route,
    cta: "Entrer en campagne",
    route: "/campaign",
  },
  {
    title: "Versus",
    description: "Prépare la future boucle joueur contre joueur avec seed partagé et résultats comparés.",
    href: "/versus" as Route,
    cta: "Voir le versus",
    route: "/versus",
  },
  {
    title: "Salon",
    description: "Le grand hub visuel et live existe toujours, mais il vit maintenant sur sa propre page.",
    href: "/salon" as Route,
    cta: "Ouvrir le mode salon",
    route: "/salon",
  },
  {
    title: "Panthéon",
    description: "Consulte les meilleurs scores et les profils déjà entrés dans la base.",
    href: "/leaderboard" as Route,
    cta: "Voir le classement",
    route: "/leaderboard",
  },
];

export function HomeLanding() {
  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero landing-hero landing-entry-hero">
          <div className="stack landing-entry-copy">
            <span className="salon-badge">Portail officiel</span>
            <h1 className="landing-entry-title">Operation Noel</h1>
            <p>
              Voici la vraie page d&apos;entrée: auth séparée, campagne séparée, versus séparé, hub salon séparé.
            </p>
            <div className="landing-route-strip">
              <span className="tag landing-route-pill">/register</span>
              <span className="tag landing-route-pill">/login</span>
              <span className="tag landing-route-pill">/campaign</span>
              <span className="tag landing-route-pill">/versus</span>
              <span className="tag landing-route-pill">/salon</span>
            </div>
          </div>
          <div className="panel stack landing-auth-panel">
            <strong>Accès joueur</strong>
            <p className="muted">Commence par créer un compte ou reprendre une session existante.</p>
            <div className="landing-hero-actions">
              <Link className="primary-button" href="/register">
                S&apos;inscrire
              </Link>
              <Link className="secondary-button" href="/login">
                Se connecter
              </Link>
            </div>
          </div>
        </section>

        <section className="landing-grid">
          {sections.map((section) => (
            <article key={section.href} className="panel stack landing-card">
              <div className="landing-card-head">
                <strong>{section.title}</strong>
                <span className="tag">{section.route}</span>
              </div>
              <p className="muted">{section.description}</p>
              <Link className="secondary-button" href={section.href}>
                {section.cta}
              </Link>
            </article>
          ))}
        </section>
      </div>
    </div>
  );
}
