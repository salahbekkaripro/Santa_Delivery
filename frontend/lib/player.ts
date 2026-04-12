import type { PlayerProfile } from "@/lib/types";

export const PLAYER_STORAGE_KEY = "operation-noel-current-player";

function sanitize(value: string) {
  return value.trim().replace(/\s+/g, " ");
}

function slugify(value: string) {
  return sanitize(value)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
}

export function buildPlayerProfile(input: {
  display_name: string;
  callsign?: string;
  avatar?: string;
}): PlayerProfile {
  const displayName = sanitize(input.display_name);
  const callsign = sanitize(input.callsign ?? "");
  return {
    id: `${slugify(displayName || "player")}-${Date.now().toString(36)}`,
    display_name: displayName || "Joueur du Pôle Nord",
    callsign: callsign || null,
    avatar: input.avatar?.trim() || null,
    created_at: new Date().toISOString(),
  };
}

export function readStoredPlayer(): PlayerProfile | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(PLAYER_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as PlayerProfile;
  } catch {
    return null;
  }
}

export function saveStoredPlayer(player: PlayerProfile): PlayerProfile {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(PLAYER_STORAGE_KEY, JSON.stringify(player));
  }
  return player;
}

export function clearStoredPlayer() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(PLAYER_STORAGE_KEY);
  }
}

export function getCampaignStorageKeyForPlayer(playerId?: string | null) {
  return `operation-noel-campaign-progress:${playerId || "guest"}`;
}
