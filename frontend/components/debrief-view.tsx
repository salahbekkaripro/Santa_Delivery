"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect } from "react";
import { usePlayer } from "@/components/player-provider";
import { getDebrief, saveLeaderboard } from "@/lib/api";
import { CAMPAIGN_MISSIONS, getStarsForScore, recordCampaignCompletion } from "@/lib/campaign";
import { AISleighSummary, DebriefPayload, HumanSleighSummary } from "@/lib/types";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function asMinutes(seconds: number) {
  return `${Math.round(seconds / 60)} min`;
}

function asDistance(meters: number) {
  return `${(meters / 1000).toFixed(2)} km`;
}

export function DebriefView({ missionId }: { missionId: string }) {
  const { player } = usePlayer();
  const debriefQuery = useQuery({
    queryKey: ["debrief", missionId],
    queryFn: () => getDebrief(missionId)
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
    return <div className="page-shell">Chargement du debriefing...</div>;
  }

  if (debriefQuery.error || !debriefQuery.data) {
    return <div className="page-shell error-box">Debriefing indisponible.</div>;
  }

  const debriefPayload: DebriefPayload = debriefQuery.data;
  const analysis = debriefPayload.analysis;
  const humanDeltaS = Number(analysis.human_vs_ai_delta_s ?? 0);
  const aiStrategy = analysis.ai_strategy ?? debriefPayload.results.ai_strategy;
  const scoreBreakdown = debriefPayload.score.breakdown;
  const secondaryObjectives = analysis.secondary_objectives ?? [];

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
        <section className="hero">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h1>Debriefing mission</h1>
              <p>
                Rang {debriefPayload.score.rank} · {debriefPayload.score.rank_title} · score {debriefPayload.score.value}/100
              </p>
            </div>
            {player ? (
              <button
                className="primary-button"
                onClick={() => leaderboardMutation.mutate()}
                disabled={leaderboardMutation.isPending}
              >
                {leaderboardMutation.isPending ? "Enregistrement..." : `Enregistrer ${player.display_name}`}
              </button>
            ) : (
              <Link className="primary-button" href={`/login?redirect=${encodeURIComponent(`/mission/${missionId}/debrief`)}`}>
                Se connecter pour enregistrer
              </Link>
            )}
            <button 
              className="secondary-button" 
              style={{ background: "#fff", border: "1px solid var(--border)" }}
              onClick={() => window.print()}
            >
              📜 Imprimer mon Certificat
            </button>
          </div>
        </section>

        {/* --- Hidden Certificate for Print --- */}
        <div className="certificate-only">
          <div className="certificate-header">📜 CERTIFICAT D&apos;EXCELLENCE LOGISTIQUE</div>
          <p>Le Pôle Nord est fier de décerner ce titre à :</p>
          <h2 style={{ fontSize: "48px", margin: "20px 0" }}>ELITE DELIVERY AGENT</h2>
          <div className="certificate-seal">🎅</div>
          <p>Pour avoir accompli la mission dans la zone :</p>
          <h3>{debriefPayload.mission.zone}</h3>
          
          <div className="certificate-stats">
            <div>
              <strong>Score Final</strong>
              <div style={{ fontSize: "32px" }}>{debriefPayload.score.value}/100</div>
            </div>
            <div>
              <strong>Rang</strong>
              <div style={{ fontSize: "32px" }}>{debriefPayload.score.rank}</div>
            </div>
            <div>
              <strong>CO2 Économisé</strong>
              <div>{debriefPayload.benchmark.savings.co2_saved_kg} kg</div>
            </div>
            <div>
              <strong>Gain de temps</strong>
              <div>{debriefPayload.benchmark.savings.time_saved_pct}%</div>
            </div>
          </div>
          
          <p style={{ marginTop: "60px", fontStyle: "italic" }}>
            &quot;Par les pouvoirs conférés par Saint Nicolas, l&apos;optimisation est désormais votre seconde nature.&quot;
          </p>
          <div style={{ marginTop: "40px", borderTop: "1px solid #000", width: "200px", margin: "40px auto 0" }}>
            Signature de Santa
          </div>
        </div>

        <section className="grid-2">
          <div className="chart-container">
            <strong>Comparaison de performance</strong>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="Humain" fill="#c1452f" radius={[4, 4, 0, 0]} />
                <Bar dataKey="IA" fill="#17324d" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid-2" style={{ gap: "16px" }}>
            <div className="metric-card">
              <div className="metric-label">Gain temps vs Naïf</div>
              <div className="metric-value">{debriefPayload.benchmark.savings.time_saved_pct}%</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">CO2 economise</div>
              <div className="metric-value">{debriefPayload.benchmark.savings.co2_saved_kg} kg</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Budget restant</div>
              <div className="metric-value">{debriefPayload.benchmark.budget?.remaining ?? 0} €</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Clients humains</div>
              <div className="metric-value">{debriefPayload.human.assigned_clients.length}</div>
            </div>
            {scoreBreakdown ? (
              <div className="metric-card">
                <div className="metric-label">Bonus profil IA</div>
                <div className="metric-value">+{scoreBreakdown.ai_profile_bonus}</div>
              </div>
            ) : null}
            {scoreBreakdown ? (
              <div className="metric-card">
                <div className="metric-label">Bonus victoire</div>
                <div className="metric-value">+{scoreBreakdown.human_bonus}</div>
              </div>
            ) : null}
          </div>
        </section>

        <section className="grid-3">
          <div className="panel stack">
            <strong>Resume IA</strong>
            <span className="muted">Temps total: {asMinutes(debriefPayload.results.total_time_s)}</span>
            <span className="muted">Poids livre: {debriefPayload.results.total_weight_kg} kg</span>
            <span className="muted">Points non servis: {analysis.dropped_points.length}</span>
            <span className="muted">Bonus humain: {debriefPayload.score.human_beat_ai ? "oui" : "non"}</span>
            {aiStrategy ? <span className="muted">Profil IA: {aiStrategy.label} · {aiStrategy.description}</span> : null}
          </div>
          <div className="panel stack">
            <strong>Comparaison</strong>
            <span className="muted">Humain: {asMinutes(debriefPayload.human.summary.total_time_s)}</span>
            <span className="muted">IA: {asMinutes(debriefPayload.results.total_time_s)}</span>
            <span className="muted">
              Ecart humain vs IA: {humanDeltaS > 0 ? `+${asMinutes(humanDeltaS)}` : humanDeltaS < 0 ? `-${asMinutes(Math.abs(humanDeltaS))}` : "0 min"}
            </span>
            <span className="muted">Gain vs naif: {asMinutes(analysis.naive_vs_ai_delta_s)}</span>
            {aiStrategy ? (
              <span className="muted">
                Réglage IA: {aiStrategy.optimization_target} · {aiStrategy.num_vehicles} traineau(x) · {aiStrategy.vehicle_capacity} kg
              </span>
            ) : null}
            {scoreBreakdown ? (
              <span className="muted">
                Score: base {scoreBreakdown.base_score} + IA {scoreBreakdown.ai_profile_bonus} + incidents {scoreBreakdown.incident_bonus} + duel {scoreBreakdown.human_bonus}
              </span>
            ) : null}
            {campaignLevel > 0 ? <span className="muted">Campagne: mission {campaignLevel} · {earnedStars} etoile(s)</span> : null}
          </div>
          <div className="panel stack">
            <strong>Navigation</strong>
            {campaignLevel > 0 ? (
              <Link className="secondary-button" href="/campaign">
                Retour a la campagne
              </Link>
            ) : null}
            {campaignLevel >= campaignTotalLevels ? (
              <Link className="secondary-button" href="/campaign/finale">
                Voir la finale de campagne
              </Link>
            ) : null}
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
            {debriefPayload.human.sleighs && debriefPayload.human.sleighs.length > 0 ? (
              debriefPayload.human.sleighs.map((sleigh: HumanSleighSummary) => (
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
            {analysis.ai_sleighs && analysis.ai_sleighs.length > 0 ? (
              analysis.ai_sleighs.map((sleigh: AISleighSummary) => (
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
          {analysis.recommendations.map((recommendation: string) => (
            <span key={recommendation} className="muted">
              {recommendation}
            </span>
          ))}
        </section>

        {secondaryObjectives.length > 0 ? (
          <section className="panel stack">
            <strong>Objectifs secondaires</strong>
            <div className="objective-results">
              {secondaryObjectives.map((objective) => (
                <div key={`${objective.code}-${objective.label}`} className={`objective-result ${objective.completed ? "is-complete" : "is-pending"}`}>
                  <div>
                    <strong>{objective.completed ? "Validé" : "Raté"}</strong>
                    <span className="muted">{objective.label}</span>
                  </div>
                  <span className="muted">{objective.progress_label}</span>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
