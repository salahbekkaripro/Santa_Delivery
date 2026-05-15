"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signIn as nextAuthSignIn } from "next-auth/react";
import { FormEvent, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import { loginPlayer } from "@/lib/api";

export function LoginForm({ redirectTo = "/" }: { redirectTo?: string }) {
  const router = useRouter();
  const { signIn } = usePlayer();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [oauthPending, setOauthPending] = useState<"google" | "github" | null>(null);
  const googleEnabled = process.env.NEXT_PUBLIC_AUTH_GOOGLE_ENABLED === "1";
  const githubEnabled = process.env.NEXT_PUBLIC_AUTH_GITHUB_ENABLED === "1";

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
    onError: (mutationError: Error) => setError(mutationError.message)
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) { setError("L'email est requis."); return; }
    if (!password.trim()) { setError("Le mot de passe est requis."); return; }
    loginMutation.mutate({ email, password });
  }

  async function handleOAuthSignIn(provider: "google" | "github") {
    try {
      setError(null);
      setOauthPending(provider);
      await nextAuthSignIn(provider, {
        callbackUrl: redirectTo.startsWith("/") ? redirectTo : "/",
      });
    } catch (oauthError) {
      setError(oauthError instanceof Error ? oauthError.message : "Impossible de lancer la connexion OAuth.");
      setOauthPending(null);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-card-hero">
          <span className="auth-card-icon">🎅</span>
          <h1>Bon retour</h1>
          <p>Connecte-toi pour reprendre ta campagne et sauvegarder tes scores au Panthéon.</p>
          <div className="auth-snowflakes">
            <span>❄️</span><span>🎄</span><span>⭐</span><span>🎄</span><span>❄️</span>
          </div>
        </div>
        <div className="auth-card-body">
          <form onSubmit={handleSubmit} className="auth-form auth-form-gap-lg">
            <div className="auth-links-row auth-links-row-center">
              {googleEnabled && (
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => handleOAuthSignIn("google")}
                  disabled={oauthPending !== null}
                >
                  {oauthPending === "google" ? "Connexion Google..." : "Continuer avec Google"}
                </button>
              )}
              {githubEnabled && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => handleOAuthSignIn("github")}
                  disabled={oauthPending !== null}
                >
                  {oauthPending === "github" ? "Connexion GitHub..." : "Continuer avec GitHub"}
                </button>
              )}
            </div>
            <span className="muted auth-muted-note">ou connexion locale</span>

            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="capitaine@pole-nord.com"
                autoComplete="email"
              />
            </label>
            <label className="field">
              <span>Mot de passe</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </label>

            {error && <div className="error-box">{error}</div>}

            <button className="primary-button" type="submit" disabled={loginMutation.isPending}>
              {loginMutation.isPending ? "Connexion…" : "Se connecter →"}
            </button>

            <div className="auth-links-row auth-links-row-center">
              <Link className="secondary-button" href={`/register?redirect=${encodeURIComponent(redirectTo)}`}>
                Créer un compte
              </Link>
              <Link className="secondary-button" href="/forgot-password">
                Mot de passe oublié ?
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
