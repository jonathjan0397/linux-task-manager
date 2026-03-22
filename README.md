# PyTask: Linux Task Manager

A modern, terminal-based task manager for Linux systems, built with Python and the [Textual](https://textual.textualize.io/) framework. PyTask provides real-time system monitoring with a clean, interactive TUI (Terminal User Interface).

## Features

- **CPU Monitoring**: Real-time per-core usage bars showing utilization across all available cores.
- **Memory Usage**: Detailed memory stats with real-time progress and history sparklines.
- **Network Traffic**: Live upload and download speed sparklines with throughput labels.
- **Active Connections**: Interactive table of active network connections, including local/remote addresses, status, and associated PIDs.
- **Disk I/O**: Real-time monitoring of disk read and write throughput with sparkline visualizations.
- **Disk Health Monitoring**: S.M.A.R.T. health assessment for connected drives with status icons and alerts.
- **GPU Performance**: Support for monitoring NVIDIA and AMD GPU utilization and memory.
- **Process Management**: View top system processes sorted by CPU and Memory usage.
- **System Log Viewer**: Interactive viewer for system logs (journalctl, dmesg, syslog, etc.).
- **Cross-Platform Mock Mode**: Includes a built-in simulator (`--mock`) for testing and development on Windows or macOS.

## Installation & Quick Start

To get the latest version and run the application:

**Linux / macOS / WSL:**
```bash
# Clone the repository (if not already done)
git clone https://github.com/jonathjan0397/linux-task-manager.git
cd linux-task-manager

# Get the latest updates
git pull origin master

# Run with automated runner
chmod +x run.sh
./run.sh
```

**Windows (PowerShell):**
```powershell
# Get the latest updates
git pull origin master

# First time setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run
python app.py --mock
```

## Usage

Run the utility directly from your terminal (if dependencies are already installed):
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
