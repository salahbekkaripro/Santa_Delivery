"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { GuidedOnboarding, type GuidedOnboardingStep } from "@/components/guided-onboarding";
import { VersusMapBuilder, VersusMapBuilderHandle } from "@/components/versus-map-builder";
import { usePlayer } from "@/components/player-provider";
import { TeleprinterText } from "@/components/teleprinter-text";
import { createVersusMatch, getVersusTemplates, joinVersusMatch } from "@/lib/api";
import type { VersusMapSource, VersusMissionConfig, VersusWinnerRule } from "@/lib/types";
import { DEFAULT_CUSTOM_MISSION_CONFIG, WINNER_RULE_OPTIONS } from "@/lib/versus";

const PRIVATE_ONBOARDING_STEPS: GuidedOnboardingStep[] = [
  {
    targetId: "private-overview",
    title: "Configurer un duel privé",
    description: "Ici tu prépares un match en code privé puis tu invites l'adversaire à rejoindre.",
  },
  {
    targetId: "private-config",
    title: "Choisis template ou map custom",
    description: "Template pour aller vite, custom pour une démo guidée avec zone/météo/rayon/colis.",
  },
  {
    targetId: "private-rule",
    title: "Définis la règle de victoire",
    description: "Le gagnant est calculé selon cette règle commune pour les deux joueurs.",
  },
  {
    targetId: "private-create",
    title: "Crée la room",
    description: "Après création, partage le code puis passe au lobby live pour valider les statuts Ready.",
  },
  {
    targetId: "private-join",
    title: "Ou rejoins un code existant",
    description: "Si tu as déjà reçu un code, colle-le ici pour entrer directement dans le match.",
  },
];

export default function VersusPrivatePage() {
  const router = useRouter();
  const { player, isReady } = usePlayer();

  const [mapSource, setMapSource] = useState<VersusMapSource>("template");
  const [templateId, setTemplateId] = useState("paris_duel");
  const [winnerRule, setWinnerRule] = useState<VersusWinnerRule>("score_time");
  const [customConfig, setCustomConfig] = useState<VersusMissionConfig>(DEFAULT_CUSTOM_MISSION_CONFIG);
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [customCreateGate, setCustomCreateGate] = useState({
    isAddressLoading: false,
    isAddressEmpty: false,
    exceedsClientsLimit: false,
    canCreate: true,
  });
  const mapBuilderRef = useRef<VersusMapBuilderHandle>(null);

  const templatesQuery = useQuery({
    queryKey: ["versus-templates"],
    queryFn: getVersusTemplates,
  });

  const selectedRuleDescription = useMemo(
    () => WINNER_RULE_OPTIONS.find((option) => option.value === winnerRule)?.description,
    [winnerRule],
  );

  const createMutation = useMutation({
    mutationFn: async () => {
      const missionConfig =
        mapSource === "custom"
          ? await mapBuilderRef.current?.resolveCustomMissionConfigForSubmit()
          : undefined;
      if (mapSource === "custom" && !missionConfig) {
        throw new Error("Impossible de préparer la carte custom pour cette partie.");
      }
      return createVersusMatch({
        player_id: player!.id,
        mode: "private",
        map_source: mapSource,
        template_id: mapSource === "template" ? templateId : undefined,
        mission_config: mapSource === "custom" ? (missionConfig ?? undefined) : undefined,
        winner_rule: winnerRule,
      });
    },
    onSuccess: (match) => {
      setError(null);
      if (match.join_code) {
        navigator.clipboard.writeText(match.join_code).catch(() => {});
      }
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
      router.push(`/versus/match/${match.match_id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const isCreateDisabled =
    createMutation.isPending || (mapSource === "custom" && !customCreateGate.canCreate);

  if (!isReady) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="panel-loading" style={{ height: 110 }} />
          <div className="panel-loading" style={{ height: 200 }} />
          <div className="panel-loading" style={{ height: 120 }} />
        </div>
      </div>
    );
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
        <section className="hero" data-onboarding-id="private-overview">
          <h1>Versus · Code privé</h1>
          <TeleprinterText text="Étape 2/3: configure la partie (template ou map custom) puis crée ou rejoins une room." />
        </section>

        <section className="panel stack" data-onboarding-id="private-config">
          <strong>Configuration host</strong>
          <VersusMapBuilder
            ref={mapBuilderRef}
            mapSource={mapSource}
            onMapSourceChange={setMapSource}
            templateId={templateId}
            onTemplateIdChange={setTemplateId}
            templates={templatesQuery.data?.templates ?? []}
            customConfig={customConfig}
            onCustomConfigChange={setCustomConfig}
            onCustomGateStateChange={setCustomCreateGate}
          />

          <label className="field" data-onboarding-id="private-rule">
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

          <button
            className="primary-button"
            onClick={() => createMutation.mutate()}
            disabled={isCreateDisabled}
            data-onboarding-id="private-create"
          >
            {createMutation.isPending ? "Création..." : "Créer la partie"}
          </button>
          {mapSource === "custom" && customCreateGate.isAddressEmpty && (
            <span className="muted">Renseigne une adresse pour créer la partie custom.</span>
          )}
          {mapSource === "custom" && customCreateGate.isAddressLoading && (
            <span className="muted">Géocodage en cours... patiente avant de créer.</span>
          )}
        </section>

        <section className="panel stack" data-onboarding-id="private-join">
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

        {error && (
          <section className="error-box">{error}</section>
        )}

        <section className="panel stack">
          <Link className="secondary-button" href="/versus">← Retour choix mode</Link>
        </section>

        <GuidedOnboarding
          storageKey="operation-noel-onboarding-versus-private-v1"
          tutorialLabel="Versus privé"
          steps={PRIVATE_ONBOARDING_STEPS}
        />
      </div>
    </div>
  );
}
