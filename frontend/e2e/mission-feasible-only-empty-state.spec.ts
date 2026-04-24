import { expect, test } from "@playwright/test";

const missionPayload = {
  mission_id: "e2e-mission",
  mission: {
    zone: "Paris 5e",
    num_clients: 2,
    budget: 500,
    sleigh_cost: 50,
    weather_key: "Clear",
    random_incidents: false,
    level: null,
    ai_profile: "express",
    secondary_objectives: [],
  },
  depot: { id: 0, lat: 48.85, lon: 2.35, nom_client: "Depot", poids_colis: 0 },
  clients: [
    { id: 1, lat: 48.851, lon: 2.351, nom_client: "Client 1", poids_colis: 10, tw_start: 0, tw_end: 999999 },
    { id: 2, lat: 48.852, lon: 2.352, nom_client: "Client 2", poids_colis: 11, tw_start: 0, tw_end: 999999 },
  ],
  graph_available: true,
  weather: { desc: "Clear", factor: 1.0 },
  human_state: {
    routes_by_sleigh: { "0": [] },
    segments_by_sleigh: { "0": [] },
    assigned_clients: [],
    live_stats: { "0": {} },
    stop_meta_by_client: {},
    speed_multiplier: 1.0,
    vehicle_capacity: 200,
    num_vehicles: 1,
  },
  results_available: false,
  incidents: { count: 0, segments: [] },
};

const infeasibleRouteOptionResponse = {
  options: [
    {
      route_nodes: [0, 10, 1],
      geometry: [
        [48.85, 2.35],
        [48.8505, 2.3505],
        [48.851, 2.351],
      ],
      dist_m: 230,
      base_time_s: 130,
      time_s: 130,
      label: "Option 1",
      is_feasible: false,
      feasibility_badges: ["Surcharge +5 kg"],
      projected_arrival_clock: "18:05",
      projected_load_kg: 205,
      projected_overload_kg: 5,
    },
  ],
};

test("shows empty state when feasible-only filter hides all route options", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("mission.show_feasible_only", "0");
  });

  await page.route("http://localhost:8000/api/missions/e2e-mission", async (route) => {
    await route.fulfill({ json: missionPayload });
  });

  await page.route("http://localhost:8000/api/missions/e2e-mission/human/suggest-next", async (route) => {
    await route.fulfill({
      json: {
        suggestions: [{ client_id: 1, nom_client: "Client 1", arrival_clock: "18:05", is_feasible: true }],
      },
    });
  });

  await page.route("http://localhost:8000/api/missions/e2e-mission/human/route-options", async (route) => {
    await route.fulfill({ json: infeasibleRouteOptionResponse });
  });

  await page.goto("/mission/e2e-mission");
  await expect(page.getByRole("heading", { name: "Paris 5e" })).toBeVisible();

  await page.getByRole("button", { name: /Suggérer le prochain stop/ }).click();
  await page.getByRole("button", { name: /^Client 1/ }).click();
  await expect(page.getByText("Options — Client #1")).toBeVisible();
  await expect(page.locator("button:has-text('Option 1')")).toHaveCount(1);

  const toggle = page.getByRole("button", { name: /Faisables uniquement:/ });
  await expect(toggle).toHaveText("Faisables uniquement: OFF");
  await toggle.click();
  await expect(toggle).toHaveText("Faisables uniquement: ON");

  await expect(page.getByText("Aucune option faisable pour ce client avec les paramètres actuels.")).toBeVisible();
  await expect(page.locator("button:has-text('Option 1')")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Valider ce segment/ })).toHaveCount(0);
});
