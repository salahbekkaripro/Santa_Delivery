import Link from "next/link";

export default function VersusPage() {
  return (
    <div className="page-shell campaign-shell">
      <div className="page-stack campaign-stack">
        <section className="campaign-hero">
          <div className="campaign-hero-copy">
            <span className="salon-badge">Versus · Direct entre joueurs</span>
            <h1>Duel live à seed partagé</h1>
            <p>
              Ce mode est la prochaine étape: même mission, même seed, même chrono, puis comparaison instantanée des
              plans et du score final.
            </p>
          </div>
          <div className="campaign-hero-stats">
            <div className="campaign-stat-card">
              <span>Future room</span>
              <strong>1 seed</strong>
            </div>
            <div className="campaign-stat-card">
              <span>Comparaison</span>
              <strong>Live</strong>
            </div>
            <div className="campaign-stat-card">
              <span>État actuel</span>
              <strong>À construire</strong>
            </div>
          </div>
        </section>

        <section className="grid-3">
          <div className="panel stack">
            <strong>Boucle de jeu visée</strong>
            <span className="muted">Lobby</span>
            <span className="muted">Seed commun</span>
            <span className="muted">Timer partagé</span>
            <span className="muted">Score final en direct</span>
          </div>
          <div className="panel stack">
            <strong>Pré-requis techniques</strong>
            <span className="muted">Rooms et session de match</span>
            <span className="muted">WebSocket ou polling temps réel</span>
            <span className="muted">Synchronisation et anti-triche minimale</span>
          </div>
          <div className="panel stack">
            <strong>Navigation</strong>
            <Link className="secondary-button" href="/campaign">
              Ouvrir la campagne
            </Link>
            <Link className="primary-button" href="/">
              Retour au hub
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
