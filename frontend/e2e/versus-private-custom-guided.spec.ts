import { expect, test } from "@playwright/test";

const PLAYER_STORAGE_KEY = "operation-noel-current-player";

const templatesResponse = {
  templates: [
    {
      template_id: "paris_duel",
      label: "Paris Rush",
      description: "Duel urbain rapide sans incidents.",
    },
  ],
};

function matchStatePayload() {
  return {
    match_id: "match-e2e-1",
    mode: "private",
    template_id: "custom_map",
    map_source: "custom",
    mission_summary: {
      map_source: "custom",
      template_id: "custom_map",
      template_label: "Custom · London",
      zone: "London",
      num_clients: 30,
      weather_key: "Clear",
      budget: 3000,
      sleigh_cost: 500,
    },
    template_label: "Custom · London",
    winner_rule: "score_time",
    join_code: "ABC123",
    host_player_id: "e2e-player",
    status: "waiting_opponent",
    participants: [
      {
        player_id: "e2e-player",
        display_name: "E2E Player",
        seat: 0,
        state: "joined",
        mission_id: null,
        is_self: true,
      },
    ],
    current_player_mission_id: null,
    created_at: "2026-04-24T12:00:00+00:00",
    updated_at: "2026-04-24T12:00:00+00:00",
  };
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(([storageKey]) => {
    window.localStorage.setItem(
      storageKey,
      JSON.stringify({
        id: "e2e-player",
        display_name: "E2E Player",
        callsign: null,
        avatar: null,
        created_at: new Date().toISOString(),
      }),
    );
  }, [PLAYER_STORAGE_KEY]);

  await page.route("http://localhost:8000/api/versus/templates", async (route) => {
    await route.fulfill({ json: templatesResponse });
  });

  await page.route("http://localhost:8000/api/versus/matches/match-e2e-1/state*", async (route) => {
    await route.fulfill({ json: matchStatePayload() });
  });
});

test("blocks create when custom address input is empty", async ({ page }) => {
  await page.goto("/versus/private");

  await page.getByRole("button", { name: "Map custom" }).click();
  await page.getByPlaceholder("Tape une adresse complète").fill("");

  await expect(page.getByRole("button", { name: "Créer la partie" })).toBeDisabled();
  await expect(page.getByText("Renseigne une adresse pour créer la partie custom.")).toBeVisible();
});

test("creates custom match with selected suggestion", async ({ page }) => {
  let createPayload: any = null;

  await page.route("**/geocoding/v5/mapbox.places/*", async (route) => {
    const url = new URL(route.request().url());
    const isAutocomplete = url.searchParams.get("autocomplete") === "true";
    if (!isAutocomplete) {
      await route.fulfill({ json: { features: [] } });
      return;
    }
    await route.fulfill({
      json: {
        features: [
          {
            place_name: "221B Baker Street, London, United Kingdom",
            center: [-0.1586, 51.5237],
          },
        ],
      },
    });
  });

  await page.route("http://localhost:8000/api/versus/matches", async (route) => {
    createPayload = JSON.parse(route.request().postData() ?? "{}");
    await route.fulfill({ json: matchStatePayload() });
  });

  await page.goto("/versus/private");
  await page.getByRole("button", { name: "Map custom" }).click();

  const addressInput = page.getByPlaceholder("Tape une adresse complète");
  await addressInput.fill("Baker");
  await page.locator(".address-suggestion-item").first().dispatchEvent("mousedown");
  await page.getByRole("button", { name: "Créer la partie" }).click();

  await expect.poll(() => createPayload !== null).toBeTruthy();
  expect(createPayload.map_source).toBe("custom");
  expect(createPayload.mission_config.zone).toBe("221B Baker Street, London, United Kingdom");
  expect(createPayload.mission_config.center_lat).toBe(51.5237);
  expect(createPayload.mission_config.center_lon).toBe(-0.1586);
});

test("resolves custom address by fallback geocoding on submit", async ({ page }) => {
  let createPayload: any = null;

  await page.route("**/geocoding/v5/mapbox.places/*", async (route) => {
    const url = new URL(route.request().url());
    const isAutocomplete = url.searchParams.get("autocomplete") === "true";
    if (isAutocomplete) {
      await route.fulfill({ json: { features: [] } });
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 220));
    await route.fulfill({
      json: {
        features: [
          {
            place_name: "10 Rue de Rivoli, Paris, France",
            center: [2.3522, 48.8566],
          },
        ],
      },
    });
  });

  await page.route("http://localhost:8000/api/versus/matches", async (route) => {
    createPayload = JSON.parse(route.request().postData() ?? "{}");
    await route.fulfill({ json: matchStatePayload() });
  });

  await page.goto("/versus/private");
  await page.getByRole("button", { name: "Map custom" }).click();

  const addressInput = page.getByPlaceholder("Tape une adresse complète");
  await addressInput.fill("10 Rue de Rivoli Paris");

  await page.getByRole("button", { name: "Créer la partie" }).click();

  await expect.poll(() => createPayload !== null).toBeTruthy();
  expect(createPayload.mission_config.zone).toBe("10 Rue de Rivoli, Paris, France");
  expect(createPayload.mission_config.center_lat).toBe(48.8566);
  expect(createPayload.mission_config.center_lon).toBe(2.3522);
});

test("disables create while address lookup is in progress", async ({ page }) => {
  await page.route("**/geocoding/v5/mapbox.places/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("autocomplete") !== "true") {
      await route.fulfill({ json: { features: [] } });
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.fulfill({ json: { features: [] } });
  });

  await page.goto("/versus/private");
  await page.getByRole("button", { name: "Map custom" }).click();
  await page.getByPlaceholder("Tape une adresse complète").fill("London");

  await expect(page.getByRole("button", { name: "Créer la partie" })).toBeDisabled();
  await expect(page.getByText("Géocodage en cours... patiente avant de créer.")).toBeVisible();
});
