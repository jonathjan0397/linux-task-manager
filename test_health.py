from monitor import Monitor
import json

m = Monitor()
health = m.get_disk_health()
print(f"Disk Health Data (count: {len(health)}):")
print(json.dumps(health, indent=2))
