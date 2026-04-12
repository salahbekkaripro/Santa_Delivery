"use client";

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { clearStoredPlayer, readStoredPlayer, saveStoredPlayer } from "@/lib/player";
import type { PlayerProfile } from "@/lib/types";

type PlayerContextValue = {
  player: PlayerProfile | null;
  isReady: boolean;
  signIn: (player: PlayerProfile) => PlayerProfile;
  signOut: () => void;
};

const PlayerContext = createContext<PlayerContextValue | null>(null);

export function PlayerProvider({ children }: { children: ReactNode }) {
  const [player, setPlayer] = useState<PlayerProfile | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setPlayer(readStoredPlayer());
    setIsReady(true);

    const syncPlayer = () => setPlayer(readStoredPlayer());
    window.addEventListener("storage", syncPlayer);
    return () => window.removeEventListener("storage", syncPlayer);
  }, []);

  const value = useMemo<PlayerContextValue>(
    () => ({
      player,
      isReady,
      signIn: (nextPlayer) => {
        const next = saveStoredPlayer(nextPlayer);
        setPlayer(next);
        return next;
      },
      signOut: () => {
        clearStoredPlayer();
        setPlayer(null);
      },
    }),
    [isReady, player]
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
