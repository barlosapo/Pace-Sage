# Changelog

All notable changes to pace-sage will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-03-16

### Added
- VDOT estimation from any standard race distance (5K, 10K, half, marathon)
- Six training pace zones derived from the Daniels/Gilbert equation
- Periodized plan generator (Base → Build → Peak → Taper)
- Run log with local JSON persistence (`~/.pace_sage/runs.json`)
- Analytics: total mileage, weekly mileage, avg pace by type, PR pace
- JSON export for run log
- Prediction of all standard race times from VDOT
- Static single-file web dashboard (`web/index.html`) — no server required
- Full CLI via `pace-sage` command
- 18-test pytest suite
- GitHub Actions CI (Python 3.10, 3.11, 3.12)

## [Unreleased]

### Planned
- GPX file import (parse Garmin/Strava exports)
- `pace-sage log import --gpx run.gpx`
- Heart rate zone analysis (Karvonen method)
- Week-over-week mileage progression guard (≤10% increase warning)
- CSV export option
- macOS/Linux shell completions
