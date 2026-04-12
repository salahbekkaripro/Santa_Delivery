import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
import os

client = TestClient(app)

def test_free_routing_workflow():
    # 1. Créer une mission
    resp = client.post("/api/missions", json={
        "zone": "Paris, France",
        "num_clients": 5,
        "budget": 1000,
        "sleigh_cost": 100,
        "weather_key": "Clear"
    })
    assert resp.status_code == 200
    data = resp.json()
    mission_id = data["mission_id"]
    depot = data["depot"]
    
    # 2. Demander le nœud le plus proche d'un point arbitraire (proche du dépôt)
    lat = depot["lat"] + 0.001
    lon = depot["lon"] + 0.001
    resp = client.get(f"/api/missions/{mission_id}/nearest-node?lat={lat}&lon={lon}")
    assert resp.status_code == 200
    node_data = resp.json()
    assert "node_id" in node_data
    osm_node_id = node_data["node_id"]
    
    # 3. Calculer les options de route vers ce nœud OSM
    resp = client.post(f"/api/missions/{mission_id}/human/route-options", json={
        "from_id": 0,
        "to_id": osm_node_id,
        "speed_multiplier": 1.0
    })
    assert resp.status_code == 200
    options = resp.json()["options"]
    assert len(options) > 0
    selected_option = options[0]
    
    # 4. Valider ce segment vers un nœud OSM
    resp = client.post(f"/api/missions/{mission_id}/human/validate-segment", json={
        "sleigh_id": 0,
        "from_id": 0,
        "to_id": osm_node_id,
        "selected_route": selected_option,
        "speed_multiplier": 1.0,
        "vehicle_capacity": 200,
        "num_vehicles": 3
    })
    assert resp.status_code == 200
    state = resp.json()
    
    # Vérifier que le nœud OSM est dans la route mais PAS dans assigned_clients
    assert osm_node_id in state["routes_by_sleigh"]["0"]
    # Un nœud OSM ne devrait pas être dans assigned_clients car il n'est pas dans le CSV initial (probablement)
    # Sauf si par chance osmnx a retourné un nœud qui est EXACTEMENT un client (peu probable avec 5 clients)
    # En fait, validate_human_segment vérifie si l'ID est dans client_ids.
    
    # Récupérer les IDs des clients de la mission
    resp_mission = client.get(f"/api/missions/{mission_id}")
    client_ids = [c["id"] for c in resp_mission.json()["clients"]]
    
    if osm_node_id not in client_ids:
        assert osm_node_id not in state["assigned_clients"]
    else:
        assert osm_node_id in state["assigned_clients"]

    # 5. Annuler le segment
    resp = client.post(f"/api/missions/{mission_id}/human/undo-last", json={
        "sleigh_id": 0,
        "speed_multiplier": 1.0,
        "vehicle_capacity": 200,
        "num_vehicles": 3
    })
    assert resp.status_code == 200
    state = resp.json()
    assert osm_node_id not in state["routes_by_sleigh"]["0"]
