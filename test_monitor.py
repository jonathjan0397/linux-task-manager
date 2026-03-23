import unittest
from unittest.mock import Mock, patch

from monitor import Monitor


class FakeProcess:
    def __init__(self, pid, name, mem, cpu_sequence):
        self.pid = pid
        self._name = name
        self._mem = mem
        self._cpu_sequence = list(cpu_sequence)

    def cpu_percent(self, interval=None):
        if self._cpu_sequence:
            return self._cpu_sequence.pop(0)
        return 0.0

    def memory_percent(self):
        return self._mem

    def name(self):
        return self._name

    def oneshot(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class MonitorTests(unittest.TestCase):
    @patch.object(Monitor, "_prime_process_cpu_counters", autospec=True)
    def test_process_list_uses_primed_cpu_samples(self, _prime_mock):
        proc_a = FakeProcess(11, "python", 2.5, [0.0, 35.0])
        proc_b = FakeProcess(12, "chrome", 4.0, [0.0, 12.0])

        with patch("monitor.psutil.net_io_counters", return_value=Mock(bytes_recv=0, bytes_sent=0)), \
             patch("monitor.psutil.disk_io_counters", return_value=Mock(read_bytes=0, write_bytes=0)), \
             patch("monitor.psutil.process_iter", side_effect=[[proc_a, proc_b], [proc_a, proc_b]]):
            monitor = Monitor()
            first = monitor.get_process_list(limit=5)
            second = monitor.get_process_list(limit=5)

        self.assertEqual(first, [])
        self.assertEqual(second[0]["pid"], 11)
        self.assertEqual(second[0]["cpu"], 35.0)
        self.assertEqual(second[1]["cpu"], 12.0)

    @patch.object(Monitor, "_prime_process_cpu_counters", autospec=True)
    def test_network_connections_format_addresses(self, _prime_mock):
        inet_conn = Mock(
            type=1,
            laddr=("127.0.0.1", 8000),
            raddr=("10.0.0.2", 443),
            status="ESTABLISHED",
            pid=321,
        )

        with patch("monitor.psutil.net_io_counters", return_value=Mock(bytes_recv=0, bytes_sent=0)), \
             patch("monitor.psutil.disk_io_counters", return_value=Mock(read_bytes=0, write_bytes=0)), \
             patch("monitor.psutil.net_connections", return_value=[inet_conn]):
            monitor = Monitor()
            connections = monitor.get_network_connections(limit=5)

        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0]["proto"], "TCP")
        self.assertEqual(connections[0]["laddr"], "127.0.0.1:8000")
        self.assertEqual(connections[0]["raddr"], "10.0.0.2:443")

    @patch.object(Monitor, "_prime_process_cpu_counters", autospec=True)
    def test_disk_health_falls_back_without_smartctl(self, _prime_mock):
        devices = [
            {
                "device": "/dev/nvme0n1",
                "model": "TEAM TM8FPK500G",
                "transport": "nvme",
                "size": "477G",
                "rotational": "0",
                "temp": "36°C",
            }
        ]

        with patch("monitor.psutil.net_io_counters", return_value=Mock(bytes_recv=0, bytes_sent=0)), \
             patch("monitor.psutil.disk_io_counters", return_value=Mock(read_bytes=0, write_bytes=0)), \
             patch.object(Monitor, "_discover_block_devices", return_value=devices), \
             patch("monitor.shutil.which", side_effect=lambda cmd: None if cmd == "smartctl" else "/usr/bin/lsblk"):
            monitor = Monitor()
            disk_health = monitor.get_disk_health()

        self.assertEqual(disk_health[0]["status"], "UNAVAILABLE")
        self.assertEqual(disk_health[0]["temp"], "36°C")
        self.assertIn("smartmontools", disk_health[0]["notes"])


if __name__ == "__main__":
    unittest.main()
