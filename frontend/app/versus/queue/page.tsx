"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import { enterVersusQueue, getVersusTemplates, leaveVersusQueue } from "@/lib/api";
import type { VersusWinnerRule } from "@/lib/types";
import { WINNER_RULE_OPTIONS } from "@/lib/versus";

export default function VersusQueuePage() {
  const router = useRouter();
  const { player, isReady } = usePlayer();

  const [templateId, setTemplateId] = useState("paris_duel");
  const [winnerRule, setWinnerRule] = useState<VersusWinnerRule>("score_time");
  const [queueActive, setQueueActive] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
        setFeedback("Adversaire trouvé.");
        router.push(`/versus/match/${payload.match.match_id}`);
        return;
      }
      setQueueActive(true);
      setFeedback("En file d'attente. Recherche en cours...");
    },
    onError: (err: Error) => setError(err.message),
  });

  const leaveMutation = useMutation({
    mutationFn: () => leaveVersusQueue({ player_id: player!.id }),
    onSuccess: () => {
      setQueueActive(false);
      setError(null);
      setFeedback("Vous avez quitté la file.");
    },
    onError: (err: Error) => setError(err.message),
  });

  useEffect(() => {
    if (!queueActive || !player?.id) {
      return;
    }
    const timer = window.setInterval(() => {
      if (!queueMutation.isPending) {
        queueMutation.mutate();
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [player?.id, queueActive, queueMutation]);

  if (!isReady) {
    return <div className="page-shell"><div className="page-stack"><div className="panel">Chargement...</div></div></div>;
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
        <section className="hero">
          <h1>Versus · File auto</h1>
          <p>Étape 2/3: sélection template + règle, puis entrée/sortie file.</p>
        </section>

        <section className="panel stack">
          <strong>Configuration matchmaking</strong>
          <label className="field">
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

          <label className="field">
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
            <button className="primary-button" onClick={() => queueMutation.mutate()} disabled={queueMutation.isPending}>
              {queueMutation.isPending ? "Recherche..." : "Entrer en file"}
            </button>
          ) : (
            <button className="secondary-button" onClick={() => leaveMutation.mutate()} disabled={leaveMutation.isPending}>
              {leaveMutation.isPending ? "Sortie..." : "Quitter la file"}
            </button>
          )}
        </section>

        {(feedback || error) && (
          <section className={error ? "error-box" : "panel"}>
            {error ?? feedback}
          </section>
        )}

        <section className="panel stack">
          <Link className="secondary-button" href="/versus">← Retour choix mode</Link>
        </section>
      </div>
    </div>
  );
}
