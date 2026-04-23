import unittest
from unittest.mock import patch

import networkx as nx

import scripts.routing_payloads as routing_payloads
from scripts.routing_payloads import (
    _incident_edge_sets,
    _pick_diverse_options,
    _route_has_incident_overlap,
    _route_overlap_ratio,
    compute_route_options,
)


class RouteOptionDiversityTests(unittest.TestCase):
    def setUp(self):
        with routing_payloads._incident_graph_cache_lock:
            routing_payloads._incident_graph_cache.clear()

    def test_route_overlap_ratio(self):
        ratio = _route_overlap_ratio([1, 2, 3], [1, 2, 3, 4])
        self.assertAlmostEqual(ratio, 2 / 3)

    def test_pick_diverse_options_prefers_lower_overlap(self):
        options = [
            {"route_nodes": [1, 2, 3], "time_s": 100.0, "dist_m": 800.0},
            {"route_nodes": [1, 2, 3, 4], "time_s": 105.0, "dist_m": 820.0},
            {"route_nodes": [1, 5, 6], "time_s": 120.0, "dist_m": 900.0},
        ]

        selected = _pick_diverse_options(options, k=2)
        selected_routes = [entry["route_nodes"] for entry in selected]
        self.assertEqual(selected_routes[0], [1, 2, 3])
        self.assertIn([1, 5, 6], selected_routes)

    def test_pick_diverse_options_fallback_keeps_best_when_all_overlap(self):
        options = [
            {"route_nodes": [1, 2, 3], "time_s": 100.0, "dist_m": 800.0},
            {"route_nodes": [1, 2, 3, 4], "time_s": 101.0, "dist_m": 805.0},
            {"route_nodes": [1, 2, 3, 5], "time_s": 102.0, "dist_m": 810.0},
        ]

        selected = _pick_diverse_options(options, k=2)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["route_nodes"], [1, 2, 3])

    def test_incident_edge_sets_and_route_overlap(self):
        directed, undirected = _incident_edge_sets([{"route_nodes": [10, 11, 12]}])
        self.assertIn((10, 11), directed)
        self.assertIn((11, 12), directed)
        self.assertIn((10, 11), undirected)
        self.assertTrue(_route_has_incident_overlap([9, 10, 11], directed, undirected))
        self.assertFalse(_route_has_incident_overlap([9, 8, 7], directed, undirected))

    @patch("scripts.routing_payloads.ox.distance.nearest_nodes", side_effect=[1, 3])
    def test_compute_route_options_prefers_non_incident_path_when_available(self, _nearest_nodes_mock):
        graph = nx.MultiDiGraph()
        graph.add_node(1, x=2.0, y=48.0)
        graph.add_node(2, x=2.01, y=48.0)
        graph.add_node(3, x=2.02, y=48.0)
        graph.add_node(4, x=2.0, y=48.01)
        graph.add_node(5, x=2.01, y=48.01)
        graph.add_node(6, x=2.02, y=48.01)

        graph.add_edge(1, 2, length=100.0, travel_time=30.0)
        graph.add_edge(2, 3, length=100.0, travel_time=30.0)
        graph.add_edge(1, 4, length=120.0, travel_time=36.0)
        graph.add_edge(4, 5, length=120.0, travel_time=36.0)
        graph.add_edge(5, 6, length=120.0, travel_time=36.0)
        graph.add_edge(6, 3, length=120.0, travel_time=36.0)

        options = compute_route_options(
            graph,
            from_lat=48.0,
            from_lon=2.0,
            to_lat=48.0,
            to_lon=2.02,
            time_factor=1.0,
            k=1,
            incident_segments=[{"route_nodes": [2, 3]}],
        )

        self.assertEqual(len(options), 1)
        self.assertNotIn([1, 2, 3], [options[0]["route_nodes"]])
        self.assertEqual(options[0]["route_nodes"], [1, 4, 5, 6, 3])

    @patch("scripts.routing_payloads.ox.distance.nearest_nodes", side_effect=[1, 3, 1, 3])
    def test_compute_route_options_reuses_incident_safe_graph_cache(self, _nearest_nodes_mock):
        graph = nx.MultiDiGraph()
        graph.add_node(1, x=2.0, y=48.0)
        graph.add_node(2, x=2.01, y=48.0)
        graph.add_node(3, x=2.02, y=48.0)
        graph.add_node(4, x=2.0, y=48.01)
        graph.add_node(5, x=2.01, y=48.01)
        graph.add_node(6, x=2.02, y=48.01)

        graph.add_edge(1, 2, length=100.0, travel_time=30.0)
        graph.add_edge(2, 3, length=100.0, travel_time=30.0)
        graph.add_edge(1, 4, length=120.0, travel_time=36.0)
        graph.add_edge(4, 5, length=120.0, travel_time=36.0)
        graph.add_edge(5, 6, length=120.0, travel_time=36.0)
        graph.add_edge(6, 3, length=120.0, travel_time=36.0)

        with patch("scripts.routing_payloads._remove_incident_edges", wraps=routing_payloads._remove_incident_edges) as remove_mock:
            compute_route_options(
                graph,
                from_lat=48.0,
                from_lon=2.0,
                to_lat=48.0,
                to_lon=2.02,
                time_factor=1.0,
                k=1,
                incident_segments=[{"route_nodes": [2, 3]}],
            )
            compute_route_options(
                graph,
                from_lat=48.0,
                from_lon=2.0,
                to_lat=48.0,
                to_lon=2.02,
                time_factor=1.0,
                k=1,
                incident_segments=[{"route_nodes": [2, 3]}],
            )
            self.assertEqual(remove_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()
