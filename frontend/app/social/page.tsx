"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { usePlayer } from "@/components/player-provider";
import {
  blockPlayer,
  getBlockedPlayers,
  getSocialFriendships,
  removeFriendship,
  respondFriendRequest,
  searchSocialPlayers,
  sendFriendRequest,
  unblockPlayer,
} from "@/lib/api";
import { useSocialLive } from "@/lib/social-live";

export default function SocialPage() {
  const { player, isReady } = usePlayer();
  const [friendPlayerIdInput, setFriendPlayerIdInput] = useState("");
  const [pseudoQuery, setPseudoQuery] = useState("");
  const [debouncedPseudoQuery, setDebouncedPseudoQuery] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const socialLive = useSocialLive(player?.id);

  const friendshipsQuery = useQuery({
    queryKey: ["social-friendships", player?.id],
    queryFn: () => getSocialFriendships(player!.id),
    enabled: Boolean(player?.id),
    refetchOnWindowFocus: true,
  });

  const blockedQuery = useQuery({
    queryKey: ["social-blocked", player?.id],
    queryFn: () => getBlockedPlayers(player!.id),
    enabled: Boolean(player?.id),
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedPseudoQuery(pseudoQuery.trim()), 220);
    return () => window.clearTimeout(timer);
  }, [pseudoQuery]);

  const playerSearchQuery = useQuery({
    queryKey: ["social-player-search", player?.id, debouncedPseudoQuery],
    queryFn: () => searchSocialPlayers(player!.id, debouncedPseudoQuery, 12),
    enabled: Boolean(player?.id && debouncedPseudoQuery.length >= 2),
  });

  const friendPeers = useMemo(() => friendshipsQuery.data?.friends ?? [], [friendshipsQuery.data?.friends]);
  const incomingRequests = useMemo(
    () => friendshipsQuery.data?.incoming_requests ?? [],
    [friendshipsQuery.data?.incoming_requests],
  );
  const outgoingRequests = useMemo(
    () => friendshipsQuery.data?.outgoing_requests ?? [],
    [friendshipsQuery.data?.outgoing_requests],
  );
  const blockedPlayers = useMemo(() => blockedQuery.data?.blocked ?? [], [blockedQuery.data?.blocked]);

  const searchResult = debouncedPseudoQuery.length >= 2 ? (playerSearchQuery.data?.players ?? []) : [];

  const sendRequestMutation = useMutation({
    mutationFn: (friendPlayerId: string) => sendFriendRequest({ player_id: player!.id, friend_player_id: friendPlayerId }),
    onSuccess: () => {
      setError(null);
      setFeedback("Demande envoyée.");
      setFriendPlayerIdInput("");
      friendshipsQuery.refetch();
      blockedQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const respondRequestMutation = useMutation({
    mutationFn: (payload: { friend_player_id: string; action: "accept" | "decline" }) =>
      respondFriendRequest({ player_id: player!.id, friend_player_id: payload.friend_player_id, action: payload.action }),
    onSuccess: (_payload, variables) => {
      setError(null);
      setFeedback(variables.action === "accept" ? "Demande acceptée." : "Demande refusée.");
      friendshipsQuery.refetch();
      blockedQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const removeFriendMutation = useMutation({
    mutationFn: (friendPlayerId: string) => removeFriendship({ player_id: player!.id, friend_player_id: friendPlayerId }),
    onSuccess: () => {
      setError(null);
      setFeedback("Relation supprimée.");
      friendshipsQuery.refetch();
      blockedQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const blockMutation = useMutation({
    mutationFn: (blockedPlayerId: string) => blockPlayer({ player_id: player!.id, blocked_player_id: blockedPlayerId }),
    onSuccess: () => {
      setError(null);
      setFeedback("Joueur bloqué.");
      friendshipsQuery.refetch();
      blockedQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const unblockMutation = useMutation({
    mutationFn: (blockedPlayerId: string) => unblockPlayer({ player_id: player!.id, blocked_player_id: blockedPlayerId }),
    onSuccess: () => {
      setError(null);
      setFeedback("Joueur débloqué.");
      blockedQuery.refetch();
      friendshipsQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  useEffect(() => {
    if (!socialLive.lastEvent) return;
    const event = socialLive.lastEvent.event;

    if (event.startsWith("friend_request") || event === "friendship_removed") {
      friendshipsQuery.refetch();
      if (event === "friend_request_incoming") {
        setToast("Nouvelle demande d'ami.");
      }
      return;
    }

    if (event === "blocked_by_player" || event === "player_blocked" || event === "player_unblocked") {
      blockedQuery.refetch();
      friendshipsQuery.refetch();
      if (event === "blocked_by_player") {
        setToast("Un joueur vous a bloqué.");
      }
    }
  }, [blockedQuery, friendshipsQuery, socialLive.lastEvent]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  if (!isReady) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="panel-loading" style={{ height: 120 }} />
          <div className="panel-loading" style={{ height: 300 }} />
        </div>
      </div>
    );
  }

  if (!player) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="panel stack">
            <strong>Connexion requise</strong>
            <span>Connecte-toi pour gérer tes amis et tes messages privés.</span>
            <Link className="primary-button" href="/login?redirect=%2Fsocial">
              Se connecter
            </Link>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero">
          <h1>Social Hub</h1>
          <span className="muted">Demandes d&apos;amis + gestion des contacts</span>
          <span className="muted">Live: {socialLive.connection}</span>
          <div className="hero-cta-row">
            <Link className="primary-button" href="/messages">
              Ouvrir les messages
            </Link>
          </div>
        </section>

        <section className="panel stack">
          <strong>Ajouter des amis</strong>
          <label className="field">
            <span>Ajouter par ID joueur</span>
            <input
              type="text"
              value={friendPlayerIdInput}
              onChange={(event) => setFriendPlayerIdInput(event.target.value)}
              placeholder="player_id affiché (@...)"
            />
          </label>
          <button
            className="primary-button"
            onClick={() => sendRequestMutation.mutate(friendPlayerIdInput.trim())}
            disabled={sendRequestMutation.isPending || friendPlayerIdInput.trim().length < 3}
          >
            {sendRequestMutation.isPending ? "Envoi..." : "Envoyer la demande par ID"}
          </button>

          <label className="field">
            <span>Ou chercher par pseudo</span>
            <input
              type="text"
              value={pseudoQuery}
              onChange={(event) => setPseudoQuery(event.target.value)}
              placeholder="Nom affiché / callsign"
            />
          </label>
          <span className="muted">
            {pseudoQuery.trim().length < 2
              ? "Tape au moins 2 caractères pour afficher des suggestions."
              : playerSearchQuery.isPending
                ? "Recherche de profils..."
                : `${searchResult.length} suggestion(s)`}
          </span>

          {searchResult.length > 0 && (
            <div className="stack">
              {searchResult.map((result) => (
                <div key={result.player_id} className="lb-row sr-visible">
                  <span className="lb-row-avatar">{result.avatar ?? "🎅"}</span>
                  <div className="lb-row-main">
                    <div className="lb-row-name">{result.display_name}</div>
                    <div className="lb-callsign">@{result.player_id}</div>
                  </div>
                  <button
                    className="primary-button"
                    onClick={() => sendRequestMutation.mutate(result.player_id)}
                    disabled={sendRequestMutation.isPending}
                  >
                    Demander
                  </button>
                  <button
                    className="secondary-button"
                    onClick={() => blockMutation.mutate(result.player_id)}
                    disabled={blockMutation.isPending}
                  >
                    Bloquer
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel stack">
          <strong>Demandes en attente</strong>
          <span className="muted">Reçues: {incomingRequests.length} · Envoyées: {outgoingRequests.length}</span>

          {incomingRequests.map((entry) => (
            <div key={`in-${entry.peer_player_id}`} className="lb-row sr-visible">
              <span className="lb-row-avatar">{entry.peer_avatar ?? "🧑‍🎄"}</span>
              <div className="lb-row-main">
                <div className="lb-row-name">{entry.peer_display_name ?? entry.peer_player_id}</div>
                <div className="lb-callsign">@{entry.peer_player_id}</div>
              </div>
              <button
                className="primary-button"
                onClick={() => respondRequestMutation.mutate({ friend_player_id: entry.peer_player_id, action: "accept" })}
                disabled={respondRequestMutation.isPending}
              >
                Accepter
              </button>
              <button
                className="secondary-button"
                onClick={() => respondRequestMutation.mutate({ friend_player_id: entry.peer_player_id, action: "decline" })}
                disabled={respondRequestMutation.isPending}
              >
                Refuser
              </button>
            </div>
          ))}

          {outgoingRequests.map((entry) => (
            <div key={`out-${entry.peer_player_id}`} className="lb-row sr-visible">
              <span className="lb-row-avatar">{entry.peer_avatar ?? "🧑‍🎄"}</span>
              <div className="lb-row-main">
                <div className="lb-row-name">{entry.peer_display_name ?? entry.peer_player_id}</div>
                <div className="lb-callsign">En attente · @{entry.peer_player_id}</div>
              </div>
            </div>
          ))}
        </section>

        <section className="panel stack">
          <strong>Amis</strong>
          <span className="muted">{friendPeers.length} amis</span>

          {friendPeers.map((friend) => (
            <div key={friend.peer_player_id} className="lb-row sr-visible">
              <span className="lb-row-avatar">{friend.peer_avatar ?? "🎄"}</span>
              <div className="lb-row-main">
                <div className="lb-row-name">{friend.peer_display_name ?? friend.peer_player_id}</div>
                <div className="lb-callsign">@{friend.peer_player_id}</div>
              </div>
              <Link className="secondary-button" href={`/messages?peer=${encodeURIComponent(friend.peer_player_id)}`}>
                Message
              </Link>
              <button
                className="secondary-button"
                onClick={() => removeFriendMutation.mutate(friend.peer_player_id)}
                disabled={removeFriendMutation.isPending}
              >
                Supprimer
              </button>
              <button
                className="secondary-button"
                onClick={() => blockMutation.mutate(friend.peer_player_id)}
                disabled={blockMutation.isPending}
              >
                Bloquer
              </button>
            </div>
          ))}
        </section>

        <section className="panel stack">
          <strong>Joueurs bloqués</strong>
          <span className="muted">{blockedPlayers.length} bloqués</span>
          {blockedPlayers.map((blocked) => (
            <div key={blocked.player_id} className="lb-row sr-visible">
              <span className="lb-row-avatar">{blocked.avatar ?? "🚫"}</span>
              <div className="lb-row-main">
                <div className="lb-row-name">{blocked.display_name ?? blocked.player_id}</div>
                <div className="lb-callsign">@{blocked.player_id}</div>
              </div>
              <button
                className="secondary-button"
                onClick={() => unblockMutation.mutate(blocked.player_id)}
                disabled={unblockMutation.isPending}
              >
                Débloquer
              </button>
            </div>
          ))}
        </section>

        {feedback && <section className="panel"><span>{feedback}</span></section>}
        {error && <section className="error-box">{error}</section>}
        {toast && <section className="panel social-toast">{toast}</section>}
      </div>
    </div>
  );
}
