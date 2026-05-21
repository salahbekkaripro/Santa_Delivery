"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { getComparison, getDebrief, getMission } from "@/lib/api";
import { MapSurface } from "@/components/map-surface";
import { AISleighSummary, ComparisonPayload, DebriefPayload, HumanSleighSummary, MissionResponse } from "@/lib/types";

function useCountUp(target: number, duration = 1400) {
  const [value, setValue] = useState(0);
  const rafRef = useRef(0);
  useEffect(() => {
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const t = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(Math.round(eased * target));
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);
  return value;
}

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
  const solverScoreRaw = Number(
    debriefQuery.data?.benchmark?.savings?.score
    ?? debriefQuery.data?.score?.value
    ?? 0
  );
  const animatedScore = useCountUp(solverScoreRaw);

  if (missionQuery.isLoading || comparisonQuery.isLoading || debriefQuery.isLoading) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="hero" style={{ height: 120 }}>
            <div className="skeleton-bar h-lg w-60" style={{ marginBottom: 12 }} />
            <div className="skeleton-bar h-sm w-80" />
          </div>
          <div className="grid-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="metric-card" style={{ height: 90 }}>
                <div className="skeleton-bar h-sm w-60" style={{ marginBottom: 8 }} />
                <div className="skeleton-bar h-lg w-80" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (missionQuery.error || comparisonQuery.error || debriefQuery.error || !missionQuery.data || !comparisonQuery.data || !debriefQuery.data) {
    return <div className="page-shell error-box">Impossible de charger les résultats de mission.</div>;
  }

  const mission: MissionResponse = missionQuery.data;
  const comparison: ComparisonPayload = comparisonQuery.data;
  const debrief: DebriefPayload = debriefQuery.data;
  const humanTimeS = Number(comparison.summary_metrics.human.total_time_s ?? 0);
  const aiTimeS = Number(comparison.summary_metrics.ai.total_time_s ?? debrief.results.total_time_s ?? 0);
  const humanDistM = Number(comparison.summary_metrics.human.total_dist_m ?? 0);
  const aiDistM = Number(comparison.summary_metrics.ai.total_dist_m ?? 0);
  const deltaS = humanTimeS - aiTimeS;
  const humanWon = deltaS <= 0;
  const deltaLabel = deltaS > 0 ? `+${asMinutes(deltaS)} vs IA` : deltaS < 0 ? `${asMinutes(Math.abs(deltaS))} d'avance` : "À égalité";
  const humanSleighs = comparison.summary_metrics.human.sleighs ?? [];
  const aiSleighs = comparison.summary_metrics.ai.sleighs ?? [];
  const aiStrategy = debrief.results.ai_strategy ?? comparison.summary_metrics.ai.strategy;
  const aiLearning = aiStrategy?.learning;
  const aiProfileOrigin = aiStrategy?.profile_origin ?? (aiLearning ? "learned" : "preset");

  return (
    <div className="page-shell">
      <div className="page-stack">

        {/* HERO */}
        <section className="hero">
          <div className="score-hero-layout">
            <div>
              <h1>Résultats</h1>
              <div className="score-big-display" style={{ marginTop: 8 }}>
                <span className="score-big-number score-big-number--reveal">{animatedScore}</span>
                <span className="score-big-denom">/100</span>
              </div>
              <span className="muted" style={{ fontSize: "0.82rem" }}>Score solveur</span>
              <span className="score-rank-badge">
                {debrief.score.rank_title} · {mission.mission.zone}
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div className="hero-badge" style={{ justifyContent: "center", padding: "8px 16px", fontSize: "0.9rem" }}>
                {humanWon ? "🏆 Vous avez battu l'IA !" : "🤖 L'IA vous précède"}
              </div>
              <div className="hero-badge" style={{ justifyContent: "center", padding: "8px 16px", fontSize: "0.88rem" }}>
                {deltaLabel}
              </div>
            </div>
          </div>
        </section>

        {/* METRICS */}
        <section className="grid-4">
          <div className="metric-card is-accent">
            <div className="metric-label">Temps IA</div>
            <div className="metric-value">{asMinutes(debrief.results.total_time_s)}</div>
          </div>
          <div className={`metric-card ${humanWon ? "is-good" : "is-bad"}`}>
            <div className="metric-label">Temps humain</div>
            <div className="metric-value">{asMinutes(humanTimeS)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Distance IA</div>
            <div className="metric-value">{asDistance(aiDistM)}</div>
          </div>
          <div className={`metric-card ${humanWon ? "is-good" : "is-bad"}`}>
            <div className="metric-label">Écart humain vs IA</div>
            <div className="metric-value">{deltaLabel}</div>
          </div>
        </section>

        {/* CARTE */}
        <section className="panel stack">
          <div className="panel-head">
            <strong>Carte de comparaison</strong>
            <div className="legend">
              <label className="legend-chip">
                <input type="checkbox" checked={showHuman} onChange={(e) => setShowHuman(e.target.checked)} />
                <span className="line-dot is-dashed" style={{ color: "#9e2f3f" }} />
                Vous
              </label>
              <label className="legend-chip">
                <input type="checkbox" checked={showAi} onChange={(e) => setShowAi(e.target.checked)} />
                <span className="line-dot" style={{ color: "#143c5a" }} />
                IA
              </label>
            </div>
          </div>
          <MapSurface
            depot={comparison.depot}
            clients={comparison.clients}
            humanSegments={comparison.human_segments}
            aiSegments={comparison.ai_segments}
            incidentSegments={comparison.incidents?.segments ?? []}
            assignedClientIds={comparison.clients.map((c) => c.id)}
            humanStopMetaByClient={comparison.human_stop_meta_by_client ?? {}}
            showHuman={showHuman}
            showAi={showAi}
          />
        </section>

        {/* DÉTAILS */}
        <section className="grid-4">
          <div className="panel stack">
            <div className="panel-head">
              <strong>🧍 Humain</strong>
            </div>
            <span className="muted">Temps : {asMinutes(humanTimeS)}</span>
            <span className="muted">Distance : {asDistance(humanDistM)}</span>
            <span className="muted">Segments : {Number(comparison.summary_metrics.human.segment_count ?? 0)}</span>
            <span className="muted">Clients : {Number(comparison.summary_metrics.human.assigned_clients ?? 0)}</span>
          </div>

          <div className="panel stack">
            <div className="panel-head">
              <strong>🤖 IA</strong>
              {aiStrategy && <span className="tag">{aiStrategy.label}</span>}
            </div>
            <span className="muted">
              Origine : {aiProfileOrigin === "learned" ? "Modèle apprenant" : "Preset mission"}
            </span>
            <span className="muted">Temps : {asMinutes(aiTimeS)}</span>
            <span className="muted">Distance : {asDistance(aiDistM)}</span>
            <span className="muted">Segments : {Number(comparison.summary_metrics.ai.segment_count ?? 0)}</span>
            <span className="muted">Poids livré : {debrief.results.total_weight_kg} kg</span>
            {aiStrategy?.signature && <span className="muted">Signature : {aiStrategy.signature}</span>}
            {typeof aiStrategy?.difficulty_bonus === "number" && (
              <span className="muted">Bonus difficulté : +{aiStrategy.difficulty_bonus}</span>
            )}
            {aiLearning && (
              <>
                <span className="muted">Confiance modèle : {(aiLearning.confidence * 100).toFixed(0)}%</span>
                <span className="muted">Contexte : {aiLearning.context_key}</span>
                <span className="muted">
                  Top candidats : {aiLearning.top_candidates.map((candidate) => candidate.label).join(" · ")}
                </span>
              </>
            )}
          </div>

          <div className="panel stack">
            <strong>📊 Benchmark</strong>
            <span className="muted">Gain vs naïf : {debrief.benchmark.savings.time_saved_pct}%</span>
            <span className="muted">Temps gagné : {debrief.benchmark.savings.time_saved_min} min</span>
            <span className="muted">CO₂ économisé : {debrief.benchmark.savings.co2_saved_kg} kg</span>
            <span className="muted">Incidents : {comparison.incidents?.count ?? 0}</span>
          </div>

          <div className="panel stack">
            <strong>Navigation</strong>
            <Link className="secondary-button" href={`/mission/${missionId}`}>
              ← Retour à la mission
            </Link>
            <Link className="primary-button" href={`/mission/${missionId}/debrief`}>
              Ouvrir le débriefing →
            </Link>
          </div>
        </section>

        {/* TRAÎNEAUX */}
        <section className="grid-2">
          <div className="panel stack">
            <strong>Traîneaux humain</strong>
            {humanSleighs.length > 0 ? (
              humanSleighs.map((sleigh: HumanSleighSummary) => (
                <div key={`human-${sleigh.sleigh_id}`} className="sleigh-row">
                  <span className="sleigh-row-id">#{sleigh.sleigh_id + 1}</span>
                  <div className="sleigh-row-stats">
                    <span>{asMinutes(sleigh.time_s)}</span>
                    <span>{asDistance(sleigh.dist_m)}</span>
                    <span>{sleigh.stop_count} stop(s)</span>
                  </div>
                </div>
              ))
            ) : (
              <span className="muted">Aucun trajet humain détaillé.</span>
            )}
          </div>

          <div className="panel stack">
            <strong>Traîneaux IA</strong>
            {aiSleighs.length > 0 ? (
              aiSleighs.map((sleigh: AISleighSummary) => (
                <div key={`ai-${sleigh.sleigh_id}`} className="sleigh-row">
                  <span className="sleigh-row-id" style={{ background: "var(--accent)" }}>#{sleigh.sleigh_id + 1}</span>
                  <div className="sleigh-row-stats">
                    <span>{asMinutes(sleigh.time_s)}</span>
                    <span>{sleigh.stop_count} stop(s)</span>
                    <span>{sleigh.weight_kg} kg</span>
                  </div>
                </div>
              ))
            ) : (
              <span className="muted">Aucune tournée IA détaillée.</span>
            )}
          </div>
        </section>

      </div>

      {/* CTA contextuel */}
      <div className="results-cta-bar">
        <div className="results-cta-bar-inner">
          <div className="results-cta-outcome">
            <span className="results-cta-icon">{humanWon ? "🏆" : "🤖"}</span>
            <span>{humanWon ? "Vous avez battu l'IA !" : "L'IA vous devance — réessayez ?"}</span>
          </div>
          <div className="results-cta-actions">
            <Link className="secondary-button" href={`/mission/${missionId}`}>
              ↺ Rejouer
            </Link>
            <Link className="primary-button" href={`/mission/${missionId}/debrief`}>
              📊 Débriefing complet →
            </Link>
            <Link className="secondary-button" href="/campaign">
              🗺️ Campagne
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
