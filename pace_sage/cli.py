"""
pace-sage CLI entry point.

Usage:
  pace-sage plan   --name "Carlos" --race-date 2026-11-02 --recent-race "half:1:28:30"
  pace-sage zones  --recent-race "half:1:28:30"
  pace-sage log    add --date 2026-03-10 --miles 8 --time 1:02:10 --type easy
  pace-sage log    list
  pace-sage log    summary
  pace-sage predict --vdot 52
  pace-sage export --format json --out my_runs.json
"""

from __future__ import annotations
import argparse
import json
import sys
from datetime import date

from .engine import (
    PaceZones, TrainingPlan, estimate_vdot,
    predict_marathon, hms_to_seconds, seconds_to_hms,
)
from .runlog import Run, RunLog


RACE_DISTANCES = {
    "5k":   3.10686,
    "10k":  6.21371,
    "half": 13.1094,
    "marathon": 26.2188,
}


def parse_recent_race(s: str) -> tuple[float, float]:
    """Parse 'distance:H:MM:SS' → (miles, seconds)."""
    parts = s.split(":")
    dist_key = parts[0].lower()
    if dist_key not in RACE_DISTANCES:
        sys.exit(f"Unknown distance '{dist_key}'. Use: {', '.join(RACE_DISTANCES)}")
    miles = RACE_DISTANCES[dist_key]
    time_parts = parts[1:]
    if len(time_parts) == 3:
        secs = hms_to_seconds(int(time_parts[0]), int(time_parts[1]), int(time_parts[2]))
    elif len(time_parts) == 2:
        secs = hms_to_seconds(0, int(time_parts[0]), int(time_parts[1]))
    else:
        sys.exit("Invalid time format. Use H:MM:SS or MM:SS.")
    return miles, secs


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_zones(args):
    miles, secs = parse_recent_race(args.recent_race)
    vdot = estimate_vdot(miles, secs)
    zones = PaceZones(round(vdot, 1))

    print(f"\n🏃  PACE ZONES  (VDOT = {vdot:.1f})\n")
    print(f"  {'Zone':<18} {'Pace/mile':>10}  {'Pace/km':>10}")
    print("  " + "-" * 42)
    km_factor = 1.60934
    for name, pace in zones.display().items():
        # Convert sec/mile to sec/km for display
        from .engine import pace_to_seconds, seconds_to_pace
        spm = pace_to_seconds(pace)
        spkm = spm / km_factor
        from .engine import seconds_to_pace as s2p
        print(f"  {name:<18} {pace:>10}  {s2p(spkm):>10}")
    print(f"\n  Predicted marathon: {predict_marathon(vdot)}\n")


def cmd_plan(args):
    race_date = date.fromisoformat(args.race_date)
    recent_time_str = ":".join(args.recent_race.split(":")[1:])
    recent_dist_key = args.recent_race.split(":")[0].lower()
    miles, secs = parse_recent_race(args.recent_race)

    # Build full time string for plan generator
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    time_str = f"{h}:{m:02d}:{s:02d}"

    plan = TrainingPlan.generate(
        athlete_name=args.name,
        race_date=race_date,
        recent_race_distance_miles=miles,
        recent_race_time=time_str,
    )

    d = plan.to_dict()
    print(f"\n🏁  TRAINING PLAN FOR {d['athlete'].upper()}")
    print(f"    Race Date  : {d['race_date']}")
    print(f"    VDOT       : {d['vdot']}")
    print(f"    Goal Time  : {d['goal_marathon_time']}")
    print(f"\n  PACE ZONES:")
    for z, p in d["zones"].items():
        print(f"    {z:<18} {p}")

    print(f"\n  SCHEDULE OVERVIEW ({len(d['weeks'])} weeks):\n")
    print(f"  {'Wk':>3}  {'Phase':<8}  {'Week of':<12}  {'Miles':>6}")
    print("  " + "-" * 35)
    for w in d["weeks"]:
        print(f"  {w['week_number']:>3}  {w['phase']:<8}  {w['start_date']:<12}  {w['total_miles']:>6.1f}")

    if args.out:
        import json, pathlib
        pathlib.Path(args.out).write_text(json.dumps(d, indent=2))
        print(f"\n  ✅  Full plan saved to {args.out}\n")
    else:
        print()


def cmd_log_add(args):
    log = RunLog()
    parts = args.time.split(":")
    if len(parts) == 3:
        secs = hms_to_seconds(int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        secs = hms_to_seconds(0, int(parts[0]), int(parts[1]))

    run = Run(
        run_date=args.date or date.today().isoformat(),
        distance_miles=args.miles,
        duration_seconds=secs,
        run_type=args.type,
        notes=args.notes or "",
        heart_rate_avg=args.hr,
        elevation_ft=args.elevation,
    )
    log.add(run)
    print(f"\n  ✅  Logged: {run.distance_miles} mi @ {run.pace_per_mile}/mi on {run.run_date}\n")


def cmd_log_list(args):
    log = RunLog()
    runs = log.recent(args.n)
    if not runs:
        print("\n  No runs logged yet.\n")
        return

    print(f"\n  {'Date':<12} {'Miles':>6} {'Time':<10} {'Pace/mi':>8} {'Type':<12} Notes")
    print("  " + "-" * 65)
    for r in runs:
        notes_preview = (r.notes[:20] + "…") if len(r.notes) > 20 else r.notes
        print(f"  {r.run_date:<12} {r.distance_miles:>6.1f} {r.duration_hms:<10} "
              f"{r.pace_per_mile:>8} {r.run_type:<12} {notes_preview}")
    print()


def cmd_log_summary(args):
    log = RunLog()
    s = log.summary()
    print("\n  📊  RUN LOG SUMMARY\n")
    for k, v in s.items():
        label = k.replace("_", " ").title()
        print(f"  {label:<25} {v}")
    weekly = log.weekly_mileage()
    if weekly:
        print(f"\n  WEEKLY MILEAGE (last 8 weeks):\n")
        for wk, miles in list(weekly.items())[-8:]:
            bar = "█" * int(miles / 2)
            print(f"  {wk}  {miles:>5.1f} mi  {bar}")
    print()


def cmd_export(args):
    log = RunLog()
    path = log.export_json(args.out)
    print(f"\n  ✅  Exported {len(log.all_runs())} runs to {path}\n")


def cmd_predict(args):
    zones = PaceZones(args.vdot)
    print(f"\n  🔮  PREDICTIONS FOR VDOT {args.vdot}\n")
    from .engine import seconds_to_hms
    RACE_DISTANCES_MILES = {
        "5K":       3.10686,
        "10K":      6.21371,
        "Half":    13.1094,
        "Marathon": 26.2188,
    }
    mp_secs = zones.marathon
    for name, miles in RACE_DISTANCES_MILES.items():
        t = mp_secs * miles
        # Apply rough Riegel exponent correction for shorter distances
        riegel_base = mp_secs * 26.2188
        t = mp_secs * 26.2188 * (miles / 26.2188) ** 1.06
        print(f"  {name:<12} {seconds_to_hms(t)}")
    print()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pace-sage",
        description="Marathon training plan generator & run analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # zones
    p_zones = sub.add_parser("zones", help="Show VDOT-based pace zones")
    p_zones.add_argument("--recent-race", required=True,
                         help="Format: distance:H:MM:SS  e.g. half:1:28:30")

    # plan
    p_plan = sub.add_parser("plan", help="Generate a full training plan")
    p_plan.add_argument("--name", required=True)
    p_plan.add_argument("--race-date", required=True, help="YYYY-MM-DD")
    p_plan.add_argument("--recent-race", required=True,
                        help="Format: distance:H:MM:SS  e.g. half:1:28:30")
    p_plan.add_argument("--out", help="Save plan JSON to file")

    # log
    p_log = sub.add_parser("log", help="Record and review runs")
    log_sub = p_log.add_subparsers(dest="log_command", required=True)

    p_add = log_sub.add_parser("add", help="Log a run")
    p_add.add_argument("--date", help="YYYY-MM-DD (default: today)")
    p_add.add_argument("--miles", type=float, required=True)
    p_add.add_argument("--time", required=True, help="H:MM:SS or MM:SS")
    p_add.add_argument("--type", required=True,
                       choices=["easy", "long", "threshold", "interval", "race", "recovery"])
    p_add.add_argument("--notes", help="Optional notes")
    p_add.add_argument("--hr", type=int, help="Avg heart rate")
    p_add.add_argument("--elevation", type=float, help="Elevation gain (ft)")

    p_list = log_sub.add_parser("list", help="List recent runs")
    p_list.add_argument("-n", type=int, default=10, help="Number of runs to show")

    log_sub.add_parser("summary", help="Show run log statistics")

    # predict
    p_predict = sub.add_parser("predict", help="Predict race times from VDOT")
    p_predict.add_argument("--vdot", type=float, required=True)

    # export
    p_export = sub.add_parser("export", help="Export run log")
    p_export.add_argument("--format", choices=["json"], default="json")
    p_export.add_argument("--out", default="runs_export.json")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "zones":   cmd_zones,
        "plan":    cmd_plan,
        "predict": cmd_predict,
        "export":  cmd_export,
    }

    if args.command == "log":
        log_dispatch = {
            "add":     cmd_log_add,
            "list":    cmd_log_list,
            "summary": cmd_log_summary,
        }
        log_dispatch[args.log_command](args)
    else:
        dispatch[args.command](args)


if __name__ == "__main__":
    main()
