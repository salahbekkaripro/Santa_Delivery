"use client";

import { useEffect, useRef, useState } from "react";
import { getVersusWebSocketUrl } from "@/lib/api";
import type { VersusMatch } from "@/lib/types";

export type VersusLiveConnection = "idle" | "connecting" | "open" | "reconnecting" | "closed" | "error";

type VersusStateMessage = {
  type: "versus_state";
  sent_at: string;
  data: VersusMatch;
};

type VersusErrorMessage = {
  type: "error";
  message: string;
};

export function useVersusLiveState(matchId?: string | null, playerId?: string | null) {
  const [liveState, setLiveState] = useState<VersusMatch | null>(null);
  const [connection, setConnection] = useState<VersusLiveConnection>("idle");
  const [error, setError] = useState<string | null>(null);

  const reconnectTimerRef = useRef<number | null>(null);
  const pingTimerRef = useRef<number | null>(null);

  useEffect(() => {
    setLiveState(null);
    setError(null);

    if (!matchId || !playerId) {
      setConnection("idle");
      return;
    }

    let cancelled = false;
    let socket: WebSocket | null = null;

    const clearTimers = () => {
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (pingTimerRef.current !== null) {
        window.clearInterval(pingTimerRef.current);
        pingTimerRef.current = null;
      }
    };

    const connect = () => {
      if (cancelled) return;
      setConnection((previous) => (previous === "open" ? "reconnecting" : "connecting"));
      const url = getVersusWebSocketUrl(matchId, playerId);
      socket = new WebSocket(url);

      socket.onopen = () => {
        if (cancelled) return;
        setConnection("open");
        setError(null);
        clearTimers();
        pingTimerRef.current = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send("ping");
          }
        }, 15_000);
      };

      socket.onmessage = (event) => {
        if (cancelled) return;
        try {
          const parsed = JSON.parse(String(event.data)) as
            | VersusStateMessage
            | VersusErrorMessage
            | { type?: string; data?: VersusMatch; message?: string };
          if (parsed.type === "versus_state" && parsed.data) {
            setLiveState(parsed.data);
            setConnection("open");
            return;
          }
          if (parsed.type === "error") {
            setError(parsed.message || "Erreur WebSocket versus.");
            setConnection("error");
          }
        } catch {
          // Ignore malformed frames.
        }
      };

      socket.onerror = () => {
        if (cancelled) return;
        setConnection("error");
      };

      socket.onclose = () => {
        clearTimers();
        if (cancelled) {
          setConnection("closed");
          return;
        }
        setConnection("reconnecting");
        reconnectTimerRef.current = window.setTimeout(connect, 1200);
      };
    };

    connect();

    return () => {
      cancelled = true;
      clearTimers();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close(1000, "component_unmount");
      }
    };
  }, [matchId, playerId]);

  return {
    liveState,
    connection,
    error,
    setLiveState,
  };
}
