import random
import unittest

from scripts.generator_engine import _select_depot_and_clients


class GeneratorSelectionTests(unittest.TestCase):
    def test_select_depot_nearest_to_center_when_center_provided(self):
        nodes = [
            (10, {"y": 48.8000, "x": 2.0000}),
            (11, {"y": 48.7751, "x": 2.0296}),
            (12, {"y": 48.7900, "x": 2.0400}),
            (13, {"y": 48.7600, "x": 2.0500}),
        ]
        depot_node, clients_nodes = _select_depot_and_clients(
            nodes,
            num_clients=2,
            center_lat=48.775072,
            center_lon=2.029589,
        )

        self.assertEqual(depot_node[0], 11)
        self.assertEqual(len(clients_nodes), 2)
        self.assertNotIn(depot_node[0], [node[0] for node in clients_nodes])

    def test_select_depot_and_clients_without_center(self):
        random.seed(42)
        nodes = [
            (1, {"y": 48.8, "x": 2.0}),
            (2, {"y": 48.81, "x": 2.01}),
            (3, {"y": 48.82, "x": 2.02}),
            (4, {"y": 48.83, "x": 2.03}),
        ]
        depot_node, clients_nodes = _select_depot_and_clients(nodes, num_clients=2)

        ids = [depot_node[0], *[node[0] for node in clients_nodes]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(clients_nodes), 2)


if __name__ == "__main__":
    unittest.main()
