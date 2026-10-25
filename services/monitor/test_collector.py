import unittest
from pathlib import Path

from collector import cpu_usage, disks, rate, Collector


class CollectorTests(unittest.TestCase):
    def test_deltas_missing_values_and_reset(self):
        self.assertEqual(cpu_usage((200, 100), (100, 50)), 50)
        self.assertIsNone(cpu_usage((200, 100), None))
        self.assertIsNone(cpu_usage((1, 1), (100, 50)))
        self.assertEqual(rate([100, 200], [50, 100], 10), [5, 10])
        self.assertEqual(rate([1, 2], [50, 100], 10), [None, None])

    def test_same_filesystem_preserves_storage_roles(self):
        values, errors = disks([("OS", "/"), ("取得データ", "/tmp")])
        if Path("/").stat().st_dev == Path("/tmp").stat().st_dev:
            self.assertEqual(len(values), 1)
            self.assertIn("取得データ", values[0]["label"])
        self.assertFalse(errors)

    def test_first_sample_does_not_report_rates_as_zero(self):
        collector = Collector("test", "host", [("OS", "/")])
        value = collector.sample()
        self.assertIsNone(value["cpu_percent"])
        self.assertIsNone(value["net_rx_bytes_sec"])
        self.assertGreater(value["memory_total_bytes"], 0)
        second = Collector("test", "host", [("OS", "/")])
        self.assertNotEqual(collector.boot_id, second.boot_id)


if __name__ == "__main__":
    unittest.main()
