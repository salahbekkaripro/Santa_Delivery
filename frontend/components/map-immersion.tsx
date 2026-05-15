"use client";

import { useEffect, useRef, useState } from "react";

type Flake = {
  x: number;
  y: number;
  radius: number;
  speedY: number;
  sway: number;
};

const AMBIENT_TRACKS = [
  {
    key: "noel",
    label: "🎄 Noël",
    src: "https://assets.mixkit.co/music/preview/mixkit-christmas-background-165.mp3",
  },
  {
    key: "sleigh",
    label: "🛷 Traîneau",
    src: "https://assets.mixkit.co/music/preview/mixkit-sleigh-ride-music-570.mp3",
  },
];

export function MapImmersion() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [enabled, setEnabled] = useState(false);
  const [trackIndex, setTrackIndex] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrapper = wrapperRef.current;
    if (!canvas || !wrapper) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const flakes: Flake[] = [];
    const maxFlakes = 120;

    const resize = () => {
      const rect = wrapper.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(rect.width));
      canvas.height = Math.max(1, Math.floor(rect.height));
      if (flakes.length === 0) {
        for (let i = 0; i < maxFlakes; i += 1) {
          flakes.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            radius: Math.random() * 2.3 + 0.6,
            speedY: Math.random() * 0.6 + 0.45,
            sway: Math.random() * 1.8 + 0.4,
          });
        }
      }
    };

    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(wrapper);

    let frame = 0;
    let animationId = 0;

    const draw = () => {
      frame += 1;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "rgba(255, 255, 255, 0.85)";

      for (const flake of flakes) {
        flake.y += flake.speedY;
        flake.x += Math.sin((frame + flake.y) * 0.008) * 0.05 * flake.sway;

        if (flake.y > canvas.height + 8) {
          flake.y = -8;
          flake.x = Math.random() * canvas.width;
        }
        if (flake.x > canvas.width + 8) flake.x = -8;
        if (flake.x < -8) flake.x = canvas.width + 8;

        ctx.beginPath();
        ctx.arc(flake.x, flake.y, flake.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      animationId = window.requestAnimationFrame(draw);
    };

    animationId = window.requestAnimationFrame(draw);
    return () => {
      window.cancelAnimationFrame(animationId);
      resizeObserver.disconnect();
    };
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (!enabled) {
      audio.pause();
      audio.currentTime = 0;
      return;
    }

    audio.volume = 0.28;
    void audio.play().catch(() => {
      setEnabled(false);
    });
  }, [enabled, trackIndex]);

  return (
    <div ref={wrapperRef} style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 1000 }}>
      <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />

      <div
        style={{
          position: "absolute",
          left: 12,
          top: 12,
          display: "flex",
          gap: 8,
          alignItems: "center",
          pointerEvents: "auto",
          background: "rgba(255,255,255,0.9)",
          border: "1px solid var(--border)",
          borderRadius: 999,
          padding: "6px 10px",
          boxShadow: "0 6px 14px rgba(18, 50, 71, 0.16)",
        }}
      >
        <button
          type="button"
          className="secondary-button"
          onClick={() => setEnabled((previous) => !previous)}
          style={{ minHeight: 38, minWidth: 120 }}
        >
          {enabled ? "🔊 Ambiance ON" : "🔈 Ambiance OFF"}
        </button>
        <button
          type="button"
          className="secondary-button"
          onClick={() => setTrackIndex((previous) => (previous + 1) % AMBIENT_TRACKS.length)}
          disabled={!enabled}
          style={{ minHeight: 38 }}
        >
          {AMBIENT_TRACKS[trackIndex].label}
        </button>
      </div>

      <audio ref={audioRef} loop preload="none" src={AMBIENT_TRACKS[trackIndex].src} />
    </div>
  );
}
