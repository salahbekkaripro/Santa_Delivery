import { expect, test } from "@playwright/test";

const missionPayload = {
  mission_id: "e2e-mission",
  mission: {
    zone: "Paris 5e",
    num_clients: 1,
    budget: 500,
    sleigh_cost: 50,
    weather_key: "Clear",
    random_incidents: false,
    level: null,
    ai_profile: "express",
    secondary_objectives: [],
  },
  depot: { id: 0, lat: 48.85, lon: 2.35, nom_client: "Depot", poids_colis: 0 },
  clients: [{ id: 1, lat: 48.851, lon: 2.351, nom_client: "Client 1", poids_colis: 10 }],
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

const adjacentResponse = {
  adjacents: [
    {
      node_id: 42,
      lat: 48.8504,
      lon: 2.3506,
      geometry: [
        [48.85, 2.35],
        [48.8504, 2.3506],
      ],
      dist_m: 80,
      time_s: 25,
      label: "Adj test",
    },
  ],
  future_adjacents: [],
};

test("free routing validates adjacent segment with explicit from/to ids", async ({ page }) => {
  const validatePayloads: Array<Record<string, unknown>> = [];
  let adjacentCalls = 0;

  await page.route("http://localhost:8000/api/missions/e2e-mission", async (route) => {
    await route.fulfill({ json: missionPayload });
  });

  await page.route(/http:\/\/localhost:8000\/api\/missions\/e2e-mission\/adjacent-nodes\?.*/, async (route) => {
    adjacentCalls += 1;
    await route.fulfill({ json: adjacentResponse });
  });

  await page.route("http://localhost:8000/api/missions/e2e-mission/human/validate-segment", async (route) => {
    const body = route.request().postData() ?? "{}";
    validatePayloads.push(JSON.parse(body));
    await route.fulfill({
      json: {
        ...missionPayload.human_state,
        routes_by_sleigh: { "0": [42] },
        segments_by_sleigh: {
          "0": [
            {
              variant: "human",
              sleigh_id: 0,
              from_id: 0,
              to_id: 42,
              route_nodes: [0, 42],
              geometry: [
                [48.85, 2.35],
                [48.8504, 2.3506],
              ],
              dist_m: 80,
              time_s: 25,
              base_time_s: 25,
            },
          ],
        },
      },
    });
  });

  await page.goto("/mission/e2e-mission");
  await expect(page.getByRole("heading", { name: "Paris 5e" })).toBeVisible();

  await page.getByRole("button", { name: /2D \(Leaflet\)/ }).click();
  await page.getByRole("button", { name: /📍 Sélection/ }).click();
  await expect(page.getByRole("button", { name: /🗺️ Tracé Libre/ })).toBeVisible();
  await expect.poll(() => adjacentCalls).toBeGreaterThan(0);

  const adjacentMarker = page.locator('path.leaflet-interactive[fill="#3b82f6"]').first();
  await expect(adjacentMarker).toBeVisible();
  await adjacentMarker.evaluate((element) => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });

  await expect.poll(() => validatePayloads.length).toBe(1);
  expect(validatePayloads[0]?.from_id).toBe(0);
  expect(validatePayloads[0]?.to_id).toBe(42);
});
