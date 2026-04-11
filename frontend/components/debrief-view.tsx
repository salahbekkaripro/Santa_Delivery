"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getDebrief, saveLeaderboard } from "@/lib/api";
import { AISleighSummary, DebriefPayload, HumanSleighSummary } from "@/lib/types";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

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

  const leaderboardMutation = useMutation({
    mutationFn: (playerName: string) => saveLeaderboard(missionId, { player_name: playerName }),
    onSuccess: () => alert("Score enregistré au Panthéon !")
  });

  if (debriefQuery.isLoading) {
    return <div className="page-shell">Chargement du debriefing...</div>;
  }

  if (debriefQuery.error || !debriefQuery.data) {
    return <div className="page-shell error-box">Debriefing indisponible.</div>;
  }

  const debrief: DebriefPayload = debriefQuery.data;
  const analysis = debrief.analysis;
  const humanDeltaS = Number(analysis.human_vs_ai_delta_s ?? 0);

  const chartData = [
    {
      name: "Temps (min)",
      Humain: Math.round(debrief.human.summary.total_time_s / 60),
      IA: Math.round(debrief.results.total_time_s / 60)
    },
    {
      name: "Distance (km)",
      Humain: Math.round(debrief.human.summary.total_dist_m / 1000),
      IA: Math.round(debrief.benchmark.optimized.total_dist_m / 1000)
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
                Rang {debrief.score.rank} · {debrief.score.rank_title} · score {debrief.score.value}/100
              </p>
            </div>
            <button 
              className="primary-button" 
              onClick={() => {
                const name = prompt("Entrez votre nom pour le classement :", "Père Noël");
                if (name) leaderboardMutation.mutate(name);
              }}
              disabled={leaderboardMutation.isPending}
            >
              {leaderboardMutation.isPending ? "Enregistrement..." : "Enregistrer mon score"}
            </button>
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
          <h3>{debrief.mission.zone}</h3>
          
          <div className="certificate-stats">
            <div>
              <strong>Score Final</strong>
              <div style={{ fontSize: "32px" }}>{debrief.score.value}/100</div>
            </div>
            <div>
              <strong>Rang</strong>
              <div style={{ fontSize: "32px" }}>{debrief.score.rank}</div>
            </div>
            <div>
              <strong>CO2 Économisé</strong>
              <div>{debrief.benchmark.savings.co2_saved_kg} kg</div>
            </div>
            <div>
              <strong>Gain de temps</strong>
              <div>{debrief.benchmark.savings.time_saved_pct}%</div>
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
          </div>
        </section>

        <section className="grid-3">
          <div className="panel stack">
            <strong>Resume IA</strong>
            <span className="muted">Temps total: {asMinutes(debrief.results.total_time_s)}</span>
            <span className="muted">Poids livre: {debrief.results.total_weight_kg} kg</span>
            <span className="muted">Points non servis: {analysis.dropped_points.length}</span>
            <span className="muted">Bonus humain: {debrief.score.human_beat_ai ? "oui" : "non"}</span>
          </div>
          <div className="panel stack">
            <strong>Comparaison</strong>
            <span className="muted">Humain: {asMinutes(debrief.human.summary.total_time_s)}</span>
            <span className="muted">IA: {asMinutes(debrief.results.total_time_s)}</span>
            <span className="muted">
              Ecart humain vs IA: {humanDeltaS > 0 ? `+${asMinutes(humanDeltaS)}` : humanDeltaS < 0 ? `-${asMinutes(Math.abs(humanDeltaS))}` : "0 min"}
            </span>
            <span className="muted">Gain vs naif: {asMinutes(analysis.naive_vs_ai_delta_s)}</span>
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
              debrief.human.sleighs.map((sleigh: HumanSleighSummary) => (
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
      </div>
    </div>
  );
}
