"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

// Only safe "card" elements — never layout containers like .panel (used as sidebar)
const TARGETS =
  ".metric-card, .campaign-card, .campaign-row, " +
  ".versus-hub-card, .salon-stage-card, .salon-feed-row, " +
  ".lb-row:not(.reveal-lift)";

export function ScrollReveal() {
  const pathname = usePathname();

  useEffect(() => {
    document.body.classList.add("sr-init");

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("sr-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.04, rootMargin: "0px 0px -20px 0px" }
    );

    document.querySelectorAll<Element>(TARGETS).forEach((el) => {
      const rect = el.getBoundingClientRect();
      const inViewport = rect.top < window.innerHeight + 60 && rect.bottom > -60;
      if (inViewport) {
        el.classList.add("sr-visible");
      } else {
        io.observe(el);
      }
    });

    return () => io.disconnect();
  }, [pathname]);

  return null;
}
