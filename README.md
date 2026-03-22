# PyTask: Linux Task Manager

A modern, terminal-based task manager for Linux systems, built with Python and the [Textual](https://textual.textualize.io/) framework.

## Features

- **CPU Monitoring**: Real-time per-core usage bars.
- **Network Traffic**: Live upload and download speed sparklines.
- **Connections**: List of active network connections with PID and status.
- **Disk I/O**: Real-time read and write throughput monitoring.
- **GPU Status**: Support for NVIDIA (via NVML) and AMD (via sysfs) utilization and memory.
- **Process List**: Top system processes sorted by CPU usage.
- **Mock Mode**: Built-in simulator for testing on non-Linux environments.

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/linux-task-manager.git
   cd linux-task-manager
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the utility:
```bash
python app.py
```

### Mock Mode (for testing on Windows/Mac)
```bash
python app.py --mock
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
