"use client";

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { signOut as nextAuthSignOut, useSession } from "next-auth/react";
import { clearStoredPlayer, readStoredPlayer, saveStoredPlayer } from "@/lib/player";
import { syncOAuthPlayer } from "@/lib/api";
import type { PlayerProfile } from "@/lib/types";

type PlayerContextValue = {
  player: PlayerProfile | null;
  isReady: boolean;
  signIn: (player: PlayerProfile) => PlayerProfile;
  signOut: () => void;
};

const PlayerContext = createContext<PlayerContextValue | null>(null);

type SessionUser = {
  name?: string | null;
  email?: string | null;
  image?: string | null;
  oauth_provider?: string;
  oauth_account_id?: string;
};

export function PlayerProvider({ children }: { children: ReactNode }) {
  const { data: session, status: sessionStatus } = useSession();
  const [storedPlayer, setStoredPlayer] = useState<PlayerProfile | null>(null);
  const [sessionPlayer, setSessionPlayer] = useState<PlayerProfile | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setStoredPlayer(readStoredPlayer());
    setIsHydrated(true);

    const syncPlayer = () => setStoredPlayer(readStoredPlayer());
    window.addEventListener("storage", syncPlayer);
    return () => window.removeEventListener("storage", syncPlayer);
  }, []);

  useEffect(() => {
    if (sessionStatus !== "authenticated") {
      setSessionPlayer(null);
      return;
    }
    const user = (session?.user ?? {}) as SessionUser;
    const provider = String(user.oauth_provider || "").trim().toLowerCase();
    const providerAccountId = String(user.oauth_account_id || "").trim();
    const fallbackName = String(user.email || "").split("@")[0] || "Joueur du Pole Nord";
    const displayName = String(user.name || "").trim() || fallbackName;

    if (!provider || !providerAccountId || !displayName) {
      return;
    }

    let aborted = false;
    void syncOAuthPlayer({
      provider,
      provider_account_id: providerAccountId,
      display_name: displayName,
      email: user.email ?? null,
      avatar: user.image ?? null,
    })
      .then((player) => {
        if (aborted) return;
        saveStoredPlayer(player);
        setStoredPlayer(player);
        setSessionPlayer(player);
      })
      .catch(() => {
        if (aborted) return;
        setSessionPlayer(null);
      });

    return () => {
      aborted = true;
    };
  }, [session, sessionStatus]);

  const resolvedPlayer = sessionPlayer ?? storedPlayer;
  const isReady = isHydrated && sessionStatus !== "loading";

  const value = useMemo<PlayerContextValue>(
    () => ({
      player: resolvedPlayer,
      isReady,
      signIn: (nextPlayer) => {
        const next = saveStoredPlayer(nextPlayer);
        setStoredPlayer(next);
        return next;
      },
      signOut: () => {
        clearStoredPlayer();
        setStoredPlayer(null);
        setSessionPlayer(null);
        void nextAuthSignOut({ redirect: false });
      },
    }),
    [isReady, resolvedPlayer],
  );

  return <PlayerContext.Provider value={value}>{children}</PlayerContext.Provider>;
}

export function usePlayer() {
  const context = useContext(PlayerContext);
  if (!context) {
    throw new Error("usePlayer must be used within PlayerProvider");
  }
  return context;
}
