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

const invitesResponse = { invites: [] };

function createInviteResponse() {
  return {
    invite: {
      invite_id: "invite-e2e-1",
      inviter_player_id: "e2e-player",
      invitee_player_id: "target-player",
      template_id: "custom_map",
      map_source: "custom",
      mission_summary: {
        map_source: "custom",
        template_id: "custom_map",
        template_label: "Custom · Paris",
        zone: "Paris",
        num_clients: 30,
        weather_key: "Clear",
        budget: 3000,
        sleigh_cost: 500,
      },
      winner_rule: "score_time",
      status: "pending",
      created_at: "2026-04-24T12:00:00+00:00",
      updated_at: "2026-04-24T12:00:00+00:00",
    },
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

  await page.route("http://localhost:8000/api/versus/invites*", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: invitesResponse });
      return;
    }
    await route.continue();
  });
});

test("blocks invite send when custom address input is empty", async ({ page }) => {
  await page.goto("/versus/invite");

  await page.getByRole("button", { name: "Map custom" }).click();
  await page.getByPlaceholder("player_id").fill("target-player");
  await page.getByPlaceholder("Tape une adresse complète").fill("");

  await expect(page.getByRole("button", { name: "Envoyer l'invitation" })).toBeDisabled();
  await expect(page.getByText("Renseigne une adresse pour créer une invitation custom.")).toBeVisible();
});

test("creates custom invite payload with selected suggestion", async ({ page }) => {
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

  await page.route("http://localhost:8000/api/versus/invites", async (route) => {
    createPayload = JSON.parse(route.request().postData() ?? "{}");
    await route.fulfill({ json: createInviteResponse() });
  });

  await page.goto("/versus/invite");
  await page.getByRole("button", { name: "Map custom" }).click();
  await page.getByPlaceholder("player_id").fill("target-player");

  const addressInput = page.getByPlaceholder("Tape une adresse complète");
  await addressInput.fill("Baker");
  await page.locator(".address-suggestion-item").first().dispatchEvent("mousedown");
  await page.getByRole("button", { name: "Envoyer l'invitation" }).click();

  await expect.poll(() => createPayload !== null).toBeTruthy();
  expect(createPayload.map_source).toBe("custom");
  expect(createPayload.invitee_player_id).toBe("target-player");
  expect(createPayload.mission_config.zone).toBe("221B Baker Street, London, United Kingdom");
  expect(createPayload.mission_config.center_lat).toBe(51.5237);
  expect(createPayload.mission_config.center_lon).toBe(-0.1586);
  await expect(page.getByText("Invitation envoyée.")).toBeVisible();
});

test("resolves invite custom address by fallback geocoding on submit", async ({ page }) => {
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

  await page.route("http://localhost:8000/api/versus/invites", async (route) => {
    createPayload = JSON.parse(route.request().postData() ?? "{}");
    await route.fulfill({ json: createInviteResponse() });
  });

  await page.goto("/versus/invite");
  await page.getByRole("button", { name: "Map custom" }).click();
  await page.getByPlaceholder("player_id").fill("target-player");

  await page.getByPlaceholder("Tape une adresse complète").fill("10 Rue de Rivoli Paris");
  await page.getByRole("button", { name: "Envoyer l'invitation" }).click();

  await expect.poll(() => createPayload !== null).toBeTruthy();
  expect(createPayload.mission_config.zone).toBe("10 Rue de Rivoli, Paris, France");
  expect(createPayload.mission_config.center_lat).toBe(48.8566);
  expect(createPayload.mission_config.center_lon).toBe(2.3522);
});

test("blocks invite send when custom demand exceeds zone capacity", async ({ page }) => {
  await page.goto("/versus/invite");
  await page.getByRole("button", { name: "Map custom" }).click();
  await page.getByPlaceholder("player_id").fill("target-player");

  await page.locator('label:has-text("Nombre de colis") input').fill("60");

  await expect(page.getByRole("button", { name: "Envoyer l'invitation" })).toBeDisabled();
  await expect(page.getByText(/La zone actuelle autorise au maximum/)).toBeVisible();
});

test("disables invite send while address lookup is in progress", async ({ page }) => {
  await page.route("**/geocoding/v5/mapbox.places/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("autocomplete") !== "true") {
      await route.fulfill({ json: { features: [] } });
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.fulfill({ json: { features: [] } });
  });

  await page.goto("/versus/invite");
  await page.getByRole("button", { name: "Map custom" }).click();
  await page.getByPlaceholder("player_id").fill("target-player");
  await page.getByPlaceholder("Tape une adresse complète").fill("London");

  await expect(page.getByRole("button", { name: "Envoyer l'invitation" })).toBeDisabled();
  await expect(page.getByText("Géocodage en cours... patiente avant l'envoi.")).toBeVisible();
});
