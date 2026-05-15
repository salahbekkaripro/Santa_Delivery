"use client";

import { CSSProperties, useCallback, useEffect, useMemo, useState } from "react";

export type GuidedOnboardingStep = {
  targetId: string;
  title: string;
  description: string;
};

type GuidedOnboardingProps = {
  storageKey: string;
  tutorialLabel: string;
  steps: GuidedOnboardingStep[];
  showReplayButton?: boolean;
};

const STORAGE_DONE_VALUE = "done";
const CARD_WIDTH = 340;
const CARD_HEIGHT_ESTIMATE = 220;
const CARD_MARGIN = 16;
const FOCUS_PADDING = 10;

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function stepSelector(targetId: string) {
  return `[data-onboarding-id=\"${targetId}\"]`;
}

export function GuidedOnboarding({
  storageKey,
  tutorialLabel,
  steps,
  showReplayButton = true,
}: GuidedOnboardingProps) {
  const [isHydrated, setIsHydrated] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);

  const currentStep = steps[stepIndex] ?? null;
  const isLastStep = stepIndex >= steps.length - 1;

  const saveDoneFlag = useCallback(() => {
    try {
      window.localStorage.setItem(storageKey, STORAGE_DONE_VALUE);
    } catch {
      // No-op when storage is unavailable.
    }
  }, [storageKey]);

  const refreshTargetRect = useCallback(() => {
    if (!currentStep) {
      setTargetRect(null);
      return;
    }
    const element = document.querySelector<HTMLElement>(stepSelector(currentStep.targetId));
    if (!element) {
      setTargetRect(null);
      return;
    }
    const rect = element.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      setTargetRect(null);
      return;
    }
    setTargetRect(rect);
  }, [currentStep]);

  useEffect(() => {
    setIsHydrated(true);
    try {
      const alreadyDone = window.localStorage.getItem(storageKey) === STORAGE_DONE_VALUE;
      if (!alreadyDone && steps.length > 0) {
        setIsOpen(true);
      }
    } catch {
      if (steps.length > 0) {
        setIsOpen(true);
      }
    }
  }, [storageKey, steps.length]);

  useEffect(() => {
    if (!isOpen || !currentStep) {
      return;
    }
    const element = document.querySelector<HTMLElement>(stepSelector(currentStep.targetId));
    element?.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
  }, [currentStep, isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    refreshTargetRect();

    const update = () => window.requestAnimationFrame(refreshTargetRect);
    const intervalId = window.setInterval(update, 350);

    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [isOpen, refreshTargetRect]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") {
        return;
      }
      saveDoneFlag();
      setIsOpen(false);
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isOpen, saveDoneFlag]);

  const focusStyle = useMemo<CSSProperties | undefined>(() => {
    if (!targetRect) {
      return undefined;
    }
    return {
      top: Math.max(CARD_MARGIN, targetRect.top - FOCUS_PADDING),
      left: Math.max(CARD_MARGIN, targetRect.left - FOCUS_PADDING),
      width: targetRect.width + FOCUS_PADDING * 2,
      height: targetRect.height + FOCUS_PADDING * 2,
    };
  }, [targetRect]);

  const cardStyle = useMemo<CSSProperties>(() => {
    const viewportWidth = typeof window === "undefined" ? 1280 : window.innerWidth;
    const viewportHeight = typeof window === "undefined" ? 720 : window.innerHeight;
    const maxLeft = Math.max(CARD_MARGIN, viewportWidth - CARD_WIDTH - CARD_MARGIN);

    if (!targetRect) {
      return {
        top: clamp(viewportHeight * 0.22, CARD_MARGIN, viewportHeight - CARD_HEIGHT_ESTIMATE - CARD_MARGIN),
        left: clamp((viewportWidth - CARD_WIDTH) / 2, CARD_MARGIN, maxLeft),
      };
    }

    const preferredTop = targetRect.bottom + 14;
    const fallbackTop = targetRect.top - CARD_HEIGHT_ESTIMATE - 14;
    const top =
      preferredTop + CARD_HEIGHT_ESTIMATE + CARD_MARGIN <= viewportHeight
        ? preferredTop
        : fallbackTop;

    return {
      top: clamp(top, CARD_MARGIN, viewportHeight - CARD_HEIGHT_ESTIMATE - CARD_MARGIN),
      left: clamp(targetRect.left + targetRect.width / 2 - CARD_WIDTH / 2, CARD_MARGIN, maxLeft),
    };
  }, [targetRect]);

  function closeTour() {
    saveDoneFlag();
    setIsOpen(false);
  }

  function replayTour() {
    setStepIndex(0);
    setIsOpen(true);
  }

  if (!isHydrated || steps.length === 0) {
    return null;
  }

  return (
    <>
      {!isOpen && showReplayButton && (
        <button className="secondary-button onboarding-replay-button" onClick={replayTour}>
          Mini tutoriel
        </button>
      )}

      {isOpen && currentStep && (
        <div className="onboarding-overlay" role="dialog" aria-modal="true" aria-label={`Tutoriel ${tutorialLabel}`}>
          {focusStyle && <div className="onboarding-focus" style={focusStyle} />}
          <section className="onboarding-card" style={cardStyle}>
            <span className="onboarding-kicker">Tutoriel {tutorialLabel}</span>
            <h2>{currentStep.title}</h2>
            <p>{currentStep.description}</p>
            <div className="onboarding-footer">
              <span>
                Étape {stepIndex + 1}/{steps.length}
              </span>
              <div className="onboarding-actions">
                <button
                  className="secondary-button"
                  onClick={() => setStepIndex((value) => Math.max(0, value - 1))}
                  disabled={stepIndex === 0}
                >
                  Précédent
                </button>
                {isLastStep ? (
                  <button className="primary-button" onClick={closeTour}>
                    Terminer
                  </button>
                ) : (
                  <button className="primary-button" onClick={() => setStepIndex((value) => Math.min(steps.length - 1, value + 1))}>
                    Suivant
                  </button>
                )}
              </div>
            </div>
            <button className="onboarding-skip" onClick={closeTour}>
              Passer le tutoriel
            </button>
          </section>
        </div>
      )}
    </>
  );
}
