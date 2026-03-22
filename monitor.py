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

    def get_memory_stats(self):
        """Returns (percent, used_gb, total_gb)."""
        if self.mock:
            total = 16.0
            used = random.uniform(2.0, 14.0)
            return (used / total) * 100, used, total
        
        mem = psutil.virtual_memory()
        return mem.percent, mem.used / (1024**3), mem.total / (1024**3)

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

    def get_system_info(self):
        """Returns (os_name, uptime_str)."""
        if self.mock:
            return "Ubuntu 22.04.3 LTS (Mock)", "3 days, 14:22:05"

        import platform
        import datetime

        os_name = platform.platform(terse=True)
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d, {hours:02d}:{minutes:02d}:{seconds:02d}"

        return os_name, uptime_str

    def get_available_logs(self):
        """Detects available log sources on the system."""
        if self.mock:
            return ["journalctl", "dmesg", "syslog", "auth.log"]

        import shutil
        import os
        sources = []
        if shutil.which("journalctl"): sources.append("journalctl")
        if shutil.which("dmesg"): sources.append("dmesg")

        standard_files = [
            "/var/log/syslog", "/var/log/messages", "/var/log/auth.log", 
            "/var/log/secure", "/var/log/kern.log", "/var/log/cron.log",
            "/var/log/boot.log"
        ]
        for f in standard_files:
            if os.path.exists(f):
                sources.append(os.path.basename(f))

        return sources

    def get_log_content(self, source, limit=50):
        """Fetches the last N lines of a specified log source."""
        if self.mock:
            mock_logs = {
                "journalctl": [f"Mar 22 18:00:01 host systemd[1]: Started Session {i} of user jc." for i in range(100, 100+limit)],
                "dmesg": [f"[{i*1.5:.6f}] pci 0000:00:1f.3: Intel Corporation Device 7a50" for i in range(limit)],
                "syslog": [f"Mar 22 18:05:{i:02d} host CRON[1234]: (root) CMD (command)" for i in range(limit)],
                "auth.log": [f"Mar 22 18:10:00 host sshd[5678]: Accepted password for user from 192.168.1.{i}" for i in range(limit)]
            }
            return mock_logs.get(source, ["No mock data for this source."])

        import subprocess
        try:
            if source == "journalctl":
                res = subprocess.run(["journalctl", "-n", str(limit), "--no-pager"], capture_output=True, text=True)
                return res.stdout.splitlines()
            elif source == "dmesg":
                res = subprocess.run(["dmesg", "--tail", str(limit)], capture_output=True, text=True)
                if res.returncode != 0: # Some systems don't support --tail
                    res = subprocess.run(["dmesg"], capture_output=True, text=True)
                    return res.stdout.splitlines()[-limit:]
                return res.stdout.splitlines()
            else:
                # Standard file
                path = f"/var/log/{source}"
                if os.path.exists(path):
                    res = subprocess.run(["tail", "-n", str(limit), path], capture_output=True, text=True)
                    return res.stdout.splitlines()
        except Exception as e:
            return [f"Error reading log: {e}"]

        return ["Log source not found."]

    def get_disk_health(self):
        """Returns list of dicts with Disk S.M.A.R.T / Health info."""
        if self.mock:
            return [
                {
                    "device": "/dev/nvme0n1",
                    "model": "Samsung SSD 980 PRO 1TB",
                    "status": "PASSED",
                    "alert": False,
                    "temp": "32°C",
                    "power_on": "4,520 hours",
                    "reallocated": 0,
                    "wear_level": "98%"
                },
                {
                    "device": "/dev/sda",
                    "model": "Crucial CT500MX500SSD1",
                    "status": "WARNING",
                    "alert": True,
                    "temp": "45°C",
                    "power_on": "12,150 hours",
                    "reallocated": 42,
                    "wear_level": "85%"
                }
            ]

        disks = []
        try:
            import subprocess
            import json

            # Check if smartctl is available
            import shutil
            if not shutil.which("smartctl"):
                return []

            devices_proc = subprocess.run(['sudo', 'smartctl', '--scan-open', '-j'], capture_output=True, text=True, timeout=5)
            if devices_proc.returncode == 0:
                try:
                    scan_data = json.loads(devices_proc.stdout)
                except json.JSONDecodeError:
                    return []

                for dev in scan_data.get('devices', []):
                    name = dev.get('name')
                    if not name: continue

                    info_proc = subprocess.run(['sudo', 'smartctl', '-a', '-j', name], capture_output=True, text=True, timeout=5)
                    if info_proc.returncode == 0:
                        try:
                            data = json.loads(info_proc.stdout)
                        except json.JSONDecodeError:
                            continue
                        
                        status_passed = data.get('smart_status', {}).get('passed', False)
                        model = data.get('model_name', 'Unknown')
                        temp = data.get('temperature', {}).get('current', 'N/A')
                        power_on = data.get('power_on_time', {}).get('hours', 'N/A')
                        
                        reallocated = 0
                        # Try to find reallocated sectors in different table formats
                        for table_key in ['ata_smart_attributes', 'nvme_smart_health_information_log']:
                            table = data.get(table_key, {})
                            if isinstance(table, dict) and 'table' in table:
                                for attr in table['table']:
                                    if attr.get('id') == 5 or "reallocated" in attr.get('name', "").lower():
                                        reallocated = attr.get('raw', {}).get('value', 0)
                                        break

                        disks.append({
                            "device": name,
                            "model": model,
                            "status": "PASSED" if status_passed else "FAILED",
                            "alert": not status_passed or reallocated > 0,
                            "temp": f"{temp}°C" if temp != 'N/A' else 'N/A',
                            "power_on": f"{power_on:,} hours" if power_on != 'N/A' else 'N/A',
                            "reallocated": reallocated,
                            "wear_level": "N/A"
                        })
        except Exception:
            pass
            
        return disks

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
