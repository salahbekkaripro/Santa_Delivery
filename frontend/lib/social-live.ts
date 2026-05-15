"use client";

import { useEffect, useRef, useState } from "react";
import { getSocialWebSocketUrl } from "@/lib/api";

export type SocialLiveConnection = "idle" | "connecting" | "open" | "reconnecting" | "closed" | "error";

export type SocialLiveEvent = {
  event: string;
  sent_at?: string;
  data?: Record<string, unknown>;
};

export function useSocialLive(playerId?: string | null) {
  const [connection, setConnection] = useState<SocialLiveConnection>("idle");
  const [lastEvent, setLastEvent] = useState<SocialLiveEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reconnectAttemptRef = useRef(0);

  useEffect(() => {
    if (!playerId) {
      setConnection("idle");
      setLastEvent(null);
      setError(null);
      reconnectAttemptRef.current = 0;
      return;
    }

    let cancelled = false;
    let socket: WebSocket | null = null;
    let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const cleanup = () => {
      if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close(1000, "client closing");
      }
      socket = null;
    };

    const connect = () => {
      if (cancelled) return;
      setConnection((prev) => (prev === "open" ? "reconnecting" : "connecting"));
      socket = new WebSocket(getSocialWebSocketUrl(playerId));

      socket.onopen = () => {
        reconnectAttemptRef.current = 0;
        setConnection("open");
        setError(null);
        heartbeatTimer = setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send("ping");
          }
        }, 12000);
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(String(event.data || "{}")) as {
            type?: string;
            event?: string;
            sent_at?: string;
            data?: Record<string, unknown>;
            message?: string;
          };
          if (parsed.type === "social_event" && parsed.event) {
            setLastEvent({ event: parsed.event, sent_at: parsed.sent_at, data: parsed.data });
            return;
          }
          if (parsed.type === "error") {
            setError(parsed.message || "Erreur WebSocket social.");
            setConnection("error");
          }
        } catch {
          setError("Message social temps réel invalide.");
          setConnection("error");
        }
      };

      socket.onerror = () => {
        setError("Connexion social temps réel indisponible.");
        setConnection("error");
      };

      socket.onclose = () => {
        if (cancelled) {
          setConnection("closed");
          return;
        }
        setConnection("reconnecting");
        reconnectAttemptRef.current += 1;
        const delay = Math.min(10000, 1000 * reconnectAttemptRef.current);
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      cancelled = true;
      cleanup();
      setConnection("closed");
    };
  }, [playerId]);

  return { connection, lastEvent, error };
}
