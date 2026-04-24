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
    if (!displayName.trim()) { setError("Le nom de joueur est requis."); return; }
    if (!email.trim()) { setError("L'email est requis."); return; }
    if (password.length < 8) { setError("Le mot de passe doit contenir au moins 8 caractères."); return; }
    if (password !== confirmPassword) { setError("Les mots de passe ne correspondent pas."); return; }
    registerMutation.mutate({ display_name: displayName, email, password, callsign, avatar });
  }

  return (
    <div className="auth-shell">
      <div className="auth-card auth-card-wide">
        <div className="auth-card-hero">
          <span className="auth-card-icon">🎄</span>
          <h1>Rejoins le Pôle Nord</h1>
          <p>Crée ton compte pour débloquer la campagne complète, sauvegarder tes scores et entrer au Panthéon.</p>
          <div className="auth-snowflakes">
            <span>⭐</span><span>❄️</span><span>🎁</span><span>❄️</span><span>⭐</span>
          </div>
        </div>
        <div className="auth-card-body">
          <form onSubmit={handleSubmit} className="auth-form auth-form-gap-md">
            <label className="field">
              <span>Nom de joueur</span>
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Capitaine Nord"
              />
            </label>
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="capitaine@pole-nord.com"
              />
            </label>
            <label className="field">
              <span>Mot de passe</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="8 caractères minimum"
              />
            </label>
            <label className="field">
              <span>Confirmer le mot de passe</span>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Retape le mot de passe"
              />
            </label>
            <label className="field">
              <span>Indicatif <span className="muted auth-muted-note">(optionnel)</span></span>
              <input
                value={callsign}
                onChange={(e) => setCallsign(e.target.value)}
                placeholder="Polar-7"
              />
            </label>

            <div className="field">
              <span>Choisis ton avatar</span>
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

            {error && <div className="error-box">{error}</div>}

            <button className="primary-button" type="submit" disabled={registerMutation.isPending}>
              {registerMutation.isPending ? "Création…" : "🎅 Créer mon compte"}
            </button>

            <div className="auth-center">
              <Link className="secondary-button" href={`/login?redirect=${encodeURIComponent(redirectTo)}`}>
                J&apos;ai déjà un compte →
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
