import unittest

from backend.app import services


class SearchConstraintTests(unittest.TestCase):
    def test_max_clients_for_radius(self):
        self.assertEqual(services._max_clients_for_radius(3.0), 56)
        self.assertEqual(services._max_clients_for_radius(0.5), 8)
        self.assertEqual(services._max_clients_for_radius(30.0), 200)

    def test_validate_search_area_rejects_excess_clients(self):
        with self.assertRaises(ValueError):
            services._validate_search_area_constraints(
                {
                    "search_radius_km": 1.0,
                    "num_clients": 20,
                }
            )

    def test_validate_search_area_requires_center_coordinates(self):
        with self.assertRaises(ValueError):
            services._validate_search_area_constraints(
                {
                    "search_radius_km": 1.0,
                    "num_clients": 5,
                }
            )


if __name__ == "__main__":
    unittest.main()
