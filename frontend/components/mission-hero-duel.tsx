"use client";

import Link from "next/link";

type MissionHeroDuelProps = {
  missionZone: string;
  weatherLabel: string;
  weatherIcon: string;
  weatherCls: string;
  missionLevel?: number | null;
  aiLabel: string;
  aiDifficultyBonus: number;
  clientCount: number;
  budget: number;
  overloadedSleighs: number[];
  assignedClientsCount: number;
  totalClientsCount: number;
  progressPct: number;
  estimatedTimeLabel: string;
  estimatedDistanceKm: number;
  incidentsCount: number;
  versusMatchId?: string | null;
  versusSelfState?: string;
  versusConnection: string;
  versusCountdown?: number | null;
  selfAssignedClients: number;
  selfTotalClients: number;
  selfProgressPct: number;
  hasOpponent: boolean;
  opponentDisplayName?: string | null;
  opponentAssignedClients: number;
  opponentTotalClients: number;
  opponentProgressPct: number;
  submitPending: boolean;
  versusLocked: boolean;
  canSubmit: boolean;
  remainingClientsCount: number;
  showVersusReminder: boolean;
  onSubmitAttempt: () => void;
  onDismissReminder: () => void;
};

export function MissionHeroDuel(props: MissionHeroDuelProps) {
  return (
    <>
      <section className="hero" data-onboarding-id="versus-mission-hero">
        <h1>{props.missionZone}</h1>
        <div className="hero-badges">
          <span className={`hero-badge ${props.weatherCls}`}>
            {props.weatherIcon} {props.weatherLabel}
          </span>
          <span className="hero-badge">
            {props.missionLevel ? `Niveau ${props.missionLevel}` : "Sandbox"}
          </span>
          <span className="hero-badge">
            IA {props.aiLabel} · +{props.aiDifficultyBonus} score
          </span>
          <span className="hero-badge">
            {props.clientCount} clients · {props.budget} €
          </span>
          {props.overloadedSleighs.length > 0 && (
            <span className="hero-badge incident-badge">
              ⚠️ Surcharge #{props.overloadedSleighs.join(", #")}
            </span>
          )}
        </div>
        <div className="hero-progress">
          <div className="hero-progress-fill" style={{ width: `${props.progressPct}%` }} />
        </div>
        <p className="hero-progress-label">
          {props.assignedClientsCount} / {props.totalClientsCount} clients assignés
        </p>
      </section>

      <div className="grid-4">
        <div className="metric-card">
          <div className="metric-label">Temps estimé</div>
          <div className="metric-value">{props.estimatedTimeLabel}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Distance</div>
          <div className="metric-value">{props.estimatedDistanceKm.toFixed(2)} km</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Clients assignés</div>
          <div className="metric-value">{props.assignedClientsCount} / {props.totalClientsCount}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Budget restant</div>
          <div className="metric-value">{props.budget} €</div>
        </div>
      </div>

      {props.incidentsCount > 0 && (
        <div className="error-box">
          ⚠️ Incidents actifs : {props.incidentsCount} axe(s) bloqué(s) — visible sur la carte.
        </div>
      )}

      {props.versusMatchId && (
        <section className="panel stack" data-onboarding-id="versus-mission-duel-panel">
          <div className="panel-head">
            <strong>⚔️ Duel Versus</strong>
            <span className="tag">Match {props.versusMatchId}</span>
          </div>
          <span className="muted">
            État duel: {props.versusSelfState ?? "inconnu"} · Soumission valide requise: tous les clients assignés.
          </span>
          <span className="muted">
            Live: {props.versusConnection === "open" ? "connecté" : props.versusConnection}
            {props.versusCountdown && props.versusCountdown > 0 ? ` · départ dans ${props.versusCountdown}s` : ""}
          </span>
          <div style={{ display: "grid", gap: 8 }}>
            <div>
              <span className="muted" style={{ fontSize: "0.82rem" }}>
                Moi: {props.selfAssignedClients}/{props.selfTotalClients} clients
              </span>
              <div className="hero-progress" style={{ marginTop: 4 }}>
                <div className="hero-progress-fill" style={{ width: `${Math.max(0, Math.min(100, props.selfProgressPct))}%` }} />
              </div>
            </div>
            {props.hasOpponent && (
              <div>
                <span className="muted" style={{ fontSize: "0.82rem" }}>
                  {props.opponentDisplayName ?? "Adversaire"}: {props.opponentAssignedClients}/{props.opponentTotalClients} clients
                </span>
                <div className="hero-progress" style={{ marginTop: 4 }}>
                  <div
                    className="hero-progress-fill"
                    style={{ width: `${Math.max(0, Math.min(100, props.opponentProgressPct))}%`, background: "var(--accent-2)" }}
                  />
                </div>
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              className="primary-button"
              onClick={props.onSubmitAttempt}
              disabled={!props.canSubmit || props.submitPending || props.versusLocked}
              data-onboarding-id="versus-mission-submit"
            >
              {props.submitPending
                ? "Soumission..."
                : props.versusLocked
                  ? "Tentative soumise"
                  : props.remainingClientsCount > 0
                    ? `Soumettre ma tentative (reste ${props.remainingClientsCount})`
                    : "Soumettre ma tentative"}
            </button>
            <Link className="secondary-button" href={`/versus/match/${props.versusMatchId}`} data-onboarding-id="versus-mission-back">
              Retour au match live
            </Link>
          </div>
        </section>
      )}

      {props.versusMatchId && !props.versusLocked && props.showVersusReminder && props.remainingClientsCount > 0 && (
        <section className="versus-reminder-toast" role="status" aria-live="polite">
          <div className="versus-reminder-copy">
            <strong>Soumission incomplète</strong>
            <span>
              Il reste {props.remainingClientsCount} client{props.remainingClientsCount > 1 ? "s" : ""} à assigner avant la validation de ta tentative.
            </span>
          </div>
          <button className="secondary-button" onClick={props.onDismissReminder}>
            Masquer
          </button>
        </section>
      )}
    </>
  );
}
