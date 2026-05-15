# Scenario Mission: Tempete de neige

## Objectif de demo
Montrer que l'interface reste lisible, reactive et orientee decision meme quand la mission bascule en mode crise (meteo extreme + incidents simultanes).

## Setup mission
- Zone: Plateau-Mont-Royal (Montreal)
- Profil IA: `Championne (Secteurs)`
- Meteo: `Snow` avec facteur de ralentissement severe
- Clients: 34
- Budget: 3800
- Cout par traineau: 800
- Incidents aleatoires: actifs
- Heure de depart: 06:30

## Chronologie operationnelle

### Phase 1 - Lancement (T+0 a T+8 min)
- Neige dense, vitesse moyenne en baisse.
- L'IA propose une sectorisation initiale pour limiter les croisements inter-routes.
- Le joueur valide les premieres routes avec marges de capacite conservatrices.

### Phase 2 - Crise locale (T+9 a T+20 min)
- Incident 1: axe principal bloque (congestion + deneigement prioritaire).
- Incident 2: micro-coupure sur une zone de communication (retards de confirmation).
- Incident 3: surcharge temporaire d'un traineau apres reaffectation d'urgence.
- L'interface doit afficher:
  - segments impactes,
  - deltas ETA,
  - risques de surcharge,
  - options de reroutage faisables.

### Phase 3 - Replanification (T+21 a T+35 min)
- Replanification automatique OR-Tools + ajustement manuel du joueur.
- Priorisation des livraisons critiques (fenetres horaires courtes).
- Compensation des retards avec redistribution de charge sur les traineaux stables.

### Phase 4 - Stabilisation (T+36 a fin)
- Retour progressif a une mission stable.
- Les KPI de fin doivent montrer:
  - maintien de la couverture client,
  - nombre limite de points ignores,
  - derive temps/distance sous controle.

## Elements de resilience a montrer au jury
- Vision immediate des incidents sur la carte (avant/apres reroutage).
- Comparaison de strategie (`Glouton` vs `OR-Tools`) sur le debrief.
- Alertes capacite explicites (charge, surcharge, marge restante).
- Continuites UX en mode degrade: pas de blocage ecran, actions prioritaires accessibles.
- Debrief final avec KPI clairs: distance, poids livre, vehicules engages, points non servis.

## KPI cibles pour une mission reussie
- Points servis: >= 90%
- Taux de surcharge: <= 5%
- Ecart temps vs plan initial: <= +20%
- Replanifications manuelles: <= 3
- Score final de mission: >= 75/100

## Narration demo (pitch court)
"La tempete coupe nos marges de manoeuvre, mais pas notre capacite de pilotage. L'interface garde le controle decisionnel: elle signale, priorise, replannifie et prouve en fin de mission que la performance reste mesurable et defendable."
