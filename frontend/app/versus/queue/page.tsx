"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { GuidedOnboarding, type GuidedOnboardingStep } from "@/components/guided-onboarding";
import { usePlayer } from "@/components/player-provider";
import { TeleprinterText } from "@/components/teleprinter-text";
import { enterVersusQueue, getVersusQueueStatus, getVersusTemplates, leaveVersusQueue } from "@/lib/api";
import type { VersusWinnerRule } from "@/lib/types";
import { WINNER_RULE_OPTIONS } from "@/lib/versus";

const QUEUE_ONBOARDING_STEPS: GuidedOnboardingStep[] = [
  {
    targetId: "queue-overview",
    title: "Matchmaking rapide",
    description: "La file auto utilise des templates versus prédéfinis pour trouver vite un adversaire.",
  },
  {
    targetId: "queue-template",
    title: "Sélectionne ton template",
    description: "Choisis la carte de duel sur laquelle le matchmaking doit t'apparier.",
  },
  {
    targetId: "queue-rule",
    title: "Choisis la règle de victoire",
    description: "Le classement du duel suivra cette règle une fois la partie terminée.",
  },
  {
    targetId: "queue-action",
    title: "Entre en file puis attends le match",
    description: "Dès qu'un adversaire compatible est trouvé, tu es redirigé automatiquement vers le lobby live.",
  },
];

export default function VersusQueuePage() {
  const router = useRouter();
  const { player, isReady } = usePlayer();

  const [templateId, setTemplateId] = useState("paris_duel");
  const [winnerRule, setWinnerRule] = useState<VersusWinnerRule>("score_time");
  const [queueActive, setQueueActive] = useState(false);
  const [queueContext, setQueueContext] = useState<{ templateId: string; winnerRule: VersusWinnerRule } | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedS, setElapsedS] = useState(0);
  const queueStartRef = useRef<number | null>(null);

  const templatesQuery = useQuery({
    queryKey: ["versus-templates"],
    queryFn: getVersusTemplates,
  });

  const selectedTemplateDescription = useMemo(
    () => templatesQuery.data?.templates.find((template) => template.template_id === templateId)?.description,
    [templatesQuery.data?.templates, templateId],
  );

  const queueMutation = useMutation({
    mutationFn: () =>
      enterVersusQueue({
        player_id: player!.id,
        map_source: "template",
        template_id: templateId,
        winner_rule: winnerRule,
      }),
    onSuccess: (payload) => {
      setError(null);
      if (payload.status === "matched" && payload.match) {
        setQueueActive(false);
        setQueueContext(null);
        setFeedback("Adversaire trouvé.");
        router.push(`/versus/match/${payload.match.match_id}`);
        return;
      }
      if (payload.queue_entry?.enqueued_at) {
        const parsed = Date.parse(payload.queue_entry.enqueued_at);
        queueStartRef.current = Number.isNaN(parsed) ? Date.now() : parsed;
      } else if (!queueStartRef.current) {
        queueStartRef.current = Date.now();
      }
      setQueueActive(true);
      setQueueContext({ templateId, winnerRule });
      setFeedback("En file d'attente. Recherche en cours...");
    },
    onError: (err: Error) => setError(err.message),
  });

  const queueStatusMutation = useMutation({
    mutationFn: (payload: { templateId: string; winnerRule: VersusWinnerRule }) =>
      getVersusQueueStatus({
        player_id: player!.id,
        template_id: payload.templateId,
        winner_rule: payload.winnerRule,
      }),
    onSuccess: (payload) => {
      setError(null);
      if (payload.status === "matched" && payload.match) {
        setQueueActive(false);
        setQueueContext(null);
        setFeedback("Adversaire trouvé.");
        router.push(`/versus/match/${payload.match.match_id}`);
        return;
      }
      if (payload.status === "queued") {
        setQueueActive(true);
        if (payload.queue_entry?.enqueued_at) {
          const parsed = Date.parse(payload.queue_entry.enqueued_at);
          if (!Number.isNaN(parsed)) {
            queueStartRef.current = parsed;
          }
        }
        return;
      }
      setQueueActive(false);
      setQueueContext(null);
      setElapsedS(0);
      queueStartRef.current = null;
      setFeedback("Vous n'êtes plus dans la file.");
    },
    onError: (err: Error) => setError(err.message),
  });

  const leaveMutation = useMutation({
    mutationFn: () => leaveVersusQueue({ player_id: player!.id }),
    onSuccess: () => {
      setQueueActive(false);
      setQueueContext(null);
      setElapsedS(0);
      queueStartRef.current = null;
      setError(null);
      setFeedback("Vous avez quitté la file.");
    },
    onError: (err: Error) => setError(err.message),
  });

  const statusMutateRef = useRef(queueStatusMutation.mutate);
  const isStatusPendingRef = useRef(queueStatusMutation.isPending);
  statusMutateRef.current = queueStatusMutation.mutate;
  isStatusPendingRef.current = queueStatusMutation.isPending;

  useEffect(() => {
    if (!queueActive || !player?.id || !queueContext) {
      return;
    }
    const timer = window.setInterval(() => {
      if (!isStatusPendingRef.current) {
        statusMutateRef.current(queueContext);
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [player?.id, queueActive, queueContext]);

  useEffect(() => {
    if (!queueActive) { setElapsedS(0); return; }
    const tick = window.setInterval(() => {
      if (queueStartRef.current) {
        setElapsedS(Math.floor((Date.now() - queueStartRef.current) / 1000));
      }
    }, 1000);
    return () => window.clearInterval(tick);
  }, [queueActive]);

  if (!isReady) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <div className="panel-loading" style={{ height: 110 }} />
          <div className="panel-loading" style={{ height: 160 }} />
        </div>
      </div>
    );
  }

  if (!player) {
    return (
      <div className="page-shell">
        <div className="page-stack">
          <section className="panel stack">
            <span>Connexion requise pour la file auto.</span>
            <Link className="primary-button" href="/login?redirect=%2Fversus%2Fqueue">Se connecter</Link>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="page-stack">
        <section className="hero" data-onboarding-id="queue-overview">
          <h1>Versus · File auto</h1>
          <TeleprinterText text="Étape 2/3: sélection template + règle, puis entrée/sortie file." />
        </section>

        <section className="panel stack">
          <strong>Configuration matchmaking</strong>
          <label className="field" data-onboarding-id="queue-template">
            <span>Template</span>
            <select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
              {(templatesQuery.data?.templates ?? []).map((template) => (
                <option key={template.template_id} value={template.template_id}>
                  {template.label}
                </option>
              ))}
            </select>
          </label>
          <span className="muted">{selectedTemplateDescription ?? "Chargement des templates..."}</span>

          <label className="field" data-onboarding-id="queue-rule">
            <span>Règle de victoire</span>
            <select value={winnerRule} onChange={(event) => setWinnerRule(event.target.value as VersusWinnerRule)}>
              {WINNER_RULE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <span className="muted">{WINNER_RULE_OPTIONS.find((option) => option.value === winnerRule)?.description}</span>

          {!queueActive ? (
            <button
              className="primary-button"
              onClick={() => { queueStartRef.current = Date.now(); queueMutation.mutate(); }}
              disabled={queueMutation.isPending}
              data-onboarding-id="queue-action"
            >
              {queueMutation.isPending ? "Recherche..." : "⚡ Entrer en file"}
            </button>
          ) : (
            <button
              className="secondary-button"
              onClick={() => leaveMutation.mutate()}
              disabled={leaveMutation.isPending}
              data-onboarding-id="queue-action"
            >
              {leaveMutation.isPending ? "Sortie..." : "Quitter la file"}
            </button>
          )}
        </section>

        {queueActive && (
          <section className="queue-searching-box">
            <div className="queue-searching-ring" aria-hidden="true">
              <div className="queue-searching-pulse" />
            </div>
            <div className="queue-searching-text">
              <strong>Recherche d&apos;un adversaire…</strong>
              <span className="queue-searching-dots">
                <span /><span /><span />
              </span>
            </div>
            <div className="queue-searching-meta">
              <span className="muted">
                {Math.floor(elapsedS / 60).toString().padStart(2, "0")}:{(elapsedS % 60).toString().padStart(2, "0")}
              </span>
              <span className="muted">·</span>
              <span className="muted">
                {templatesQuery.data?.templates.find((t) => t.template_id === (queueContext?.templateId ?? templateId))?.label ?? (queueContext?.templateId ?? templateId)}
              </span>
            </div>
          </section>
        )}

        {error && <section className="error-box">{error}</section>}

        <section className="panel stack">
          <Link className="secondary-button" href="/versus">← Retour choix mode</Link>
        </section>

        <GuidedOnboarding
          storageKey="operation-noel-onboarding-versus-queue-v1"
          tutorialLabel="Versus file auto"
          steps={QUEUE_ONBOARDING_STEPS}
        />
      </div>
    </div>
  );
}
