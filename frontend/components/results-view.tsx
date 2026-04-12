"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { getComparison, getDebrief, getMission } from "@/lib/api";
import { MapSurface } from "@/components/map-surface";
import { AISleighSummary, ComparisonPayload, DebriefPayload, HumanSleighSummary, MissionResponse } from "@/lib/types";

function asMinutes(seconds: number) {
  return `${Math.round(seconds / 60)} min`;
}

function asDistance(meters: number) {
  return `${(meters / 1000).toFixed(2)} km`;
}

export function ResultsView({ missionId }: { missionId: string }) {
  const [showHuman, setShowHuman] = useState(true);
  const [showAi, setShowAi] = useState(true);

  const missionQuery = useQuery({
    queryKey: ["mission", missionId],
    queryFn: () => getMission(missionId)
  });
  const comparisonQuery = useQuery({
    queryKey: ["comparison", missionId],
    queryFn: () => getComparison(missionId)
  });
  const debriefQuery = useQuery({
    queryKey: ["debrief", missionId],
    queryFn: () => getDebrief(missionId)
  });

  if (missionQuery.isLoading || comparisonQuery.isLoading || debriefQuery.isLoading) {
    return <div className="page-shell">Chargement des resultats...</div>;
  }

  if (missionQuery.error || comparisonQuery.error || debriefQuery.error || !missionQuery.data || !comparisonQuery.data || !debriefQuery.data) {
    return <div className="page-shell error-box">Impossible de charger les resultats de mission.</div>;
  }

  const mission: MissionResponse = missionQuery.data;
  const comparison: ComparisonPayload = comparisonQuery.data;
  const debrief: DebriefPayload = debriefQuery.data;
  const humanTimeS = Number(comparison.summary_metrics.human.total_time_s ?? 0);
  const aiTimeS = Number(comparison.summary_metrics.ai.total_time_s ?? debrief.results.total_time_s ?? 0);
  const humanDistM = Number(comparison.summary_metrics.human.total_dist_m ?? 0);
  const aiDistM = Number(comparison.summary_metrics.ai.total_dist_m ?? 0);
  const deltaS = humanTimeS - aiTimeS;
  const deltaLabel = deltaS > 0 ? `+${asMinutes(deltaS)}` : deltaS < 0 ? `-${asMinutes(Math.abs(deltaS))}` : "0 min";
  const humanSleighs = comparison.summary_metrics.human.sleighs ?? [];
  const aiSleighs = comparison.summary_metrics.ai.sleighs ?? [];
  const aiStrategy = debrief.results.ai_strategy ?? comparison.summary_metrics.ai.strategy;

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Resultats IA vs humain</h1>
          <p>
            {mission.mission.zone} · mission {missionId} · score {debrief.score.value}/100
            {aiStrategy ? ` · IA ${aiStrategy.label}` : mission.mission.ai_profile ? ` · IA ${mission.mission.ai_profile}` : ""}
          </p>
        </section>

        <section className="grid-4">
          <div className="metric-card">
            <div className="metric-label">Temps IA</div>
            <div className="metric-value">{asMinutes(debrief.results.total_time_s)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Temps humain</div>
            <div className="metric-value">{asMinutes(humanTimeS)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Distance IA</div>
            <div className="metric-value">{asDistance(aiDistM)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Ecart humain vs IA</div>
            <div className="metric-value">{deltaLabel}</div>
          </div>
        </section>

        <section className="panel stack">
          <div className="legend">
            <label className="legend-chip">
              <input type="checkbox" checked={showHuman} onChange={(event) => setShowHuman(event.target.checked)} />
              <span className="line-dot is-dashed" style={{ color: "#c1452f" }} />
              Vous
            </label>
            <label className="legend-chip">
              <input type="checkbox" checked={showAi} onChange={(event) => setShowAi(event.target.checked)} />
              <span className="line-dot" style={{ color: "#143c5a" }} />
              IA
            </label>
          </div>
          <MapSurface
            depot={comparison.depot}
            clients={comparison.clients}
            humanSegments={comparison.human_segments}
            aiSegments={comparison.ai_segments}
            incidentSegments={comparison.incidents?.segments ?? []}
            assignedClientIds={comparison.clients.map((client) => client.id)}
            humanStopMetaByClient={comparison.human_stop_meta_by_client ?? {}}
            showHuman={showHuman}
            showAi={showAi}
          />
        </section>

        <section className="grid-4">
          <div className="panel stack">
            <strong>Humain</strong>
            <span className="muted">Temps: {asMinutes(humanTimeS)}</span>
            <span className="muted">Distance: {asDistance(humanDistM)}</span>
            <span className="muted">Segments: {Number(comparison.summary_metrics.human.segment_count ?? 0)}</span>
            <span className="muted">Clients assignes: {Number(comparison.summary_metrics.human.assigned_clients ?? 0)}</span>
          </div>
          <div className="panel stack">
            <strong>IA</strong>
            <span className="muted">Temps: {asMinutes(aiTimeS)}</span>
            <span className="muted">Distance: {asDistance(aiDistM)}</span>
            <span className="muted">Segments: {Number(comparison.summary_metrics.ai.segment_count ?? 0)}</span>
            <span className="muted">Poids livre: {debrief.results.total_weight_kg} kg</span>
            {aiStrategy ? (
              <span className="muted">
                Profil: {aiStrategy.label} · cible {aiStrategy.optimization_target} · vitesse x{aiStrategy.speed_multiplier}
              </span>
            ) : null}
            {aiStrategy?.signature ? <span className="muted">Signature: {aiStrategy.signature}</span> : null}
            {typeof aiStrategy?.difficulty_bonus === "number" ? (
              <span className="muted">Bonus difficulté: +{aiStrategy.difficulty_bonus}</span>
            ) : null}
          </div>
          <div className="panel stack">
            <strong>Benchmark</strong>
            <span className="muted">Gain vs naif: {debrief.benchmark.savings.time_saved_pct}%</span>
            <span className="muted">Temps gagne: {debrief.benchmark.savings.time_saved_min} min</span>
            <span className="muted">CO2 economise: {debrief.benchmark.savings.co2_saved_kg} kg</span>
            <span className="muted">Incidents: {comparison.incidents?.count ?? 0}</span>
          </div>
          <div className="panel stack">
            <strong>Navigation</strong>
            <Link className="secondary-button" href={`/mission/${missionId}`}>
              Retour a la mission
            </Link>
            <Link className="primary-button" href={`/mission/${missionId}/debrief`}>
              Ouvrir le debriefing
            </Link>
          </div>
        </section>

        <section className="grid-2">
          <div className="panel stack">
            <strong>Detail par traineau humain</strong>
            {humanSleighs.length > 0 ? (
              humanSleighs.map((sleigh: HumanSleighSummary) => (
                <span key={`human-${sleigh.sleigh_id}`} className="muted">
                  T#{sleigh.sleigh_id + 1} · {asMinutes(sleigh.time_s)} · {asDistance(sleigh.dist_m)} · {sleigh.stop_count} stop(s)
                </span>
              ))
            ) : (
              <span className="muted">Aucun trajet humain detaillee.</span>
            )}
          </div>
          <div className="panel stack">
            <strong>Detail par traineau IA</strong>
            {aiSleighs.length > 0 ? (
              aiSleighs.map((sleigh: AISleighSummary) => (
                <span key={`ai-${sleigh.sleigh_id}`} className="muted">
                  T#{sleigh.sleigh_id + 1} · {asMinutes(sleigh.time_s)} · {sleigh.stop_count} stop(s) · {sleigh.weight_kg} kg
                </span>
              ))
            ) : (
              <span className="muted">Aucune tournee IA detaillee.</span>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
