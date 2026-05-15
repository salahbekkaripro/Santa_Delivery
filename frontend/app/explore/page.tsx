"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { getBidirectionalAstarSteps, getDijkstraSteps, getGraphMetrics, getMission, getMissions, getNearestNode } from "@/lib/api";
import type { AstarCompareResult, DijkstraResult } from "@/lib/types";

const DijkstraMap = dynamic(() => import("@/components/explore-dijkstra-map"), { ssr: false });
const AstarMap = dynamic(() => import("@/components/explore-astar-map"), { ssr: false });

type Tab = "graph" | "dijkstra" | "astar" | "vrp" | "twoopt" | "oropt" | "nn" | "ils";

const EXPLORE_TABS: Array<{ key: Tab; label: string; icon: string }> = [
  { key: "graph", label: "Graphe OSM", icon: "🗺️" },
  { key: "dijkstra", label: "Dijkstra animé", icon: "🔍" },
  { key: "astar", label: "A* vs Dijkstra", icon: "⭐" },
  { key: "vrp", label: "VRP / OR-Tools", icon: "📦" },
  { key: "twoopt", label: "2-opt", icon: "🔁" },
  { key: "oropt", label: "Or-opt", icon: "🔀" },
  { key: "nn", label: "Nearest Neighbor", icon: "📍" },
  { key: "ils", label: "ILS", icon: "🔥" },
];

const AUTO_DEMO_SEQUENCE: Array<{ key: "story" | Tab; label: string; durationMs: number }> = [
  { key: "story", label: "Intro story", durationMs: 4000 },
  { key: "graph", label: "Graphe OSM", durationMs: 4500 },
  { key: "dijkstra", label: "Dijkstra", durationMs: 4500 },
  { key: "astar", label: "A* bidirectionnel", durationMs: 4500 },
  { key: "vrp", label: "VRP / OR-Tools", durationMs: 3000 },
  { key: "twoopt", label: "2-opt", durationMs: 3000 },
];

// ─────────────────────────────────────────────────────────────────────────────
// GRAPH TAB
// ─────────────────────────────────────────────────────────────────────────────

function GraphTab({ missionId }: { missionId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["graph-metrics", missionId],
    queryFn: () => getGraphMetrics(missionId),
    enabled: Boolean(missionId),
    retry: false,
  });

  if (!missionId) {
    return (
      <>
        <section className="panel stack">
          <strong>Qu&apos;est-ce qu&apos;un graphe OSM ?</strong>
          <p className="muted">
            OpenStreetMap (OSM) modélise le réseau routier comme un <em>graphe orienté pondéré</em>.
            Chaque <strong>nœud</strong> représente une intersection ou un point remarquable, chaque
            <strong> arc</strong> un tronçon de route avec sa longueur et sa vitesse légale.
            La bibliothèque Python <code>osmnx</code> télécharge ce graphe pour une zone géographique
            définie par un rayon autour d&apos;une adresse, puis calcule automatiquement les temps de
            trajet via <code>ox.add_edge_travel_times()</code>.
          </p>
          <div className="grid-2" style={{ gap: 10 }}>
            {[
              { icon: "🔵", label: "Nœud", desc: "Intersection ou point GPS notable" },
              { icon: "➡️", label: "Arc orienté", desc: "Tronçon de route avec longueur + vitesse" },
              { icon: "⏱️", label: "Poids", desc: "Temps de trajet en secondes" },
              { icon: "🌐", label: "Source", desc: "OpenStreetMap via osmnx" },
            ].map(({ icon, label, desc }) => (
              <div key={label} className="metric-card">
                <div style={{ fontSize: "1.4rem" }}>{icon}</div>
                <div style={{ fontWeight: 600 }}>{label}</div>
                <div className="metric-label">{desc}</div>
              </div>
            ))}
          </div>
        </section>
        <section className="panel stack">
          <span className="muted">← Sélectionne une mission pour charger les métriques réelles du graphe.</span>
        </section>
      </>
    );
  }

  if (isLoading) return <div className="panel-loading" style={{ height: 260 }} />;
  if (error || !data) return <section className="panel stack"><span className="muted">Graphe indisponible pour cette mission.</span></section>;

  return (
    <>
      <section className="panel stack">
        <strong>Qu&apos;est-ce qu&apos;un graphe OSM ?</strong>
        <p className="muted">
          OpenStreetMap (OSM) modélise le réseau routier comme un <em>graphe orienté pondéré</em>.
          Chaque <strong>nœud</strong> est une intersection, chaque <strong>arc</strong> un tronçon
          avec sa longueur et sa vitesse légale. <code>osmnx</code> télécharge et enrichit ce graphe
          pour la zone de la mission.
        </p>
      </section>

      <section className="panel stack">
        <strong>Métriques du graphe chargé</strong>
        <div className="grid-2" style={{ gap: 10 }}>
          {[
            { label: "Nœuds (intersections)", value: data.num_nodes.toLocaleString() },
            { label: "Arcs (tronçons orientés)", value: data.num_edges.toLocaleString() },
            { label: "Degré sortant moyen", value: data.avg_degree },
            { label: "Degré maximum", value: data.max_degree },
            { label: "Densité du graphe", value: data.density },
            { label: "Clustering moyen", value: data.avg_clustering },
            { label: "Fortement connexe", value: data.is_strongly_connected ? "Oui ✓" : "Non ✗" },
            { label: "Plus grande CFC", value: `${data.largest_scc_pct}%` },
          ].map(({ label, value }) => (
            <div key={label} className="metric-card">
              <div className="metric-label">{label}</div>
              <div className="metric-value">{value}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel stack">
        <strong>Top 5 carrefours stratégiques — centralité betweenness</strong>
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          La centralité betweenness mesure la proportion des plus courts chemins du graphe qui
          transitent par un nœud. Un score élevé = carrefour incontournable. Approxi­mé par
          échantillonnage (k = 30 pivots) pour rester rapide sur les grands graphes.
        </p>
        {data.top_betweenness_nodes.map((n, i) => (
          <div key={n.node} className="sleigh-row">
            <span className="sleigh-row-id" style={{ background: i === 0 ? "var(--accent)" : undefined }}>
              #{i + 1}
            </span>
            <div className="sleigh-row-stats">
              <span>Nœud {n.node}</span>
              <span className="muted">{n.lat.toFixed(5)}, {n.lon.toFixed(5)}</span>
              <span className="muted">score {n.score}</span>
            </div>
          </div>
        ))}
      </section>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DIJKSTRA TAB
// ─────────────────────────────────────────────────────────────────────────────

function DijkstraTab({ missionId }: { missionId: string }) {
  const [dijkstraResult, setDijkstraResult] = useState<DijkstraResult | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(80);
  const intervalRef = useRef<number | null>(null);

  const missionQuery = useQuery({
    queryKey: ["mission", missionId],
    queryFn: () => getMission(missionId),
    enabled: Boolean(missionId),
  });

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!missionQuery.data) throw new Error("Mission non chargée");
      const { depot, clients } = missionQuery.data;
      if (!clients.length) throw new Error("Aucun client dans cette mission");
      const [fromNode, toNode] = await Promise.all([
        getNearestNode(missionId, depot.lat, depot.lon).then((r) => r.node_id),
        getNearestNode(missionId, clients[0].lat, clients[0].lon).then((r) => r.node_id),
      ]);
      return getDijkstraSteps(missionId, fromNode, toNode);
    },
    onSuccess: (data) => {
      setDijkstraResult(data);
      setCurrentStep(0);
      setPlaying(false);
    },
  });

  useEffect(() => {
    if (!playing || !dijkstraResult) return;
    intervalRef.current = window.setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= dijkstraResult.steps_count - 1) {
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, speed);
    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
    };
  }, [playing, dijkstraResult, speed]);

  const step = dijkstraResult?.steps[currentStep];

  return (
    <>
      <section className="panel stack">
        <strong>Comment fonctionne Dijkstra ?</strong>
        <p className="muted">
          Dijkstra est un algorithme de <em>plus court chemin</em> sur graphe à poids positifs.
          Il maintient un <strong>tas min</strong> (priority queue) : à chaque itération, le
          nœud de coût minimal est extrait et finalisé — son chemin est définitif. Les voisins
          non visités sont mis à jour si un chemin plus court est trouvé.
        </p>
        <pre className="code-block">{`heap = [(0, dépôt)]
tant que heap non vide :
  (d, u) = extraire_min(heap)
  pour chaque voisin v de u :
    si d + w(u,v) < dist[v] :
      dist[v] = d + w(u,v)
      insérer (dist[v], v) dans heap`}</pre>
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          Dans ce projet, A* remplace Dijkstra avec une heuristique haversine admissible
          (distance vol ÷ 13,89 m/s = 50 km/h). A* explore moins de nœuds tout en
          garantissant l&apos;optimalité car l&apos;heuristique ne surestime jamais le coût réel.
        </p>
      </section>

      {!missionId ? (
        <section className="panel stack">
          <span className="muted">← Sélectionne une mission pour lancer la visualisation.</span>
        </section>
      ) : (
        <section className="panel stack">
          <strong>Visualisation live — Dépôt → Client 1</strong>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <button
              className="primary-button"
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || !missionQuery.data}
            >
              {runMutation.isPending ? "Calcul en cours..." : "▶ Lancer Dijkstra"}
            </button>

            {dijkstraResult && (
              <>
                <button
                  className="secondary-button"
                  onClick={() => setPlaying((p) => !p)}
                >
                  {playing ? "⏸ Pause" : "▶ Play"}
                </button>
                <button
                  className="secondary-button"
                  onClick={() => { setCurrentStep(0); setPlaying(false); }}
                >
                  ⏮ Reset
                </button>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem" }}>
                  Vitesse
                  <select
                    value={speed}
                    onChange={(e) => setSpeed(Number(e.target.value))}
                    style={{ padding: "4px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--panel)" }}
                  >
                    <option value={300}>Lente</option>
                    <option value={80}>Normale</option>
                    <option value={20}>Rapide</option>
                    <option value={4}>Turbo</option>
                  </select>
                </label>
              </>
            )}
          </div>

          {runMutation.error && (
            <span className="muted" style={{ color: "var(--accent)" }}>
              {(runMutation.error as Error).message}
            </span>
          )}

          {dijkstraResult && (
            <>
              <input
                type="range"
                min={0}
                max={dijkstraResult.steps_count - 1}
                value={currentStep}
                onChange={(e) => { setCurrentStep(Number(e.target.value)); setPlaying(false); }}
                style={{ width: "100%", accentColor: "var(--accent)" }}
              />

              <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                <span className="muted">
                  Étape <strong>{currentStep + 1}</strong> / {dijkstraResult.steps_count}
                </span>
                {step && (
                  <span className="muted">
                    Nœud finalisé : <strong>{step.node}</strong> · Distance : <strong>{step.dist.toFixed(0)} s</strong>
                    {step.predecessor != null ? ` · prédécesseur ${step.predecessor}` : " · source"}
                  </span>
                )}
                <span className="muted">
                  {dijkstraResult.reached
                    ? `✓ Destination atteinte — coût total ${dijkstraResult.total_cost} s · chemin ${dijkstraResult.path_length} nœuds`
                    : dijkstraResult.truncated
                      ? "⚠ Tronqué (max 400 étapes)"
                      : "En cours…"}
                </span>
              </div>

              <div style={{ display: "flex", gap: 16, fontSize: "0.8rem", flexWrap: "wrap" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#17324d", display: "inline-block" }} />
                  Dépôt (source)
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#9e2f3f", display: "inline-block" }} />
                  Nœud courant
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#aab8c6", display: "inline-block" }} />
                  Finalisés
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#1f7a56", display: "inline-block" }} />
                  Destination / chemin final
                </span>
              </div>

              <DijkstraMap result={dijkstraResult} currentStep={currentStep} />
            </>
          )}
        </section>
      )}
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// A* TAB
// ─────────────────────────────────────────────────────────────────────────────

function AstarTab({ missionId }: { missionId: string }) {
  const [result, setResult] = useState<AstarCompareResult | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(80);
  const intervalRef = useRef<number | null>(null);

  const missionQuery = useQuery({
    queryKey: ["mission", missionId],
    queryFn: () => getMission(missionId),
    enabled: Boolean(missionId),
  });

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!missionQuery.data) throw new Error("Mission non chargée");
      const { depot, clients } = missionQuery.data;
      if (!clients.length) throw new Error("Aucun client dans cette mission");
      const [fromNode, toNode] = await Promise.all([
        getNearestNode(missionId, depot.lat, depot.lon).then((r) => r.node_id),
        getNearestNode(missionId, clients[0].lat, clients[0].lon).then((r) => r.node_id),
      ]);
      return getBidirectionalAstarSteps(missionId, fromNode, toNode);
    },
    onSuccess: (data) => {
      setResult(data);
      setCurrentStep(0);
      setPlaying(false);
    },
  });

  const totalSteps = result
    ? result.steps_forward.length + result.steps_backward.length
    : 0;

  useEffect(() => {
    if (!playing || !result) return;
    intervalRef.current = window.setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= totalSteps - 1) { setPlaying(false); return prev; }
        return prev + 1;
      });
    }, speed);
    return () => { if (intervalRef.current) window.clearInterval(intervalRef.current); };
  }, [playing, result, speed, totalSteps]);

  return (
    <>
      <section className="panel stack">
        <strong>Dijkstra vs A* — Pourquoi A* explore moins de nœuds ?</strong>
        <p className="muted">
          Dijkstra explore tous les nœuds par ordre de coût croissant, sans connaissance de
          la direction. A* ajoute une <em>heuristique h(n)</em> : la distance haversine (vol
          d&apos;oiseau) divisée par 13,89 m/s (50 km/h). Cette heuristique est <strong>admissible</strong> —
          elle ne surestime jamais le coût réel car la distance euclidienne ≤ distance routière.
          A* priorise les nœuds qui semblent proches du but, réduisant drastiquement l&apos;espace exploré.
        </p>
        <div className="grid-2" style={{ gap: 10 }}>
          {[
            { icon: "📐", label: "Dijkstra", desc: "f(n) = g(n) — coût depuis la source uniquement" },
            { icon: "🧭", label: "A*", desc: "f(n) = g(n) + h(n) — coût réel + estimation vers la cible" },
            { icon: "✅", label: "Admissibilité", desc: "h(n) ≤ coût réel → optimalité garantie" },
            { icon: "⚡", label: "Heuristique", desc: "haversine(n, dest) ÷ 13,89 m/s (50 km/h max)" },
          ].map(({ icon, label, desc }) => (
            <div key={label} className="metric-card">
              <div style={{ fontSize: "1.4rem" }}>{icon}</div>
              <div style={{ fontWeight: 600 }}>{label}</div>
              <div className="metric-label">{desc}</div>
            </div>
          ))}
        </div>
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          Version bidirectionnelle : deux frontières se propagent simultanément — l&apos;une depuis
          la source (en bleu), l&apos;autre depuis la destination (en rouge). Quand elles se rencontrent,
          le chemin optimal est reconstruit. Cela réduit encore davantage les nœuds explorés.
        </p>
        <pre className="code-block">{`f(n) = g(n) + h(n)
h(n) = haversine(n, dest) / 13.89   ← admissible car dist_vol ≤ dist_route
Terminaison : min(f_forward_top, f_backward_top) ≥ mu (meilleur chemin connu)`}</pre>
      </section>

      {!missionId ? (
        <section className="panel stack">
          <span className="muted">← Sélectionne une mission pour lancer la comparaison.</span>
        </section>
      ) : (
        <section className="panel stack">
          <strong>Comparaison live — Dépôt → Client 1</strong>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <button
              className="primary-button"
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || !missionQuery.data}
            >
              {runMutation.isPending ? "Calcul en cours..." : "▶ Lancer A* bidirectionnel"}
            </button>
            {result && (
              <>
                <button className="secondary-button" onClick={() => setPlaying((p) => !p)}>
                  {playing ? "⏸ Pause" : "▶ Play"}
                </button>
                <button className="secondary-button" onClick={() => { setCurrentStep(0); setPlaying(false); }}>
                  ⏮ Reset
                </button>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem" }}>
                  Vitesse
                  <select
                    value={speed}
                    onChange={(e) => setSpeed(Number(e.target.value))}
                    style={{ padding: "4px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--panel)" }}
                  >
                    <option value={300}>Lente</option>
                    <option value={80}>Normale</option>
                    <option value={20}>Rapide</option>
                    <option value={4}>Turbo</option>
                  </select>
                </label>
              </>
            )}
          </div>

          {runMutation.error && (
            <span className="muted" style={{ color: "var(--accent)" }}>
              {(runMutation.error as Error).message}
            </span>
          )}

          {result && (
            <>
              {/* Barre de comparaison visuelle */}
              <div className="algo-compare-bar">
                <div className="algo-compare-row">
                  <span className="algo-compare-label">Dijkstra</span>
                  <div className="algo-compare-track">
                    <div
                      className="algo-compare-fill dijkstra"
                      style={{ width: "100%" }}
                    />
                  </div>
                  <span className="algo-compare-count">{result.nodes_explored_unidir} nœuds</span>
                </div>
                <div className="algo-compare-row">
                  <span className="algo-compare-label" style={{ color: "#1a6fb5" }}>A* bidir.</span>
                  <div className="algo-compare-track">
                    <div
                      className="algo-compare-fill astar"
                      style={{ width: `${100 - result.reduction_pct}%` }}
                    />
                  </div>
                  <span className="algo-compare-count" style={{ color: "#1f7a56" }}>
                    {result.nodes_explored_astar_bidir} nœuds
                  </span>
                </div>
              </div>

              {result.reduction_pct > 0 && (
                <p className="muted" style={{ fontSize: "0.9rem" }}>
                  A* a exploré <strong style={{ color: "#1f7a56" }}>{result.reduction_pct}% de nœuds en moins</strong> que Dijkstra
                  — même chemin optimal, même coût ({result.total_cost.toFixed(0)} s), {result.path_length} nœuds dans le chemin.
                </p>
              )}

              {/* Barre de progression */}
              <input
                type="range"
                min={0}
                max={Math.max(0, totalSteps - 1)}
                value={currentStep}
                onChange={(e) => { setCurrentStep(Number(e.target.value)); setPlaying(false); }}
                style={{ width: "100%", accentColor: "var(--accent)" }}
              />
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                Étape <strong>{currentStep + 1}</strong> / {totalSteps}
                {result.reached && currentStep === totalSteps - 1
                  ? ` · chemin trouvé en ${result.total_cost.toFixed(0)} s`
                  : ""}
              </span>

              {/* Légende */}
              <div style={{ display: "flex", gap: 16, fontSize: "0.8rem", flexWrap: "wrap" }}>
                {[
                  { color: "#17324d", label: "Source (dépôt)" },
                  { color: "#5b9bd5", label: "Frontière avant (A*)" },
                  { color: "#c47a85", label: "Frontière arrière (A*)" },
                  { color: "#d4a017", label: "Point de rencontre" },
                  { color: "#1f7a56", label: "Destination / chemin final" },
                ].map(({ color, label }) => (
                  <span key={label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <span style={{ width: 10, height: 10, borderRadius: "50%", background: color, display: "inline-block" }} />
                    {label}
                  </span>
                ))}
              </div>

              <AstarMap result={result} currentStep={currentStep} />
            </>
          )}
        </section>
      )}
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// VRP TAB
// ─────────────────────────────────────────────────────────────────────────────

function VrpTab() {
  return (
    <>
      <section className="panel stack">
        <strong>Le problème : CVRPTW</strong>
        <p className="muted">
          Le projet résout un <em>Capacitated Vehicle Routing Problem with Time Windows</em>.
          On dispose de <strong>N traîneaux</strong> partant d&apos;un dépôt commun, chacun limité en
          capacité de charge. Chaque client doit être livré dans une fenêtre horaire.
          L&apos;objectif : minimiser le temps total (ou la distance) de la flotte.
        </p>
        <div className="grid-2" style={{ gap: 10 }}>
          {[
            { icon: "📍", label: "1 dépôt commun", desc: "Point de départ et d'arrivée obligatoire pour tous les traîneaux" },
            { icon: "🦌", label: "N traîneaux", desc: "Flotte fixe, capacité max en kg par véhicule" },
            { icon: "🎁", label: "M clients", desc: "Chacun avec un poids de colis et une fenêtre horaire" },
            { icon: "⏱️", label: "Matrice n×n", desc: "Temps de trajet précalculés entre chaque paire de points" },
          ].map(({ icon, label, desc }) => (
            <div key={label} className="metric-card">
              <div style={{ fontSize: "1.6rem" }}>{icon}</div>
              <div style={{ fontWeight: 600 }}>{label}</div>
              <div className="metric-label">{desc}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel stack">
        <strong>Construction de la matrice temps</strong>
        <p className="muted">
          Avant toute résolution, on précalcule une matrice n×n (n = clients + dépôt) où
          <code> M[i][j]</code> = temps du plus court chemin OSM entre le point i et le point j.
          Ce calcul est fait <em>une seule fois</em> à la génération de la mission, stocké en
          fichier <code>.npy</code> (NumPy binaire). Pendant la résolution OR-Tools accède
          aux valeurs en O(1) — aucun recalcul de graphe pendant l&apos;optimisation.
        </p>
        <pre className="code-block">{`       D      C1     C2     C3
D  [   0    240    310    180  ]
C1 [ 230      0    140    290  ]
C2 [ 290    130      0    210  ]
C3 [ 175    280    200      0  ]   ← unité : secondes`}</pre>
      </section>

      <section className="panel stack">
        <strong>Résolution avec Google OR-Tools</strong>
        <p className="muted">
          OR-Tools formalise le CVRPTW comme un modèle de routage en 6 étapes :
        </p>
        <ol style={{ color: "var(--muted)", lineHeight: 2.2, paddingLeft: 22, margin: 0 }}>
          <li><strong>RoutingIndexManager</strong> — indexe les nœuds (dépôt + clients)</li>
          <li><strong>Callback de transit</strong> — retourne M[i][j] pour chaque paire</li>
          <li><strong>Dimension temps</strong> — fenêtres horaires + temps de service client</li>
          <li><strong>Dimension capacité</strong> — contrainte de poids par traîneau</li>
          <li><strong>Drop penalty</strong> — pénalité pour clients non servis (éviter l&apos;infaisabilité)</li>
          <li><strong>Résolution</strong> — heuristique d&apos;init + amélioration locale (metaheuristique)</li>
        </ol>
      </section>

      <section className="panel stack">
        <strong>Les profils IA et leurs paramètres</strong>
        <p className="muted" style={{ fontSize: "0.85rem", marginBottom: 8 }}>
          Chaque profil ajuste la stratégie de résolution pour produire des tournées de styles différents.
        </p>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid var(--border)" }}>
                {["Profil", "Objectif", "Init", "Métaheuristique", "Budget temps"].map((h) => (
                  <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: "var(--muted)", fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ["Express", "Temps", "Parallel cheapest", "Guided local search", "12 s"],
                ["Écolo", "Distance", "Path cheapest arc", "Simulated annealing", "18 s"],
                ["Prudent", "Temps + marge", "Parallel cheapest", "Guided local search", "28 s"],
                ["Opportuniste", "Temps + flexib.", "Parallel cheapest", "Tabu search", "22 s"],
              ].map(([profil, ...rest]) => (
                <tr key={profil} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "8px 12px", fontWeight: 600 }}>{profil}</td>
                  {rest.map((cell, i) => (
                    <td key={i} style={{ padding: "8px 12px", color: "var(--muted)" }}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel stack">
        <strong>Flotte dynamique — SetFixedCostOfVehicle</strong>
        <p className="muted">
          Par défaut, OR-Tools accepte d&apos;utiliser tous les traîneaux disponibles même si certains
          restent vides — gaspillage de flotte. Pour forcer le solveur à minimiser naturellement
          le nombre de véhicules, on ajoute un <strong>coût fixe par traîneau utilisé</strong> via
          <code> SetFixedCostOfVehicle</code>. OR-Tools préfère alors charger un traîneau déjà
          utilisé plutôt qu&apos;en ouvrir un nouveau, sauf si la capacité ou les fenêtres horaires
          l&apos;imposent.
        </p>
        <pre className="code-block">{`max_vehicles = ceil(num_clients / 3)   ← borne haute
vehicle_fixed_cost = int(max_route_time_s × 0.15)
for v in range(max_vehicles):
    routing.SetFixedCostOfVehicle(vehicle_fixed_cost, v)
# → OR-Tools choisit 1, 2 ou 3 traîneaux selon la charge réelle`}</pre>
      </section>

      <section className="panel stack">
        <strong>A* pour la géométrie des tournées IA</strong>
        <p className="muted">
          Une fois l&apos;ordre des stops optimisé par OR-Tools, on reconstruit la géométrie de chaque
          segment (la vraie route sur le réseau OSM) pour l&apos;afficher sur la carte.
          Initialement, ce calcul utilisait Dijkstra brut (<code>nx.shortest_path</code>).
          Il utilise maintenant <strong>A* avec heuristique haversine admissible</strong> —
          même chemin optimal, mais moins de nœuds explorés.
          Les routes humaines utilisaient déjà A* ; les routes IA sont maintenant cohérentes.
        </p>
        <div className="algo-compare-bar">
          <div className="algo-compare-row">
            <span className="algo-compare-label">Avant (Dijkstra)</span>
            <div className="algo-compare-track">
              <div className="algo-compare-fill dijkstra" style={{ width: "100%" }} />
            </div>
            <span className="algo-compare-count">tous les nœuds à égale distance</span>
          </div>
          <div className="algo-compare-row">
            <span className="algo-compare-label" style={{ color: "#1a6fb5" }}>Après (A*)</span>
            <div className="algo-compare-track">
              <div className="algo-compare-fill astar" style={{ width: "40%" }} />
            </div>
            <span className="algo-compare-count" style={{ color: "#1f7a56" }}>guidé vers la destination</span>
          </div>
        </div>
      </section>

      <section className="panel stack">
        <strong>Sources de données</strong>
        {[
          { src: "OpenStreetMap", role: "Réseau routier (nœuds, arcs, vitesses légales)", lib: "osmnx" },
          { src: "CSV mission", role: "Clients, poids colis, fenêtres horaires", lib: "pandas" },
          { src: "OpenWeatherMap API", role: "Facteur météo multiplicatif sur les temps de trajet", lib: "requests" },
          { src: "Générateur aléatoire", role: "Incidents routiers — arcs supprimés temporairement", lib: "networkx" },
        ].map(({ src, role, lib }) => (
          <div key={src} className="sleigh-row">
            <span className="lb-zone" style={{ minWidth: 160 }}>{src}</span>
            <span className="muted" style={{ flex: 1 }}>{role}</span>
            <code style={{ fontSize: "0.8rem", color: "var(--accent-2)", whiteSpace: "nowrap" }}>{lib}</code>
          </div>
        ))}
      </section>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 2-OPT TAB
// ─────────────────────────────────────────────────────────────────────────────

const ROUTE_A = [
  { x: 80, y: 200 }, { x: 280, y: 70 }, { x: 470, y: 220 },
  { x: 300, y: 360 }, { x: 130, y: 310 },
];
const ROUTE_B = [
  { x: 80, y: 200 }, { x: 130, y: 310 }, { x: 300, y: 360 },
  { x: 470, y: 220 }, { x: 280, y: 70 },
];

function routeLen(pts: { x: number; y: number }[]) {
  let t = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    t += Math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y);
  }
  return Math.round(t);
}

function RouteSvg({ pts, color, label }: { pts: { x: number; y: number }[]; color: string; label: string }) {
  const closed = [...pts, pts[0]];
  const d = closed.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
  return (
    <div style={{ flex: "1 1 260px" }}>
      <div style={{ fontWeight: 600, color, marginBottom: 8 }}>{label}</div>
      <svg viewBox="0 0 560 430" style={{ width: "100%", background: "rgba(18,50,71,0.03)", borderRadius: 14 }}>
        <path d={d} fill="none" stroke={color} strokeWidth={2.5} strokeLinejoin="round" />
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={i === 0 ? 13 : 9} fill={i === 0 ? "#17324d" : color} />
            <text x={p.x} y={p.y + 5} textAnchor="middle" fill="white" fontSize={i === 0 ? 11 : 10} fontWeight="bold">
              {i === 0 ? "D" : i}
            </text>
          </g>
        ))}
      </svg>
      <div style={{ marginTop: 6, color: "var(--muted)", fontSize: "0.85rem" }}>
        Longueur estimée : {routeLen(pts)} u.
      </div>
    </div>
  );
}

function TwoOptTab() {
  const [showAfter, setShowAfter] = useState(false);
  const gain = routeLen(ROUTE_A) - routeLen(ROUTE_B);
  const gainPct = Math.round((gain / routeLen(ROUTE_A)) * 100);

  return (
    <>
      <section className="panel stack">
        <strong>Principe du 2-opt</strong>
        <p className="muted">
          Le 2-opt est une <em>recherche locale</em> pour le TSP/VRP. Il parcourt toutes les paires
          de positions (i, j) dans la route et inverse le sous-segment [i, j+1]. Si le nouveau coût
          est inférieur, il accepte et recommence. Il converge car le coût est strictement décroissant
          et le nombre de permutations est fini.
        </p>
        <pre className="code-block">{`route  = [D → 1 → 2 → 3 → 4 → D]
inversion [1:3]  →  [D → 1 → 3 → 2 → 4 → D]
si coût(nouvelle) < coût(route) → accepter  ✓`}</pre>
      </section>

      <section className="panel stack">
        <strong>Visualisation — avant / après 2-opt</strong>
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          <RouteSvg pts={ROUTE_A} color="#9e2f3f" label="Avant 2-opt — croisements visibles" />
          {showAfter && (
            <RouteSvg pts={ROUTE_B} color="#1f7a56" label="Après 2-opt — croisements éliminés" />
          )}
        </div>
        <button
          className={showAfter ? "secondary-button" : "primary-button"}
          onClick={() => setShowAfter((v) => !v)}
          style={{ alignSelf: "flex-start" }}
        >
          {showAfter ? "Masquer" : "→ Voir après 2-opt"}
        </button>
        {showAfter && (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Le croisement entre (1→2) et (3→D) est éliminé en inversant [2, 3].
            Gain : <strong>{gain} u. ({gainPct}%)</strong> — de {routeLen(ROUTE_A)} à {routeLen(ROUTE_B)}.
          </p>
        )}
      </section>

      <section className="panel stack">
        <strong>Dans le projet</strong>
        <p className="muted">
          Le 2-opt est appliqué <em>après la mission</em> sur la solution humaine brute, avec la
          matrice temps précalculée (accès O(1)). Les résultats apparaissent dans le débriefing :
          gain en secondes et en pourcentage par traîneau, et ordre optimal suggéré au joueur.
        </p>
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          Seuil de 1 seconde pour éviter les acceptations dues au bruit flottant.
          Complexité : O(n²) par itération, généralement convergence en 2-5 passes.
        </p>
        <Link className="secondary-button" href="/leaderboard" style={{ alignSelf: "flex-start" }}>
          Voir les débriefings →
        </Link>
      </section>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// OR-OPT TAB
// ─────────────────────────────────────────────────────────────────────────────

const OO_BEFORE = {
  a: [{ x: 80, y: 160 }, { x: 200, y: 60 }, { x: 340, y: 80 }, { x: 240, y: 200 }],
  b: [{ x: 80, y: 160 }, { x: 130, y: 290 }, { x: 300, y: 320 }, { x: 420, y: 260 }],
};
const OO_AFTER = {
  a: [{ x: 80, y: 160 }, { x: 200, y: 60 }, { x: 340, y: 80 }],
  b: [{ x: 80, y: 160 }, { x: 240, y: 200 }, { x: 130, y: 290 }, { x: 300, y: 320 }, { x: 420, y: 260 }],
};

function OrOptSvg({
  routes,
  label,
  colorA = "#9e2f3f",
  colorB = "#17324d",
}: {
  routes: { a: { x: number; y: number }[]; b: { x: number; y: number }[] };
  label: string;
  colorA?: string;
  colorB?: string;
}) {
  const depot = routes.a[0];
  function polyline(pts: { x: number; y: number }[], loop = true) {
    const all = loop ? [...pts, pts[0]] : pts;
    return all.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + (loop ? " Z" : "");
  }
  return (
    <div style={{ flex: "1 1 260px" }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{label}</div>
      <svg viewBox="0 0 520 380" style={{ width: "100%", background: "rgba(18,50,71,0.03)", borderRadius: 14 }}>
        <path d={polyline(routes.a)} fill="none" stroke={colorA} strokeWidth={2.5} strokeLinejoin="round" />
        <path d={polyline(routes.b)} fill="none" stroke={colorB} strokeWidth={2.5} strokeLinejoin="round" strokeDasharray="6 4" />
        {routes.a.map((p, i) => (
          <g key={`a-${i}`}>
            <circle cx={p.x} cy={p.y} r={i === 0 ? 12 : 8} fill={i === 0 ? "#17324d" : colorA} />
            <text x={p.x} y={p.y + 4} textAnchor="middle" fill="white" fontSize={10} fontWeight="bold">{i === 0 ? "D" : `A${i}`}</text>
          </g>
        ))}
        {routes.b.slice(1).map((p, i) => (
          <g key={`b-${i}`}>
            <circle cx={p.x} cy={p.y} r={8} fill={colorB} />
            <text x={p.x} y={p.y + 4} textAnchor="middle" fill="white" fontSize={10} fontWeight="bold">{`B${i + 1}`}</text>
          </g>
        ))}
        {depot && <circle cx={depot.x} cy={depot.y} r={12} fill="#17324d" />}
      </svg>
    </div>
  );
}

function OrOptTab() {
  const [showAfter, setShowAfter] = useState(false);
  return (
    <>
      <section className="panel stack">
        <strong>Principe de l&apos;or-opt (relocalisation inter-routes)</strong>
        <p className="muted">
          L&apos;or-opt est une <em>recherche locale</em> qui déplace un segment de 1, 2 ou 3 clients
          consécutifs d&apos;une route vers une autre. Contrairement au 2-opt (qui n&apos;inverse des
          segments <em>intra-route</em>), l&apos;or-opt rééquilibre la charge entre traîneaux — utile
          quand un véhicule est surchargé et un autre sous-utilisé.
        </p>
        <pre className="code-block">{`pour chaque longueur seg_len ∈ {1, 2, 3} :
  pour chaque paire (route_a, route_b) :
    pour chaque position i dans route_a :
      segment = route_a[i : i + seg_len]
      pour chaque position j dans route_b :
        delta = coût(insérer segment en j) - coût(retirer segment de i)
        si delta < -1 s → accepter et continuer`}</pre>
      </section>

      <section className="panel stack">
        <strong>Visualisation — relocalisation d&apos;un client entre deux tournées</strong>
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          <OrOptSvg routes={OO_BEFORE} label="Avant or-opt — A2 mal placé dans la route rouge" />
          {showAfter && (
            <OrOptSvg routes={OO_AFTER} label="Après or-opt — A2 relocalisé dans la route bleue" />
          )}
        </div>
        <button
          className={showAfter ? "secondary-button" : "primary-button"}
          onClick={() => setShowAfter((v) => !v)}
          style={{ alignSelf: "flex-start" }}
        >
          {showAfter ? "Masquer" : "→ Voir après or-opt"}
        </button>
        {showAfter && (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Le client A2 est retiré de la tournée rouge et inséré entre D et B1 dans la tournée bleue.
            La route rouge perd un détour coûteux, la route bleue absorbe le client à faible coût marginal.
          </p>
        )}
      </section>

      <section className="panel stack">
        <strong>Dans le projet</strong>
        <p className="muted">
          L&apos;or-opt est appliqué post-mission sur la solution humaine, après le 2-opt.
          Les deux optimisations sont complémentaires : le 2-opt corrige les croisements
          intra-route, l&apos;or-opt rééquilibre la charge inter-routes. Les gains comparés
          sont affichés dans le débriefing par traîneau.
        </p>
      </section>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// NEAREST NEIGHBOR TAB
// ─────────────────────────────────────────────────────────────────────────────

const NN_STEPS = [
  { from: { x: 80, y: 200 }, to: { x: 200, y: 80 }, label: "D → 2", cost: 160 },
  { from: { x: 200, y: 80 }, to: { x: 360, y: 100 }, label: "2 → 4", cost: 163 },
  { from: { x: 360, y: 100 }, to: { x: 460, y: 250 }, label: "4 → 3", cost: 195 },
  { from: { x: 460, y: 250 }, to: { x: 300, y: 350 }, label: "3 → 1", cost: 190 },
  { from: { x: 300, y: 350 }, to: { x: 80, y: 200 }, label: "1 → D", cost: 254 },
];
const NN_NODES = [
  { x: 80, y: 200, label: "D" },
  { x: 300, y: 350, label: "1" },
  { x: 200, y: 80, label: "2" },
  { x: 460, y: 250, label: "3" },
  { x: 360, y: 100, label: "4" },
];

function NearestNeighborTab() {
  const [step, setStep] = useState(0);
  const visibleEdges = NN_STEPS.slice(0, step);
  const visitedNodes = new Set(["D", ...NN_STEPS.slice(0, step).map((s) => s.label.split(" → ")[1])]);

  return (
    <>
      <section className="panel stack">
        <strong>Nearest Neighbor — construction greedy</strong>
        <p className="muted">
          Le Nearest Neighbor (plus proche voisin) est l&apos;heuristique la plus simple pour le TSP.
          À partir du dépôt, on visite toujours le client non visité dont le temps de trajet
          est le plus faible. L&apos;algorithme est rapide (O(n²)) mais sa solution n&apos;est pas garantie
          optimale — il sert de <em>baseline pédagogique</em> pour comparer avec OR-Tools.
        </p>
        <pre className="code-block">{`position = dépôt ; non_visités = {tous les clients}
tant que non_visités non vide :
  prochain = argmin(temps[position][c] pour c ∈ non_visités)
  route.append(prochain)
  non_visités.remove(prochain)
  position = prochain
route.append(dépôt)  ← retour final`}</pre>
      </section>

      <section className="panel stack">
        <strong>Visualisation pas-à-pas — 4 clients</strong>
        <svg viewBox="0 0 560 430" style={{ width: "100%", background: "rgba(18,50,71,0.03)", borderRadius: 14 }}>
          {visibleEdges.map((e, i) => (
            <line key={i}
              x1={e.from.x} y1={e.from.y} x2={e.to.x} y2={e.to.y}
              stroke={i === visibleEdges.length - 1 ? "#9e2f3f" : "#aab8c6"}
              strokeWidth={i === visibleEdges.length - 1 ? 3 : 2}
            />
          ))}
          {NN_NODES.map((n) => (
            <g key={n.label}>
              <circle cx={n.x} cy={n.y} r={n.label === "D" ? 14 : 10}
                fill={visitedNodes.has(n.label) ? (n.label === "D" ? "#17324d" : "#1f7a56") : "#aab8c6"} />
              <text x={n.x} y={n.y + 5} textAnchor="middle" fill="white" fontSize={11} fontWeight="bold">{n.label}</text>
            </g>
          ))}
          {visibleEdges.length > 0 && (() => {
            const e = visibleEdges[visibleEdges.length - 1];
            const mx = (e.from.x + e.to.x) / 2;
            const my = (e.from.y + e.to.y) / 2 - 14;
            return <text x={mx} y={my} textAnchor="middle" fill="#9e2f3f" fontSize={11}>{e.cost} s</text>;
          })()}
        </svg>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button className="secondary-button" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>← Précédent</button>
          <button className="primary-button" onClick={() => setStep((s) => Math.min(NN_STEPS.length, s + 1))} disabled={step === NN_STEPS.length}>Suivant →</button>
          <span className="muted" style={{ fontSize: "0.85rem" }}>
            {step === 0 && "Démarre depuis le dépôt D"}
            {step > 0 && step < NN_STEPS.length && `Étape ${step} : ${NN_STEPS[step - 1].label} — coût +${NN_STEPS[step - 1].cost} s`}
            {step === NN_STEPS.length && `✓ Tournée complète — coût total ${NN_STEPS.reduce((s, e) => s + e.cost, 0)} s`}
          </span>
        </div>
      </section>

      <section className="panel stack">
        <strong>Limite du greedy & gap d&apos;optimalité</strong>
        <p className="muted">
          Le Nearest Neighbor peut produire des routes sous-optimales car chaque décision locale
          ignore l&apos;impact sur la suite. Dans le projet, on calcule aussi une <em>borne inférieure</em>
          (somme des distances minimales dépôt → chaque client) pour estimer le gap d&apos;optimalité
          de la solution humaine : <code>(coût humain - borne) / borne × 100%</code>.
          Un gap &lt; 15% signifie une solution proche de l&apos;optimum théorique.
        </p>
      </section>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ILS TAB
// ─────────────────────────────────────────────────────────────────────────────

const DB_NODES = [
  { x: 80,  y: 200, label: "D" },
  { x: 200, y: 80,  label: "A" },
  { x: 340, y: 60,  label: "B" },
  { x: 460, y: 180, label: "C" },
  { x: 400, y: 320, label: "D2" },
  { x: 220, y: 340, label: "E" },
];
// Avant : D→A→B→C→D2→E→D
const DB_BEFORE = [0,1,2,3,4,5];
// Après double-bridge (A+C+B+D → D→A→D2→C→B→E→D) : coupe en i=2,j=4,k=5
// A=[D,A] B=[B,C] C=[D2] D=[E]  → A+C+B+D = [D,A,D2,B,C,E]
const DB_AFTER  = [0,1,4,2,3,5];

function DbSvg({ order, color, label }: { order: number[]; color: string; label: string }) {
  const pts = order.map((i) => DB_NODES[i]);
  const closed = [...pts, pts[0]];
  const d = closed.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  return (
    <div style={{ flex: "1 1 260px" }}>
      <div style={{ fontWeight: 600, color, marginBottom: 8, fontSize: "0.9rem" }}>{label}</div>
      <svg viewBox="0 0 560 420" style={{ width: "100%", background: "rgba(18,50,71,0.03)", borderRadius: 14 }}>
        <path d={d} fill="none" stroke={color} strokeWidth={2.5} strokeLinejoin="round" />
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={i === 0 ? 14 : 10} fill={i === 0 ? "#17324d" : color} />
            <text x={p.x} y={p.y + 5} textAnchor="middle" fill="white" fontSize={10} fontWeight="bold">
              {DB_NODES[order[i]].label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function IlsTab() {
  const [showDb, setShowDb] = useState(false);
  const [ilsStep, setIlsStep] = useState(0);

  const ILS_STEPS = [
    { label: "Solution initiale S*", sub: "3-opt + or-opt + 2-opt* → optimum local", cost: 1420, color: "#9e2f3f" },
    { label: "Perturbation double-bridge", sub: "4-opt non-séquentiel sur la route la plus longue", cost: 1610, color: "#b8892f" },
    { label: "Recherche locale complète", sub: "3-opt + or-opt + 2-opt* → nouveau local", cost: 1330, color: "#6b3fa0" },
    { label: "Acceptation (S' < S*)", sub: "Amélioration de 90 s acceptée — S* ← S'", cost: 1330, color: "#1a6fb5" },
    { label: "Perturbation #2 + LS", sub: "Nouvel essai — pas d'amélioration, rejet", cost: 1380, color: "#b8892f" },
    { label: "Solution finale S*", sub: "Meilleure solution trouvée sur 8 itérations", cost: 1330, color: "#1f7a56" },
  ];

  return (
    <>
      <section className="panel stack">
        <strong>ILS — Iterated Local Search</strong>
        <p className="muted">
          OR-Tools produit une bonne solution initiale, mais elle reste bloquée dans un{" "}
          <em>optimum local</em> : aucune perturbation 2-opt ou 3-opt ne peut l&apos;améliorer.
          L&apos;ILS s&apos;en échappe en appliquant une <strong>perturbation structurelle forte</strong> —
          le <em>double-bridge</em> — puis en relançant la recherche locale depuis le nouvel état.
          Cette boucle se répète 8 fois ; seules les améliorations sont acceptées.
        </p>
        <pre className="code-block">{`S* = local_search(solution_OR-Tools)   ← phase 1

for i in range(8):                      ← phase 2
    S_perturb = double_bridge(route_max(S*))
    S'        = local_search(S_perturb)   # 3-opt + or-opt + 2-opt*
    if coût(S') < coût(S*):
        S* = S'                           # acceptation stricte
return S*`}</pre>
      </section>

      <section className="panel stack">
        <strong>Trace d&apos;exécution — 8 itérations</strong>
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          Avance pas-à-pas pour voir l&apos;évolution du coût total de la flotte.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {ILS_STEPS.map((s, i) => (
            <div
              key={i}
              onClick={() => setIlsStep(i)}
              style={{
                display: "flex", alignItems: "center", gap: 14, cursor: "pointer",
                opacity: i <= ilsStep ? 1 : 0.3,
                transition: "opacity 0.25s",
              }}
            >
              <span style={{
                width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                background: i <= ilsStep ? s.color : "rgba(18,50,71,0.1)",
                display: "grid", placeItems: "center",
                fontSize: "0.75rem", fontWeight: 700, color: "white",
                transition: "background 0.3s",
              }}>
                {i + 1}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: "0.9rem", color: i <= ilsStep ? "var(--text)" : "var(--muted)" }}>{s.label}</div>
                <div style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{s.sub}</div>
              </div>
              <span style={{
                fontWeight: 700, fontSize: "0.9rem", minWidth: 64, textAlign: "right",
                color: i === ilsStep ? s.color : "var(--muted)",
              }}>
                {s.cost} s
              </span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
          <button className="secondary-button" onClick={() => setIlsStep((s) => Math.max(0, s - 1))} disabled={ilsStep === 0}>← Précédent</button>
          <button className="primary-button" onClick={() => setIlsStep((s) => Math.min(ILS_STEPS.length - 1, s + 1))} disabled={ilsStep === ILS_STEPS.length - 1}>Suivant →</button>
          <button className="secondary-button" onClick={() => setIlsStep(0)}>⏮ Reset</button>
        </div>
        {ilsStep === ILS_STEPS.length - 1 && (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Gain final : <strong style={{ color: "#1f7a56" }}>90 s (6,3%)</strong> par rapport à l&apos;optimum local OR-Tools initial.
            La perturbation double-bridge a permis d&apos;explorer un nouveau bassin d&apos;attraction inaccessible par 2-opt ou 3-opt seuls.
          </p>
        )}
      </section>

      <section className="panel stack">
        <strong>Double-bridge — la perturbation irréversible</strong>
        <p className="muted">
          Le double-bridge coupe une route en 4 segments (A, B, C, D) puis les recolle
          dans l&apos;ordre <strong>A + C + B + D</strong>. Ce mouvement est un <em>4-opt non-séquentiel</em> :
          aucune séquence de 2-opt ou 3-opt ne peut produire ce réarrangement, ce qui garantit
          que l&apos;ILS explore un nouveau bassin d&apos;attraction à chaque itération.
        </p>
        <pre className="code-block">{`cuts i < j < k  (aléatoires dans [1, n-1])
A = route[ :i]  B = route[i:j]
C = route[j:k]  D = route[k: ]
→  A + C + B + D   ← 4-opt, impossible à défaire par 2-opt/3-opt`}</pre>
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          <DbSvg order={DB_BEFORE} color="#9e2f3f" label="Avant double-bridge — ordre original" />
          {showDb && <DbSvg order={DB_AFTER} color="#1a6fb5" label="Après double-bridge — A+C+B+D reconnecté" />}
        </div>
        <button
          className={showDb ? "secondary-button" : "primary-button"}
          onClick={() => setShowDb((v) => !v)}
          style={{ alignSelf: "flex-start" }}
        >
          {showDb ? "Masquer" : "→ Voir après double-bridge"}
        </button>
      </section>

      <section className="panel stack">
        <strong>Recherche locale en pipeline : 3-opt → or-opt → 2-opt*</strong>
        <p className="muted">
          Après chaque perturbation, trois optimisations locales s&apos;enchaînent dans l&apos;ordre :
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            { num: "1", name: "3-opt intra-route", desc: "Teste toutes les triples inversions dans chaque tournée. Plus puissant que 2-opt mais O(n³) — limité aux routes courtes.", color: "#1a6fb5" },
            { num: "2", name: "or-opt inter-routes", desc: "Déplace des segments de 1, 2 ou 3 clients vers d'autres traîneaux si la capacité le permet. Rééquilibre la charge.", color: "#6b3fa0" },
            { num: "3", name: "2-opt* inter-routes", desc: "Échange les queues de deux routes (swap des fins). Complémentaire à or-opt : permet des transferts massifs.", color: "#1f7a56" },
          ].map(({ num, name, desc, color }) => (
            <div key={num} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
              <span style={{
                width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                background: color, display: "grid", placeItems: "center",
                fontSize: "0.75rem", fontWeight: 700, color: "white",
              }}>{num}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{name}</div>
                <div style={{ fontSize: "0.82rem", color: "var(--muted)" }}>{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────────────────

export default function ExplorePage() {
  const [tab, setTab] = useState<Tab>("graph");
  const [missionId, setMissionId] = useState("");
  const [autoDemoEnabled, setAutoDemoEnabled] = useState(false);
  const [autoDemoStep, setAutoDemoStep] = useState(0);
  const [autoDemoPaused, setAutoDemoPaused] = useState(false);
  const [heroPulse, setHeroPulse] = useState(false);
  const tabsAnchorRef = useRef<HTMLDivElement | null>(null);

  const missionsQuery = useQuery({
    queryKey: ["missions"],
    queryFn: () => getMissions(20),
  });
  const graphMetricsQuery = useQuery({
    queryKey: ["graph-metrics-hero", missionId],
    queryFn: () => getGraphMetrics(missionId),
    enabled: Boolean(missionId),
    retry: false,
  });

  const missions = missionsQuery.data?.missions ?? [];
  const selectedMission = missions.find((m) => m.mission_id === missionId);
  const currentAutoDemo = AUTO_DEMO_SEQUENCE[autoDemoStep];
  const autoDemoProgress = ((autoDemoStep + 1) / AUTO_DEMO_SEQUENCE.length) * 100;

  function scrollToTabs() {
    tabsAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function startAutoDemo() {
    setAutoDemoEnabled(true);
    setAutoDemoPaused(false);
    setAutoDemoStep(0);
    setHeroPulse(true);
    scrollToTabs();
  }

  function stopAutoDemo() {
    setAutoDemoEnabled(false);
    setAutoDemoPaused(false);
    setAutoDemoStep(0);
    setHeroPulse(false);
  }

  useEffect(() => {
    if (!autoDemoEnabled || autoDemoPaused) return;
    const step = AUTO_DEMO_SEQUENCE[autoDemoStep];
    if (!step) {
      stopAutoDemo();
      return;
    }
    if (step.key !== "story") {
      setTab(step.key);
      setHeroPulse(false);
    } else {
      setHeroPulse(true);
    }
    const timeout = window.setTimeout(() => {
      setAutoDemoStep((prev) => {
        const next = prev + 1;
        if (next >= AUTO_DEMO_SEQUENCE.length) {
          setAutoDemoEnabled(false);
          setAutoDemoPaused(false);
          setHeroPulse(false);
          return prev;
        }
        return next;
      });
    }, step.durationMs);
    return () => window.clearTimeout(timeout);
  }, [autoDemoEnabled, autoDemoPaused, autoDemoStep]);

  return (
    <div className="page-shell explore-shell">
      <div className="page-stack">

        <section className={`hero explore-story-hero ${heroPulse ? "is-pulsing" : ""}`}>
          <div className="explore-story-grid">
            <div className="explore-story-main">
              <h1>Coulisses algorithmiques — mode showcase</h1>
              <p>
                De la carte OSM brute à la tournée optimisée : visualise le pipeline IA en live,
                avec des démos orientées présentation.
              </p>
              <div className="explore-story-badges">
                <span className="hero-badge">⭐ A* bidirectionnel</span>
                <span className="hero-badge">📦 VRPTW OR-Tools</span>
                <span className="hero-badge">🔥 ILS + 2-opt + or-opt</span>
              </div>
              <div className="explore-story-cta">
                <button className="primary-button" onClick={startAutoDemo}>
                  ▶ Lancer Auto-Demo
                </button>
                <button className="secondary-button" onClick={scrollToTabs}>
                  Aller aux tabs
                </button>
              </div>
            </div>
            <div className="explore-kpi-strip">
              <div className="explore-kpi-head">Signal live de présentation</div>
              <div className="explore-kpi-grid">
                <div className="explore-kpi-card">
                  <span>Nœuds graphe</span>
                  <strong>
                    {graphMetricsQuery.isLoading
                      ? "…"
                      : graphMetricsQuery.data
                        ? graphMetricsQuery.data.num_nodes.toLocaleString()
                        : "—"}
                  </strong>
                </div>
                <div className="explore-kpi-card">
                  <span>Réduction A* (démo)</span>
                  <strong>{missionId ? "mission dépendante" : "placeholder"}</strong>
                </div>
                <div className="explore-kpi-card">
                  <span>Pipeline</span>
                  <strong>OSM → A* → VRPTW</strong>
                </div>
                <div className="explore-kpi-card">
                  <span>Mission active</span>
                  <strong>{selectedMission ? selectedMission.mission.zone : "Aucune"}</strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="panel stack explore-mission-source">
          <div className="panel-head">
            <strong>Mission source</strong>
            {autoDemoEnabled ? (
              <span className="tag">
                Auto-Demo · étape {Math.min(autoDemoStep + 1, AUTO_DEMO_SEQUENCE.length)}/{AUTO_DEMO_SEQUENCE.length}
              </span>
            ) : (
              <span className="tag">Sélection recommandée pour les démos Graph/Dijkstra/A*</span>
            )}
          </div>
          <label className="field">
            <span>Sélectionne une mission</span>
            <select value={missionId} onChange={(e) => setMissionId(e.target.value)}>
              <option value="">-- choisir --</option>
              {missions.map((m) => (
                <option key={m.mission_id} value={m.mission_id}>
                  {m.mission.zone} · {m.mission_id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <div className="explore-narrative-track">
            <div className="explore-narrative-step">
              <span>1</span>
              <div>
                <strong>Graphe</strong>
                <p>Extraction OSM + métriques structurelles.</p>
              </div>
            </div>
            <div className="explore-narrative-step">
              <span>2</span>
              <div>
                <strong>Recherche de chemin</strong>
                <p>Dijkstra vs A* bidirectionnel pas-à-pas.</p>
              </div>
            </div>
            <div className="explore-narrative-step">
              <span>3</span>
              <div>
                <strong>Optimisation tournée</strong>
                <p>VRPTW OR-Tools + raffinements locaux.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="panel stack explore-autodemo-panel">
          <div className="panel-head">
            <strong>Auto-Demo</strong>
            <span className={`state-chip ${autoDemoEnabled ? "is-live" : "is-ready"}`}>
              {autoDemoEnabled ? "En cours" : "Prêt"}
            </span>
          </div>
          <div className="explore-autodemo-controls">
            <button className="primary-button" onClick={startAutoDemo} disabled={autoDemoEnabled && !autoDemoPaused}>
              ▶ Lancer
            </button>
            <button
              className="secondary-button"
              onClick={() => setAutoDemoPaused((prev) => !prev)}
              disabled={!autoDemoEnabled}
            >
              {autoDemoPaused ? "⏯ Reprendre" : "⏸ Pause"}
            </button>
            <button className="secondary-button" onClick={stopAutoDemo} disabled={!autoDemoEnabled}>
              ⏹ Stop
            </button>
          </div>
          <div className="hero-progress" aria-label="progression auto demo">
            <div className="hero-progress-fill" style={{ width: `${autoDemoEnabled ? autoDemoProgress : 0}%` }} />
          </div>
          <div className="hero-progress-label">
            {autoDemoEnabled ? `Étape actuelle: ${currentAutoDemo?.label ?? "—"}` : "Lance la séquence guidée de présentation"}
          </div>
        </section>

        <div ref={tabsAnchorRef} className="explore-tabs explore-tabs-premium">
          {EXPLORE_TABS.map(({ key, label, icon }) => (
            <button
              key={key}
              className={tab === key ? "explore-tab-pill is-active" : "explore-tab-pill"}
              onClick={() => {
                setTab(key);
                if (autoDemoEnabled) {
                  setAutoDemoEnabled(false);
                  setAutoDemoPaused(false);
                  setHeroPulse(false);
                }
              }}
            >
              <span aria-hidden>{icon}</span>
              <span>{label}</span>
            </button>
          ))}
        </div>

        <div key={tab} className="tab-content explore-tab-stage">
          {tab === "graph" && <GraphTab missionId={missionId} />}
          {tab === "dijkstra" && <DijkstraTab missionId={missionId} />}
          {tab === "astar" && <AstarTab missionId={missionId} />}
          {tab === "vrp" && <VrpTab />}
          {tab === "twoopt" && <TwoOptTab />}
          {tab === "oropt" && <OrOptTab />}
          {tab === "nn" && <NearestNeighborTab />}
          {tab === "ils" && <IlsTab />}
        </div>

        <section className="panel stack">
          <Link className="secondary-button" href="/" style={{ alignSelf: "flex-start" }}>← Retour accueil</Link>
        </section>

      </div>
    </div>
  );
}
