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
  clients: [
    { id: 1, lat: 48.851, lon: 2.351, nom_client: "Client 1", poids_colis: 10, tw_start: 0, tw_end: 999999 },
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

const validatedState = {
  routes_by_sleigh: { "0": [1] },
  segments_by_sleigh: {
    "0": [
      {
        variant: "human",
        sleigh_id: 0,
        from_id: 0,
        to_id: 1,
        route_nodes: [0, 10, 1],
        geometry: [
          [48.85, 2.35],
          [48.8505, 2.3505],
          [48.851, 2.351],
        ],
        dist_m: 230,
        time_s: 130,
        base_time_s: 130,
        arrival_eta_s: 130,
        arrival_clock: "18:02",
      },
    ],
  },
  assigned_clients: [1],
  live_stats: { "0": { time_s: 130, dist_m: 230, load_kg: 10, over_kg: 0, return_time_s: 0, return_arrival_clock: "18:02" } },
  stop_meta_by_client: { 1: { sleigh_id: 0, stop_order: 1, arrival_eta_s: 130, arrival_clock: "18:02" } },
  speed_multiplier: 1.0,
  vehicle_capacity: 200,
  num_vehicles: 1,
};

const emptyState = {
  ...validatedState,
  routes_by_sleigh: { "0": [] },
  segments_by_sleigh: { "0": [] },
  assigned_clients: [],
  live_stats: { "0": {} },
  stop_meta_by_client: {},
};

test("clicking a feasible preview route confirms exactly once and undo reverts", async ({ page }) => {
  let validateCalls = 0;
  let undoCalls = 0;

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
    await route.fulfill({
      json: {
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
            is_feasible: true,
            feasibility_badges: ["Sûr"],
            projected_arrival_clock: "18:05",
            projected_load_kg: 10,
            projected_overload_kg: 0,
          },
        ],
      },
    });
  });

  await page.route("http://localhost:8000/api/missions/e2e-mission/human/validate-segment", async (route) => {
    validateCalls += 1;
    await new Promise((resolve) => setTimeout(resolve, 260));
    await route.fulfill({ json: validatedState });
  });

  await page.route("http://localhost:8000/api/missions/e2e-mission/human/undo-last", async (route) => {
    undoCalls += 1;
    await route.fulfill({ json: emptyState });
  });

  await page.goto("/mission/e2e-mission");
  await expect(page.getByRole("heading", { name: "Paris 5e" })).toBeVisible();

  await page.getByRole("button", { name: /2D \(Leaflet\)/ }).click();
  await page.getByRole("button", { name: /Suggérer le prochain stop/ }).click();
  await page.getByRole("button", { name: /^Client 1/ }).click();

  const feasiblePreview = page.locator(".preview-option-line.preview-option-feasible").first();
  await expect(feasiblePreview).toBeVisible();

  await feasiblePreview.evaluate((element) => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });

  await expect.poll(() => validateCalls).toBe(1);
  await expect(page.getByText("1 / 1 clients assignés")).toBeVisible();

  const undoButton = page.getByRole("button", { name: "↩ Undo" });
  await expect(undoButton).toBeVisible();
  await undoButton.click();

  await expect.poll(() => undoCalls).toBe(1);
  await expect(page.getByText("0 / 1 clients assignés")).toBeVisible();
});

test("clicking an infeasible preview route does not validate and shows explicit message", async ({ page }) => {
  let validateCalls = 0;

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
    await route.fulfill({
      json: {
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
            label: "Option impossible",
            is_feasible: false,
            feasibility_badges: ["Surcharge +5 kg"],
            projected_arrival_clock: "18:05",
            projected_load_kg: 205,
            projected_overload_kg: 5,
          },
        ],
      },
    });
  });

  await page.route("http://localhost:8000/api/missions/e2e-mission/human/validate-segment", async (route) => {
    validateCalls += 1;
    await route.fulfill({ json: validatedState });
  });

  await page.goto("/mission/e2e-mission");
  await expect(page.getByRole("heading", { name: "Paris 5e" })).toBeVisible();

  await page.getByRole("button", { name: /2D \(Leaflet\)/ }).click();
  await page.getByRole("button", { name: /Suggérer le prochain stop/ }).click();
  await page.getByRole("button", { name: /^Client 1/ }).click();

  const infeasiblePreview = page.locator(".preview-option-line.preview-option-infeasible").first();
  await expect(infeasiblePreview).toBeVisible();
  await infeasiblePreview.evaluate((element) => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });

  await expect.poll(() => validateCalls).toBe(0);
  await expect(page.getByRole("status")).toContainText("Segment non faisable: Surcharge +5 kg.");
});
