import psutil
import time
from monitor import Monitor

m = Monitor()
print("Initial call (should be 0.0 for all):")
procs = m.get_process_list()
print(f"Count: {len(procs)}")
for p in procs[:5]:
    print(p)

print("\nWaiting 1 second...")
time.sleep(1)

print("\nSecond call (should have real values):")
procs = m.get_process_list()
print(f"Count: {len(procs)}")
for p in procs[:5]:
    print(p)
