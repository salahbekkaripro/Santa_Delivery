"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { getDirectConversations, getVersusInvites } from "@/lib/api";
import { usePlayer } from "@/components/player-provider";
import { useSocialLive } from "@/lib/social-live";

export function PlayerBanner() {
  const pathname = usePathname();
  const { player, isReady, signOut } = usePlayer();
  const socialLive = useSocialLive(player?.id);

  const invitesQuery = useQuery({
    queryKey: ["versus-invites-counter", player?.id],
    queryFn: () => getVersusInvites(player!.id),
    enabled: Boolean(player?.id),
    refetchOnWindowFocus: true,
  });
  const inviteCount = invitesQuery.data?.invites.length ?? 0;

  const socialQuery = useQuery({
    queryKey: ["social-unread-counter", player?.id],
    queryFn: () => getDirectConversations(player!.id, 30),
    enabled: Boolean(player?.id),
    refetchOnWindowFocus: true,
  });
  const unreadDmCount = (socialQuery.data?.conversations ?? []).reduce((sum, conversation) => sum + (conversation.unread_count ?? 0), 0);
  const { refetch: refetchSocialCounter } = socialQuery;

  useEffect(() => {
    if (!socialLive.lastEvent) return;
    const event = socialLive.lastEvent.event;
    if (
      event === "direct_message_received" ||
      event === "direct_message_sent" ||
      event === "friendship_removed" ||
      event === "blocked_by_player" ||
      event === "player_blocked" ||
      event === "player_unblocked"
    ) {
      refetchSocialCounter();
    }
  }, [refetchSocialCounter, socialLive.lastEvent]);

  const authRedirect = encodeURIComponent("/");

  if (!isReady) {
    return (
      <div className="player-banner">
        <div className="player-banner-card" style={{ minHeight: 56, gap: 12 }}>
          <div className="skeleton-bar h-md" style={{ width: 36, borderRadius: "50%" }} />
          <div className="skeleton-bar h-md w-60" />
        </div>
      </div>
    );
  }

  return (
    <div className="player-banner">
      <div className="player-banner-card">
        {player ? (
          <>
            <div className="player-banner-ident">
              <span className="login-preview-avatar">{player.avatar ?? "🎅"}</span>
              <div>
                <strong>{player.display_name}</strong>
                <span className="muted">{player.email || player.callsign || "Joueur enregistré"}</span>
              </div>
            </div>
            <div className="player-banner-actions">
              {pathname !== "/" && (
                <Link className="secondary-button" href="/">
                  🏠 Accueil
                </Link>
              )}
              {inviteCount > 0 && (
                <Link className="primary-button" href="/versus/invite">
                  Invitations ({inviteCount})
                </Link>
              )}
              <Link className={unreadDmCount > 0 ? "primary-button" : "secondary-button"} href="/messages">
                Messages {unreadDmCount > 0 ? `(${unreadDmCount})` : ""}
              </Link>
              <Link className="secondary-button" href="/social">
                Social
              </Link>
              <Link className="secondary-button" href="/solver">
                🧮 Solveur
              </Link>
              <Link className="secondary-button" href="/explore">
                🔬 Coulisses
              </Link>
              <Link className="secondary-button" href="/data">
                📊 Données
              </Link>
              {pathname !== "/login" && pathname !== "/register" ? (
                <Link className="secondary-button" href={`/login?redirect=${authRedirect}`}>
                  Changer de compte
                </Link>
              ) : null}
              <button className="secondary-button" onClick={() => signOut()}>
                Déconnexion
              </button>
            </div>
          </>
        ) : (
          <>
            <div>
              <strong>Aucun joueur connecté</strong>
              <span className="muted">Inscris-toi ou connecte-toi pour isoler progression et score.</span>
            </div>
            <div className="player-banner-actions">
              {pathname !== "/" && (
                <Link className="secondary-button" href="/">
                  🏠 Accueil
                </Link>
              )}
              <Link className="secondary-button" href={`/login?redirect=${authRedirect}`}>
                Se connecter
              </Link>
              <Link className="primary-button" href={`/register?redirect=${authRedirect}`}>
                S&apos;inscrire
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
