"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getDebrief } from "@/lib/api";

function asMinutes(seconds: number) {
  return `${Math.round(seconds / 60)} min`;
}

function asDistance(meters: number) {
  return `${(meters / 1000).toFixed(2)} km`;
}

export function DebriefView({ missionId }: { missionId: string }) {
  const debriefQuery = useQuery({
    queryKey: ["debrief", missionId],
    queryFn: () => getDebrief(missionId)
  });

  if (debriefQuery.isLoading) {
    return <div className="page-shell">Chargement du debriefing...</div>;
  }

  if (debriefQuery.error || !debriefQuery.data) {
    return <div className="page-shell error-box">Debriefing indisponible.</div>;
  }

  const debrief = debriefQuery.data;
  const humanDeltaS = Number(debrief.analysis.human_vs_ai_delta_s ?? 0);

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Debriefing mission</h1>
          <p>
            Rang {debrief.score.rank} · {debrief.score.rank_title} · score {debrief.score.value}/100
          </p>
        </section>

        <section className="grid-4">
          <div className="metric-card">
            <div className="metric-label">Gain temps</div>
            <div className="metric-value">{debrief.benchmark.savings.time_saved_pct}%</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">CO2 economise</div>
            <div className="metric-value">{debrief.benchmark.savings.co2_saved_kg} kg</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Budget restant</div>
            <div className="metric-value">{debrief.benchmark.budget?.remaining ?? 0} €</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Clients humains</div>
            <div className="metric-value">{debrief.human.assigned_clients.length}</div>
          </div>
        </section>

        <section className="grid-3">
          <div className="panel stack">
            <strong>Resume IA</strong>
            <span className="muted">Temps total: {asMinutes(debrief.results.total_time_s)}</span>
            <span className="muted">Poids livre: {debrief.results.total_weight_kg} kg</span>
            <span className="muted">Points non servis: {debrief.analysis.dropped_points.length}</span>
            <span className="muted">Bonus humain: {debrief.score.human_beat_ai ? "oui" : "non"}</span>
          </div>
          <div className="panel stack">
            <strong>Comparaison</strong>
            <span className="muted">Humain: {asMinutes(debrief.human.summary.total_time_s)}</span>
            <span className="muted">IA: {asMinutes(debrief.results.total_time_s)}</span>
            <span className="muted">
              Ecart humain vs IA: {humanDeltaS > 0 ? `+${asMinutes(humanDeltaS)}` : humanDeltaS < 0 ? `-${asMinutes(Math.abs(humanDeltaS))}` : "0 min"}
            </span>
            <span className="muted">Gain vs naif: {asMinutes(debrief.analysis.naive_vs_ai_delta_s)}</span>
          </div>
          <div className="panel stack">
            <strong>Navigation</strong>
            <Link className="secondary-button" href={`/mission/${missionId}/results`}>
              Retour aux resultats
            </Link>
            <Link className="primary-button" href={`/mission/${missionId}`}>
              Revenir a la mission
            </Link>
          </div>
        </section>

        <section className="grid-2">
          <div className="panel stack">
            <strong>Analyse par traineau humain</strong>
            {debrief.human.sleighs && debrief.human.sleighs.length > 0 ? (
              debrief.human.sleighs.map((sleigh) => (
                <span key={`human-${sleigh.sleigh_id}`} className="muted">
                  T#{sleigh.sleigh_id + 1} · {sleigh.stop_count} stop(s) · {asMinutes(sleigh.time_s)} · {asDistance(sleigh.dist_m)} · retour {sleigh.return_arrival_clock ?? "--:--"}
                </span>
              ))
            ) : (
              <span className="muted">Pas de trace humaine detaillee.</span>
            )}
          </div>
          <div className="panel stack">
            <strong>Analyse par traineau IA</strong>
            {debrief.analysis.ai_sleighs.length > 0 ? (
              debrief.analysis.ai_sleighs.map((sleigh) => (
                <span key={`ai-${sleigh.sleigh_id}`} className="muted">
                  T#{sleigh.sleigh_id + 1} · {sleigh.stop_count} stop(s) · {asMinutes(sleigh.time_s)} · {sleigh.weight_kg} kg
                </span>
              ))
            ) : (
              <span className="muted">Pas de tournee IA detaillee.</span>
            )}
          </div>
        </section>

        <section className="panel stack">
          <strong>Recommandations</strong>
          {debrief.analysis.recommendations.map((recommendation) => (
            <span key={recommendation} className="muted">
              {recommendation}
            </span>
          ))}
        </section>
      </div>
    </div>
  );
}
