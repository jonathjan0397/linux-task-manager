# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
