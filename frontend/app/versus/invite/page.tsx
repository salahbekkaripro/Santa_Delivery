"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { VersusMapBuilder, VersusMapBuilderHandle } from "@/components/versus-map-builder";
import { usePlayer } from "@/components/player-provider";
import {
  acceptVersusInvite,
  createVersusInvite,
  declineVersusInvite,
  getVersusInvites,
  getVersusTemplates,
} from "@/lib/api";
import type { VersusInvite, VersusMapSource, VersusMissionConfig, VersusWinnerRule } from "@/lib/types";
import { DEFAULT_CUSTOM_MISSION_CONFIG, WINNER_RULE_OPTIONS, formatMissionSummary, ruleLabel } from "@/lib/versus";

function InviteMapPreview({ invite }: { invite: VersusInvite }) {
  const summary = invite.mission_summary;
  return (
    <div className="stack" style={{ gap: 4 }}>
      <div className="lb-zone">{formatMissionSummary(summary)}</div>
      <div className="muted">
        Source: {invite.map_source === "custom" ? "Custom" : "Template"}
        {typeof summary?.num_clients === "number" ? ` · ${summary.num_clients} colis` : ""}
        {typeof summary?.budget === "number" ? ` · Budget ${summary.budget}` : ""}
        {typeof summary?.sleigh_cost === "number" ? ` · Coût ${summary.sleigh_cost}` : ""}
        {typeof summary?.search_radius_km === "number" ? ` · Rayon ${summary.search_radius_km}km` : ""}
      </div>
      <div className="muted">
        Météo: {summary?.weather_key ?? "--"}
        {summary?.random_incidents ? " · Incidents actifs" : " · Sans incidents"}
        {summary?.ai_profile ? ` · IA ${summary.ai_profile}` : ""}
      </div>
    </div>
  );
}

export default function VersusInvitePage() {
  const router = useRouter();
  const { player, isReady } = usePlayer();

  const [inviteePlayerId, setInviteePlayerId] = useState("");
  const [mapSource, setMapSource] = useState<VersusMapSource>("template");
  const [templateId, setTemplateId] = useState("paris_duel");
  const [winnerRule, setWinnerRule] = useState<VersusWinnerRule>("score_time");
  const [customConfig, setCustomConfig] = useState<VersusMissionConfig>(DEFAULT_CUSTOM_MISSION_CONFIG);
  const [feedback, setFeedback] = useState<string | null>(null);
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

  const invitesQuery = useQuery({
    queryKey: ["versus-invites", player?.id],
    queryFn: () => getVersusInvites(player!.id),
    enabled: Boolean(player?.id),
    refetchInterval: 3000,
  });

  const createInviteMutation = useMutation({
    mutationFn: async () => {
      const missionConfig =
        mapSource === "custom"
          ? await mapBuilderRef.current?.resolveCustomMissionConfigForSubmit()
          : undefined;
      if (mapSource === "custom" && !missionConfig) {
        throw new Error("Impossible de préparer la carte custom pour cette invitation.");
      }
      return createVersusInvite({
        player_id: player!.id,
        invitee_player_id: inviteePlayerId.trim(),
        map_source: mapSource,
        template_id: mapSource === "template" ? templateId : undefined,
        mission_config: mapSource === "custom" ? (missionConfig ?? undefined) : undefined,
        winner_rule: winnerRule,
      });
    },
    onSuccess: () => {
      setError(null);
      setFeedback("Invitation envoyée.");
      setInviteePlayerId("");
      invitesQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const acceptInviteMutation = useMutation({
    mutationFn: (inviteId: string) => acceptVersusInvite(inviteId, { player_id: player!.id }),
    onSuccess: ({ match }) => {
      setError(null);
      setFeedback("Invitation acceptée.");
      invitesQuery.refetch();
      router.push(`/versus/match/${match.match_id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  const declineInviteMutation = useMutation({
    mutationFn: (inviteId: string) => declineVersusInvite(inviteId, { player_id: player!.id }),
    onSuccess: () => {
      setError(null);
      setFeedback("Invitation refusée.");
      invitesQuery.refetch();
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
            <span>Connexion requise pour les invitations.</span>
            <Link className="primary-button" href="/login?redirect=%2Fversus%2Finvite">Se connecter</Link>
          </section>
        </div>
      </div>
    );
  }

  const invites: VersusInvite[] = invitesQuery.data?.invites ?? [];
  const isInviteDisabled =
    createInviteMutation.isPending ||
    inviteePlayerId.trim().length < 3 ||
    (mapSource === "custom" && !customCreateGate.canCreate);

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Versus · Invitation</h1>
          <p>Étape 2/3: crée une invitation ciblée ou réponds à celles reçues.</p>
        </section>

        <section className="panel stack">
          <strong>Créer une invitation</strong>
          <label className="field">
            <span>Identifiant joueur cible</span>
            <input
              type="text"
              value={inviteePlayerId}
              onChange={(event) => setInviteePlayerId(event.target.value)}
              placeholder="player_id"
            />
          </label>

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

          <button
            className="primary-button"
            onClick={() => createInviteMutation.mutate()}
            disabled={isInviteDisabled}
          >
            {createInviteMutation.isPending ? "Envoi..." : "Envoyer l'invitation"}
          </button>
          {mapSource === "custom" && customCreateGate.isAddressEmpty && (
            <span className="muted">Renseigne une adresse pour créer une invitation custom.</span>
          )}
          {mapSource === "custom" && customCreateGate.isAddressLoading && (
            <span className="muted">Géocodage en cours... patiente avant l&apos;envoi.</span>
          )}
        </section>

        <section className="panel stack">
          <div className="panel-head">
            <strong>Invitations reçues</strong>
            <span className="muted">{invites.length} en attente</span>
          </div>

          {invites.length === 0 ? (
            <span className="muted">Aucune invitation en attente.</span>
          ) : (
            <div className="stack" style={{ gap: 10 }}>
              {invites.map((invite) => (
                <div key={invite.invite_id} className="lb-row">
                  <span className="lb-row-avatar">{invite.inviter_avatar ?? "🎅"}</span>
                  <div className="lb-row-meta">
                    <div className="lb-row-name">{invite.inviter_display_name ?? invite.inviter_player_id}</div>
                    <InviteMapPreview invite={invite} />
                    <div className="lb-callsign">Règle: {ruleLabel(invite.winner_rule)}</div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      className="primary-button"
                      onClick={() => acceptInviteMutation.mutate(invite.invite_id)}
                      disabled={acceptInviteMutation.isPending}
                    >
                      Accepter
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => declineInviteMutation.mutate(invite.invite_id)}
                      disabled={declineInviteMutation.isPending}
                    >
                      Refuser
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
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
