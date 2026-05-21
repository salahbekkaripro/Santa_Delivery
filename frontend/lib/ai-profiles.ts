type AiProfilePreview = {
  key: string;
  label: string;
  signature: string;
  description: string;
  difficultyBonus: number;
  optimizationTarget: "time" | "distance" | "composite";
  accentClass: string;
};

const AI_PROFILE_PREVIEWS: Record<string, AiProfilePreview> = {
  express: {
    key: "express",
    label: "Express",
    signature: "Rush urbain",
    description: "Pousse la vitesse et cherche le temps minimal, même si le plan devient plus tendu.",
    difficultyBonus: 2,
    optimizationTarget: "time",
    accentClass: "profile-express",
  },
  ecolo: {
    key: "ecolo",
    label: "Écolo",
    signature: "Trajectoires sobres",
    description: "Réduit les kilomètres et le CO2, quitte à accepter des détours temporels.",
    difficultyBonus: 3,
    optimizationTarget: "distance",
    accentClass: "profile-ecolo",
  },
  prudent: {
    key: "prudent",
    label: "Prudent",
    signature: "Marge de sécurité",
    description: "Préserve les retours dépôt et encaisse mieux les incidents et les aléas météo.",
    difficultyBonus: 4,
    optimizationTarget: "time",
    accentClass: "profile-prudent",
  },
  opportuniste: {
    key: "opportuniste",
    label: "Opportuniste",
    signature: "Rebond tactique",
    description: "Réagit aux ouvertures de la carte et exploite les angles favorables au fil de la mission.",
    difficultyBonus: 4,
    optimizationTarget: "time",
    accentClass: "profile-opportuniste",
  },
  agressive: {
    key: "agressive",
    label: "Agressive",
    signature: "Pression maximale",
    description: "Joue vite et lâche plus facilement les points coûteux pour viser un finish brutal.",
    difficultyBonus: 6,
    optimizationTarget: "time",
    accentClass: "profile-agressive",
  },
  championne: {
    key: "championne",
    label: "Championne",
    signature: "Meta complète",
    description: "Combine couverture, vitesse et profondeur de recherche pour viser la meilleure note.",
    difficultyBonus: 8,
    optimizationTarget: "time",
    accentClass: "profile-championne",
  },
  adaptatif: {
    key: "adaptatif",
    label: "Adaptative",
    signature: "Mode libre",
    description: "Reprend simplement les paramètres de mission choisis par le joueur.",
    difficultyBonus: 0,
    optimizationTarget: "composite",
    accentClass: "profile-adaptatif",
  },
};

function normalizeProfile(value?: string | null) {
  return (value ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

export function getAiProfilePreview(profile?: string | null): AiProfilePreview {
  return AI_PROFILE_PREVIEWS[normalizeProfile(profile)] ?? AI_PROFILE_PREVIEWS.adaptatif;
}
