import unittest

from monitor import Monitor


class DiskHealthTests(unittest.TestCase):
    def test_mock_disk_health_returns_expected_shape(self):
        health = Monitor(mock=True).get_disk_health()

        self.assertGreaterEqual(len(health), 1)
        for disk in health:
            self.assertIn("device", disk)
            self.assertIn("model", disk)
            self.assertIn("status", disk)
            self.assertIn("alert", disk)
            self.assertIn("temp", disk)
            self.assertIn("power_on", disk)
            self.assertIn("reallocated", disk)


if __name__ == "__main__":
    unittest.main()
