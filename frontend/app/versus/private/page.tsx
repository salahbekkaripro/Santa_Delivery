"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { VersusMapBuilder } from "@/components/versus-map-builder";
import { usePlayer } from "@/components/player-provider";
import { createVersusMatch, getVersusTemplates, joinVersusMatch } from "@/lib/api";
import type { VersusMapSource, VersusMissionConfig, VersusWinnerRule } from "@/lib/types";
import { DEFAULT_CUSTOM_MISSION_CONFIG, WINNER_RULE_OPTIONS } from "@/lib/versus";

export default function VersusPrivatePage() {
  const router = useRouter();
  const { player, isReady } = usePlayer();

  const [mapSource, setMapSource] = useState<VersusMapSource>("template");
  const [templateId, setTemplateId] = useState("paris_duel");
  const [winnerRule, setWinnerRule] = useState<VersusWinnerRule>("score_time");
  const [customConfig, setCustomConfig] = useState<VersusMissionConfig>(DEFAULT_CUSTOM_MISSION_CONFIG);
  const [joinCode, setJoinCode] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const templatesQuery = useQuery({
    queryKey: ["versus-templates"],
    queryFn: getVersusTemplates,
  });

  const selectedRuleDescription = useMemo(
    () => WINNER_RULE_OPTIONS.find((option) => option.value === winnerRule)?.description,
    [winnerRule],
  );

  const createMutation = useMutation({
    mutationFn: () =>
      createVersusMatch({
        player_id: player!.id,
        mode: "private",
        map_source: mapSource,
        template_id: mapSource === "template" ? templateId : undefined,
        mission_config: mapSource === "custom" ? customConfig : undefined,
        winner_rule: winnerRule,
      }),
    onSuccess: (match) => {
      setError(null);
      setFeedback(`Partie créée. Code: ${match.join_code ?? "--"}`);
      router.push(`/versus/match/${match.match_id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const joinMutation = useMutation({
    mutationFn: () =>
      joinVersusMatch({
        player_id: player!.id,
        join_code: joinCode.trim().toUpperCase(),
      }),
    onSuccess: (match) => {
      setError(null);
      setFeedback("Partie rejointe.");
      router.push(`/versus/match/${match.match_id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  if (!isReady) {
    return <div className="page-shell"><div className="page-stack"><div className="panel">Chargement...</div></div></div>;
  }

  if (!player) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="panel stack">
            <span>Connexion requise pour le mode privé.</span>
            <Link className="primary-button" href="/login?redirect=%2Fversus%2Fprivate">Se connecter</Link>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Versus · Code privé</h1>
          <p>Étape 2/3: configure la partie (template ou map custom) puis crée ou rejoins une room.</p>
        </section>

        <section className="panel stack">
          <strong>Configuration host</strong>
          <VersusMapBuilder
            mapSource={mapSource}
            onMapSourceChange={setMapSource}
            templateId={templateId}
            onTemplateIdChange={setTemplateId}
            templates={templatesQuery.data?.templates ?? []}
            customConfig={customConfig}
            onCustomConfigChange={setCustomConfig}
          />

          <label className="field">
            <span>Règle de victoire</span>
            <select value={winnerRule} onChange={(event) => setWinnerRule(event.target.value as VersusWinnerRule)}>
              {WINNER_RULE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <span className="muted">{selectedRuleDescription}</span>

          <button className="primary-button" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            {createMutation.isPending ? "Création..." : "Créer la partie"}
          </button>
        </section>

        <section className="panel stack">
          <strong>Rejoindre une room</strong>
          <label className="field">
            <span>Code</span>
            <input
              type="text"
              value={joinCode}
              onChange={(event) => setJoinCode(event.target.value.toUpperCase())}
              placeholder="ABC123"
            />
          </label>
          <button
            className="secondary-button"
            onClick={() => joinMutation.mutate()}
            disabled={joinMutation.isPending || joinCode.trim().length < 4}
          >
            {joinMutation.isPending ? "Connexion..." : "Rejoindre"}
          </button>
        </section>

        {(feedback || error) && (
          <section className={error ? "error-box" : "panel"}>
            {error ?? feedback}
          </section>
        )}

        <section className="panel stack">
          <Link className="secondary-button" href="/versus">← Retour choix mode</Link>
        </section>
      </div>
    </div>
  );
}
