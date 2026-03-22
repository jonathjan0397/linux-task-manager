# PyTask: Linux Task Manager

A modern, terminal-based task manager for Linux systems, built with Python and the [Textual](https://textual.textualize.io/) framework. PyTask provides real-time system monitoring with a clean, interactive TUI (Terminal User Interface).

## Features

- **CPU Monitoring**: Real-time per-core usage bars showing utilization across all available cores.
- **Network Traffic**: Live upload and download speed sparklines with throughput labels.
- **Active Connections**: Interactive table of active network connections, including local/remote addresses, status, and associated PIDs.
- **Disk I/O**: Real-time monitoring of disk read and write throughput with sparkline visualizations.
- **GPU Performance**: Support for monitoring NVIDIA GPU utilization and memory (via NVML).
- **Process Management**: View top system processes sorted by CPU and Memory usage.
- **Cross-Platform Mock Mode**: Includes a built-in simulator (`--mock`) for testing and development on Windows or macOS.

## Installation

### Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jonathjan0397/linux-task-manager.git
   cd linux-task-manager
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the utility directly from your terminal:
```bash
python app.py
```

### Development & Testing
If you are on a non-Linux system (like Windows or macOS) or want to test the UI without affecting system stats, use the **Mock Mode**:
```bash
python app.py --mock
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
