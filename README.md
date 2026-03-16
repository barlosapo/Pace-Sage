Built with the assistance of [Claude](https://claude.ai) by Anthropic :)
An attempt at going all in on the vibecode train and build something im into while focusing on other life duties

# pace-sage 🏃

> Marathon training plan generator & run analytics — VDOT-based pace zones, periodized plans, and a browser dashboard. Zero dependencies.

![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Tests](https://img.shields.io/badge/tests-18%20passed-brightgreen?style=flat-square)

---

## What it does

**pace-sage** is a pure-Python CLI tool and static web dashboard for serious marathon runners. It implements Jack Daniels' VDOT model to:

- Calculate personalized training pace zones from any recent race result
- Generate a fully periodized 12–24 week marathon training plan (Base → Build → Peak → Taper)
- Log runs locally and analyze trends (weekly mileage, avg pace by type, PRs)
- Predict race times across all standard distances
- Export everything to JSON

No accounts. No subscriptions. Your data stays on your machine.

---

## Installation

```bash
# From source (recommended)
git clone https://github.com/your-username/pace-sage.git
cd pace-sage
pip install -e .

# Or directly
pip install pace-sage
```

Requires Python 3.10+. No third-party dependencies.

---

## CLI Usage

### Calculate pace zones

```bash
pace-sage zones --recent-race half:1:28:30
```

```
🏃  PACE ZONES  (VDOT = 52.0)

  Zone               Pace/mile    Pace/km
  ──────────────────────────────────────
  Easy (lo)              9:41        6:01
  Easy (hi)              9:19        5:47
  Marathon Pace          8:32        5:18
  Threshold              8:04        5:01
  Interval               7:14        4:30
  Repetition             6:45        4:12

  Predicted marathon: 3:44:12
```

### Generate a training plan

```bash
pace-sage plan \
  --name "Carlos" \
  --race-date 2026-11-02 \
  --recent-race half:1:28:30 \
  --out my_plan.json
```

### Log runs

```bash
# Add a run
pace-sage log add \
  --date 2026-03-15 \
  --miles 8 \
  --time 1:09:20 \
  --type easy \
  --notes "Felt strong, cool morning" \
  --hr 142

# List recent runs
pace-sage log list -n 20

# View summary stats
pace-sage log summary
```

### Predict race times from VDOT

```bash
pace-sage predict --vdot 52
```

```
  🔮  PREDICTIONS FOR VDOT 52

  5K           20:35
  10K          42:44
  Half         1:34:02
  Marathon     3:16:28
```

### Export run log

```bash
pace-sage export --out my_runs.json
```

---

## Web Dashboard

Open `web/index.html` in any browser — no server required.

Features:
- **Dashboard** — total mileage, weekly mileage bar chart, pace-by-type breakdown
- **Run Log** — add/delete runs, full history table with pace badges
- **Pace Zones** — interactive VDOT calculator with zone visualization
- **Training Plan** — collapsible week-by-week plan with daily workouts

Data is stored in `localStorage` — stays in your browser between sessions.

---

## The VDOT Model

VDOT is a VO₂ max proxy derived from race performance, developed by Jack Daniels in *Daniels' Running Formula*. pace-sage implements the Daniels/Gilbert equation:

```
velocity (m/min) = distance_meters / time_minutes

%VO₂max = 0.8 + 0.1894393·e^(-0.012778·t) + 0.2989558·e^(-0.1932605·t)

VO₂ = -4.60 + 0.182258·v + 0.000104·v²

VDOT = VO₂ / %VO₂max
```

Training zones are derived by inverting the equation at each intensity factor:

| Zone        | %VO₂max | Purpose                         |
|-------------|---------|----------------------------------|
| Easy        | 76–79%  | Aerobic base, recovery          |
| Marathon    | 84%     | Race-specific endurance          |
| Threshold   | 88%     | Lactate clearance rate           |
| Interval    | 98%     | VO₂max stimulus                 |
| Repetition  | 105%    | Economy and speed                |

---

## Training Plan Structure

Plans are periodized into four phases, length auto-calculated from race date:

| Phase  | Weeks | Focus                                    |
|--------|-------|-------------------------------------------|
| Base   | 4–8   | Aerobic foundation, easy volume          |
| Build  | 3–6   | Introduce intervals and longer tempos    |
| Peak   | 2–4   | Maximum volume, marathon-pace long runs  |
| Taper  | 3     | Reduce volume, maintain intensity        |

---

## Project Structure

```
pace-sage/
├── pace_sage/
│   ├── __init__.py      # Package metadata
│   ├── engine.py        # VDOT model, pace zones, plan generation
│   ├── runlog.py        # Run storage and analytics
│   ├── cli.py           # CLI entry point (argparse)
│   └── constants.py     # Shared race distances
├── tests/
│   ├── conftest.py
│   └── test_engine.py   # 18 unit tests
├── web/
│   └── index.html       # Static web dashboard (no server needed)
├── docs/
│   └── pace_zones.md    # VDOT zone reference table
├── pyproject.toml
├── .github/
│   └── workflows/
│       └── ci.yml       # GitHub Actions: test on push
├── .gitignore
├── LICENSE
└── README.md
```

---

## Running Tests

```bash
pip install pytest
pytest
```

All 18 tests cover: pace utilities, VDOT estimation, zone ordering, plan generation, run log CRUD, weekly mileage aggregation, and JSON export.

---

## Contributing

PRs welcome. Please add tests for any new functionality.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/gpx-import`)
3. Run `pytest` and confirm green
4. Open a PR with a clear description

---

## License

MIT © 2026 Carlos Salinas
