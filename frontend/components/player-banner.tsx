"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { usePlayer } from "@/components/player-provider";

export function PlayerBanner() {
  const pathname = usePathname();
  const { player, isReady, signOut } = usePlayer();
  const authRedirect = encodeURIComponent("/");

  if (!isReady) {
    return null;
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
