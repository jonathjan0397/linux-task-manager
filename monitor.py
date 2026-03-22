import os
import time
import psutil
import random

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False

class Monitor:
    def __init__(self, mock=False):
        self.mock = mock
        self._last_net_stats = psutil.net_io_counters()
        self._last_net_time = time.time()
        self._last_disk_stats = psutil.disk_io_counters()
        self._last_disk_time = time.time()
        self._nvidia_initialized = False

        if not self.mock and HAS_PYNVML:
            try:
                pynvml.nvmlInit()
                self._nvidia_initialized = True
            except:
                self._nvidia_initialized = False

    def get_cpu_stats(self):
        """Returns per-core CPU usage."""
        if self.mock:
            return [random.randint(5, 95) for _ in range(8)]
        return psutil.cpu_percent(percpu=True)

    def get_network_stats(self):
        """Returns (download_kbps, upload_kbps)."""
        current_stats = psutil.net_io_counters()
        current_time = time.time()
        
        dt = current_time - self._last_net_time
        if dt <= 0:
            return 0.0, 0.0

        download_kbps = (current_stats.bytes_recv - self._last_net_stats.bytes_recv) / 1024 / dt
        upload_kbps = (current_stats.bytes_sent - self._last_net_stats.bytes_sent) / 1024 / dt

        self._last_net_stats = current_stats
        self._last_net_time = current_time

        if self.mock:
            return random.uniform(10, 500), random.uniform(5, 100)

        return download_kbps, upload_kbps

    def get_disk_stats(self):
        """Returns (read_kbps, write_kbps)."""
        current_stats = psutil.disk_io_counters()
        current_time = time.time()
        
        dt = current_time - self._last_disk_time
        if dt <= 0:
            return 0.0, 0.0

        read_kbps = (current_stats.read_bytes - self._last_disk_stats.read_bytes) / 1024 / dt
        write_kbps = (current_stats.write_bytes - self._last_disk_stats.write_bytes) / 1024 / dt

        self._last_disk_stats = current_stats
        self._last_disk_time = current_time

        if self.mock:
            return random.uniform(50, 2000), random.uniform(20, 1000)

        return read_kbps, write_kbps

    def get_process_list(self, limit=10):
        """Returns a list of top processes by CPU usage."""
        if self.mock:
            mock_names = ["python", "chrome", "vscode", "docker", "slack", "systemd", "gnome-shell"]
            return [
                {
                    "pid": random.randint(100, 9999),
                    "name": random.choice(mock_names),
                    "cpu": round(random.uniform(0.1, 15.0), 1),
                    "mem": round(random.uniform(0.5, 5.0), 1)
                } for _ in range(limit)
            ]

        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu": proc.info['cpu_percent'],
                    "mem": proc.info['memory_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage and return top N
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        return processes[:limit]

    def get_network_connections(self, limit=20):
        """Returns a list of active network connections."""
        if self.mock:
            return [
                {
                    "laddr": f"127.0.0.1:{random.randint(1024, 65535)}",
                    "raddr": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}:443",
                    "status": random.choice(["ESTABLISHED", "CLOSE_WAIT", "LISTEN"]),
                    "pid": random.randint(100, 9999)
                } for _ in range(limit)
            ]

        connections = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "-"
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
                connections.append({
                    "laddr": laddr,
                    "raddr": raddr,
                    "status": conn.status,
                    "pid": conn.pid or "-"
                })
        except (psutil.AccessDenied):
            pass
            
        return connections[:limit]

    def get_gpu_stats(self):
        """Returns list of dicts with GPU usage info."""
        if self.mock:
            return [{"name": "Mock NVIDIA RTX 4090", "util": random.randint(10, 90), "mem": random.randint(20, 80)}]

        gpus = []
        
        # NVIDIA (via pynvml)
        if self._nvidia_initialized:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    mem_util = (mem_info.used / mem_info.total) * 100
                    gpus.append({
                        "vendor": "NVIDIA",
                        "name": name if isinstance(name, str) else name.decode('utf-8'),
                        "util": util,
                        "mem": mem_util
                    })
            except:
                pass

        # AMD (via sysfs)
        amd_path = "/sys/class/drm/"
        if os.path.exists(amd_path):
            for card in os.listdir(amd_path):
                if card.startswith("card") and not "-" in card:
                    busy_path = os.path.join(amd_path, card, "device/gpu_busy_percent")
                    if os.path.exists(busy_path):
                        try:
                            with open(busy_path, 'r') as f:
                                util = int(f.read().strip())
                            gpus.append({
                                "vendor": "AMD",
                                "name": card,
                                "util": util,
                                "mem": 0  # AMD mem info is in separate sysfs files, keeping simple for now
                            })
                        except:
                            pass

        return gpus
