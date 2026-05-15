"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { usePlayer } from "@/components/player-provider";
import {
  blockPlayer,
  getDirectConversations,
  getDirectMessages,
  getSocialFriendships,
  removeDirectConversation,
  restoreDirectConversation,
  sendDirectMessage,
} from "@/lib/api";
import { useSocialLive } from "@/lib/social-live";

type AvailablePeer = {
  player_id: string;
  display_name: string;
  callsign?: string | null;
  avatar?: string | null;
  unread_count: number;
  hidden: boolean;
  cleared_before_at?: string | null;
  last_message_at?: string | null;
  last_message_body?: string | null;
};

export default function MessagesPage() {
  const { player, isReady } = usePlayer();
  const [queryPeer, setQueryPeer] = useState<string | null>(null);
  const [selectedPeerId, setSelectedPeerId] = useState<string | null>(null);
  const [messageDraft, setMessageDraft] = useState("");
  const [filterQuery, setFilterQuery] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mobilePane, setMobilePane] = useState<"list" | "chat">("list");
  const socialLive = useSocialLive(player?.id);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const peer = params.get("peer")?.trim() || null;
    setQueryPeer(peer);
  }, []);

  const conversationsQuery = useQuery({
    queryKey: ["social-conversations", player?.id],
    queryFn: () => getDirectConversations(player!.id, 40),
    enabled: Boolean(player?.id),
    refetchOnWindowFocus: true,
  });

  const friendshipsQuery = useQuery({
    queryKey: ["social-friendships", player?.id],
    queryFn: () => getSocialFriendships(player!.id),
    enabled: Boolean(player?.id),
    refetchOnWindowFocus: true,
  });

  const friendPeers = useMemo(() => friendshipsQuery.data?.friends ?? [], [friendshipsQuery.data?.friends]);
  const conversations = useMemo(
    () => conversationsQuery.data?.conversations ?? [],
    [conversationsQuery.data?.conversations],
  );

  const availablePeers = useMemo(() => {
    const peerMap = new Map<string, AvailablePeer>();
    for (const conversation of conversations) {
      if (!conversation.peer_player_id) continue;
      peerMap.set(conversation.peer_player_id, {
        player_id: conversation.peer_player_id,
        display_name: conversation.peer_display_name ?? conversation.peer_player_id,
        callsign: conversation.peer_callsign ?? null,
        avatar: conversation.peer_avatar ?? null,
        unread_count: conversation.unread_count ?? 0,
        hidden: Boolean(conversation.hidden),
        cleared_before_at: conversation.cleared_before_at ?? null,
        last_message_at: conversation.last_message_at ?? null,
        last_message_body: conversation.last_message?.body ?? null,
      });
    }

    for (const friend of friendPeers) {
      if (!friend.peer_player_id) continue;
      if (!peerMap.has(friend.peer_player_id)) {
        peerMap.set(friend.peer_player_id, {
          player_id: friend.peer_player_id,
          display_name: friend.peer_display_name ?? friend.peer_player_id,
          callsign: friend.peer_callsign ?? null,
          avatar: friend.peer_avatar ?? null,
          unread_count: 0,
          hidden: false,
          cleared_before_at: null,
          last_message_at: null,
          last_message_body: null,
        });
      }
    }

    return Array.from(peerMap.values()).sort((a, b) => {
      const aTime = a.last_message_at ? Date.parse(a.last_message_at) : 0;
      const bTime = b.last_message_at ? Date.parse(b.last_message_at) : 0;
      if (aTime !== bTime) {
        return bTime - aTime;
      }
      return a.display_name.localeCompare(b.display_name, "fr", { sensitivity: "base" });
    });
  }, [conversations, friendPeers]);

  const selectedConversation = useMemo(
    () => conversations.find((conversation) => conversation.peer_player_id === selectedPeerId) ?? null,
    [conversations, selectedPeerId],
  );

  const storageKey = player?.id ? `lastDmPeerByPlayer:${player.id}` : null;

  useEffect(() => {
    if (!storageKey || !selectedPeerId) return;
    window.localStorage.setItem(storageKey, selectedPeerId);
  }, [selectedPeerId, storageKey]);

  useEffect(() => {
    if (!availablePeers.length) {
      setSelectedPeerId(null);
      return;
    }

    if (selectedPeerId && availablePeers.some((peer) => peer.player_id === selectedPeerId)) {
      return;
    }

    const queryCandidate = queryPeer && availablePeers.some((peer) => peer.player_id === queryPeer) ? queryPeer : null;
    if (queryCandidate) {
      setSelectedPeerId(queryCandidate);
      setMobilePane("chat");
      return;
    }

    const savedPeerId = storageKey ? window.localStorage.getItem(storageKey) : null;
    if (savedPeerId && availablePeers.some((peer) => peer.player_id === savedPeerId)) {
      setSelectedPeerId(savedPeerId);
      return;
    }

    setSelectedPeerId(availablePeers[0].player_id);
  }, [availablePeers, queryPeer, selectedPeerId, storageKey]);

  const messagesQuery = useQuery({
    queryKey: ["social-messages", player?.id, selectedPeerId],
    queryFn: () => getDirectMessages({ player_id: player!.id, with_player_id: selectedPeerId!, limit: 100 }),
    enabled: Boolean(player?.id && selectedPeerId),
    refetchOnWindowFocus: true,
  });

  const sendMessageMutation = useMutation({
    mutationFn: () =>
      sendDirectMessage({
        player_id: player!.id,
        recipient_player_id: selectedPeerId!,
        body: messageDraft.trim(),
      }),
    onSuccess: () => {
      setError(null);
      setMessageDraft("");
      messagesQuery.refetch();
      conversationsQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const removeConversationMutation = useMutation({
    mutationFn: () => removeDirectConversation({ player_id: player!.id, with_player_id: selectedPeerId! }),
    onSuccess: () => {
      setError(null);
      setFeedback("Conversation effacée pour vous.");
      messagesQuery.refetch();
      conversationsQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const restoreConversationMutation = useMutation({
    mutationFn: () => restoreDirectConversation({ player_id: player!.id, with_player_id: selectedPeerId! }),
    onSuccess: () => {
      setError(null);
      setFeedback("Historique local restauré.");
      messagesQuery.refetch();
      conversationsQuery.refetch();
    },
    onError: (err: Error) => setError(err.message),
  });

  const blockMutation = useMutation({
    mutationFn: (blockedPlayerId: string) => blockPlayer({ player_id: player!.id, blocked_player_id: blockedPlayerId }),
    onSuccess: () => {
      setError(null);
      setFeedback("Joueur bloqué.");
      setSelectedPeerId(null);
      friendshipsQuery.refetch();
      conversationsQuery.refetch();
      messagesQuery.refetch();
      setMobilePane("list");
    },
    onError: (err: Error) => setError(err.message),
  });

  useEffect(() => {
    if (!socialLive.lastEvent) return;
    const event = socialLive.lastEvent.event;

    if (event === "direct_message_received" || event === "direct_message_sent") {
      conversationsQuery.refetch();
      if (selectedPeerId) {
        messagesQuery.refetch();
      }
      return;
    }

    if (event === "conversation_cleared" || event === "conversation_restored") {
      conversationsQuery.refetch();
      if (selectedPeerId) {
        messagesQuery.refetch();
      }
      return;
    }

    if (
      event.startsWith("friend_request") ||
      event === "friendship_removed" ||
      event === "blocked_by_player" ||
      event === "player_blocked" ||
      event === "player_unblocked"
    ) {
      friendshipsQuery.refetch();
      conversationsQuery.refetch();
      if (selectedPeerId) {
        messagesQuery.refetch();
      }
    }
  }, [conversationsQuery, friendshipsQuery, messagesQuery, selectedPeerId, socialLive.lastEvent]);

  const filteredPeers = useMemo(() => {
    const q = filterQuery.trim().toLowerCase();
    if (!q) return availablePeers;
    return availablePeers.filter((peer) => {
      const displayName = peer.display_name.toLowerCase();
      const peerId = peer.player_id.toLowerCase();
      const callsign = (peer.callsign ?? "").toLowerCase();
      return displayName.includes(q) || peerId.includes(q) || callsign.includes(q);
    });
  }, [availablePeers, filterQuery]);

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
            <span>Connecte-toi pour accéder à tes messages privés.</span>
            <Link className="primary-button" href="/login?redirect=%2Fmessages">
              Se connecter
            </Link>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell messages-shell">
      <div className="page-stack messages-page-stack">
        <section className="hero">
          <h1>Messages</h1>
          <span className="muted">Sélectionne un ami et discute en direct.</span>
          <span className="muted">Live: {socialLive.connection}</span>
        </section>

        <section className="panel stack messages-panel">
          <div className="messages-grid">
            <aside className={`messages-list ${mobilePane === "chat" ? "messages-list--mobile-hidden" : ""}`}>
              <label className="field">
                <span>Rechercher un ami</span>
                <input
                  type="text"
                  value={filterQuery}
                  onChange={(event) => setFilterQuery(event.target.value)}
                  placeholder="Pseudo, callsign ou player_id"
                />
              </label>
              <span className="muted">{filteredPeers.length} contact(s)</span>
              <div className="stack">
                {filteredPeers.length === 0 && <span className="muted">Aucun contact trouvé.</span>}
                {filteredPeers.map((peer) => (
                  <button
                    key={peer.player_id}
                    className={`social-peer-btn ${selectedPeerId === peer.player_id ? "social-peer-btn--active" : ""} ${peer.hidden ? "social-peer-btn--hidden" : ""}`}
                    onClick={() => {
                      setSelectedPeerId(peer.player_id);
                      setMobilePane("chat");
                    }}
                  >
                    <span>{peer.avatar ?? "📨"}</span>
                    <span className="messages-peer-main">
                      <span className="messages-peer-name">{peer.display_name}</span>
                      <span className="messages-peer-preview">{peer.last_message_body ?? `@${peer.player_id}`}</span>
                    </span>
                    {peer.hidden ? <span className="social-hidden-chip">masquée</span> : null}
                    {peer.unread_count ? <span className="social-unread">{peer.unread_count}</span> : null}
                  </button>
                ))}
              </div>
            </aside>

            <div className={`messages-chat ${mobilePane === "list" ? "messages-chat--mobile-hidden" : ""}`}>
              {!selectedPeerId ? (
                <span className="muted">Sélectionne un ami.</span>
              ) : (
                <>
                  <div className="messages-chat-head">
                    <button className="secondary-button messages-mobile-back" onClick={() => setMobilePane("list")}>
                      Retour
                    </button>
                    <strong>{selectedConversation?.peer_display_name ?? availablePeers.find((peer) => peer.player_id === selectedPeerId)?.display_name ?? selectedPeerId}</strong>
                  </div>
                  {selectedConversation?.hidden ? (
                    <span className="muted">Historique masqué localement. Utilise “Restaurer l&apos;historique”.</span>
                  ) : null}
                  <div className="social-chat-log messages-chat-log">
                    {(messagesQuery.data?.messages ?? []).map((message) => (
                      <div
                        key={message.message_id}
                        className={`social-message ${message.is_mine ? "social-message--mine" : "social-message--peer"}`}
                      >
                        <div>{message.body}</div>
                        <small>{message.created_at ? new Date(message.created_at).toLocaleString() : ""}</small>
                      </div>
                    ))}
                  </div>
                  <label className="field">
                    <span>Nouveau message</span>
                    <textarea
                      rows={3}
                      value={messageDraft}
                      onChange={(event) => setMessageDraft(event.target.value)}
                      placeholder="Écris ton message..."
                    />
                  </label>
                  <button
                    className="primary-button"
                    onClick={() => sendMessageMutation.mutate()}
                    disabled={sendMessageMutation.isPending || messageDraft.trim().length === 0}
                  >
                    {sendMessageMutation.isPending ? "Envoi..." : "Envoyer"}
                  </button>
                  <div className="social-chat-actions">
                    <button
                      className="secondary-button"
                      onClick={() => removeConversationMutation.mutate()}
                      disabled={removeConversationMutation.isPending}
                    >
                      {removeConversationMutation.isPending ? "Effacement..." : "Effacer pour moi"}
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => restoreConversationMutation.mutate()}
                      disabled={restoreConversationMutation.isPending}
                    >
                      {restoreConversationMutation.isPending ? "Restauration..." : "Restaurer l'historique"}
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => blockMutation.mutate(selectedPeerId)}
                      disabled={blockMutation.isPending}
                    >
                      {blockMutation.isPending ? "Blocage..." : "Bloquer ce joueur"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </section>

        {feedback && <section className="panel"><span>{feedback}</span></section>}
        {error && <section className="error-box">{error}</section>}
      </div>
    </div>
  );
}
