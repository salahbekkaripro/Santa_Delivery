import os
import tempfile
import time
import unittest
from unittest.mock import patch

from backend.app import services


class GraphCacheTests(unittest.TestCase):
    def setUp(self):
        with services._graph_cache_lock:
            services._graph_cache.clear()

    def test_load_graph_cached_reuses_same_mtime_key(self):
        with tempfile.NamedTemporaryFile() as tmp:
            sentinel = object()
            with patch("backend.app.services.load_graph", return_value=sentinel) as load_graph_mock:
                graph_first = services._load_graph_cached(tmp.name)
                graph_second = services._load_graph_cached(tmp.name)

        self.assertIs(graph_first, sentinel)
        self.assertIs(graph_second, sentinel)
        self.assertEqual(load_graph_mock.call_count, 1)

    def test_load_graph_cached_invalidates_on_mtime_change(self):
        with tempfile.NamedTemporaryFile() as tmp:
            first_graph = object()
            second_graph = object()
            with patch("backend.app.services.load_graph", side_effect=[first_graph, second_graph]) as load_graph_mock:
                graph_first = services._load_graph_cached(tmp.name)
                now_ns = time.time_ns()
                os.utime(tmp.name, ns=(now_ns, now_ns + 5_000_000))
                graph_second = services._load_graph_cached(tmp.name)

        self.assertIs(graph_first, first_graph)
        self.assertIs(graph_second, second_graph)
        self.assertEqual(load_graph_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
