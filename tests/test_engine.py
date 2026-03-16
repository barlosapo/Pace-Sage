"""
Tests for pace-sage engine and runlog.
"""

import pytest
from datetime import date, timedelta
from pace_sage.engine import (
    seconds_to_pace, pace_to_seconds, estimate_vdot,
    PaceZones, TrainingPlan, predict_marathon,
    hms_to_seconds, miles_to_km,
)
from pace_sage.runlog import Run, RunLog
import tempfile, os
from pathlib import Path


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------

def test_seconds_to_pace_roundtrip():
    for spm in [300, 360, 420, 480, 540]:
        assert abs(pace_to_seconds(seconds_to_pace(spm)) - spm) <= 1


def test_miles_to_km():
    assert abs(miles_to_km(1) - 1.60934) < 0.001


def test_hms_to_seconds():
    assert hms_to_seconds(1, 30, 0) == 5400
    assert hms_to_seconds(0, 45, 30) == 2730


# ---------------------------------------------------------------------------
# VDOT / pace zone tests
# ---------------------------------------------------------------------------

def test_vdot_reasonable_half_marathon():
    # 1:28:30 half marathon → VDOT ~52
    secs = hms_to_seconds(1, 28, 30)
    vdot = estimate_vdot(13.1094, secs)
    assert 49 < vdot < 56, f"Expected ~52, got {vdot:.1f}"


def test_vdot_5k():
    # 20:00 5K → VDOT ~52
    secs = hms_to_seconds(0, 20, 0)
    vdot = estimate_vdot(3.10686, secs)
    assert 49 < vdot < 55, f"Expected ~52, got {vdot:.1f}"


def test_pace_zones_ordering():
    zones = PaceZones(50.0)
    # Easy should be slowest (highest sec/mile), repetition fastest
    assert zones.easy_lo > zones.easy_hi > zones.marathon > zones.threshold > zones.interval


def test_predict_marathon_sub3h30_for_vdot55():
    # VDOT 55 should predict sub-3:30 marathon
    prediction = predict_marathon(55.0)
    parts = prediction.split(":")
    total_min = int(parts[0]) * 60 + int(parts[1])
    assert total_min < 210, f"Expected <3:30, got {prediction}"


def test_pace_zones_display_format():
    zones = PaceZones(52.0)
    display = zones.display()
    for zone, pace in display.items():
        assert ":" in pace, f"Pace '{pace}' for {zone} not in MM:SS format"
        mins, secs = pace.split(":")
        assert 0 <= int(secs) < 60


# ---------------------------------------------------------------------------
# Training plan tests
# ---------------------------------------------------------------------------

def test_plan_generation_produces_weeks():
    race_date = date.today() + timedelta(weeks=18)
    plan = TrainingPlan.generate(
        athlete_name="Test Runner",
        race_date=race_date,
        recent_race_distance_miles=13.1094,
        recent_race_time="1:28:30",
    )
    assert len(plan.weeks) >= 4
    assert plan.vdot > 40


def test_plan_phases_present():
    race_date = date.today() + timedelta(weeks=20)
    plan = TrainingPlan.generate(
        athlete_name="Test Runner",
        race_date=race_date,
        recent_race_distance_miles=13.1094,
        recent_race_time="1:28:30",
    )
    phases = {w["phase"] for w in plan.weeks}
    assert "base" in phases
    assert "taper" in phases


def test_plan_to_dict_keys():
    race_date = date.today() + timedelta(weeks=16)
    plan = TrainingPlan.generate(
        athlete_name="Carlos",
        race_date=race_date,
        recent_race_distance_miles=13.1094,
        recent_race_time="1:29:00",
    )
    d = plan.to_dict()
    for key in ("athlete", "vdot", "goal_marathon_time", "race_date", "zones", "weeks"):
        assert key in d


# ---------------------------------------------------------------------------
# Run log tests
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_log(tmp_path):
    return RunLog(path=tmp_path / "runs.json")


def test_add_and_retrieve_run(tmp_log):
    run = Run(
        run_date="2026-03-10",
        distance_miles=8.0,
        duration_seconds=3600,  # 1:00:00
        run_type="easy",
    )
    tmp_log.add(run)
    assert len(tmp_log.all_runs()) == 1
    assert tmp_log.all_runs()[0].distance_miles == 8.0


def test_pace_calculation():
    run = Run(
        run_date="2026-03-10",
        distance_miles=6.0,
        duration_seconds=2700,  # 45 min → 7:30/mi
        run_type="easy",
    )
    assert run.pace_per_mile == "7:30"


def test_total_miles(tmp_log):
    for miles in [5, 8, 12, 6]:
        tmp_log.add(Run(
            run_date="2026-03-01",
            distance_miles=miles,
            duration_seconds=miles * 540,
            run_type="easy",
        ))
    assert tmp_log.total_miles() == 31


def test_avg_pace_by_type(tmp_log):
    tmp_log.add(Run("2026-03-01", 6.0, 3240, "easy"))   # 9:00/mi
    tmp_log.add(Run("2026-03-02", 10.0, 5400, "long"))  # 9:00/mi
    avg = tmp_log.avg_pace("easy")
    assert avg == "9:00"


def test_weekly_mileage(tmp_log):
    tmp_log.add(Run("2026-03-09", 5.0, 2700, "easy"))
    tmp_log.add(Run("2026-03-10", 8.0, 4320, "long"))
    weekly = tmp_log.weekly_mileage()
    assert len(weekly) >= 1
    total = sum(weekly.values())
    assert abs(total - 13.0) < 0.01


def test_summary_keys(tmp_log):
    tmp_log.add(Run("2026-03-10", 5.0, 2700, "easy"))
    s = tmp_log.summary()
    for key in ("total_runs", "total_miles", "avg_easy_pace", "longest_run_miles"):
        assert key in s


def test_export_json(tmp_log, tmp_path):
    tmp_log.add(Run("2026-03-10", 5.0, 2700, "easy", notes="felt good"))
    out = str(tmp_path / "export.json")
    tmp_log.export_json(out)
    import json
    data = json.loads(Path(out).read_text())
    assert len(data) == 1
    assert data[0]["distance_miles"] == 5.0
