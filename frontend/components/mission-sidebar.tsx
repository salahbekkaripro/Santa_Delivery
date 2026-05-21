"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import type { AiLearningEvaluationResponse, AiLearningRecommendation, MissionResponse, RouteOption, RouteSegment } from "@/lib/types";

function cargoConstraintLabel(constraint: string | null | undefined): string | null {
  if (!constraint || constraint === "null") return null;
  if (constraint === "slow") return "⚠️ Fragile — conduite lente";
  if (constraint === "time_window_strict") return "⏰ Réfrigéré — livraison urgente";
  if (constraint === "capacity") return "🏋️ Encombrant — capacité réduite";
  return null;
}

function metricTime(seconds: number | undefined) {
  const minutes = Math.round((seconds ?? 0) / 60);
  return `${minutes} min`;
}

function optionBadgeStyle(badge: string): CSSProperties {
  if (badge === "Sûr") {
    return {
      background: "rgba(31, 143, 95, 0.14)",
      color: "var(--success)",
      border: "1px solid rgba(31, 143, 95, 0.22)",
    };
  }
  if (
    badge.startsWith("Surcharge")
    || badge.startsWith("Retard")
    || badge === "Déjà assigné"
    || badge === "Axe incident"
  ) {
    return {
      background: "rgba(158, 47, 63, 0.12)",
      color: "#69222d",
      border: "1px solid rgba(158, 47, 63, 0.22)",
    };
  }
  return {
    background: "rgba(217, 119, 6, 0.12)",
    color: "var(--warning)",
    border: "1px solid rgba(217, 119, 6, 0.24)",
  };
}

function optionFeasibilityClass(option: RouteOption): string {
  if (option.is_feasible === false) return "is-infeasible";
  const badges = option.feasibility_badges ?? ["Sûr"];
  if (badges.every((b) => b === "Sûr")) return "is-feasible-good";
  return "is-warning-opt";
}

function splitStrategyLabel(strategy?: string): string {
  if (!strategy) return "N/A";
  if (strategy === "stratified_by_context_profile") return "Stratifié contexte+profil";
  if (strategy === "stratified_by_context") return "Stratifié contexte";
  return strategy;
}

type AiPreview = {
  accentClass: string;
  label: string;
  signature: string;
  difficultyBonus: number;
  description: string;
  optimizationTarget: "time" | "distance" | "composite";
};

type MissionSidebarProps = {
  missionId: string;
  mission: MissionResponse;
  numVehicles: number;
  limitMaxVehicles: boolean;
  maxVehicles: number;
  maxVehiclesLocked?: boolean;
  vehicleCapacity: number;
  speedMultiplier: number;
  activeSleigh: number;
  versusLocked: boolean;
  aiProfileLocked: boolean;
  aiProfilePreview: AiPreview;
  optimizationTarget: "time" | "distance" | "composite";
  secondaryObjectives: Array<{ code: string; label: string }>;
  isFreeRouting: boolean;
  showFeasibleOnly: boolean;
  suggestPending: boolean;
  suggestions: Array<{ client_id: number; nom_client: string; arrival_clock: string; is_feasible: boolean }>;
  activeRoute: number[];
  activeSegments: RouteSegment[];
  routeError: string | null;
  selectedClientId: number | null;
  isRouteOptionsDebouncing: boolean;
  optionsPending: boolean;
  routeOptions: RouteOption[];
  displayedRouteOptions: RouteOption[];
  selectedOptionIndex: number;
  useLearnedAi: boolean;
  learningInfo: string | null;
  learningEvaluation: AiLearningEvaluationResponse | null;
  learningRecommendation: AiLearningRecommendation | null;
  clearPending: boolean;
  resetPending: boolean;
  trainPending: boolean;
  recommendationPending: boolean;
  evaluatePending: boolean;
  solvePending: boolean;
  resultsAvailable: boolean;
  onNumVehiclesChange: (value: number) => void;
  onLimitMaxVehiclesChange: (value: boolean) => void;
  onMaxVehiclesChange: (value: number) => void;
  onVehicleCapacityChange: (value: number) => void;
  onSpeedMultiplierChange: (value: number) => void;
  onActiveSleighChange: (value: number) => void;
  onOptimizationTargetChange: (value: "time" | "distance" | "composite") => void;
  onToggleFreeRouting: () => void;
  onToggleShowFeasibleOnly: () => void;
  onSuggest: () => void;
  onSelectSuggestion: (clientId: number) => void;
  onClearSuggestions: () => void;
  onSelectOption: (index: number) => void;
  onCancelClientChoice: () => void;
  onClearSleigh: () => void;
  onResetAll: () => void;
  onUseLearnedAiChange: (value: boolean) => void;
  onTrainModel: () => void;
  onRecommendProfile: () => void;
  onEvaluateModel: () => void;
  onSolve: () => void;
};

export function MissionSidebar(props: MissionSidebarProps) {
  const {
    missionId,
    mission,
    numVehicles,
    limitMaxVehicles,
    maxVehicles,
    maxVehiclesLocked = false,
    vehicleCapacity,
    speedMultiplier,
    activeSleigh,
    versusLocked,
    aiProfileLocked,
    aiProfilePreview,
    optimizationTarget,
    secondaryObjectives,
    isFreeRouting,
    showFeasibleOnly,
    suggestPending,
    suggestions,
    activeRoute,
    activeSegments,
    routeError,
    selectedClientId,
    isRouteOptionsDebouncing,
    optionsPending,
    routeOptions,
    displayedRouteOptions,
    selectedOptionIndex,
    useLearnedAi,
    learningInfo,
    learningEvaluation,
    learningRecommendation,
    clearPending,
    resetPending,
    trainPending,
    recommendationPending,
    evaluatePending,
    solvePending,
    resultsAvailable,
    onNumVehiclesChange,
    onLimitMaxVehiclesChange,
    onMaxVehiclesChange,
    onVehicleCapacityChange,
    onSpeedMultiplierChange,
    onActiveSleighChange,
    onOptimizationTargetChange,
    onToggleFreeRouting,
    onToggleShowFeasibleOnly,
    onSuggest,
    onSelectSuggestion,
    onClearSuggestions,
    onSelectOption,
    onCancelClientChoice,
    onClearSleigh,
    onResetAll,
    onUseLearnedAiChange,
    onTrainModel,
    onRecommendProfile,
    onEvaluateModel,
    onSolve,
  } = props;

  return (
    <aside className="panel stack">
      <div>
        <span className="sidebar-section-title">Configuration</span>
      </div>
      <label className="field">
        <span>Traîneaux</span>
        <input type="number" min={1} max={10} value={numVehicles} onChange={(e) => onNumVehiclesChange(Number(e.target.value))} />
      </label>
      <label className="field">
        <span>Cap max solveur</span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label className={`tag ${limitMaxVehicles ? "is-selected" : ""}`} style={{ cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={limitMaxVehicles}
              onChange={(e) => onLimitMaxVehiclesChange(e.target.checked)}
              disabled={versusLocked || maxVehiclesLocked}
            />
            &nbsp;Limiter
          </label>
          <input
            type="number"
            min={1}
            max={20}
            value={maxVehicles}
            onChange={(e) => onMaxVehiclesChange(Number(e.target.value))}
            disabled={!limitMaxVehicles || versusLocked || maxVehiclesLocked}
            style={{ maxWidth: 110 }}
          />
        </div>
        <span className="muted" style={{ fontSize: "0.78rem" }}>
          {maxVehiclesLocked
            ? "Cap imposé par la configuration du duel custom."
            : "Limite le nombre de traîneaux autorisés pour l&apos;IA pendant la résolution."}
        </span>
      </label>
      <label className="field">
        <span>Capacité (kg)</span>
        <input type="number" min={50} max={500} value={vehicleCapacity} onChange={(e) => onVehicleCapacityChange(Number(e.target.value))} />
      </label>
      <label className="field">
        <span>Vitesse</span>
        <select value={speedMultiplier} onChange={(e) => onSpeedMultiplierChange(Number(e.target.value))}>
          <option value={0.7}>🐢 Prudent</option>
          <option value={1}>🚗 Normal</option>
          <option value={1.5}>🚀 Turbo</option>
        </select>
      </label>

      <div className="field">
        <span>Traîneau actif</span>
        <div className="sleigh-tab-group">
          {Array.from({ length: numVehicles }, (_, i) => (
            <button
              key={i}
              className={`sleigh-tab ${activeSleigh === i ? "is-active" : ""}`}
              onClick={() => onActiveSleighChange(i)}
              disabled={versusLocked}
            >
              🎅 #{i + 1}
            </button>
          ))}
        </div>
      </div>

      <label className="field">
        <span>Objectif IA</span>
        <select
          value={aiProfileLocked ? aiProfilePreview.optimizationTarget : optimizationTarget}
          disabled={aiProfileLocked}
          onChange={(e) => onOptimizationTargetChange(e.target.value as "time" | "distance" | "composite")}
        >
          <option value="time">⚡ Express (Temps)</option>
          <option value="distance">🌱 Écolo (Distance)</option>
          <option value="composite">🧠 Composite (Temps+Distance+CO₂+Risque)</option>
        </select>
      </label>

      <div className={`sidebar-section ai-profile-card ${aiProfilePreview.accentClass}`}>
        <span className="sidebar-section-title">Profil IA</span>
        <div className="ai-profile-head">
          <div>
            <strong>IA {aiProfilePreview.label}</strong>
            <span className="muted">{aiProfilePreview.signature}</span>
          </div>
          <span className="tag">+{aiProfilePreview.difficultyBonus} score</span>
        </div>
        <p className="muted">{aiProfilePreview.description}</p>
        <div className="ai-profile-meta">
          <span>
            Cible : {
              aiProfilePreview.optimizationTarget === "time"
                ? "temps"
                : aiProfilePreview.optimizationTarget === "distance"
                  ? "distance"
                  : "composite"
            }
          </span>
          <span className="muted">{aiProfileLocked ? "Verrouillé" : "Libre"}</span>
        </div>
      </div>

      {secondaryObjectives.length > 0 && (
        <div className="sidebar-section">
          <span className="sidebar-section-title">Objectifs secondaires</span>
          <div className="objective-list">
            {secondaryObjectives.map((obj) => (
              <div key={`${obj.code}-${obj.label}`} className="objective-chip">
                <span className="objective-dot" />
                <span>{obj.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="sidebar-section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span className="sidebar-section-title">Mode de sélection</span>
          <button
            className={`tag ${isFreeRouting ? "is-selected" : ""}`}
            style={{ cursor: "pointer", background: isFreeRouting ? "var(--accent)" : "rgba(0,0,0,0.05)", color: isFreeRouting ? "white" : "var(--text)" }}
            onClick={onToggleFreeRouting}
            disabled={versusLocked}
          >
            {isFreeRouting ? "🗺️ Tracé Libre" : "📍 Sélection"}
          </button>
        </div>
        <span className="muted" style={{ fontSize: "0.83rem" }}>
          {isFreeRouting
            ? "Clique n'importe où sur la carte pour tracer ta route segment par segment."
            : "Clique un client sur la carte pour voir les options de chemins."}
        </span>
        {!isFreeRouting && (
          <button
            className={`tag ${showFeasibleOnly ? "is-selected" : ""}`}
            style={{
              cursor: "pointer",
              width: "fit-content",
              background: showFeasibleOnly ? "rgba(31, 143, 95, 0.16)" : "rgba(23, 50, 77, 0.08)",
              color: showFeasibleOnly ? "var(--success)" : "var(--accent-2)",
              border: showFeasibleOnly ? "1px solid rgba(31, 143, 95, 0.32)" : "1px solid var(--border)",
            }}
            onClick={onToggleShowFeasibleOnly}
            disabled={versusLocked}
          >
            {showFeasibleOnly ? "Faisables uniquement: ON" : "Faisables uniquement: OFF"}
          </button>
        )}
        <button className="secondary-button" onClick={onSuggest} disabled={suggestPending || versusLocked}>
          {suggestPending ? "Calcul..." : "💡 Suggérer le prochain stop"}
        </button>
        {suggestions.length > 0 && (
          <div className="stack" style={{ gap: "6px" }}>
            {suggestions.map((s) => {
              const clientData = mission.clients.find((c) => c.id === s.client_id);
              const emoji = clientData?.cargo_emoji ?? "📦";
              const constraint = cargoConstraintLabel(clientData?.cargo_constraint);
              return (
                <button
                  key={s.client_id}
                  className={`tag ${!s.is_feasible ? "error-box" : ""}`}
                  style={{ cursor: "pointer", border: "1px solid var(--border)", width: "100%", justifyContent: "space-between", flexDirection: "column", alignItems: "flex-start", gap: 2 }}
                  onClick={() => onSelectSuggestion(s.client_id)}
                  disabled={!s.is_feasible || versusLocked}
                >
                  <span style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                    <span>{emoji} {s.nom_client}</span>
                    <span className="muted">{s.arrival_clock}</span>
                  </span>
                  {constraint && <span style={{ fontSize: "0.75rem", opacity: 0.75 }}>{constraint}</span>}
                </button>
              );
            })}
            <button className="secondary-button" style={{ fontSize: "0.78rem", padding: "6px" }} onClick={onClearSuggestions}>
              Effacer suggestions
            </button>
          </div>
        )}
      </div>

      <div className="sidebar-section">
        <span className="sidebar-section-title">Route courante — Traîneau #{activeSleigh + 1}</span>
        <span className="muted" style={{ fontSize: "0.83rem", lineHeight: 1.5 }}>
          {activeRoute.length > 0
            ? activeRoute.map((id) => mission.clients.find((c) => c.id === id)?.nom_client ?? `#${id}`).join(" → ")
            : "Aucun stop sur ce traîneau"}
        </span>
        {activeSegments.length > 0 && (
          <div className="stack" style={{ gap: "6px" }}>
            {activeSegments.map((seg) => {
              const client = mission.clients.find((c) => c.id === seg.to_id);
              if (!client) return null;
              const emoji = client.cargo_emoji ?? "📦";
              return (
                <span key={`${seg.from_id}-${seg.to_id}`} className="muted" style={{ fontSize: "0.82rem" }}>
                  Stop {seg.segment_idx} · {emoji} {client.nom_client} · {seg.arrival_clock ?? "--:--"} · {metricTime(seg.arrival_eta_s)}
                </span>
              );
            })}
          </div>
        )}
      </div>

      {routeError && <div className="error-box">{routeError}</div>}

      {selectedClientId ? (
        <div className="sidebar-section">
          {(() => {
            const sc = mission.clients.find((c) => c.id === selectedClientId);
            const constraintLabel = cargoConstraintLabel(sc?.cargo_constraint);
            return (
              <>
                <span className="sidebar-section-title">
                  {sc?.cargo_emoji ?? "📦"} {sc?.nom_client ?? `Client #${selectedClientId}`}
                </span>
                <span className="muted" style={{ fontSize: "0.8rem" }}>
                  {sc?.cargo_label ?? "Colis standard"} · {sc?.poids_colis ?? 0} kg
                </span>
                {constraintLabel && (
                  <span className="tag" style={{ fontSize: "0.78rem", color: "var(--danger, #c0392b)", background: "rgba(192,57,43,0.08)", border: "1px solid rgba(192,57,43,0.2)" }}>
                    {constraintLabel}
                  </span>
                )}
              </>
            );
          })()}
          {(isRouteOptionsDebouncing || optionsPending) && (
            <span className="muted" style={{ fontSize: "0.83rem" }}>
              {isRouteOptionsDebouncing ? "Recalcul…" : "Calcul des options…"}
            </span>
          )}
          {showFeasibleOnly && routeOptions.length > 0 && displayedRouteOptions.length === 0 && (
            <div className="error-box">Aucune option faisable pour ce client avec les paramètres actuels.</div>
          )}
          {displayedRouteOptions.map((option, index) => (
            <button
              key={`${option.route_nodes.join("-")}-${index}`}
              className={`option-card ${selectedOptionIndex === index ? "is-selected" : ""} ${optionFeasibilityClass(option)}`}
              onClick={() => onSelectOption(index)}
            >
              <strong>{option.label}</strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
                {(option.feasibility_badges ?? ["Sûr"]).map((badge) => (
                  <span key={`${option.label}-${badge}`} className="tag" style={optionBadgeStyle(badge)}>
                    {badge}
                  </span>
                ))}
              </div>
              <div className="muted" style={{ fontSize: "0.82rem", marginTop: 6 }}>
                {option.route_nodes.length} nœuds · Arrivée {option.projected_arrival_clock ?? "--:--"} · {Number(option.projected_load_kg ?? 0).toFixed(0)} kg
              </div>
              {Number(option.projected_overload_kg ?? 0) > 0 && (
                <div style={{ color: "#69222d", fontSize: "0.82rem" }}>
                  Dépassement : +{Number(option.projected_overload_kg ?? 0).toFixed(0)} kg
                </div>
              )}
            </button>
          ))}
          {displayedRouteOptions.length > 0 && (
            <>
              <span className="muted" style={{ fontSize: "0.82rem" }}>
                Clique directement le tracé sur la carte pour confirmer.
              </span>
              <button className="secondary-button" onClick={onCancelClientChoice}>
                Annuler ce choix
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="sidebar-section">
          <span className="muted" style={{ fontSize: "0.83rem" }}>Aucun client sélectionné — clique un client sur la carte.</span>
        </div>
      )}

      <div className="sidebar-section">
        <span className="sidebar-section-title">Actions</span>
        <button className="secondary-button" onClick={onClearSleigh} disabled={clearPending || versusLocked}>
          {clearPending ? "Vidage…" : "🗑 Vider ce traîneau"}
        </button>
        <button className="secondary-button" onClick={onResetAll} disabled={resetPending || versusLocked}>
          {resetPending ? "Reset…" : "↺ Réinitialiser tout"}
        </button>
      </div>

      <div className="solve-zone solve-zone--prominent">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
          <div>
            <strong style={{ color: "var(--accent-2)" }}>Lancer l&apos;IA</strong>
            <p className="muted" style={{ fontSize: "0.8rem", margin: "4px 0 0" }}>
              {aiProfileLocked
                ? `Profil ${aiProfilePreview.label} imposé · ${aiProfilePreview.signature}`
                : optimizationTarget === "time"
                  ? "L'IA cherchera à finir le plus vite possible."
                  : optimizationTarget === "distance"
                    ? "L'IA parcourra le moins de km possible."
                    : "L'IA arbitre en multi-objectif (temps, distance, CO₂, risque)."}
            </p>
          </div>
          <span className="tag">+{aiProfilePreview.difficultyBonus}</span>
        </div>
        <label
          className="tag"
          style={{
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            width: "fit-content",
            border: "1px solid var(--border)",
            background: useLearnedAi ? "rgba(23, 50, 77, 0.10)" : "rgba(0, 0, 0, 0.04)",
          }}
        >
          <input
            type="checkbox"
            checked={useLearnedAi}
            onChange={(event) => onUseLearnedAiChange(event.target.checked)}
            style={{ accentColor: "var(--accent-2)" }}
            disabled={versusLocked}
          />
          IA apprenante (profil auto)
        </label>
        {useLearnedAi && (
          <div className="stack" style={{ gap: 8 }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className="secondary-button" onClick={onTrainModel} disabled={trainPending || versusLocked}>
                {trainPending ? "Entraînement..." : "🧠 Entraîner le modèle"}
              </button>
              <button className="secondary-button" onClick={onRecommendProfile} disabled={recommendationPending || versusLocked}>
                {recommendationPending ? "Calcul..." : "📊 Recommander un profil"}
              </button>
              <button className="secondary-button" onClick={onEvaluateModel} disabled={evaluatePending || versusLocked}>
                {evaluatePending ? "Évaluation..." : "🧪 Évaluer le modèle"}
              </button>
            </div>
            {learningInfo && (
              <span className="muted" style={{ fontSize: "0.8rem" }}>
                {learningInfo}
              </span>
            )}
            {learningEvaluation && (
              <>
                <span className="muted" style={{ fontSize: "0.8rem" }}>
                  Split: {splitStrategyLabel(learningEvaluation.split_strategy)} · Holdout: {learningEvaluation.sample_count_holdout} · Match sample: {(learningEvaluation.sample_match_rate * 100).toFixed(0)}%
                </span>
                <span className="muted" style={{ fontSize: "0.8rem" }}>
                  Top-1 contexte: {(learningEvaluation.context_top1_accuracy * 100).toFixed(0)}% · Regret: {learningEvaluation.avg_context_regret.toFixed(1)}
                </span>
              </>
            )}
            {learningRecommendation && (
              <span className="muted" style={{ fontSize: "0.8rem" }}>
                Top 3: {learningRecommendation.top_candidates.map((candidate) => candidate.label).join(" · ")}
              </span>
            )}
          </div>
        )}
        <button className="primary-button" onClick={onSolve} disabled={solvePending || versusLocked}>
          {solvePending
            ? "Optimisation en cours…"
            : useLearnedAi
              ? "🤖 Lancer IA apprenante"
              : "🤖 Lancer la solution IA"}
        </button>
        {resultsAvailable && (
          <Link className="secondary-button" href={`/mission/${missionId}/results`}>
            Voir les derniers résultats
          </Link>
        )}
      </div>
    </aside>
  );
}
