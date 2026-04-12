import type { CampaignMission, CampaignProgress, SecondaryObjectiveResult } from "@/lib/types";
import { getCampaignStorageKeyForPlayer, readStoredPlayer } from "@/lib/player";

export const CAMPAIGN_MISSIONS: CampaignMission[] = [
  {
    level: 1,
    title: "Le Marais sous contrôle",
    chapter: "Acte I · Mise en route",
    zone: "Le Marais, Paris",
    weather_key: "Clear",
    num_clients: 10,
    budget: 1500,
    sleigh_cost: 500,
    random_incidents: false,
    briefing: "Premier secteur dense. Il faut battre une IA rapide sans sur-investir dans la flotte.",
    objective: "Terminer sans surcharge et garder du budget.",
    ai_profile: "Express",
    secondary_objectives: [
      { code: "assign_all_clients", label: "Affecter tous les clients" },
      { code: "no_overload", label: "Zéro surcharge sur les traîneaux" },
      { code: "max_human_delta_s", label: "Rester à moins de 5 min de l'IA", target: 300 },
    ],
    reward_label: "Débloque Mitte",
  },
  {
    level: 2,
    title: "Mitte sous pression",
    chapter: "Acte I · Mise en route",
    zone: "Mitte, Berlin",
    weather_key: "Rain",
    num_clients: 18,
    budget: 2200,
    sleigh_cost: 550,
    random_incidents: false,
    briefing: "Le réseau se densifie et la pluie ralentit les segments les plus directs.",
    objective: "Battre l'IA sur le temps ou finir à moins de 5 min.",
    ai_profile: "Prudent",
    secondary_objectives: [
      { code: "assign_all_clients", label: "Affecter tous les clients" },
      { code: "beat_ai", label: "Battre l'IA" },
      { code: "min_score", label: "Atteindre au moins 75/100", target: 75 },
    ],
    reward_label: "Débloque Vieux-Lyon",
  },
  {
    level: 3,
    title: "Vieux-Lyon en entonnoir",
    chapter: "Acte I · Mise en route",
    zone: "Vieux Lyon, Lyon",
    weather_key: "Clear",
    num_clients: 24,
    budget: 2600,
    sleigh_cost: 600,
    random_incidents: true,
    briefing: "Les ruelles créent des goulets. Quelques incidents suffisent à casser une tournée moyenne.",
    objective: "Limiter les détours malgré les axes bloqués.",
    ai_profile: "Opportuniste",
    secondary_objectives: [
      { code: "assign_all_clients", label: "Affecter tous les clients" },
      { code: "ai_no_drop", label: "Ne laisser aucun point à l'IA" },
      { code: "no_overload", label: "Éviter toute surcharge" },
    ],
    reward_label: "Débloque Bruxelles",
  },
  {
    level: 4,
    title: "Bruxelles en pluie froide",
    chapter: "Acte II · Montée en charge",
    zone: "Quartier des Marolles, Bruxelles",
    weather_key: "Rain",
    num_clients: 28,
    budget: 3000,
    sleigh_cost: 650,
    random_incidents: true,
    briefing: "Le budget devient serré. Tu dois choisir entre vitesse et stabilité opérationnelle.",
    objective: "Finir avec du budget restant et zéro traîneau saturé.",
    ai_profile: "Écolo",
    secondary_objectives: [
      { code: "min_budget_remaining_pct", label: "Garder au moins 30% du budget", target: 30 },
      { code: "no_overload", label: "Zéro surcharge" },
      { code: "min_score", label: "Atteindre au moins 78/100", target: 78 },
    ],
    reward_label: "Débloque Bordeaux",
  },
  {
    level: 5,
    title: "Bordeaux contre la montre",
    chapter: "Acte II · Montée en charge",
    zone: "Bordeaux Centre",
    weather_key: "real",
    num_clients: 32,
    budget: 3200,
    sleigh_cost: 700,
    random_incidents: false,
    briefing: "La météo réelle met la pression. Le jeu commence à te demander de vraies décisions de répartition.",
    objective: "Rester sous le budget et battre la météo.",
    ai_profile: "Express",
    secondary_objectives: [
      { code: "assign_all_clients", label: "Affecter tous les clients" },
      { code: "max_human_delta_s", label: "Rester à moins de 3 min de l'IA", target: 180 },
      { code: "min_score", label: "Atteindre au moins 80/100", target: 80 },
    ],
    reward_label: "Débloque Montréal",
  },
  {
    level: 6,
    title: "Plateau Mont-Royal",
    chapter: "Acte II · Montée en charge",
    zone: "Le Plateau-Mont-Royal, Montréal, Québec, Canada",
    weather_key: "Snow",
    num_clients: 40,
    budget: 3800,
    sleigh_cost: 800,
    random_incidents: true,
    briefing: "La neige casse les intuitions. Il faut lisser la charge et protéger les retours dépôt.",
    objective: "Terminer la mission complète malgré la neige.",
    ai_profile: "Prudent",
    secondary_objectives: [
      { code: "assign_all_clients", label: "Affecter tous les clients" },
      { code: "ai_no_drop", label: "Forcer l'IA à tout couvrir" },
      { code: "min_score", label: "Atteindre au moins 82/100", target: 82 },
    ],
    reward_label: "Débloque Londres",
  },
  {
    level: 7,
    title: "Soho sous turbulence",
    chapter: "Acte III · Finale",
    zone: "Soho, London",
    weather_key: "Thunderstorm",
    num_clients: 46,
    budget: 4300,
    sleigh_cost: 850,
    random_incidents: true,
    briefing: "La tempête rend le plan instable. Chaque mauvais choix se paie immédiatement.",
    objective: "Conserver un score d'élite face à une IA agressive.",
    ai_profile: "Agressive",
    secondary_objectives: [
      { code: "beat_ai", label: "Battre l'IA agressive" },
      { code: "no_overload", label: "Zéro surcharge" },
      { code: "min_score", label: "Atteindre au moins 85/100", target: 85 },
    ],
    reward_label: "Débloque finale Stockholm",
  },
  {
    level: 8,
    title: "Stockholm Night Run",
    chapter: "Acte III · Finale",
    zone: "Gamla stan, Stockholm",
    weather_key: "Snow",
    num_clients: 55,
    budget: 5000,
    sleigh_cost: 900,
    random_incidents: true,
    briefing: "Finale de campagne. Densité, neige et budget tendu: il faut une exécution propre du début à la fin.",
    objective: "Atteindre le rang S et battre l'IA sur l'ensemble de la mission.",
    ai_profile: "Championne",
    secondary_objectives: [
      { code: "beat_ai", label: "Battre l'IA championne" },
      { code: "ai_no_drop", label: "Aucun point abandonné" },
      { code: "min_score", label: "Atteindre au moins 90/100", target: 90 },
    ],
    reward_label: "Couronne la campagne",
  },
];

export function getDefaultCampaignProgress(): CampaignProgress {
  return {
    unlockedLevel: 1,
    completedLevels: [],
    bestScoreByLevel: {},
    starsByLevel: {},
    objectivesCompletedByLevel: {},
    defeatedProfiles: [],
    lastPlayedLevel: null,
    updatedAt: null,
  };
}

export function getStarsForScore(score: number): number {
  if (score >= 90) {
    return 3;
  }
  if (score >= 75) {
    return 2;
  }
  if (score >= 60) {
    return 1;
  }
  return 0;
}

export function readCampaignProgress(): CampaignProgress {
  if (typeof window === "undefined") {
    return getDefaultCampaignProgress();
  }

  try {
    const raw = window.localStorage.getItem(getCampaignStorageKeyForPlayer(readStoredPlayer()?.id));
    if (!raw) {
      return getDefaultCampaignProgress();
    }

    const parsed = JSON.parse(raw) as Partial<CampaignProgress>;
    const fallback = getDefaultCampaignProgress();
    return {
      unlockedLevel: Math.max(1, Number(parsed.unlockedLevel ?? fallback.unlockedLevel)),
      completedLevels: Array.isArray(parsed.completedLevels)
        ? parsed.completedLevels.map((level) => Number(level)).filter((level) => Number.isFinite(level))
        : fallback.completedLevels,
      bestScoreByLevel: parsed.bestScoreByLevel ?? fallback.bestScoreByLevel,
      starsByLevel: parsed.starsByLevel ?? fallback.starsByLevel,
      objectivesCompletedByLevel: parsed.objectivesCompletedByLevel ?? fallback.objectivesCompletedByLevel,
      defeatedProfiles: Array.isArray(parsed.defeatedProfiles) ? parsed.defeatedProfiles : fallback.defeatedProfiles,
      lastPlayedLevel: parsed.lastPlayedLevel ?? fallback.lastPlayedLevel,
      updatedAt: parsed.updatedAt ?? fallback.updatedAt,
    };
  } catch {
    return getDefaultCampaignProgress();
  }
}

export function saveCampaignProgress(progress: CampaignProgress): CampaignProgress {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(getCampaignStorageKeyForPlayer(readStoredPlayer()?.id), JSON.stringify(progress));
  }
  return progress;
}

export function markCampaignLevelStarted(level: number): CampaignProgress {
  const current = readCampaignProgress();
  const next = {
    ...current,
    lastPlayedLevel: level,
    updatedAt: new Date().toISOString(),
  };
  return saveCampaignProgress(next);
}

export function recordCampaignCompletion(
  level: number,
  score: number,
  options?: {
    aiProfile?: string | null;
    secondaryObjectives?: SecondaryObjectiveResult[];
  }
): CampaignProgress {
  const current = readCampaignProgress();
  const previousScore = Number(current.bestScoreByLevel[level] ?? 0);
  const nextScore = Math.max(previousScore, score);
  const nextStars = Math.max(Number(current.starsByLevel[level] ?? 0), getStarsForScore(score));
  const completedObjectives = (options?.secondaryObjectives ?? []).filter((objective) => objective.completed).length;
  const previousObjectives = Number(current.objectivesCompletedByLevel[level] ?? 0);
  const completed = current.completedLevels.includes(level)
    ? current.completedLevels
    : [...current.completedLevels, level].sort((a, b) => a - b);
  const normalizedProfile = (options?.aiProfile ?? "").trim();
  const defeatedProfiles =
    normalizedProfile && !current.defeatedProfiles.includes(normalizedProfile)
      ? [...current.defeatedProfiles, normalizedProfile]
      : current.defeatedProfiles;

  const next: CampaignProgress = {
    ...current,
    completedLevels: completed,
    unlockedLevel: Math.max(current.unlockedLevel, level + 1),
    bestScoreByLevel: {
      ...current.bestScoreByLevel,
      [level]: nextScore,
    },
    starsByLevel: {
      ...current.starsByLevel,
      [level]: nextStars,
    },
    objectivesCompletedByLevel: {
      ...current.objectivesCompletedByLevel,
      [level]: Math.max(previousObjectives, completedObjectives),
    },
    defeatedProfiles: defeatedProfiles.sort((a, b) => a.localeCompare(b, "fr")),
    lastPlayedLevel: level,
    updatedAt: new Date().toISOString(),
  };

  const maxLevel = Math.max(...CAMPAIGN_MISSIONS.map((mission) => mission.level));
  next.unlockedLevel = Math.min(next.unlockedLevel, maxLevel);

  return saveCampaignProgress(next);
}

export function getCampaignMission(level: number): CampaignMission | undefined {
  return CAMPAIGN_MISSIONS.find((mission) => mission.level === level);
}

export function getCampaignCompletion(progress: CampaignProgress) {
  const totalObjectives = CAMPAIGN_MISSIONS.reduce(
    (sum, mission) => sum + (mission.secondary_objectives?.length ?? 0),
    0
  );
  const completedObjectives = Object.values(progress.objectivesCompletedByLevel).reduce(
    (sum, count) => sum + Number(count),
    0
  );
  const totalStars = Object.values(progress.starsByLevel).reduce((sum, count) => sum + Number(count), 0);
  const maxStars = CAMPAIGN_MISSIONS.length * 3;
  const isCampaignComplete = progress.completedLevels.length >= CAMPAIGN_MISSIONS.length;

  return {
    totalObjectives,
    completedObjectives,
    totalStars,
    maxStars,
    isCampaignComplete,
  };
}
