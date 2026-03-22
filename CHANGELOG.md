# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2026-03-22

### Fixed
- Fixed Processes tab: implemented persistent process cache to ensure accurate real-time CPU tracking.
- Improved error handling in Health, Connections, and Processes widgets for non-root environments.

### Changed
- Updated README with explicit `git pull` instructions for easier updates.

## [1.3.0] - 2026-03-22

### Added
- GPU Individual Tracking: Each GPU now has its own performance card with a real-time sparkline graph.
- Added `g` shortcut key for direct access to the GPU tab.
- Added comprehensive error reporting for root/sudo-dependent features (Health, Connections, Processes).

### Fixed
- Fixed Dashboard "Digits" glitches by rounding values to integers for better fit in cards.
- Fixed Top System Processes display: corrected `psutil` sampling logic to show actual CPU usage.
- Fixed Smart Health and Active Connections visibility by providing clear "Access Denied" feedback when running without root.
- Fixed hotkey for "About" tab and aligned shortcut labels.

## [1.2.3] - 2026-03-22

### Changed
- Improved UI robustness with dynamic CPU core detection (supporting >16 cores).
- Added `get_icon` helper with ASCII fallbacks for environments without Unicode/UTF-8 support.
- Refactored `CPUWidget` to use a monitor-driven core count.

## [1.2.2] - 2026-03-22

### Changed
- Improved cross-distribution compatibility for system logs (added support for RHEL/CentOS/Arch paths).
- Enhanced `smartctl` robustnes with better JSON parsing, timeouts, and NVMe attribute mapping.
- Added explicit check for `smartctl` availability before execution.

## [1.2.1] - 2026-03-22

### Fixed
- Fixed `BadIdentifier` error in Log Viewer by sanitizing `ListItem` IDs (replacing dots with underscores).
- Improved Log Viewer mapping logic using selection index for better reliability.

### Changed
- Updated `README.md` to include missing feature descriptions for Disk Health and Log Viewer.

## [1.2.0] - 2026-03-22

### Added
- Integrated Log Viewer with support for `journalctl`, `dmesg`, and standard log files.
- Added numeric tab shortcuts (1-9, 0) for faster navigation.
- Added "About" tab with project information and shortcut references.
- Added system uptime and OS information to the main dashboard.
- Implemented S.M.A.R.T. disk health monitoring with status icons and alerts.

### Fixed
- Fixed UI stability issues and footer visibility.
- Resolved `MarkupError` in Connections and Process widgets.
- Fixed tab shortcut functionality.

## [1.1.0] - 2026-03-22

### Added
- Enhanced UI with high-contrast Green/Black theme.
- Added Disk I/O throughput monitoring.
- Added GPU performance tracking support.

## [1.0.0] - 2026-03-22

### Added
- Initial release of PyTask.
- Real-time CPU and Memory monitoring.
- Network traffic and active connections view.
- Process management table.
- Cross-platform mock mode for development.
