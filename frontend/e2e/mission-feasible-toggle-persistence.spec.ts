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

test("persists feasible-only toggle across reloads", async ({ page }) => {
  await page.route("http://localhost:8000/api/missions/e2e-mission", async (route) => {
    await route.fulfill({ json: missionPayload });
  });

  await page.goto("/mission/e2e-mission");
  await expect(page.getByRole("heading", { name: "Paris 5e" })).toBeVisible();

  const toggle = page.getByRole("button", { name: /Faisables uniquement:/ });
  await page.evaluate(() => {
    window.localStorage.setItem("mission.show_feasible_only", "1");
  });
  await page.reload();
  await expect(toggle).toHaveText("Faisables uniquement: ON");

  await toggle.click();
  await expect(toggle).toHaveText("Faisables uniquement: OFF");
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("mission.show_feasible_only"))).toBe("0");

  await page.reload();
  await expect(toggle).toHaveText("Faisables uniquement: OFF");
});
