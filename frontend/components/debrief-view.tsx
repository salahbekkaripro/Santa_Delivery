"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect } from "react";
import { usePlayer } from "@/components/player-provider";
import { getDebrief, getGraphMetrics, saveLeaderboard } from "@/lib/api";
import { CAMPAIGN_MISSIONS, getStarsForScore, recordCampaignCompletion } from "@/lib/campaign";
import { AISleighSummary, DebriefPayload, HumanSleighSummary, OrOptSleighResult, TwoOptSleighResult } from "@/lib/types";

const DebriefPerformanceChart = dynamic(
  () => import("@/components/debrief-performance-chart").then((mod) => mod.DebriefPerformanceChart),
  {
    ssr: false,
    loading: () => <div className="panel-loading" style={{ height: 260 }} />,
  },
);

function asMinutes(seconds: number) {
  return `${Math.round(seconds / 60)} min`;
}

function asDistance(meters: number) {
  return `${(meters / 1000).toFixed(2)} km`;
}

function StarRow({ stars, max = 3 }: { stars: number; max?: number }) {
  return (
    <div className="stars-row">
      {Array.from({ length: max }, (_, i) => (
        <span key={i} style={{ opacity: i < stars ? 1 : 0.2 }}>⭐</span>
      ))}
    </div>
  );
}

export function DebriefView({ missionId }: { missionId: string }) {
  const { player } = usePlayer();
  const debriefQuery = useQuery({
    queryKey: ["debrief", missionId],
    queryFn: () => getDebrief(missionId)
  });
  const graphMetricsQuery = useQuery({
    queryKey: ["graph-metrics", missionId],
    queryFn: () => getGraphMetrics(missionId),
    retry: false,
  });

  const leaderboardMutation = useMutation({
    mutationFn: () =>
      saveLeaderboard(missionId, {
        player_name: player?.display_name ?? "Père Noël",
        player_id: player?.id,
        callsign: player?.callsign ?? undefined,
        avatar: player?.avatar ?? undefined,
      }),
    onSuccess: () => alert("Score enregistré au Panthéon !")
  });

  const debriefData = debriefQuery.data;
  const campaignLevel = Number(debriefData?.mission.level ?? 0);
  const campaignScore = Number(debriefData?.score.value ?? 0);
  const earnedStars = getStarsForScore(campaignScore);
  const campaignTotalLevels = CAMPAIGN_MISSIONS.length;

  useEffect(() => {
    if (campaignLevel > 0 && debriefData) {
      recordCampaignCompletion(campaignLevel, campaignScore, {
        aiProfile: debriefData.mission.ai_profile,
        secondaryObjectives: debriefData.analysis.secondary_objectives,
      });
    }
  }, [campaignLevel, campaignScore, debriefData]);

  if (debriefQuery.isLoading) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="hero" style={{ height: 160 }}>
            <div className="skeleton-bar h-lg w-60" style={{ marginBottom: 12 }} />
            <div className="skeleton-bar h-sm w-80" />
          </div>
        </div>
      </div>
    );
  }

  if (debriefQuery.error || !debriefQuery.data) {
    return <div className="page-shell error-box">Débriefing indisponible.</div>;
  }

  const debriefPayload: DebriefPayload = debriefQuery.data;
  const analysis = debriefPayload.analysis;
  const humanDeltaS = Number(analysis.human_vs_ai_delta_s ?? 0);
  const aiStrategy = analysis.ai_strategy ?? debriefPayload.results.ai_strategy;
  const aiLearning = aiStrategy?.learning;
  const aiProfileOrigin = aiStrategy?.profile_origin ?? (aiLearning ? "learned" : "preset");
  const scoreBreakdown = debriefPayload.score.breakdown;
  const secondaryObjectives = analysis.secondary_objectives ?? [];
  const humanBeatAI = debriefPayload.score.human_beat_ai;

  const chartData = [
    {
      name: "Temps (min)",
      Humain: Math.round(debriefPayload.human.summary.total_time_s / 60),
      IA: Math.round(debriefPayload.results.total_time_s / 60)
    },
    {
      name: "Distance (km)",
      Humain: Math.round(debriefPayload.human.summary.total_dist_m / 1000),
      IA: Math.round(debriefPayload.benchmark.optimized.total_dist_m / 1000)
    }
  ];

  return (
    <div className="page-shell">
      <div className="page-stack">

        {/* HERO */}
        <section className="hero">
          <div className="score-hero-layout">
            <div>
              <h1>Débriefing</h1>
              <div className="score-big-display" style={{ marginTop: 8 }}>
                <span className="score-big-number">{debriefPayload.score.value}</span>
                <span className="score-big-denom">/100</span>
              </div>
              <span className="score-rank-badge">
                {debriefPayload.score.rank} · {debriefPayload.score.rank_title}
              </span>
              {campaignLevel > 0 && <StarRow stars={earnedStars} />}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {player ? (
                <button
                  className="primary-button"
                  onClick={() => leaderboardMutation.mutate()}
                  disabled={leaderboardMutation.isPending}
                >
                  {leaderboardMutation.isPending ? "Enregistrement…" : `🏆 Enregistrer ${player.display_name}`}
                </button>
              ) : (
                <Link className="primary-button" href={`/login?redirect=${encodeURIComponent(`/mission/${missionId}/debrief`)}`}>
                  Se connecter pour enregistrer
                </Link>
              )}
              <button
                className="secondary-button"
                style={{ background: "rgba(255,255,255,0.18)", border: "1px solid rgba(255,255,255,0.24)", color: "white" }}
                onClick={() => window.print()}
              >
                📜 Imprimer le certificat
              </button>
              <div className="hero-badge" style={{ justifyContent: "center", padding: "8px 16px" }}>
                {humanBeatAI ? "🏆 Vous avez battu l'IA !" : "🤖 L'IA vous précède — revanche ?"}
              </div>
            </div>
          </div>
        </section>

        {/* Certificat caché pour impression */}
        <div className="certificate-only">
          <div className="certificate-header">📜 CERTIFICAT D&apos;EXCELLENCE LOGISTIQUE</div>
          <p>Le Pôle Nord est fier de décerner ce titre à :</p>
          <h2 style={{ fontSize: "48px", margin: "20px 0" }}>ELITE DELIVERY AGENT</h2>
          <div className="certificate-seal">🎅</div>
          <p>Pour avoir accompli la mission dans la zone :</p>
          <h3>{debriefPayload.mission.zone}</h3>
          <div className="certificate-stats">
            <div><strong>Score Final</strong><div style={{ fontSize: "32px" }}>{debriefPayload.score.value}/100</div></div>
            <div><strong>Rang</strong><div style={{ fontSize: "32px" }}>{debriefPayload.score.rank}</div></div>
            <div><strong>CO₂ Économisé</strong><div>{debriefPayload.benchmark.savings.co2_saved_kg} kg</div></div>
            <div><strong>Gain de temps</strong><div>{debriefPayload.benchmark.savings.time_saved_pct}%</div></div>
          </div>
          <p style={{ marginTop: "60px", fontStyle: "italic" }}>
            &quot;Par les pouvoirs conférés par Saint Nicolas, l&apos;optimisation est désormais votre seconde nature.&quot;
          </p>
          <div style={{ marginTop: "40px", borderTop: "1px solid #000", width: "200px", margin: "40px auto 0" }}>
            Signature de Santa
          </div>
        </div>

        {/* GRAPHIQUE + MÉTRIQUES CLÉS */}
        <section className="grid-2">
          <div className="chart-container">
            <strong>Comparaison de performance</strong>
            <DebriefPerformanceChart data={chartData} />
          </div>
          <div className="grid-2" style={{ gap: "14px", alignContent: "start" }}>
            <div className="metric-card is-good">
              <div className="metric-label">Gain vs Naïf</div>
              <div className="metric-value">{debriefPayload.benchmark.savings.time_saved_pct}%</div>
            </div>
            <div className="metric-card is-good">
              <div className="metric-label">CO₂ économisé</div>
              <div className="metric-value">{debriefPayload.benchmark.savings.co2_saved_kg} kg</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Budget restant</div>
              <div className="metric-value">{debriefPayload.benchmark.budget?.remaining ?? 0} €</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Clients livrés</div>
              <div className="metric-value">{debriefPayload.human.assigned_clients.length}</div>
            </div>
            {scoreBreakdown && (
              <>
                <div className="metric-card is-accent">
                  <div className="metric-label">Bonus profil IA</div>
                  <div className="metric-value">+{scoreBreakdown.ai_profile_bonus}</div>
                </div>
                <div className={`metric-card ${humanBeatAI ? "is-good" : ""}`}>
                  <div className="metric-label">Bonus duel</div>
                  <div className="metric-value">+{scoreBreakdown.human_bonus}</div>
                </div>
              </>
            )}
          </div>
        </section>

        {/* RÉSUMÉ + COMPARAISON */}
        <section className="grid-3">
          <div className="panel stack">
            <strong>🤖 Résumé IA</strong>
            <span className="muted">
              Origine : {aiProfileOrigin === "learned" ? "Modèle apprenant" : "Preset mission"}
            </span>
            <span className="muted">Temps total : {asMinutes(debriefPayload.results.total_time_s)}</span>
            <span className="muted">Poids livré : {debriefPayload.results.total_weight_kg} kg</span>
            <span className="muted">Points non servis : {analysis.dropped_points.length}</span>
            {aiStrategy && (
              <span className="muted">
                Profil : {aiStrategy.label} · {aiStrategy.description}
              </span>
            )}
            {aiLearning && (
              <>
                <span className="muted">Confiance modèle : {(aiLearning.confidence * 100).toFixed(0)}%</span>
                <span className="muted">Contexte : {aiLearning.context_key}</span>
              </>
            )}
          </div>

          <div className="panel stack">
            <strong>⚖️ Comparaison</strong>
            <span className="muted">Humain : {asMinutes(debriefPayload.human.summary.total_time_s)}</span>
            <span className="muted">IA : {asMinutes(debriefPayload.results.total_time_s)}</span>
            <span className="muted">
              Écart : {humanDeltaS > 0 ? `+${asMinutes(humanDeltaS)}` : humanDeltaS < 0 ? `-${asMinutes(Math.abs(humanDeltaS))}` : "Égalité"}
            </span>
            <span className="muted">Gain vs naïf : {asMinutes(analysis.naive_vs_ai_delta_s)}</span>
            {scoreBreakdown && (
              <span className="muted" style={{ fontSize: "0.8rem" }}>
                Score : {scoreBreakdown.base_score} (base) + {scoreBreakdown.ai_profile_bonus} (IA) + {scoreBreakdown.incident_bonus} (incidents) + {scoreBreakdown.human_bonus} (duel) + {scoreBreakdown.weather_bonus ?? 0} (météo)
              </span>
            )}
            {campaignLevel > 0 && (
              <span className="muted">Campagne : mission {campaignLevel} · {earnedStars} ⭐</span>
            )}
            {aiLearning && (
              <span className="muted" style={{ fontSize: "0.8rem" }}>
                Top profils proposés : {aiLearning.top_candidates.map((candidate) => candidate.label).join(" · ")}
              </span>
            )}
          </div>

          <div className="panel stack">
            <strong>Navigation</strong>
            {campaignLevel > 0 && (
              <Link className="secondary-button" href="/campaign">← Retour campagne</Link>
            )}
            {campaignLevel >= campaignTotalLevels && (
              <Link className="secondary-button" href="/campaign/finale">🎉 Voir la finale</Link>
            )}
            <Link className="secondary-button" href={`/mission/${missionId}/results`}>
              Retour aux résultats
            </Link>
            <Link className="primary-button" href={`/mission/${missionId}`}>
              ← Revenir à la mission
            </Link>
          </div>
        </section>

        {/* TRAÎNEAUX */}
        <section className="grid-2">
          <div className="panel stack">
            <strong>Traîneaux humain</strong>
            {(debriefPayload.human.sleighs ?? []).filter((s: HumanSleighSummary) => s.stop_count > 0).length > 0 ? (
              (debriefPayload.human.sleighs ?? []).filter((s: HumanSleighSummary) => s.stop_count > 0).map((sleigh: HumanSleighSummary) => (
                <div key={`human-${sleigh.sleigh_id}`} className="sleigh-row">
                  <span className="sleigh-row-id">#{sleigh.sleigh_id + 1}</span>
                  <div className="sleigh-row-stats">
                    <span>{sleigh.stop_count} stops</span>
                    <span>{asMinutes(sleigh.time_s)}</span>
                    <span>{asDistance(sleigh.dist_m)}</span>
                    {sleigh.return_arrival_clock && <span>retour {sleigh.return_arrival_clock}</span>}
                  </div>
                </div>
              ))
            ) : (
              <span className="muted">Pas de trace humaine détaillée.</span>
            )}
          </div>

          <div className="panel stack">
            <strong>Traîneaux IA</strong>
            {analysis.ai_sleighs?.length > 0 ? (
              analysis.ai_sleighs.map((sleigh: AISleighSummary) => (
                <div key={`ai-${sleigh.sleigh_id}`} className="sleigh-row">
                  <span className="sleigh-row-id" style={{ background: "var(--accent)" }}>#{sleigh.sleigh_id + 1}</span>
                  <div className="sleigh-row-stats">
                    <span>{sleigh.stop_count} stops</span>
                    <span>{asMinutes(sleigh.time_s)}</span>
                    <span>{sleigh.weight_kg} kg</span>
                  </div>
                </div>
              ))
            ) : (
              <span className="muted">Pas de tournée IA détaillée.</span>
            )}
          </div>
        </section>

        {/* RECOMMANDATIONS */}
        <section className="panel stack">
          <strong>💡 Recommandations</strong>
          <div className="recommendation-list">
            {analysis.recommendations.map((rec: string) => (
              <div key={rec} className="recommendation-item">
                <span className="recommendation-icon">→</span>
                <span>{rec}</span>
              </div>
            ))}
          </div>
        </section>

        {/* OBJECTIFS SECONDAIRES */}
        {secondaryObjectives.length > 0 && (
          <section className="panel stack">
            <strong>🎯 Objectifs secondaires</strong>
            <div className="objective-results">
              {secondaryObjectives.map((obj) => (
                <div key={`${obj.code}-${obj.label}`} className={`objective-result ${obj.completed ? "is-complete" : "is-pending"}`}>
                  <div>
                    <strong>{obj.completed ? "✓ Validé" : "✗ Raté"}</strong>
                    <span className="muted">{obj.label}</span>
                  </div>
                  <span className="muted">{obj.progress_label}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 2-OPT */}
        {analysis.two_opt && (
          <section className="panel stack">
            <strong>🔁 Optimisation 2-opt (solution humaine)</strong>
            <span className="muted">
              Gain total : {asMinutes(analysis.two_opt.total_improvement_s)} ({analysis.two_opt.total_improvement_pct}%)
              — humain {asMinutes(analysis.two_opt.total_human_time_s)} → optimisé {asMinutes(analysis.two_opt.total_two_opt_time_s)}
            </span>
            <div className="sleigh-row" style={{ fontWeight: 600, borderBottom: "1px solid var(--border)", paddingBottom: 6 }}>
              <span style={{ flex: 1 }}>Traîneau</span>
              <span style={{ flex: 1 }}>Humain</span>
              <span style={{ flex: 1 }}>2-opt</span>
              <span style={{ flex: 1 }}>Gain</span>
            </div>
            {Object.entries(analysis.two_opt.sleighs).filter(([, s]) => (s as TwoOptSleighResult).human_time_s > 0).map(([sid, s]: [string, TwoOptSleighResult]) => (
              <div key={sid} className="sleigh-row">
                <span className="sleigh-row-id">#{Number(sid) + 1}</span>
                <div className="sleigh-row-stats">
                  <span>{asMinutes(s.human_time_s)}</span>
                  <span>{asMinutes(s.two_opt_time_s)}</span>
                  <span className={s.improvement_pct > 0 ? "is-good" : ""}>
                    {s.improvement_pct > 0 ? `-${s.improvement_pct}%` : "—"}
                  </span>
                </div>
              </div>
            ))}
          </section>
        )}

        {/* OR-OPT */}
        {analysis.or_opt && (
          <section className="panel stack">
            <strong>🔀 Or-opt inter-routes (relocalisation)</strong>
            <span className="muted">
              Gain total : {asMinutes(analysis.or_opt.total_improvement_s)} ({analysis.or_opt.total_improvement_pct}%)
              — humain {asMinutes(analysis.or_opt.total_human_time_s)} → optimisé {asMinutes(analysis.or_opt.total_or_opt_time_s)}
            </span>
            <div className="sleigh-row" style={{ fontWeight: 600, borderBottom: "1px solid var(--border)", paddingBottom: 6 }}>
              <span style={{ flex: 1 }}>Traîneau</span>
              <span style={{ flex: 1 }}>Humain</span>
              <span style={{ flex: 1 }}>Or-opt</span>
              <span style={{ flex: 1 }}>Gain</span>
            </div>
            {Object.entries(analysis.or_opt.sleighs).filter(([, s]) => (s as OrOptSleighResult).human_time_s > 0).map(([sid, s]: [string, OrOptSleighResult]) => (
              <div key={sid} className="sleigh-row">
                <span className="sleigh-row-id">#{Number(sid) + 1}</span>
                <div className="sleigh-row-stats">
                  <span>{asMinutes(s.human_time_s)}</span>
                  <span>{asMinutes(s.or_opt_time_s)}</span>
                  <span className={s.improvement_pct > 0 ? "is-good" : ""}>
                    {s.improvement_pct > 0 ? `-${s.improvement_pct}%` : "—"}
                  </span>
                </div>
              </div>
            ))}
          </section>
        )}

        {/* NEAREST NEIGHBOR */}
        {analysis.nearest_neighbor && (
          <section className="panel stack">
            <strong>📍 Baseline Nearest Neighbor (greedy mono-véhicule)</strong>
            <span className="muted">
              Tournée NN : {asMinutes(analysis.nearest_neighbor.total_time_s)} · {analysis.nearest_neighbor.steps_count} étapes
            </span>
            <div className="sleigh-row" style={{ fontWeight: 600, borderBottom: "1px solid var(--border)", paddingBottom: 6 }}>
              <span style={{ flex: "0 0 2rem" }}>#</span>
              <span style={{ flex: 1 }}>De → Vers</span>
              <span style={{ flex: 1 }}>Coût</span>
              <span style={{ flex: 1 }}>Cumulé</span>
            </div>
            {analysis.nearest_neighbor.steps.slice(0, 8).map((step) => (
              <div key={step.step} className="sleigh-row">
                <span className="sleigh-row-id" style={{ background: "var(--accent)" }}>{step.step}</span>
                <div className="sleigh-row-stats">
                  <span>{step.from_node} → {step.to_node}</span>
                  <span>{asMinutes(step.cost_s)}</span>
                  <span>{asMinutes(step.cumulative_s)}</span>
                </div>
              </div>
            ))}
            {analysis.nearest_neighbor.steps.length > 8 && (
              <span className="muted" style={{ fontSize: "0.8rem" }}>… et {analysis.nearest_neighbor.steps.length - 8} étapes supplémentaires</span>
            )}
          </section>
        )}

        {/* GAP D'OPTIMALITÉ */}
        {analysis.optimality_gap && (
          <section className="panel stack">
            <strong>📐 Gap d&apos;optimalité (borne inférieure)</strong>
            <div className="grid-2" style={{ gap: 10 }}>
              <div className="metric-card">
                <div className="metric-label">Borne inférieure</div>
                <div className="metric-value">{asMinutes(analysis.optimality_gap.lower_bound_s)}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Votre solution</div>
                <div className="metric-value">{asMinutes(analysis.optimality_gap.solution_cost_s)}</div>
              </div>
            </div>
            <span className="muted">
              Gap d&apos;optimalité : {analysis.optimality_gap.gap_pct !== null ? `${analysis.optimality_gap.gap_pct}%` : "N/A"}
              {" "}· Interprétation : <strong>{analysis.optimality_gap.interpretation}</strong>
            </span>
          </section>
        )}

        {/* MÉTRIQUES GRAPHE */}
        {graphMetricsQuery.data && (
          <section className="panel stack">
            <strong>🗺️ Métriques du graphe routier</strong>
            <div className="grid-2" style={{ gap: 10 }}>
              <div className="metric-card">
                <div className="metric-label">Nœuds</div>
                <div className="metric-value">{graphMetricsQuery.data.num_nodes.toLocaleString()}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Arcs</div>
                <div className="metric-value">{graphMetricsQuery.data.num_edges.toLocaleString()}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Degré moyen</div>
                <div className="metric-value">{graphMetricsQuery.data.avg_degree}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Clustering moyen</div>
                <div className="metric-value">{graphMetricsQuery.data.avg_clustering}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Plus grande CFC</div>
                <div className="metric-value">{graphMetricsQuery.data.largest_scc_pct}%</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Densité</div>
                <div className="metric-value">{graphMetricsQuery.data.density}</div>
              </div>
            </div>
            <span className="muted" style={{ fontSize: "0.8rem" }}>
              Top carrefours (betweenness) :{" "}
              {graphMetricsQuery.data.top_betweenness_nodes.map((n) => `#${n.node} (${n.score})`).join(" · ")}
            </span>
          </section>
        )}

      </div>
    </div>
  );
}
