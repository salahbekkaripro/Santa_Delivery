"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getLeaderboard } from "@/lib/api";
import { LeaderboardEntry } from "@/lib/types";

export default function LeaderboardPage() {
  const leaderboardQuery = useQuery({
    queryKey: ["leaderboard"],
    queryFn: () => getLeaderboard()
  });

  if (leaderboardQuery.isLoading) {
    return <div className="page-shell">Chargement du Panthéon...</div>;
  }

  const entries = leaderboardQuery.data?.entries ?? [];

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Le Panthéon des Livreurs</h1>
          <p>Les meilleures performances de livraison à travers le monde.</p>
        </section>

        <section className="panel stack">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                <th style={{ padding: "12px" }}>Rang</th>
                <th style={{ padding: "12px" }}>Nom</th>
                <th style={{ padding: "12px" }}>Zone</th>
                <th style={{ padding: "12px" }}>Score</th>
                <th style={{ padding: "12px" }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry: LeaderboardEntry, index: number) => (
                <tr key={`${entry.mission_id}-${index}`} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "12px" }}><strong>{entry.rank}</strong></td>
                  <td style={{ padding: "12px" }}>{entry.player_name}</td>
                  <td style={{ padding: "12px" }}>{entry.zone}</td>
                  <td style={{ padding: "12px" }}>{entry.score}/100</td>
                  <td style={{ padding: "12px" }}>{new Date(entry.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "20px", textAlign: "center" }} className="muted">
                    Aucun score enregistré pour le moment. Soyez le premier !
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <Link href="/" className="secondary-button" style={{ textAlign: "center" }}>
            Retour à l&apos;accueil
          </Link>
        </section>
      </div>
    </div>
  );
}
