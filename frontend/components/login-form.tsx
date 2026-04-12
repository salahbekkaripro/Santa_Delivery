"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import { loginPlayer } from "@/lib/api";

export function LoginForm({ redirectTo = "/" }: { redirectTo?: string }) {
  const router = useRouter();
  const { signIn } = usePlayer();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loginMutation = useMutation({
    mutationFn: loginPlayer,
    onSuccess: (nextPlayer) => {
      signIn(nextPlayer);
      if (redirectTo.startsWith("/")) {
        window.location.assign(redirectTo);
        return;
      }
      router.push("/");
    },
    onError: (mutationError: Error) => {
      setError(mutationError.message);
    }
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) {
      setError("L'email est requis.");
      return;
    }
    if (!password.trim()) {
      setError("Le mot de passe est requis.");
      return;
    }

    loginMutation.mutate({ email, password });
  }

  return (
    <div className="page-shell campaign-shell">
      <div className="page-stack campaign-stack">
        <section className="campaign-hero">
          <div className="campaign-hero-copy">
            <span className="salon-badge">Connexion joueur</span>
            <h1>Reconnecte ton compte</h1>
            <p>
              Le compte connecté servira pour la campagne, les scores enregistrés et les futurs modes compétitifs.
            </p>
          </div>
          <div className="campaign-hero-stats">
            <div className="campaign-stat-card">
              <span>Entrée</span>
              <strong>Email + mot de passe</strong>
            </div>
            <div className="campaign-stat-card">
              <span>Effet</span>
              <strong>Profil chargé en local</strong>
            </div>
          </div>
        </section>

        <form className="panel stack login-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="capitaine@pole-nord.com"
              autoComplete="email"
            />
          </label>
          <label className="field">
            <span>Mot de passe</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="8 caractères minimum"
              autoComplete="current-password"
            />
          </label>

          {error ? <div className="error-box">{error}</div> : null}

          <div className="auth-links-row">
            <Link className="secondary-button" href={`/register?redirect=${encodeURIComponent(redirectTo)}`}>
              Créer un compte
            </Link>
            <Link className="secondary-button" href="/forgot-password">
              Mot de passe oublié
            </Link>
          </div>

          <button className="primary-button" type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
