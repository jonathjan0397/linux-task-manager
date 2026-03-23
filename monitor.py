import json
import os
import random
import shutil
import subprocess
import time

import psutil

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
        self._proc_cache = {}
        self._disk_health_cache = []
        self._disk_health_cache_time = 0.0
        self._connection_cache = []
        self._connection_cache_time = 0.0

        if not self.mock:
            self._prime_process_cpu_counters()

        if not self.mock and HAS_PYNVML:
            try:
                pynvml.nvmlInit()
                self._nvidia_initialized = True
            except:
                self._nvidia_initialized = False

    def _prime_process_cpu_counters(self):
        """Prime psutil CPU counters so the first visible sample has real data."""
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
                self._proc_cache[proc.pid] = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def _format_addr(self, addr):
        """Normalize psutil/netstat style addresses to a readable host:port form."""
        if not addr:
            return "-"

        if hasattr(addr, "ip") and hasattr(addr, "port"):
            host, port = addr.ip, addr.port
        elif isinstance(addr, tuple):
            if len(addr) >= 2:
                host, port = addr[0], addr[1]
            else:
                return str(addr[0])
        else:
            return str(addr)

        if ":" in str(host) and not str(host).startswith("["):
            host = f"[{host}]"
        return f"{host}:{port}"

    def _read_sysfs_value(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read().strip()
        except OSError:
            return None

    def _discover_block_devices(self):
        devices = []
        if not shutil.which("lsblk"):
            return devices

        try:
            result = subprocess.run(
                ["lsblk", "-J", "-d", "-o", "PATH,MODEL,TRAN,SIZE,ROTA,TYPE"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                return devices

            payload = json.loads(result.stdout or "{}")
            for entry in payload.get("blockdevices", []):
                if entry.get("type") != "disk":
                    continue
                path = entry.get("path")
                if not path:
                    continue

                name = os.path.basename(path)
                temp = self._read_disk_temperature(name)
                devices.append(
                    {
                        "device": path,
                        "model": (entry.get("model") or "Unknown").strip() or "Unknown",
                        "transport": entry.get("tran") or "unknown",
                        "size": entry.get("size") or "N/A",
                        "rotational": entry.get("rota"),
                        "temp": temp,
                    }
                )
        except (OSError, json.JSONDecodeError, subprocess.SubprocessError):
            return []

        return devices

    def _read_disk_temperature(self, device_name):
        hwmon_root = f"/sys/block/{device_name}/device/hwmon"
        if os.path.isdir(hwmon_root):
            try:
                for hwmon_dir in os.listdir(hwmon_root):
                    temp_raw = self._read_sysfs_value(os.path.join(hwmon_root, hwmon_dir, "temp1_input"))
                    if temp_raw and temp_raw.isdigit():
                        return f"{int(temp_raw) / 1000:.0f}°C"
            except OSError:
                pass

        thermal_root = f"/sys/block/{device_name}/device"
        for candidate in ("temperature", "temp"):
            temp_raw = self._read_sysfs_value(os.path.join(thermal_root, candidate))
            if temp_raw and temp_raw.isdigit():
                value = int(temp_raw)
                if value > 1000:
                    value = value / 1000
                return f"{value:.0f}°C"
        return "N/A"

    def _run_smartctl(self, device):
        commands = [["smartctl", "-a", "-j", device]]
        if hasattr(os, "getuid") and os.getuid() != 0:
            commands.append(["sudo", "-n", "smartctl", "-a", "-j", device])

        last_error = "smartctl unavailable"
        for command in commands:
            try:
                proc = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                last_error = str(exc)
                continue

            if proc.returncode == 0 and proc.stdout:
                try:
                    return json.loads(proc.stdout), None
                except json.JSONDecodeError as exc:
                    last_error = f"invalid smartctl JSON: {exc}"
                    continue

            stderr = (proc.stderr or proc.stdout or "").strip()
            if stderr:
                lowered = stderr.lower()
                if "sudo" in command[0]:
                    last_error = "sudo permission required for S.M.A.R.T. data"
                elif "permission" in lowered:
                    last_error = "permission denied reading S.M.A.R.T. data"
                else:
                    last_error = stderr.splitlines()[-1]

        return None, last_error

    def _smart_status_from_data(self, data):
        smart_passed = data.get("smart_status", {}).get("passed")
        if smart_passed is True:
            return "PASSED", False
        if smart_passed is False:
            return "FAILED", True
        return "UNAVAILABLE", False

    def _extract_reallocated_count(self, data):
        ata_table = data.get("ata_smart_attributes", {}).get("table", [])
        if isinstance(ata_table, list):
            for attr in ata_table:
                name = (attr.get("name") or "").lower()
                if attr.get("id") == 5 or "reallocated" in name:
                    return attr.get("raw", {}).get("value", 0)

        nvme_log = data.get("nvme_smart_health_information_log", {})
        for key in ("media_errors", "num_err_log_entries"):
            if key in nvme_log:
                return nvme_log.get(key, 0)
        return 0

    def _fallback_disk_entry(self, device, note):
        media_type = "SSD" if device.get("rotational") == "0" else "HDD" if device.get("rotational") == "1" else device.get("transport", "unknown").upper()
        return {
            "device": device["device"],
            "model": device["model"],
            "status": "UNAVAILABLE",
            "alert": False,
            "temp": device.get("temp", "N/A"),
            "power_on": "N/A",
            "reallocated": "N/A",
            "wear_level": "N/A",
            "media": media_type,
            "notes": note,
        }

    def _parse_ss_connections(self, limit):
        if not shutil.which("ss"):
            return []

        try:
            proc = subprocess.run(
                ["ss", "-tunapH"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if proc.returncode != 0:
                return []
        except (OSError, subprocess.SubprocessError):
            return []

        connections = []
        for raw_line in proc.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split(None, 5)
            if len(parts) < 5:
                continue

            proto = parts[0]
            state = parts[1]
            local_addr = parts[4] if len(parts) > 4 else "-"
            remote_addr = parts[5].split(" users:", 1)[0] if len(parts) > 5 else "-"
            process_info = parts[5] if len(parts) > 5 else ""
            pid = "-"
            if "pid=" in process_info:
                pid = process_info.split("pid=", 1)[1].split(",", 1)[0].rstrip(")")

            connections.append(
                {
                    "proto": proto.upper(),
                    "laddr": local_addr,
                    "raddr": remote_addr if remote_addr else "-",
                    "status": state,
                    "pid": pid,
                }
            )

        priority = {"ESTAB": 0, "ESTABLISHED": 0, "LISTEN": 1}
        connections.sort(key=lambda conn: (priority.get(conn["status"], 2), conn["laddr"]))
        return connections[:limit]

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
                    "wear_level": "98%",
                    "media": "NVMe",
                    "notes": "Healthy"
                },
                {
                    "device": "/dev/sda",
                    "model": "Crucial CT500MX500SSD1",
                    "status": "WARNING",
                    "alert": True,
                    "temp": "45°C",
                    "power_on": "12,150 hours",
                    "reallocated": 42,
                    "wear_level": "85%",
                    "media": "SSD",
                    "notes": "Reallocated sectors detected"
                }
            ]

        now = time.time()
        if self._disk_health_cache and now - self._disk_health_cache_time < 30:
            return self._disk_health_cache

        devices = self._discover_block_devices()
        if not devices:
            self._disk_health_cache = [{"error": "No block devices detected."}]
            self._disk_health_cache_time = now
            return self._disk_health_cache

        disks = []
        smartctl_available = shutil.which("smartctl") is not None
        for device in devices:
            if not smartctl_available:
                disks.append(self._fallback_disk_entry(device, "Install smartmontools for S.M.A.R.T. details"))
                continue

            smart_data, smart_error = self._run_smartctl(device["device"])
            if not smart_data:
                disks.append(self._fallback_disk_entry(device, smart_error or "S.M.A.R.T. data unavailable"))
                continue

            status, alert = self._smart_status_from_data(smart_data)
            reallocated = self._extract_reallocated_count(smart_data)
            temperature = smart_data.get("temperature", {}).get("current")
            power_hours = smart_data.get("power_on_time", {}).get("hours")
            media_type = smart_data.get("device", {}).get("type") or device.get("transport", "unknown").upper()
            if str(media_type).lower() == "nvme":
                media_type = "NVMe"

            disks.append(
                {
                    "device": device["device"],
                    "model": smart_data.get("model_name") or smart_data.get("model_family") or device["model"],
                    "status": status,
                    "alert": alert or (isinstance(reallocated, int) and reallocated > 0),
                    "temp": f"{temperature}°C" if temperature not in (None, "N/A") else device.get("temp", "N/A"),
                    "power_on": f"{power_hours:,} hours" if isinstance(power_hours, int) else "N/A",
                    "reallocated": reallocated,
                    "wear_level": "N/A",
                    "media": media_type,
                    "notes": "Healthy" if status == "PASSED" and not reallocated else smart_error or "",
                }
            )

        self._disk_health_cache = disks
        self._disk_health_cache_time = now
        return disks

    def get_process_list(self, limit=15):
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
        try:
            current_pids = set()
            for proc in psutil.process_iter():
                pid = proc.pid
                current_pids.add(pid)
                try:
                    if pid not in self._proc_cache:
                        self._proc_cache[pid] = proc
                        proc.cpu_percent(interval=None)
                        continue

                    proc = self._proc_cache[pid]
                    with proc.oneshot():
                        cpu = proc.cpu_percent(interval=None)
                        mem = proc.memory_percent()
                        name = proc.name()

                    processes.append({
                        "pid": pid,
                        "name": name,
                        "cpu": round(cpu, 1),
                        "mem": mem
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    if pid in self._proc_cache:
                        del self._proc_cache[pid]
                    continue
                except Exception:
                    continue

            for pid in list(self._proc_cache.keys()):
                if pid not in current_pids:
                    del self._proc_cache[pid]
        except Exception as e:
            return [{"error": f"Process error: {str(e)}"}]

        processes.sort(key=lambda x: (x['cpu'], x['mem']), reverse=True)
        return processes[:limit]

    def get_network_connections(self, limit=25):
        """Returns a list of active network connections."""
        if self.mock:
            return [
                {
                    "proto": random.choice(["TCP", "UDP"]),
                    "laddr": f"127.0.0.1:{random.randint(1024, 65535)}",
                    "raddr": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}:443",
                    "status": random.choice(["ESTABLISHED", "CLOSE_WAIT", "LISTEN"]),
                    "pid": random.randint(100, 9999)
                } for _ in range(limit)
            ]

        now = time.time()
        if self._connection_cache and now - self._connection_cache_time < 5:
            return self._connection_cache[:limit]

        connections = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                connections.append({
                    "proto": "TCP" if conn.type == 1 else "UDP",
                    "laddr": self._format_addr(conn.laddr),
                    "raddr": self._format_addr(conn.raddr),
                    "status": conn.status,
                    "pid": conn.pid or "-"
                })
        except psutil.AccessDenied:
            connections = self._parse_ss_connections(limit)
        except Exception as e:
            return [{"error": f"Error: {str(e)}"}]

        if not connections:
            connections = self._parse_ss_connections(limit)

        priority = {"ESTABLISHED": 0, "ESTAB": 0, "LISTEN": 1}
        connections.sort(key=lambda conn: (priority.get(conn["status"], 2), conn["laddr"]))
        self._connection_cache = connections[:limit]
        self._connection_cache_time = now
        return self._connection_cache

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
