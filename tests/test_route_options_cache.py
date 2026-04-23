import unittest

from backend.app import services


class RouteOptionsCacheTests(unittest.TestCase):
    def setUp(self):
        with services._route_options_cache_lock:
            services._route_options_cache.clear()

    def test_cache_returns_copy(self):
        key = ("mission-x", 0, 1, 1.0, 1.0, 3)
        payload = [{"route_nodes": [1, 2], "time_s": 12.0}]
        services._route_options_cache_set(key, payload)

        cached = services._route_options_cache_get(key)
        self.assertEqual(cached, payload)
        self.assertIsNot(cached, payload)

        cached[0]["time_s"] = 99.0
        cached_again = services._route_options_cache_get(key)
        self.assertEqual(cached_again[0]["time_s"], 12.0)


if __name__ == "__main__":
    unittest.main()
