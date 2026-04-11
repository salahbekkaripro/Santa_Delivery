"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createMission } from "@/lib/api";

const campaigns = [
  {
    level: 1,
    title: "Paris · Le Marais",
    zone: "Le Marais, Paris",
    weather_key: "Clear",
    num_clients: 10,
    budget: 1500,
    sleigh_cost: 500,
    random_incidents: false
  },
  {
    level: 2,
    title: "Berlin · Mitte",
    zone: "Mitte, Berlin",
    weather_key: "Rain",
    num_clients: 30,
    budget: 2500,
    sleigh_cost: 600,
    random_incidents: false
  },
  {
    level: 3,
    title: "Montreal · Plateau",
    zone: "Le Plateau-Mont-Royal, Montréal, Québec, Canada",
    weather_key: "Snow",
    num_clients: 50,
    budget: 4000,
    sleigh_cost: 800,
    random_incidents: true
  }
];

export function MissionCreator() {
  const router = useRouter();
  const [sandbox, setSandbox] = useState({
    zone: "Bordeaux",
    num_clients: 30,
    budget: 3000,
    sleigh_cost: 500,
    weather_key: "real",
    random_incidents: false
  });

  const createMutation = useMutation({
    mutationFn: createMission,
    onSuccess: (data) => {
      router.push(`/mission/${data.mission_id}`);
    }
  });

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h1>Operation Noel</h1>
              <p>Frontend Next.js + API FastAPI pour remplacer progressivement Streamlit sans toucher au moteur Python.</p>
            </div>
            <Link href="/leaderboard" className="secondary-button" style={{ background: "rgba(255,255,255,0.2)", color: "white", boxShadow: "none" }}>
              🏆 Panthéon
            </Link>
          </div>
        </section>

        {createMutation.error ? (
          <div className="error-box">{createMutation.error instanceof Error ? createMutation.error.message : "Creation impossible"}</div>
        ) : null}

        <section className="grid-3">
          {campaigns.map((campaign) => (
            <button
              key={campaign.level}
              className="panel card-button stack"
              onClick={() =>
                createMutation.mutate({
                  zone: campaign.zone,
                  num_clients: campaign.num_clients,
                  budget: campaign.budget,
                  sleigh_cost: campaign.sleigh_cost,
                  weather_key: campaign.weather_key,
                  random_incidents: campaign.random_incidents,
                  level: campaign.level
                })
              }
            >
              <strong>Niveau {campaign.level}</strong>
              <span>{campaign.title}</span>
              <span className="muted">
                {campaign.num_clients} livraisons · budget {campaign.budget} € · meteo {campaign.weather_key}
              </span>
            </button>
          ))}
        </section>

        <section className="panel stack">
          <strong>Partie libre</strong>
          <div className="grid-2">
            <label className="field">
              <span>Zone</span>
              <input
                value={sandbox.zone}
                onChange={(event) => setSandbox((prev) => ({ ...prev, zone: event.target.value }))}
                placeholder="Quartier, ville, pays"
              />
            </label>
            <label className="field">
              <span>Meteo</span>
              <select
                value={sandbox.weather_key}
                onChange={(event) => setSandbox((prev) => ({ ...prev, weather_key: event.target.value }))}
              >
                <option value="real">🌍 Temps Réel (Open-Meteo)</option>
                <option value="random">Aleatoire</option>
                <option value="Clear">Soleil</option>
                <option value="Rain">Pluie</option>
                <option value="Snow">Neige</option>
                <option value="Thunderstorm">Tempete</option>
              </select>
            </label>
            <label className="field">
              <span>Nombre de clients</span>
              <input
                type="number"
                value={sandbox.num_clients}
                onChange={(event) => setSandbox((prev) => ({ ...prev, num_clients: Number(event.target.value) }))}
              />
            </label>
            <label className="field">
              <span>Budget</span>
              <input
                type="number"
                value={sandbox.budget}
                onChange={(event) => setSandbox((prev) => ({ ...prev, budget: Number(event.target.value) }))}
              />
            </label>
          </div>
          <label className="tag" style={{ width: "fit-content" }}>
            <input
              type="checkbox"
              checked={sandbox.random_incidents}
              onChange={(event) => setSandbox((prev) => ({ ...prev, random_incidents: event.target.checked }))}
            />
            Incidents aleatoires
          </label>
          <button className="primary-button" onClick={() => createMutation.mutate({ ...sandbox, level: null })}>
            {createMutation.isPending ? "Creation..." : "Creer la mission"}
          </button>
        </section>
      </div>
    </div>
  );
}
