# Operation Noel

## Authentification et navigation

Ce document résume le système de compte joueur et la structure des pages du frontend.

## Comptes joueurs

Les joueurs sont stockés en base SQLite dans la table `players`.

Champs principaux:
- `player_id`
- `display_name`
- `email`
- `password_hash`
- `callsign`
- `avatar`
- `last_login_at`
- `created_at`
- `updated_at`

Les mots de passe sont hashés côté backend avec `PBKDF2-SHA256`.

## Réinitialisation du mot de passe

Le flux "mot de passe oublié" repose sur la table `password_reset_tokens`.

Champs principaux:
- `player_id`
- `token_hash`
- `expires_at`
- `consumed_at`
- `created_at`

Flux:
1. Le joueur saisit son email sur `/forgot-password`.
2. Le backend génère un token de reset et l’enregistre en base.
3. L’application ouvre `/reset-password?token=...`.
4. Le joueur définit un nouveau mot de passe.

Note:
- Le projet génère actuellement un lien de reset dans l’application.
- Il n’y a pas encore d’envoi d’email SMTP.

## Routes frontend

Routes principales:
- `/` : landing page légère
- `/register` : inscription
- `/login` : connexion
- `/forgot-password` : demande de réinitialisation
- `/reset-password` : définition d’un nouveau mot de passe
- `/campaign` : carte de campagne
- `/campaign/finale` : écran final de campagne
- `/versus` : base du mode direct joueur contre joueur
- `/salon` : hub visuel / démo / lancement rapide
- `/leaderboard` : Panthéon

Routes mission:
- `/mission/[id]`
- `/mission/[id]/results`
- `/mission/[id]/debrief`

## Pourquoi cette séparation

L’accueil ne doit pas concentrer toute l’application.

La structure actuelle sépare:
- l’entrée produit
- l’authentification
- le mode salon
- la campagne
- le versus
- les écrans de mission

Cela rend:
- la navigation plus lisible
- les flux plus clairs
- le projet plus simple à faire évoluer

## Endpoints backend

Authentification:
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`

Joueurs:
- `POST /api/players`
- `GET /api/players/{player_id}`

Classement:
- `GET /api/leaderboard`
- `POST /api/missions/{mission_id}/leaderboard`

## Limites actuelles

- Pas encore de session sécurisée côté backend
- Pas encore de cookie ou token d’auth persistant serveur
- Pas encore d’email réel pour le reset
- Le profil compte n’a pas encore sa page dédiée `/account`

## Suite logique

Étapes recommandées:
1. Ajouter une page `/account`
2. Permettre la modification email / mot de passe / avatar
3. Ajouter un vrai provider email pour le reset
4. Sécuriser davantage les actions liées au leaderboard et au versus
