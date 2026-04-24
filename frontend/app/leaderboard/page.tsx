"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getLeaderboard, getVersusLeaderboard, getVersusPlayerStats } from "@/lib/api";
import { LeaderboardEntry, VersusLeaderboardEntry, VersusPlayerStatsEntry } from "@/lib/types";
import { ruleLabel } from "@/lib/versus";

const medals = ["🥇", "🥈", "🥉"];
const podiumClass = ["rank-1", "rank-2", "rank-3"];

function formatAverageTime(seconds?: number | null) {
  if (seconds == null || Number.isNaN(seconds)) {
    return "—";
  }
  if (seconds >= 60) {
    return `${(seconds / 60).toFixed(1)} min`;
  }
  return `${Math.round(seconds)} s`;
}

export default function LeaderboardPage() {
  const [mode, setMode] = useState<"solo" | "versus">("solo");

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const queryMode = new URLSearchParams(window.location.search).get("mode");
    setMode(queryMode === "versus" ? "versus" : "solo");
  }, []);

  const soloLeaderboardQuery = useQuery({
    queryKey: ["leaderboard", "solo"],
    queryFn: () => getLeaderboard(),
    enabled: mode === "solo",
  });

  const versusLeaderboardQuery = useQuery({
    queryKey: ["leaderboard", "versus"],
    queryFn: () => getVersusLeaderboard(),
    enabled: mode === "versus",
  });

  const versusStatsQuery = useQuery({
    queryKey: ["leaderboard", "versus", "player-stats"],
    queryFn: () => getVersusPlayerStats(20, 1000),
    enabled: mode === "versus",
  });

  if (soloLeaderboardQuery.isLoading || versusLeaderboardQuery.isLoading || (mode === "versus" && versusStatsQuery.isLoading)) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="hero" style={{ height: 140 }}>
            <div className="skeleton-bar h-lg w-60" style={{ marginBottom: 12 }} />
            <div className="skeleton-bar h-sm w-80" />
          </div>
        </div>
      </div>
    );
  }

  const soloEntries = soloLeaderboardQuery.data?.entries ?? [];
  const versusEntries = versusLeaderboardQuery.data?.entries ?? [];
  const versusPlayerStats = versusStatsQuery.data?.entries ?? [];
  const topScore = mode === "versus" ? Number(versusEntries[0]?.winner_score ?? 0) : Number(soloEntries[0]?.score ?? 0);
  const avgScore =
    (mode === "versus" ? versusEntries.length : soloEntries.length) > 0
      ? (
          (mode === "versus" ? versusEntries : soloEntries).reduce((sum, entry) => {
            if (mode === "versus") {
              return sum + Number((entry as VersusLeaderboardEntry).winner_score ?? 0);
            }
            return sum + Number((entry as LeaderboardEntry).score ?? 0);
          }, 0) / (mode === "versus" ? versusEntries.length : soloEntries.length)
        )
      : 0;
  const distinctZones = mode === "versus"
    ? new Set(versusEntries.map((entry) => entry.map_label ?? entry.mission_summary?.template_label ?? entry.template_id)).size
    : new Set(soloEntries.map((entry) => entry.zone)).size;

  if (mode === "versus") {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="hero">
            <div className="lb-hero-head">
              <div>
                <h1>⚔️ Classement Versus</h1>
                <div className="hero-badges lb-hero-badges">
                  <span className="hero-badge">Duels PVP en direct</span>
                  <span className="hero-badge">{versusEntries.length} duel{versusEntries.length !== 1 ? "s" : ""} enregistré{versusEntries.length !== 1 ? "s" : ""}</span>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Link className="secondary-button lb-back-link" href="/leaderboard">
                  Solo
                </Link>
                <Link className="secondary-button lb-back-link" href="/">
                  ← Accueil
                </Link>
              </div>
            </div>
          </section>

          {versusEntries.length > 0 && (
            <section className="lb-summary-grid">
              <div className="metric-card">
                <div className="metric-label">Meilleur score gagnant</div>
                <div className="metric-value">{topScore.toFixed(1)}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Score moyen gagnant</div>
                <div className="metric-value">{avgScore.toFixed(1)}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Cartes disputées</div>
                <div className="metric-value">{distinctZones}</div>
              </div>
            </section>
          )}

          <section className="panel stack">
            <strong>Historique par joueur</strong>
            {versusPlayerStats.length === 0 ? (
              <span className="muted">Aucune statistique joueur disponible pour le moment.</span>
            ) : (
              <div className="lb-list">
                {versusPlayerStats.map((entry: VersusPlayerStatsEntry, index: number) => (
                  <div key={`${entry.player_id}-${index}`} className="lb-row">
                    <span className="lb-rank">#{index + 1}</span>
                    <span className="lb-row-avatar">{entry.avatar ?? "🎅"}</span>
                    <div className="lb-row-meta">
                      <div className="lb-row-name">{entry.display_name ?? entry.player_id}</div>
                      <div className="lb-zone">
                        Winrate {entry.winrate_pct.toFixed(1)}% · {entry.wins}V-{entry.losses}D · {entry.matches_played} match{entry.matches_played !== 1 ? "s" : ""}
                      </div>
                      <div className="lb-callsign">
                        Règle favorite: {ruleLabel(entry.favorite_rule)} · Temps moyen: {formatAverageTime(entry.average_time_s)}
                      </div>
                    </div>
                    <span className="lb-score">{entry.winrate_pct.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="panel stack">
            <strong>Historique des victoires</strong>
            {versusEntries.length === 0 ? (
              <span className="muted">Aucun duel terminé pour le moment.</span>
            ) : (
              <div className="lb-list">
                {versusEntries.map((entry, index) => (
                  <div key={`${entry.match_id}-${index}`} className="lb-row">
                    <span className="lb-rank">#{index + 1}</span>
                    <span className="lb-row-avatar">{entry.winner_avatar ?? "🎅"}</span>
                    <div className="lb-row-meta">
                      <div className="lb-row-name">{entry.winner_display_name ?? entry.winner_player_id}</div>
                      <div className="lb-zone">
                        {(entry.map_label ?? entry.mission_summary?.template_label ?? entry.template_id)} · {ruleLabel(entry.winner_rule)} · {new Date(entry.created_at).toLocaleDateString("fr-FR")}
                      </div>
                      <div className="lb-callsign">vs {entry.loser_display_name ?? entry.loser_player_id ?? "—"}</div>
                    </div>
                    <span className="lb-score">{Number(entry.winner_score ?? 0).toFixed(1)}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    );
  }

  const podium = soloEntries.slice(0, 3);
  const rest = soloEntries.slice(3);
  const soloTopScore = Number(soloEntries[0]?.score ?? 0);
  const soloAvgScore = soloEntries.length > 0
    ? soloEntries.reduce((sum, entry) => sum + Number(entry.score ?? 0), 0) / soloEntries.length
    : 0;
  const soloDistinctZones = new Set(soloEntries.map((entry) => entry.zone)).size;

  return (
    <div className="page-shell">
      <div className="page-stack">

        {/* HERO */}
        <section className="hero">
          <div className="lb-hero-head">
            <div>
                <h1>🏆 Le Panthéon Solo</h1>
              <div className="hero-badges lb-hero-badges">
                <span className="hero-badge">❄️ Meilleurs agents de livraison</span>
                <span className="hero-badge">{soloEntries.length} score{soloEntries.length !== 1 ? "s" : ""} enregistré{soloEntries.length !== 1 ? "s" : ""}</span>
              </div>
            </div>
            <Link className="secondary-button lb-back-link" href="/">
              ← Retour à l&apos;accueil
            </Link>
            <Link className="secondary-button lb-back-link" href="/leaderboard?mode=versus">
              Voir le versus
            </Link>
          </div>
        </section>

        {soloEntries.length > 0 && (
          <section className="lb-summary-grid">
            <div className="metric-card">
              <div className="metric-label">Meilleur score</div>
              <div className="metric-value">{soloTopScore}/100</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Score moyen</div>
              <div className="metric-value">{soloAvgScore.toFixed(1)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Zones disputées</div>
              <div className="metric-value">{soloDistinctZones}</div>
            </div>
          </section>
        )}

        {/* PODIUM top 3 */}
        {podium.length > 0 && (
          <section>
            <div className="lb-podium">
              {/* 2e place à gauche */}
              {podium[1] ? (
                <div className={`lb-podium-card ${podiumClass[1]}`}>
                  <span className="lb-medal">{medals[1]}</span>
                  <span className="lb-podium-avatar">{podium[1].avatar ?? "🎅"}</span>
                  <span className="lb-podium-name">{podium[1].player_name}</span>
                  {podium[1].callsign && <span className="lb-callsign">{podium[1].callsign}</span>}
                  <span className="lb-podium-score">{podium[1].score}</span>
                  <span className="lb-podium-zone">{podium[1].zone}</span>
                </div>
              ) : <div />}

              {/* 1ère place au centre */}
              <div className={`lb-podium-card ${podiumClass[0]}`}>
                <span className="lb-medal">{medals[0]}</span>
                <span className="lb-podium-avatar">{podium[0].avatar ?? "🎅"}</span>
                <span className="lb-podium-name">{podium[0].player_name}</span>
                {podium[0].callsign && <span className="lb-callsign">{podium[0].callsign}</span>}
                <span className="lb-podium-score">{podium[0].score}</span>
                <span className="lb-podium-zone">{podium[0].zone}</span>
              </div>

              {/* 3e place à droite */}
              {podium[2] ? (
                <div className={`lb-podium-card ${podiumClass[2]}`}>
                  <span className="lb-medal">{medals[2]}</span>
                  <span className="lb-podium-avatar">{podium[2].avatar ?? "🎅"}</span>
                  <span className="lb-podium-name">{podium[2].player_name}</span>
                  {podium[2].callsign && <span className="lb-callsign">{podium[2].callsign}</span>}
                  <span className="lb-podium-score">{podium[2].score}</span>
                  <span className="lb-podium-zone">{podium[2].zone}</span>
                </div>
              ) : <div />}
            </div>
          </section>
        )}

        {/* LISTE depuis la 4e place */}
        {rest.length > 0 && (
          <section className="panel stack">
            <strong>Classement général</strong>
            <div className="lb-list">
              {rest.map((entry: LeaderboardEntry, i: number) => (
                <div key={`${entry.mission_id}-${i}`} className="lb-row">
                  <span className="lb-rank">#{i + 4}</span>
                  <span className="lb-row-avatar">{entry.avatar ?? "🎅"}</span>
                  <div className="lb-row-meta">
                    <div className="lb-row-name">{entry.player_name}</div>
                    {entry.callsign && <div className="lb-callsign">{entry.callsign}</div>}
                    <div className="lb-zone">{entry.zone} · {new Date(entry.created_at).toLocaleDateString("fr-FR")}</div>
                  </div>
                  <span className="lb-score">{entry.score}/100</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {soloEntries.length === 0 && (
          <section className="panel lb-empty">
            <div className="lb-empty-icon">❄️</div>
            <strong>Aucun score enregistré pour le moment</strong>
            <p className="muted">Termine une mission et entre au Panthéon pour être le premier !</p>
            <Link className="primary-button lb-empty-cta" href="/campaign">
              Commencer une mission
            </Link>
          </section>
        )}

      </div>
    </div>
  );
}
