"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import { resetPassword } from "@/lib/api";

export function ResetPasswordForm({ token = "" }: { token?: string }) {
  const router = useRouter();
  const { signIn } = usePlayer();
  const [currentToken, setCurrentToken] = useState(token);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const resetMutation = useMutation({
    mutationFn: resetPassword,
    onSuccess: (nextPlayer) => {
      signIn(nextPlayer);
      router.push("/");
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!currentToken.trim()) {
      setError("Le token de réinitialisation est requis.");
      return;
    }
    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    setError(null);
    resetMutation.mutate({ token: currentToken, password });
  }

  return (
    <div className="page-shell campaign-shell">
      <div className="page-stack campaign-stack">
        <section className="campaign-hero">
          <div className="campaign-hero-copy">
            <span className="salon-badge">Nouveau mot de passe</span>
            <h1>Finalise la réinitialisation</h1>
            <p>Le token vient du flux “mot de passe oublié”. Une fois validé, le compte est reconnecté localement.</p>
          </div>
        </section>

        <form className="panel stack login-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Token de réinitialisation</span>
            <input value={currentToken} onChange={(event) => setCurrentToken(event.target.value)} placeholder="Colle le token ou viens depuis le lien généré" />
          </label>
          <label className="field">
            <span>Nouveau mot de passe</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="8 caractères minimum" />
          </label>
          <label className="field">
            <span>Confirmer le mot de passe</span>
            <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Retape le mot de passe" />
          </label>

          {error ? <div className="error-box">{error}</div> : null}

          <div className="auth-links-row">
            <Link className="secondary-button" href="/login">
              Retour connexion
            </Link>
          </div>

          <button className="primary-button" type="submit" disabled={resetMutation.isPending}>
            {resetMutation.isPending ? "Mise à jour..." : "Définir le nouveau mot de passe"}
          </button>
        </form>
      </div>
    </div>
  );
}
