"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { usePlayer } from "@/components/player-provider";
import { registerPlayer } from "@/lib/api";

const avatarChoices = ["🎅", "🦌", "🤖", "🛷", "❄️", "🎁"];

export function RegisterForm({ redirectTo = "/" }: { redirectTo?: string }) {
  const router = useRouter();
  const { signIn } = usePlayer();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [callsign, setCallsign] = useState("");
  const [avatar, setAvatar] = useState(avatarChoices[0]);
  const [error, setError] = useState<string | null>(null);

  const registerMutation = useMutation({
    mutationFn: registerPlayer,
    onSuccess: (nextPlayer) => {
      signIn(nextPlayer);
      if (redirectTo.startsWith("/")) {
        window.location.assign(redirectTo);
        return;
      }
      router.push("/");
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!displayName.trim()) {
      setError("Le nom de joueur est requis.");
      return;
    }
    if (!email.trim()) {
      setError("L'email est requis.");
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

    registerMutation.mutate({
      display_name: displayName,
      email,
      password,
      callsign,
      avatar,
    });
  }

  return (
    <div className="page-shell campaign-shell">
      <div className="page-stack campaign-stack">
        <section className="campaign-hero">
          <div className="campaign-hero-copy">
            <span className="salon-badge">Inscription joueur</span>
            <h1>Crée un vrai compte</h1>
            <p>Le compte est enregistré en base avec email et mot de passe, puis utilisé pour la progression et les scores.</p>
          </div>
          <div className="campaign-hero-stats">
            <div className="campaign-stat-card">
              <span>Stockage</span>
              <strong>Base de données</strong>
            </div>
            <div className="campaign-stat-card">
              <span>Accès</span>
              <strong>Connexion persistée</strong>
            </div>
          </div>
        </section>

        <form className="panel stack login-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Nom de joueur</span>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Capitaine Nord" />
          </label>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="capitaine@pole-nord.com" />
          </label>
          <label className="field">
            <span>Mot de passe</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="8 caractères minimum" />
          </label>
          <label className="field">
            <span>Confirmer le mot de passe</span>
            <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Retape le mot de passe" />
          </label>
          <label className="field">
            <span>Indicatif</span>
            <input value={callsign} onChange={(event) => setCallsign(event.target.value)} placeholder="Polar-7" />
          </label>

          <div className="field">
            <span>Avatar</span>
            <div className="avatar-grid">
              {avatarChoices.map((choice) => (
                <button
                  key={choice}
                  type="button"
                  className={`avatar-button ${avatar === choice ? "is-selected" : ""}`}
                  onClick={() => setAvatar(choice)}
                >
                  {choice}
                </button>
              ))}
            </div>
          </div>

          {error ? <div className="error-box">{error}</div> : null}

          <div className="auth-links-row">
            <Link className="secondary-button" href={`/login?redirect=${encodeURIComponent(redirectTo)}`}>
              J&apos;ai déjà un compte
            </Link>
          </div>

          <button className="primary-button" type="submit" disabled={registerMutation.isPending}>
            {registerMutation.isPending ? "Création..." : "Créer le compte"}
          </button>
        </form>
      </div>
    </div>
  );
}
