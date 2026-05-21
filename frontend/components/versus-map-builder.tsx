"use client";

import { forwardRef, useEffect, useImperativeHandle, useMemo, useState } from "react";
import { SearchAreaMap } from "@/components/search-area-map";
import type { VersusMapSource, VersusMissionConfig, VersusTemplate } from "@/lib/types";
import {
  computeVersusMaxClientsAllowed,
  DEFAULT_DEMO_ADDRESS,
  DEFAULT_RADIUS_KM,
  fetchAddressSuggestions,
  geocodeFirstAddress,
  MAPBOX_TOKEN,
  SEARCH_MAX_RADIUS_KM,
  SEARCH_MIN_RADIUS_KM,
} from "@/lib/versus";

type AddressSuggestion = {
  label: string;
  lat: number;
  lon: number;
};

const WEATHER_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "real", label: "🌍 Temps réel" },
  { value: "random", label: "Aléatoire" },
  { value: "Clear", label: "Soleil" },
  { value: "Rain", label: "Pluie" },
  { value: "Snow", label: "Neige" },
  { value: "Thunderstorm", label: "Tempête" },
];

export type VersusMapBuilderHandle = {
  resolveCustomMissionConfigForSubmit: () => Promise<VersusMissionConfig | null>;
};

export type VersusMapCustomGateState = {
  isAddressLoading: boolean;
  isAddressEmpty: boolean;
  exceedsClientsLimit: boolean;
  canCreate: boolean;
};

function asNumber(value: string, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function deriveCityFromLabel(label: string): string | null {
  const chunks = label
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (chunks.length >= 2) {
    return chunks[chunks.length - 2] || null;
  }
  return chunks[0] || null;
}

export const VersusMapBuilder = forwardRef<VersusMapBuilderHandle, {
  mapSource: VersusMapSource;
  onMapSourceChange: (value: VersusMapSource) => void;
  templateId: string;
  onTemplateIdChange: (value: string) => void;
  templates: VersusTemplate[];
  customConfig: VersusMissionConfig;
  onCustomConfigChange: (value: VersusMissionConfig) => void;
  onCustomGateStateChange?: (state: VersusMapCustomGateState) => void;
}>(({
  mapSource,
  onMapSourceChange,
  templateId,
  onTemplateIdChange,
  templates,
  customConfig,
  onCustomConfigChange,
  onCustomGateStateChange,
}, ref) => {
  const [addressQuery, setAddressQuery] = useState(customConfig.zone || DEFAULT_DEMO_ADDRESS.label);
  const [selectedAddress, setSelectedAddress] = useState<AddressSuggestion | null>(() => {
    const lat = customConfig.center_lat;
    const lon = customConfig.center_lon;
    if (typeof lat === "number" && typeof lon === "number") {
      return {
        label: customConfig.zone || DEFAULT_DEMO_ADDRESS.label,
        lat,
        lon,
      };
    }
    return DEFAULT_DEMO_ADDRESS;
  });
  const [addressSuggestions, setAddressSuggestions] = useState<AddressSuggestion[]>([]);
  const [addressLookupError, setAddressLookupError] = useState<string | null>(null);
  const [isAddressLoading, setIsAddressLoading] = useState(false);
  const [isAddressFocused, setIsAddressFocused] = useState(false);

  const radiusKm = Math.min(
    SEARCH_MAX_RADIUS_KM,
    Math.max(SEARCH_MIN_RADIUS_KM, Number(customConfig.search_radius_km ?? DEFAULT_RADIUS_KM)),
  );
  const requestedClients = Math.max(1, Math.min(60, Math.round(Number(customConfig.num_clients) || 1)));
  const requestedMaxVehicles = Math.max(
    1,
    Math.min(20, requestedClients, Math.round(Number(customConfig.max_vehicles ?? Math.ceil(requestedClients / 3)) || 1)),
  );
  const limitMaxVehicles = typeof customConfig.max_vehicles === "number";
  const requestedBudget = Math.max(0, Math.round(Number(customConfig.budget) || 0));
  const requestedSleighCost = Math.max(0, Math.round(Number(customConfig.sleigh_cost) || 0));
  const areaKm2 = useMemo(() => Math.PI * radiusKm * radiusKm, [radiusKm]);
  const maxClientsAllowed = useMemo(() => computeVersusMaxClientsAllowed(radiusKm), [radiusKm]);
  const exceedsClientsLimit = requestedClients > maxClientsAllowed;
  const canAutocompleteAddress = MAPBOX_TOKEN.trim().length > 0;
  const mapCenter = selectedAddress ?? DEFAULT_DEMO_ADDRESS;
  const isAddressEmpty = addressQuery.trim().length === 0;
  const canCreateCustom = !isAddressLoading && !isAddressEmpty && !exceedsClientsLimit;

  useEffect(() => {
    if (selectedAddress && addressQuery.trim() !== selectedAddress.label) {
      setSelectedAddress(null);
    }
  }, [addressQuery, selectedAddress]);

  useEffect(() => {
    onCustomGateStateChange?.({
      isAddressLoading,
      isAddressEmpty,
      exceedsClientsLimit,
      canCreate: canCreateCustom,
    });
  }, [canCreateCustom, exceedsClientsLimit, isAddressEmpty, isAddressLoading, onCustomGateStateChange]);

  useEffect(() => {
    const query = addressQuery.trim();
    if (!canAutocompleteAddress || query.length < 3 || mapSource !== "custom") {
      setAddressSuggestions([]);
      setIsAddressLoading(false);
      setAddressLookupError(null);
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      setIsAddressLoading(true);
      setAddressLookupError(null);
      try {
        const suggestions = await fetchAddressSuggestions(query);
        setAddressSuggestions(suggestions);
      } catch {
        setAddressSuggestions([]);
        setAddressLookupError("Impossible de charger les suggestions d'adresse pour le moment.");
      } finally {
        setIsAddressLoading(false);
      }
    }, 280);

    return () => window.clearTimeout(timeoutId);
  }, [addressQuery, canAutocompleteAddress, mapSource]);

  function selectAddressSuggestion(suggestion: AddressSuggestion) {
    setSelectedAddress(suggestion);
    setAddressQuery(suggestion.label);
    setAddressSuggestions([]);
    setAddressLookupError(null);
    setIsAddressFocused(false);

    onCustomConfigChange({
      ...customConfig,
      zone: suggestion.label,
      city: deriveCityFromLabel(suggestion.label),
      center_lat: suggestion.lat,
      center_lon: suggestion.lon,
      search_radius_km: radiusKm,
      num_clients: requestedClients,
      budget: requestedBudget,
      sleigh_cost: requestedSleighCost,
    });
  }

  useImperativeHandle(ref, () => ({
    async resolveCustomMissionConfigForSubmit() {
      if (mapSource !== "custom") {
        return null;
      }
      if (exceedsClientsLimit) {
        throw new Error(
          `La zone actuelle autorise au maximum ${maxClientsAllowed} colis. Réduis la demande ou augmente le rayon.`,
        );
      }

      let resolvedAddress = selectedAddress;
      const query = addressQuery.trim();

      if (!resolvedAddress) {
        if (!query) {
          throw new Error("Saisis une adresse pour configurer le point central de la carte custom.");
        }
        if (!canAutocompleteAddress) {
          throw new Error(
            "Le geocodage d'adresse est indisponible: variable NEXT_PUBLIC_MAPBOX_TOKEN manquante.",
          );
        }

        setIsAddressLoading(true);
        const geocoded = await geocodeFirstAddress(query);
        setIsAddressLoading(false);

        if (!geocoded) {
          throw new Error("Impossible de géocoder cette adresse. Affine la saisie ou sélectionne une suggestion.");
        }
        resolvedAddress = geocoded;
        setSelectedAddress(geocoded);
        setAddressQuery(geocoded.label);
      }

      const nextMissionConfig: VersusMissionConfig = {
        ...customConfig,
        zone: resolvedAddress.label,
        city: deriveCityFromLabel(resolvedAddress.label),
        center_lat: resolvedAddress.lat,
        center_lon: resolvedAddress.lon,
        search_radius_km: radiusKm,
        num_clients: requestedClients,
        max_vehicles: limitMaxVehicles ? requestedMaxVehicles : undefined,
        budget: requestedBudget,
        sleigh_cost: requestedSleighCost,
      };
      onCustomConfigChange(nextMissionConfig);
      return nextMissionConfig;
    },
  }), [
    addressQuery,
    canAutocompleteAddress,
    customConfig,
    exceedsClientsLimit,
    mapSource,
    maxClientsAllowed,
    onCustomConfigChange,
    radiusKm,
    requestedBudget,
    requestedClients,
    requestedMaxVehicles,
    requestedSleighCost,
    selectedAddress,
    limitMaxVehicles,
  ]);

  return (
    <div className="stack">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          type="button"
          className={mapSource === "template" ? "primary-button" : "secondary-button"}
          onClick={() => onMapSourceChange("template")}
        >
          Template
        </button>
        <button
          type="button"
          className={mapSource === "custom" ? "primary-button" : "secondary-button"}
          onClick={() => onMapSourceChange("custom")}
        >
          Map custom
        </button>
      </div>

      {mapSource === "template" ? (
        <label className="field">
          <span>Template</span>
          <select value={templateId} onChange={(event) => onTemplateIdChange(event.target.value)}>
            {templates.map((template) => (
              <option key={template.template_id} value={template.template_id}>
                {template.label}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <>
          <div className="grid-2" style={{ gap: 10 }}>
            <label className="field">
              <span>Adresse (point central)</span>
              <div className="address-field-wrap">
                <input
                  type="text"
                  value={addressQuery}
                  onChange={(event) => setAddressQuery(event.target.value)}
                  onFocus={() => setIsAddressFocused(true)}
                  onBlur={() => window.setTimeout(() => setIsAddressFocused(false), 120)}
                  placeholder="Tape une adresse complète"
                />
                {isAddressFocused && canAutocompleteAddress ? (
                  <div className="address-suggestions">
                    {isAddressLoading ? <div className="address-suggestion-muted">Recherche en cours...</div> : null}
                    {!isAddressLoading && addressSuggestions.length > 0
                      ? addressSuggestions.map((suggestion) => (
                          <button
                            key={`${suggestion.label}-${suggestion.lat}-${suggestion.lon}`}
                            type="button"
                            className="address-suggestion-item"
                            onMouseDown={(event) => {
                              event.preventDefault();
                              selectAddressSuggestion(suggestion);
                            }}
                          >
                            {suggestion.label}
                          </button>
                        ))
                      : null}
                    {!isAddressLoading && addressSuggestions.length === 0 && addressQuery.trim().length >= 3 ? (
                      <div className="address-suggestion-muted">Aucune suggestion pour cette saisie.</div>
                    ) : null}
                    {addressLookupError ? <div className="address-suggestion-error">{addressLookupError}</div> : null}
                  </div>
                ) : null}
              </div>
            </label>
            <label className="field">
              <span>Météo</span>
              <select
                value={customConfig.weather_key}
                onChange={(event) => onCustomConfigChange({ ...customConfig, weather_key: event.target.value })}
              >
                {WEATHER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Rayon de recherche ({radiusKm.toFixed(1)} km)</span>
              <input
                type="range"
                min={SEARCH_MIN_RADIUS_KM}
                max={SEARCH_MAX_RADIUS_KM}
                step={0.1}
                value={radiusKm}
                onChange={(event) =>
                  onCustomConfigChange({
                    ...customConfig,
                    search_radius_km: Number(event.target.value),
                  })
                }
              />
            </label>
            <label className="field">
              <span>Nombre de colis</span>
              <input
                type="number"
                min={1}
                max={60}
                value={requestedClients}
                onChange={(event) =>
                  onCustomConfigChange({
                    ...customConfig,
                    num_clients: Math.max(1, Math.min(60, Math.round(asNumber(event.target.value, requestedClients)))),
                  })
                }
              />
            </label>
            <label className="field">
              <span>Cap max traîneaux (optionnel)</span>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <label className={`tag ${limitMaxVehicles ? "is-selected" : ""}`} style={{ cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={limitMaxVehicles}
                    onChange={(event) =>
                      onCustomConfigChange({
                        ...customConfig,
                        max_vehicles: event.target.checked ? requestedMaxVehicles : undefined,
                      })
                    }
                  />
                  &nbsp;Limiter
                </label>
                <input
                  type="number"
                  min={1}
                  max={Math.min(20, requestedClients)}
                  value={requestedMaxVehicles}
                  disabled={!limitMaxVehicles}
                  onChange={(event) =>
                    onCustomConfigChange({
                      ...customConfig,
                      max_vehicles: Math.max(
                        1,
                        Math.min(20, requestedClients, Math.round(asNumber(event.target.value, requestedMaxVehicles))),
                      ),
                    })
                  }
                  style={{ maxWidth: 110 }}
                />
              </div>
            </label>
            <label className="field">
              <span>Budget</span>
              <input
                type="number"
                min={0}
                value={requestedBudget}
                onChange={(event) =>
                  onCustomConfigChange({
                    ...customConfig,
                    budget: Math.max(0, Math.round(asNumber(event.target.value, requestedBudget))),
                  })
                }
              />
            </label>
            <label className="field">
              <span>Coût traîneau</span>
              <input
                type="number"
                min={0}
                value={requestedSleighCost}
                onChange={(event) =>
                  onCustomConfigChange({
                    ...customConfig,
                    sleigh_cost: Math.max(0, Math.round(asNumber(event.target.value, requestedSleighCost))),
                  })
                }
              />
            </label>
          </div>

          {!canAutocompleteAddress ? (
            <div className="error-box">
              L&apos;autocomplétion et le géocodage d&apos;adresse sont indisponibles: variable
              `NEXT_PUBLIC_MAPBOX_TOKEN` manquante.
            </div>
          ) : null}

          <div className="salon-zone-metrics">
            <div className="salon-zone-metric">
              <span>Adresse sélectionnée</span>
              <strong>{selectedAddress?.label ?? (addressQuery.trim() || "Saisie en cours")}</strong>
            </div>
            <div className="salon-zone-metric">
              <span>Surface couverte</span>
              <strong>{areaKm2.toFixed(1)} km²</strong>
            </div>
            <div className="salon-zone-metric">
              <span>Maximum colis autorisé</span>
              <strong>{maxClientsAllowed}</strong>
            </div>
            <div className="salon-zone-metric">
              <span>Demande actuelle</span>
              <strong className={exceedsClientsLimit ? "salon-limit-breach" : undefined}>{requestedClients}</strong>
            </div>
          </div>

          <SearchAreaMap centerLat={mapCenter.lat} centerLon={mapCenter.lon} radiusKm={radiusKm} />

          {exceedsClientsLimit ? (
            <div className="error-box">
              La zone actuelle autorise au maximum {maxClientsAllowed} colis. Réduis la demande ou augmente le rayon.
            </div>
          ) : (
            <div className="tag" style={{ width: "fit-content" }}>
              Zone valide: la génération restera dans le cercle choisi.
            </div>
          )}

          <label className="tag" style={{ width: "fit-content" }}>
            <input
              type="checkbox"
              checked={customConfig.random_incidents}
              onChange={(event) => onCustomConfigChange({ ...customConfig, random_incidents: event.target.checked })}
            />
            Incidents aléatoires
          </label>
        </>
      )}
    </div>
  );
});

VersusMapBuilder.displayName = "VersusMapBuilder";
