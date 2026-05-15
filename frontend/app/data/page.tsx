"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { getMissions, getLeaderboard } from "@/lib/api";

// ─── Animated counter ────────────────────────────────────────────────────────

function AnimatedCount({ target, suffix = "", duration = 1200 }: { target: number; suffix?: string; duration?: number }) {
  const [val, setVal] = useState(0);
  const started = useRef(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (started.current || target === 0) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      started.current = true;
      observer.disconnect();
      const startedAt = performance.now();
      const tick = (now: number) => {
        const p = Math.min((now - startedAt) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        setVal(Math.round(target * eased));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { threshold: 0.3 });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target, duration]);

  return <span ref={ref}>{val.toLocaleString("fr-FR")}{suffix}</span>;
}

// ─── Data flow SVG diagram ────────────────────────────────────────────────────

function DataFlowDiagram() {
  const nodes = [
    { id: "osm",     x: 80,  y: 60,  label: "OpenStreetMap",  icon: "🌍", color: "#1a6fb5" },
    { id: "overpass",x: 80,  y: 180, label: "Overpass API",   icon: "🏪", color: "#6b3fa0" },
    { id: "owm",     x: 80,  y: 300, label: "OpenWeatherMap", icon: "⛈️", color: "#b8892f" },
    { id: "osrm",    x: 80,  y: 420, label: "OSRM public",    icon: "🛣️", color: "#9e2f3f" },
    { id: "graph",   x: 310, y: 120, label: "Graphe OSM",     icon: "🔵", color: "#1a6fb5" },
    { id: "clients", x: 310, y: 240, label: "Points clients", icon: "📍", color: "#1f7a56" },
    { id: "matrix",  x: 310, y: 360, label: "Matrice n×n",    icon: "🔢", color: "#9e2f3f" },
    { id: "vrp",     x: 530, y: 200, label: "OR-Tools VRPTW", icon: "🧮", color: "#c45e00" },
    { id: "ils",     x: 530, y: 320, label: "ILS / 2-opt",    icon: "🔥", color: "#6b3fa0" },
    { id: "result",  x: 720, y: 260, label: "Tournée",        icon: "🎁", color: "#1f7a56" },
  ];

  const edges = [
    ["osm", "graph"], ["overpass", "clients"], ["owm", "matrix"],
    ["osrm", "matrix"], ["graph", "clients"], ["graph", "matrix"],
    ["clients", "vrp"], ["matrix", "vrp"], ["vrp", "ils"], ["ils", "result"],
  ];

  const nodeMap = Object.fromEntries(nodes.map((n) => [n.id, n]));

  return (
    <svg viewBox="0 0 820 500" style={{ width: "100%", maxHeight: 320, overflow: "visible" }}>
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="rgba(18,50,71,0.35)" />
        </marker>
      </defs>
      {edges.map(([a, b], i) => {
        const na = nodeMap[a]; const nb = nodeMap[b];
        return (
          <line key={i}
            x1={na.x + 60} y1={na.y + 18} x2={nb.x - 4} y2={nb.y + 18}
            stroke="rgba(18,50,71,0.25)" strokeWidth={1.5} markerEnd="url(#arrow)"
          />
        );
      })}
      {nodes.map((n) => (
        <g key={n.id}>
          <rect x={n.x} y={n.y} width={120} height={36} rx={10}
            fill={`${n.color}18`} stroke={n.color} strokeWidth={1.5} />
          <text x={n.x + 16} y={n.y + 23} fontSize={14}>{n.icon}</text>
          <text x={n.x + 34} y={n.y + 23} fontSize={10} fill={n.color} fontWeight={600}>{n.label}</text>
        </g>
      ))}
    </svg>
  );
}

// ─── Traffic bar chart ────────────────────────────────────────────────────────

const TRAFFIC = [
  { h: "7h", f: 1.4 }, { h: "8h", f: 1.7 }, { h: "9h", f: 1.5 },
  { h: "10h", f: 1.1 }, { h: "12h", f: 1.2 }, { h: "13h", f: 1.3 },
  { h: "17h", f: 1.6 }, { h: "18h", f: 1.8 }, { h: "19h", f: 1.4 },
];

function TrafficChart() {
  const maxF = Math.max(...TRAFFIC.map((t) => t.f));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 100, padding: "0 4px" }}>
      {TRAFFIC.map(({ h, f }) => {
        const pct = ((f - 1) / (maxF - 1)) * 100;
        const color = f >= 1.6 ? "var(--accent)" : f >= 1.3 ? "#b8892f" : "#1f7a56";
        return (
          <div key={h} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <span style={{ fontSize: "0.65rem", color: "var(--muted)", fontWeight: 700 }}>×{f}</span>
            <div style={{
              width: "100%", borderRadius: "4px 4px 0 0", background: color,
              height: `${Math.max(8, pct)}%`, transition: "height 0.6s ease",
            }} />
            <span style={{ fontSize: "0.62rem", color: "var(--muted)" }}>{h}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Pipeline steps ───────────────────────────────────────────────────────────

const PIPELINE = [
  {
    n: "01", icon: "🌍", title: "Téléchargement du graphe OSM",
    detail: "osmnx.graph_from_point(center, dist=radius_m, network_type='drive') télécharge le graphe routier depuis OpenStreetMap. Chaque nœud est une intersection GPS, chaque arc un tronçon avec longueur et vitesse légale.",
    badge: "open data",
    badgeColor: "#1a6fb5",
    file: null,
    lib: "osmnx",
  },
  {
    n: "02", icon: "🔗", title: "Réduction au composant connexe",
    detail: "On garde uniquement la plus grande composante fortement connexe (SCC) pour garantir que chaque paire de nœuds est mutuellement accessible. Les nœuds isolés ou les impasses pures sont écartés.",
    badge: "networkx",
    badgeColor: "#6b3fa0",
    file: "paris5.graphml",
    lib: "nx.strongly_connected_components",
  },
  {
    n: "03", icon: "⏱️", title: "Enrichissement des vitesses et temps",
    detail: "ox.add_edge_speeds() déduit la vitesse légale de chaque tronçon depuis les tags OSM (maxspeed, highway type). ox.add_edge_travel_times() calcule la durée en secondes = longueur / vitesse.",
    badge: "calculé",
    badgeColor: "#1f7a56",
    file: null,
    lib: "osmnx",
  },
  {
    n: "04", icon: "🏪", title: "Noms réels des clients (Overpass)",
    detail: "L'API Overpass interroge OpenStreetMap pour les noms réels de commerces, équipements et POI autour du dépôt. Ces noms enrichissent les points de livraison générés — 'Boulangerie Martin' plutôt que 'Client 3'.",
    badge: "open data",
    badgeColor: "#1a6fb5",
    file: null,
    lib: "requests · Overpass QL",
  },
  {
    n: "05", icon: "📍", title: "Génération des points de livraison",
    detail: "Sélection aléatoire de nœuds OSM dans le rayon défini. Le dépôt est le nœud le plus proche du centre. Chaque client reçoit un poids (5-50 kg × facteur catégorie), une catégorie de cargaison et une fenêtre horaire (30% avec contrainte forte).",
    badge: "généré",
    badgeColor: "#1f7a56",
    file: "livraisons.csv",
    lib: "random · pandas",
  },
  {
    n: "06", icon: "⛅", title: "Météo réelle ou simulée",
    detail: "Si weather_key='real', l'API OpenWeatherMap retourne la météo actuelle de la ville. Un facteur multiplicatif est appliqué à toute la matrice de temps : ×1.0 (soleil), ×1.3 (pluie), ×2.0 (neige), ×2.5 (orage).",
    badge: "open data",
    badgeColor: "#1a6fb5",
    file: "weather_status.json",
    lib: "requests · OpenWeatherMap API",
  },
  {
    n: "07", icon: "🔢", title: "Calcul de la matrice n×n",
    detail: "Pour chaque paire de points (dépôt + clients), on calcule le plus court chemin. OSRM public (Contraction Hierarchies) est utilisé si n ≤ 40. Au-delà, fallback local : Dijkstra depuis chaque nœud source (nx.single_source_dijkstra_path_length). La matrice est stockée en binaire NumPy (.npy).",
    badge: "Dijkstra / OSRM",
    badgeColor: "#9e2f3f",
    file: "live_time_matrix.npy · dist_matrix.npy",
    lib: "networkx · OSRM",
  },
  {
    n: "08", icon: "🚦", title: "Profil de trafic horaire",
    detail: "Si une heure de départ est choisie, un multiplicateur de congestion est appliqué à toute la matrice de temps. Basé sur des données réelles de mobilité urbaine : pointe du matin ×1.7 à 8h, pointe du soir ×1.8 à 18h.",
    badge: "modèle",
    badgeColor: "#b8892f",
    file: null,
    lib: "numpy",
  },
  {
    n: "09", icon: "🧮", title: "Résolution VRPTW — OR-Tools",
    detail: "Google OR-Tools modélise le CVRPTW : dépôt commun, capacités, fenêtres horaires. La flotte est dynamique (ceil(n/3) max, coût fixe par véhicule pour minimiser le nombre utilisé). Stratégie : PATH_CHEAPEST_ARC + Guided Local Search, limite 20 s.",
    badge: "NP-difficile",
    badgeColor: "#c45e00",
    file: "resultats_finaux.json",
    lib: "ortools · pywrapcp",
  },
  {
    n: "10", icon: "🔥", title: "Post-traitement ILS",
    detail: "Iterated Local Search : 8 itérations de double-bridge (perturbation 4-opt non-réversible) suivies d'un pipeline 3-opt → or-opt → 2-opt*. Chaque amélioration est acceptée, les non-améliorations rejetées. Gain typique : 5-15% supplémentaires.",
    badge: "méta-heuristique",
    badgeColor: "#6b3fa0",
    file: null,
    lib: "networkx · numpy",
  },
  {
    n: "11", icon: "🗺️", title: "Géométrie des routes (A*)",
    detail: "Pour chaque arc de la tournée, on reconstruit la géométrie réelle sur le graphe OSM avec A* et l'heuristique haversine admissible (dist_vol ÷ 13,89 m/s). Les polylignes sont envoyées au frontend Leaflet pour affichage sur fond OpenStreetMap.",
    badge: "A* haversine",
    badgeColor: "#1a6fb5",
    file: null,
    lib: "networkx · react-leaflet",
  },
];

function PipelineStep({ step, idx }: { step: typeof PIPELINE[0]; idx: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 14,
        overflow: "hidden",
        transition: "box-shadow 0.2s",
        boxShadow: open ? "0 4px 24px rgba(18,50,71,0.10)" : "none",
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 14,
          padding: "14px 18px", background: "var(--panel)", border: "none", cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{
          fontSize: "0.72rem", fontWeight: 800, color: "var(--muted)",
          minWidth: 28, fontFamily: "var(--font-mono, monospace)",
        }}>
          {step.n}
        </span>
        <span style={{ fontSize: "1.2rem" }}>{step.icon}</span>
        <span style={{ flex: 1, fontWeight: 600, fontSize: "0.95rem" }}>{step.title}</span>
        <span style={{
          fontSize: "0.7rem", fontWeight: 700, color: step.badgeColor,
          background: `${step.badgeColor}18`, borderRadius: 6, padding: "2px 8px",
          border: `1px solid ${step.badgeColor}40`,
        }}>
          {step.badge}
        </span>
        <span style={{ color: "var(--muted)", fontSize: "0.8rem", marginLeft: 4 }}>
          {open ? "▲" : "▼"}
        </span>
      </button>
      {open && (
        <div style={{ padding: "0 18px 16px", background: "var(--panel)", display: "flex", flexDirection: "column", gap: 10 }}>
          <p className="muted" style={{ margin: 0, lineHeight: 1.7 }}>{step.detail}</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {step.lib && (
              <code style={{ fontSize: "0.78rem", color: "var(--accent-2)", background: "rgba(18,50,71,0.06)", padding: "2px 8px", borderRadius: 6 }}>
                {step.lib}
              </code>
            )}
            {step.file && (
              <code style={{ fontSize: "0.78rem", color: "var(--muted)", background: "rgba(18,50,71,0.06)", padding: "2px 8px", borderRadius: 6 }}>
                → {step.file}
              </code>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function DataPage() {
  const missionsQuery = useQuery({
    queryKey: ["missions-data-page"],
    queryFn: () => getMissions(200),
  });
  const leaderboardQuery = useQuery({
    queryKey: ["leaderboard-data-page"],
    queryFn: () => getLeaderboard(100),
  });

  const missions = missionsQuery.data?.missions ?? [];
  const entries  = leaderboardQuery.data?.entries ?? [];

  const solvedCount  = missions.filter((m) => m.status === "solved").length;
  const uniqueZones  = new Set(missions.map((m) => m.mission.zone)).size;
  const totalClients = missions.reduce((s, m) => s + m.mission.num_clients, 0);
  const avgScore     = entries.length > 0
    ? Math.round(entries.reduce((s, e) => s + e.score, 0) / entries.length * 10) / 10
    : 0;

  const [openSource, setOpenSource] = useState<string | null>(null);

  const SOURCES = [
    {
      id: "osm",
      icon: "🌍",
      name: "OpenStreetMap",
      type: "Open Data",
      typeColor: "#1a6fb5",
      format: "GraphML / .osm",
      lib: "osmnx",
      role: "Réseau routier mondial — nœuds, arcs, vitesses légales",
      detail: "OpenStreetMap est une carte collaborative libre couvrant la planète entière. Via osmnx, on télécharge le sous-graphe routier d'une zone en spécifiant un centre GPS et un rayon. Chaque nœud correspond à une intersection réelle, chaque arc à un tronçon avec son type de route (highway), sa vitesse maximale et sa géométrie précise. La licence ODbL (Open Database License) permet une réutilisation libre avec attribution.",
      stats: [
        { label: "Milliards de nœuds GPS", value: "7+" },
        { label: "Contributeurs actifs", value: "1,5M" },
        { label: "Licence", value: "ODbL" },
      ],
    },
    {
      id: "overpass",
      icon: "🏪",
      name: "Overpass API",
      type: "Open Data",
      typeColor: "#1a6fb5",
      format: "JSON (Overpass QL)",
      lib: "requests",
      role: "Noms réels de commerces et équipements OSM autour du dépôt",
      detail: "L'API Overpass permet d'interroger les données OSM avec un langage de requête dédié (Overpass QL). Pour chaque mission, on récupère jusqu'à 200 noms de POI (shops, amenities, tourism) dans le rayon choisi. Ces noms réels remplacent les étiquettes génériques 'Client N' et ancrent la simulation dans la géographie réelle — 'Café de Flore, Paris' plutôt qu'un identifiant abstrait.",
      stats: [
        { label: "Requêtes/jour max.", value: "10 000" },
        { label: "Tags OSM exploités", value: "shop · amenity · tourism" },
        { label: "Licence", value: "ODbL" },
      ],
    },
    {
      id: "owm",
      icon: "⛅",
      name: "OpenWeatherMap",
      type: "API publique",
      typeColor: "#b8892f",
      format: "JSON (REST)",
      lib: "requests",
      role: "Météo actuelle en temps réel — facteur appliqué aux temps de trajet",
      detail: "L'API OpenWeatherMap Current Weather retourne la condition météo actuelle (Clear, Rain, Snow, Thunderstorm) pour n'importe quelle ville. Un facteur multiplicatif est ensuite appliqué à toute la matrice de coût : ×1.0 par temps clair, ×1.3 sous la pluie, ×2.0 sous la neige, ×2.5 lors d'un orage. Cela modélise le ralentissement réel du trafic dû aux conditions météo.",
      stats: [
        { label: "Appels/minute (gratuit)", value: "60" },
        { label: "Facteur neige", value: "×2.0" },
        { label: "Facteur orage", value: "×2.5" },
      ],
    },
    {
      id: "osrm",
      icon: "🛣️",
      name: "OSRM public",
      type: "Service public",
      typeColor: "#9e2f3f",
      format: "JSON (REST /table)",
      lib: "requests",
      role: "Matrice n×n de temps de trajet (Contraction Hierarchies)",
      detail: "OSRM (Open Source Routing Machine) utilise l'algorithme Contraction Hierarchies (CH) pour calculer des plus courts chemins en temps quasi-constant. L'endpoint /table retourne une matrice complète n×n en un seul appel. Il est utilisé pour les petites instances (n ≤ 40) car il est très rapide. Pour les instances plus grandes, le fallback local (Dijkstra via NetworkX) prend le relais.",
      stats: [
        { label: "Algorithme", value: "Contraction Hierarchies" },
        { label: "Limite points (projet)", value: "40" },
        { label: "Temps typique", value: "< 2 s pour 40×40" },
      ],
    },
  ];

  return (
    <div className="page-shell">
      <div className="page-stack">

        {/* ── HERO ── */}
        <section className="hero" style={{ background: "linear-gradient(135deg, #0d1f2e 0%, #112b42 60%, #0e2a1c 100%)", minHeight: 220 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 680 }}>
            <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--accent-2)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
              Open Data · Graphes · IA
            </span>
            <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "clamp(1.6rem,5vw,2.8rem)", lineHeight: 1.15 }}>
              Opération Noël
              <br />
              <span style={{ color: "var(--accent-2)" }}>données & architecture</span>
            </h1>
            <p style={{ margin: 0, color: "rgba(255,255,255,0.7)", lineHeight: 1.7, fontSize: "1rem" }}>
              Un simulateur de tournées de livraison sur données ouvertes réelles.
              Le réseau routier vient d&apos;OpenStreetMap, la météo d&apos;OpenWeatherMap,
              les noms de livraison de l&apos;API Overpass — et l&apos;optimisation d&apos;OR-Tools + ILS.
            </p>
          </div>
        </section>

        {/* ── STATS EN DIRECT ── */}
        <div className="grid-2" style={{ gap: 12 }}>
          {[
            { label: "Missions générées", value: missions.length, suffix: "" },
            { label: "Missions résolues", value: solvedCount, suffix: "" },
            { label: "Villes / zones uniques", value: uniqueZones, suffix: "" },
            { label: "Colis simulés", value: totalClients, suffix: "" },
            { label: "Joueurs au Panthéon", value: entries.length, suffix: "" },
            { label: "Score moyen / 100", value: avgScore, suffix: "" },
          ].map(({ label, value, suffix }) => (
            <div key={label} className="metric-card is-good">
              <div className="metric-label">{label}</div>
              <div className="metric-value">
                {missionsQuery.isLoading ? "…" : <AnimatedCount target={value} suffix={suffix} />}
              </div>
            </div>
          ))}
        </div>

        {/* ── PRÉSENTATION DU PROJET ── */}
        <section className="panel stack">
          <strong>Qu&apos;est-ce qu&apos;Opération Noël ?</strong>
          <p className="muted" style={{ lineHeight: 1.8 }}>
            Opération Noël est un <em>simulateur pédagogique de tournées</em> de livraison,
            construit autour du problème{" "}
            <strong>CVRPTW</strong> (Capacitated Vehicle Routing Problem with Time Windows).
            Le joueur incarne un agent logistique du Père Noël : il trace les itinéraires de sa
            flotte de traîneaux sur un vrai réseau routier OpenStreetMap, puis compare sa solution
            à celle calculée par une IA (Google OR-Tools + ILS).
          </p>
          <div className="grid-2" style={{ gap: 10 }}>
            {[
              { icon: "🗺️", title: "Campagne", desc: "8 missions progressives de Paris à Stockholm, météo, incidents, niveaux de difficulté." },
              { icon: "⚔️", title: "Versus", desc: "Même seed, même carte — duel entre deux joueurs, qui bat l'IA avec le meilleur score ?" },
              { icon: "🧮", title: "Solveur libre", desc: "N'importe quelle adresse mondiale, choix de zone, profil IA — solution optimale en quelques secondes." },
              { icon: "🔬", title: "Coulisses", desc: "Dijkstra animé, A* bidirectionnel, pipeline VRP, 2-opt, or-opt, ILS — tout est interactif." },
            ].map(({ icon, title, desc }) => (
              <div key={title} className="metric-card">
                <div style={{ fontSize: "1.6rem" }}>{icon}</div>
                <div style={{ fontWeight: 700 }}>{title}</div>
                <div className="metric-label" style={{ lineHeight: 1.5 }}>{desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ── FLUX DE DONNÉES ── */}
        <section className="panel stack">
          <strong>Flux de données — de l&apos;adresse à la tournée</strong>
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Chaque mission parcourt ce pipeline complet en quelques secondes.
            Les données ouvertes sont téléchargées à la demande, combinées, et transmises à OR-Tools.
          </p>
          <div style={{ overflowX: "auto" }}>
            <DataFlowDiagram />
          </div>
        </section>

        {/* ── SOURCES DE DONNÉES ── */}
        <section className="panel stack">
          <strong>Sources de données ouvertes</strong>
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Toutes les données géographiques sont issues de projets libres et réutilisables. Clique sur une source pour les détails.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {SOURCES.map((src) => (
              <div key={src.id} style={{ border: "1px solid var(--border)", borderRadius: 14, overflow: "hidden" }}>
                <button
                  onClick={() => setOpenSource(openSource === src.id ? null : src.id)}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", gap: 14,
                    padding: "14px 18px", background: "var(--panel)", border: "none",
                    cursor: "pointer", textAlign: "left",
                  }}
                >
                  <span style={{ fontSize: "1.4rem" }}>{src.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700 }}>{src.name}</div>
                    <div className="muted" style={{ fontSize: "0.8rem" }}>{src.role}</div>
                  </div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexShrink: 0 }}>
                    <span style={{
                      fontSize: "0.7rem", fontWeight: 700, color: src.typeColor,
                      background: `${src.typeColor}18`, borderRadius: 6, padding: "2px 8px",
                      border: `1px solid ${src.typeColor}40`,
                    }}>{src.type}</span>
                    <code style={{ fontSize: "0.72rem", color: "var(--muted)" }}>{src.lib}</code>
                    <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
                      {openSource === src.id ? "▲" : "▼"}
                    </span>
                  </div>
                </button>
                {openSource === src.id && (
                  <div style={{ padding: "0 18px 16px", background: "var(--panel)", display: "flex", flexDirection: "column", gap: 14 }}>
                    <p className="muted" style={{ margin: 0, lineHeight: 1.7 }}>{src.detail}</p>
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                      {src.stats.map((s) => (
                        <div key={s.label} style={{
                          background: "rgba(18,50,71,0.06)", borderRadius: 10, padding: "8px 14px",
                          display: "flex", flexDirection: "column", gap: 2,
                        }}>
                          <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>{s.label}</span>
                          <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{s.value}</span>
                        </div>
                      ))}
                      <div style={{
                        background: "rgba(18,50,71,0.06)", borderRadius: 10, padding: "8px 14px",
                        display: "flex", flexDirection: "column", gap: 2,
                      }}>
                        <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>Format</span>
                        <code style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--accent-2)" }}>{src.format}</code>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* ── PIPELINE DE TRAITEMENT ── */}
        <section className="panel stack">
          <strong>Pipeline de traitement — 11 étapes</strong>
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Clique sur chaque étape pour voir les détails algorithmiques, la bibliothèque utilisée et le fichier produit.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {PIPELINE.map((step, i) => (
              <PipelineStep key={step.n} step={step} idx={i} />
            ))}
          </div>
        </section>

        {/* ── FORMAT DES FICHIERS ── */}
        <section className="panel stack">
          <strong>Fichiers persistés par mission</strong>
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Chaque mission crée un répertoire isolé avec ces fichiers. Le backend les charge à la demande,
            sans base de données relationnelle — toute la persistance est fichier.
          </p>
          <div className="grid-2" style={{ gap: 10 }}>
            {[
              { file: "graph.graphml", desc: "Graphe OSM — nœuds, arcs, vitesses, géométries", color: "#1a6fb5" },
              { file: "livraisons.csv", desc: "Dépôt + clients : lat/lon, poids, fenêtre horaire, catégorie cargo", color: "#1f7a56" },
              { file: "time_matrix.npy", desc: "Matrice n×n de temps de trajet (secondes, float64)", color: "#9e2f3f" },
              { file: "dist_matrix.npy", desc: "Matrice n×n de distances en mètres (float64)", color: "#9e2f3f" },
              { file: "weather_status.json", desc: "Condition météo, facteur multiplicatif, description", color: "#b8892f" },
              { file: "resultats_finaux.json", desc: "Tournées OR-Tools : véhicules, routes, temps, poids", color: "#6b3fa0" },
              { file: "benchmark.json", desc: "Comparaison naïf vs. optimisé : temps, distance, CO₂, score", color: "#c45e00" },
              { file: "incidents.json", desc: "Segments bloqués — arc + pénalité de temps appliquée", color: "#9e2f3f" },
            ].map(({ file, desc, color }) => (
              <div key={file} style={{
                background: "rgba(18,50,71,0.04)", borderRadius: 12, padding: "12px 14px",
                border: `1px solid ${color}30`,
              }}>
                <code style={{ fontSize: "0.8rem", color, fontWeight: 700 }}>{file}</code>
                <div className="muted" style={{ fontSize: "0.78rem", marginTop: 4, lineHeight: 1.5 }}>{desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ── MODÈLE DE DONNÉES CLIENTS ── */}
        <section className="panel stack">
          <strong>Structure d&apos;un point de livraison</strong>
          <pre className="code-block">{`{
  "id": 3,
  "lat": 48.8566,          // coordonnées OSM exactes
  "lon": 2.3522,
  "nom_client": "Café de Flore",  // nom POI réel (Overpass)
  "poids_colis": 12,       // kg (5-50 × facteur catégorie)
  "cargo_code": "fragile", // normal | fragile | refrigere | gros
  "cargo_emoji": "🔮",
  "tw_start": 0,           // fenêtre horaire en secondes
  "tw_end": 3600           // 30% des clients ont contrainte forte
}`}</pre>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {[
              { code: "normal",    emoji: "📦", label: "Standard",   pct: "60%", factor: "×1.0" },
              { code: "fragile",   emoji: "🔮", label: "Fragile",    pct: "20%", factor: "×0.8" },
              { code: "refrigere", emoji: "🧊", label: "Réfrigéré",  pct: "10%", factor: "×1.0" },
              { code: "gros",      emoji: "🛋️", label: "Encombrant", pct: "10%", factor: "×1.5" },
            ].map(({ emoji, label, pct, factor }) => (
              <div key={label} style={{
                background: "rgba(18,50,71,0.05)", borderRadius: 10, padding: "8px 14px",
                display: "flex", flexDirection: "column", gap: 3, minWidth: 100,
              }}>
                <span style={{ fontSize: "1.3rem" }}>{emoji}</span>
                <span style={{ fontWeight: 700, fontSize: "0.85rem" }}>{label}</span>
                <span className="muted" style={{ fontSize: "0.72rem" }}>{pct} · poids {factor}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ── TRAFIC ── */}
        <section className="panel stack">
          <strong>Profil de congestion horaire</strong>
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Basé sur des données de mobilité urbaine. Un multiplicateur est appliqué à toute la matrice
            de temps selon l&apos;heure de départ choisie.
          </p>
          <TrafficChart />
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 4 }}>
            {[
              { label: "Heure de pointe max", value: "18h · ×1.8", color: "var(--accent)" },
              { label: "Heure creuse", value: "11h/15h · ×1.0", color: "#1f7a56" },
              { label: "Matin chargé", value: "8h · ×1.7", color: "#b8892f" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ background: "rgba(18,50,71,0.05)", borderRadius: 8, padding: "6px 12px" }}>
                <div className="muted" style={{ fontSize: "0.72rem" }}>{label}</div>
                <div style={{ fontWeight: 700, fontSize: "0.85rem", color }}>{value}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ── STACK TECHNIQUE ── */}
        <section className="panel stack">
          <strong>Stack technique</strong>
          <div className="grid-2" style={{ gap: 10 }}>
            {[
              { layer: "Données géo", libs: ["osmnx", "networkx", "shapely"], color: "#1a6fb5" },
              { layer: "Optimisation", libs: ["ortools (pywrapcp)", "numpy", "pandas"], color: "#c45e00" },
              { layer: "API backend", libs: ["FastAPI", "SQLite", "Pydantic"], color: "#1f7a56" },
              { layer: "Frontend", libs: ["Next.js 14", "react-leaflet", "TanStack Query"], color: "#6b3fa0" },
              { layer: "Météo / POI", libs: ["OpenWeatherMap API", "Overpass API"], color: "#b8892f" },
              { layer: "Routing", libs: ["OSRM (public)", "Mapbox Geocoding"], color: "#9e2f3f" },
            ].map(({ layer, libs, color }) => (
              <div key={layer} style={{
                background: "rgba(18,50,71,0.04)", borderRadius: 12, padding: "12px 14px",
                borderLeft: `3px solid ${color}`,
              }}>
                <div style={{ fontWeight: 700, fontSize: "0.85rem", marginBottom: 6 }}>{layer}</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {libs.map((l) => (
                    <code key={l} style={{ fontSize: "0.72rem", color, background: `${color}15`, padding: "1px 7px", borderRadius: 5 }}>{l}</code>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link className="primary-button" href="/solver">Lancer le solveur →</Link>
          <Link className="secondary-button" href="/explore">Voir les coulisses algorithmiques →</Link>
          <Link className="secondary-button" href="/">← Accueil</Link>
        </div>

      </div>
    </div>
  );
}
