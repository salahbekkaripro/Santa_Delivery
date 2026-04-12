"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { requestPasswordReset } from "@/lib/api";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const forgotMutation = useMutation({
    mutationFn: requestPasswordReset,
    onSuccess: (payload) => {
      setStatus("Lien de réinitialisation généré.");
      if (payload.reset_url?.startsWith("/")) {
        window.location.assign(payload.reset_url);
      }
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) {
      setError("L'email est requis.");
      return;
    }
    setError(null);
    setStatus(null);
    forgotMutation.mutate({ email });
  }

  return (
    <div className="page-shell campaign-shell">
      <div className="page-stack campaign-stack">
        <section className="campaign-hero">
          <div className="campaign-hero-copy">
            <span className="salon-badge">Mot de passe oublié</span>
            <h1>Réinitialise ton accès</h1>
            <p>Entre ton email. L&apos;app génère un lien de réinitialisation stocké en base, puis t&apos;amène à la page de reset.</p>
          </div>
        </section>

        <form className="panel stack login-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="capitaine@pole-nord.com" />
          </label>

          {error ? <div className="error-box">{error}</div> : null}
          {status ? <div className="panel">{status}</div> : null}

          <div className="auth-links-row">
            <Link className="secondary-button" href="/login">
              Retour connexion
            </Link>
            <Link className="secondary-button" href="/register">
              Créer un compte
            </Link>
          </div>

          <button className="primary-button" type="submit" disabled={forgotMutation.isPending}>
            {forgotMutation.isPending ? "Génération..." : "Générer un lien de reset"}
          </button>
        </form>
      </div>
    </div>
  );
}
