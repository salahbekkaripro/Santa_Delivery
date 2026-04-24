"use client";

import type { VersusMapSource, VersusMissionConfig, VersusTemplate } from "@/lib/types";
import { SECONDARY_OBJECTIVE_PRESETS, WEATHER_OPTIONS } from "@/lib/versus";

function asNumber(value: string, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function asOptionalNumber(value: string) {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function VersusMapBuilder({
  mapSource,
  onMapSourceChange,
  templateId,
  onTemplateIdChange,
  templates,
  customConfig,
  onCustomConfigChange,
}: {
  mapSource: VersusMapSource;
  onMapSourceChange: (value: VersusMapSource) => void;
  templateId: string;
  onTemplateIdChange: (value: string) => void;
  templates: VersusTemplate[];
  customConfig: VersusMissionConfig;
  onCustomConfigChange: (value: VersusMissionConfig) => void;
}) {
  const selectedObjectiveCodes = new Set((customConfig.secondary_objectives ?? []).map((objective) => objective.code));

  function toggleObjective(code: string, label: string) {
    const current = customConfig.secondary_objectives ?? [];
    const exists = current.some((objective) => objective.code === code);
    const next = exists
      ? current.filter((objective) => objective.code !== code)
      : [...current, { code, label }];
    onCustomConfigChange({ ...customConfig, secondary_objectives: next });
  }

  return (
    <div className="stack">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          type="button"
          className={mapSource === "template" ? "primary-button" : "secondary-button"}
          onClick={() => onMapSourceChange("template")}
        >
          Template
        </button>
        <button
          type="button"
          className={mapSource === "custom" ? "primary-button" : "secondary-button"}
          onClick={() => onMapSourceChange("custom")}
        >
          Map custom
        </button>
      </div>

      {mapSource === "template" ? (
        <label className="field">
          <span>Template</span>
          <select value={templateId} onChange={(event) => onTemplateIdChange(event.target.value)}>
            {templates.map((template) => (
              <option key={template.template_id} value={template.template_id}>
                {template.label}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <div className="grid-2" style={{ gap: 10 }}>
          <label className="field">
            <span>Zone</span>
            <input
              value={customConfig.zone}
              onChange={(event) => onCustomConfigChange({ ...customConfig, zone: event.target.value })}
              placeholder="Le Marais, Paris"
            />
          </label>
          <label className="field">
            <span>Ville</span>
            <input
              value={customConfig.city ?? ""}
              onChange={(event) => onCustomConfigChange({ ...customConfig, city: event.target.value || null })}
              placeholder="Paris"
            />
          </label>

          <label className="field">
            <span>Latitude centre</span>
            <input
              type="number"
              step="0.000001"
              value={customConfig.center_lat ?? ""}
              onChange={(event) => onCustomConfigChange({ ...customConfig, center_lat: asOptionalNumber(event.target.value) })}
            />
          </label>
          <label className="field">
            <span>Longitude centre</span>
            <input
              type="number"
              step="0.000001"
              value={customConfig.center_lon ?? ""}
              onChange={(event) => onCustomConfigChange({ ...customConfig, center_lon: asOptionalNumber(event.target.value) })}
            />
          </label>

          <label className="field">
            <span>Rayon (km)</span>
            <input
              type="number"
              step="0.1"
              min={0.5}
              max={30}
              value={customConfig.search_radius_km ?? ""}
              onChange={(event) => onCustomConfigChange({ ...customConfig, search_radius_km: asOptionalNumber(event.target.value) })}
            />
          </label>
          <label className="field">
            <span>Colis (max 60)</span>
            <input
              type="number"
              min={1}
              max={60}
              value={customConfig.num_clients}
              onChange={(event) =>
                onCustomConfigChange({ ...customConfig, num_clients: Math.max(1, Math.min(60, Math.round(asNumber(event.target.value, 1)))) })
              }
            />
          </label>

          <label className="field">
            <span>Budget</span>
            <input
              type="number"
              min={0}
              value={customConfig.budget}
              onChange={(event) => onCustomConfigChange({ ...customConfig, budget: Math.max(0, Math.round(asNumber(event.target.value, 0))) })}
            />
          </label>
          <label className="field">
            <span>Coût traîneau</span>
            <input
              type="number"
              min={0}
              value={customConfig.sleigh_cost}
              onChange={(event) => onCustomConfigChange({ ...customConfig, sleigh_cost: Math.max(0, Math.round(asNumber(event.target.value, 0))) })}
            />
          </label>

          <label className="field">
            <span>Météo</span>
            <select
              value={customConfig.weather_key}
              onChange={(event) => onCustomConfigChange({ ...customConfig, weather_key: event.target.value })}
            >
              {WEATHER_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Profil IA</span>
            <input
              value={customConfig.ai_profile ?? ""}
              onChange={(event) => onCustomConfigChange({ ...customConfig, ai_profile: event.target.value || null })}
              placeholder="Express / Prudent / Championne"
            />
          </label>

          <label className="field" style={{ justifyContent: "space-between", flexDirection: "row", alignItems: "center" }}>
            <span>Incidents aléatoires</span>
            <input
              type="checkbox"
              checked={customConfig.random_incidents}
              onChange={(event) => onCustomConfigChange({ ...customConfig, random_incidents: event.target.checked })}
            />
          </label>
        </div>
      )}

      {mapSource === "custom" && (
        <div className="stack" style={{ gap: 6 }}>
          <span className="muted">Objectifs secondaires</span>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {SECONDARY_OBJECTIVE_PRESETS.map((objective) => (
              <button
                key={objective.code}
                type="button"
                className={selectedObjectiveCodes.has(objective.code) ? "primary-button" : "secondary-button"}
                onClick={() => toggleObjective(objective.code, objective.label)}
              >
                {objective.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
