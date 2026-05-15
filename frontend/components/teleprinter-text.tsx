"use client";

import { useEffect, useState } from "react";

export function TeleprinterText({ text, speedMs = 14, className }: { text: string; speedMs?: number; className?: string }) {
  const [visibleChars, setVisibleChars] = useState(0);

  useEffect(() => {
    setVisibleChars(0);
    const safeSpeed = Math.max(8, speedMs);
    const timer = window.setInterval(() => {
      setVisibleChars((previous) => {
        if (previous >= text.length) {
          window.clearInterval(timer);
          return previous;
        }
        return previous + 1;
      });
    }, safeSpeed);

    return () => window.clearInterval(timer);
  }, [text, speedMs]);

  const rendered = text.slice(0, visibleChars);
  const done = visibleChars >= text.length;

  return (
    <p className={`teleprinter ${className ?? ""}`.trim()} aria-live="polite">
      {rendered}
      {!done ? <span className="teleprinter-caret" /> : null}
    </p>
  );
}
