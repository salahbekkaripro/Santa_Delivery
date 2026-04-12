import Link from "next/link";
import type { Route } from "next";

const sections = [
  {
    title: "Campagne",
    description: "Progression solo contre l'IA, missions verrouillées, score et étoiles.",
    href: "/campaign" as Route,
    cta: "Entrer en campagne",
  },
  {
    title: "Versus",
    description: "Prépare la future boucle joueur contre joueur avec seed partagé et résultats comparés.",
    href: "/versus" as Route,
    cta: "Voir le versus",
  },
  {
    title: "Salon",
    description: "Le grand hub visuel et live existe toujours, mais il vit maintenant sur sa propre page.",
    href: "/salon" as Route,
    cta: "Ouvrir le mode salon",
  },
  {
    title: "Panthéon",
    description: "Consulte les meilleurs scores et les profils déjà entrés dans la base.",
    href: "/leaderboard" as Route,
    cta: "Voir le classement",
  },
];

export function HomeLanding() {
  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero landing-hero">
          <div className="stack">
            <span className="salon-badge">Operation Noel</span>
            <h1>Choisis une vraie page d&apos;entrée</h1>
            <p>
              Tu avais raison: l&apos;accueil ne doit pas ressembler à un seul écran qui mélange tout. On garde des routes
              distinctes pour l&apos;auth, la campagne, le versus et le hub salon.
            </p>
          </div>
          <div className="landing-hero-actions">
            <Link className="primary-button" href="/register">
              S&apos;inscrire
            </Link>
            <Link className="secondary-button" href="/login">
              Se connecter
            </Link>
          </div>
        </section>

        <section className="landing-grid">
          {sections.map((section) => (
            <article key={section.href} className="panel stack landing-card">
              <strong>{section.title}</strong>
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
