"""
Training plan engine for pace-sage.
Implements Jack Daniels VDOT-based pace zones and periodized plan generation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
import math


# ---------------------------------------------------------------------------
# Pace utilities
# ---------------------------------------------------------------------------

def seconds_to_pace(total_seconds: float) -> str:
    """Convert total seconds per mile to MM:SS string."""
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}:{seconds:02d}"


def pace_to_seconds(pace_str: str) -> float:
    """Convert MM:SS pace string to seconds per mile."""
    parts = pace_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid pace format: '{pace_str}'. Use MM:SS.")
    return int(parts[0]) * 60 + int(parts[1])


def miles_to_km(miles: float) -> float:
    return miles * 1.60934


def km_to_miles(km: float) -> float:
    return km / 1.60934


def hms_to_seconds(h: int, m: int, s: int) -> float:
    return h * 3600 + m * 60 + s


def seconds_to_hms(total: float) -> str:
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = int(total % 60)
    return f"{h}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# VDOT model (Jack Daniels)
# ---------------------------------------------------------------------------

def estimate_vdot(distance_miles: float, time_seconds: float) -> float:
    """
    Estimate VDOT from a recent race result.
    Uses the Daniels/Gilbert equation (velocity in meters/min).
    """
    distance_meters = distance_miles * 1609.34
    time_minutes = time_seconds / 60.0
    velocity = distance_meters / time_minutes  # meters per minute
    pct_max = 0.8 + 0.1894393 * math.exp(-0.012778 * time_minutes) \
              + 0.2989558 * math.exp(-0.1932605 * time_minutes)
    vo2 = -4.60 + 0.182258 * velocity + 0.000104 * velocity ** 2
    return vo2 / pct_max


@dataclass
class PaceZones:
    """Training pace zones derived from VDOT."""
    vdot: float

    # All stored as seconds/mile
    easy_lo: float = field(init=False)
    easy_hi: float = field(init=False)
    marathon: float = field(init=False)
    threshold: float = field(init=False)
    interval: float = field(init=False)
    repetition: float = field(init=False)

    def __post_init__(self):
        v = self.vdot
        # Factors calibrated from Daniels' Running Formula tables.
        # These represent the fraction of VDOT (≈VO2max) at each training intensity.
        # Derived empirically: easy ~58-61%, marathon ~70%, threshold ~76%, etc.
        self.easy_lo    = self._vdot_to_pace(v, factor=0.5845)
        self.easy_hi    = self._vdot_to_pace(v, factor=0.6107)
        self.marathon   = self._vdot_to_pace(v, factor=0.7049)
        self.threshold  = self._vdot_to_pace(v, factor=0.7557)
        self.interval   = self._vdot_to_pace(v, factor=0.8635)
        self.repetition = self._vdot_to_pace(v, factor=0.9343)

    @staticmethod
    def _vdot_to_pace(vdot: float, factor: float) -> float:
        """
        Approximate pace in sec/mile at a given %VO2max (factor).
        Inverts the Daniels velocity equation (velocity in meters/min).
        """
        target_vo2 = factor * vdot
        # Quadratic: 0.000104*v^2 + 0.182258*v - (target_vo2 + 4.60) = 0
        a = 0.000104
        b = 0.182258
        c = -(target_vo2 + 4.60)
        velocity_m_per_min = (-b + math.sqrt(b ** 2 - 4 * a * c)) / (2 * a)
        velocity_miles_per_min = velocity_m_per_min / 1609.34
        return 60.0 / velocity_miles_per_min  # sec/mile

    def display(self) -> dict[str, str]:
        return {
            "Easy (lo)":     seconds_to_pace(self.easy_lo),
            "Easy (hi)":     seconds_to_pace(self.easy_hi),
            "Marathon Pace": seconds_to_pace(self.marathon),
            "Threshold":     seconds_to_pace(self.threshold),
            "Interval":      seconds_to_pace(self.interval),
            "Repetition":    seconds_to_pace(self.repetition),
        }


def predict_marathon(vdot: float) -> str:
    """Predict marathon finish time from VDOT."""
    zones = PaceZones(vdot)
    total_seconds = zones.marathon * 26.2188
    return seconds_to_hms(total_seconds)


# ---------------------------------------------------------------------------
# Training week templates
# ---------------------------------------------------------------------------

WEEK_TEMPLATES = {
    "base": [
        {"day": "Monday",    "type": "rest",      "miles": 0,   "description": "Full rest or cross-train"},
        {"day": "Tuesday",   "type": "easy",      "miles": 5,   "description": "Easy aerobic run"},
        {"day": "Wednesday", "type": "easy",      "miles": 6,   "description": "Easy aerobic run"},
        {"day": "Thursday",  "type": "threshold", "miles": 5,   "description": "Tempo run (20–25 min @ threshold)"},
        {"day": "Friday",    "type": "easy",      "miles": 4,   "description": "Easy recovery run"},
        {"day": "Saturday",  "type": "long",      "miles": 12,  "description": "Long easy run"},
        {"day": "Sunday",    "type": "easy",      "miles": 4,   "description": "Easy recovery run"},
    ],
    "build": [
        {"day": "Monday",    "type": "rest",      "miles": 0,   "description": "Full rest"},
        {"day": "Tuesday",   "type": "interval",  "miles": 7,   "description": "Track intervals (6×800m @ interval pace)"},
        {"day": "Wednesday", "type": "easy",      "miles": 7,   "description": "Easy aerobic run"},
        {"day": "Thursday",  "type": "threshold", "miles": 7,   "description": "Tempo run (30–35 min @ threshold)"},
        {"day": "Friday",    "type": "easy",      "miles": 5,   "description": "Easy recovery run"},
        {"day": "Saturday",  "type": "long",      "miles": 16,  "description": "Long run with last 4mi @ marathon pace"},
        {"day": "Sunday",    "type": "easy",      "miles": 5,   "description": "Easy recovery run"},
    ],
    "peak": [
        {"day": "Monday",    "type": "rest",      "miles": 0,   "description": "Full rest"},
        {"day": "Tuesday",   "type": "interval",  "miles": 9,   "description": "Track intervals (5×1mile @ interval pace)"},
        {"day": "Wednesday", "type": "easy",      "miles": 8,   "description": "Easy aerobic run"},
        {"day": "Thursday",  "type": "threshold", "miles": 9,   "description": "Cruise intervals (4×2mi @ threshold)"},
        {"day": "Friday",    "type": "easy",      "miles": 5,   "description": "Easy recovery run"},
        {"day": "Saturday",  "type": "long",      "miles": 20,  "description": "Long run — last 6mi @ marathon pace"},
        {"day": "Sunday",    "type": "easy",      "miles": 6,   "description": "Easy recovery run"},
    ],
    "taper": [
        {"day": "Monday",    "type": "rest",      "miles": 0,   "description": "Rest"},
        {"day": "Tuesday",   "type": "easy",      "miles": 5,   "description": "Easy run with 4×100m strides"},
        {"day": "Wednesday", "type": "threshold", "miles": 5,   "description": "Short tempo: 15 min @ threshold"},
        {"day": "Thursday",  "type": "easy",      "miles": 4,   "description": "Easy shakeout"},
        {"day": "Friday",    "type": "rest",      "miles": 0,   "description": "Rest"},
        {"day": "Saturday",  "type": "easy",      "miles": 3,   "description": "Easy 3mi, 4×strides"},
        {"day": "Sunday",    "type": "race",      "miles": 26.2,"description": "🏁 RACE DAY"},
    ],
}


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

@dataclass
class TrainingPlan:
    athlete_name: str
    vdot: float
    race_date: date
    goal_time: str
    weeks: list[dict] = field(default_factory=list)
    zones: PaceZones = field(init=False)

    def __post_init__(self):
        self.zones = PaceZones(self.vdot)

    @classmethod
    def generate(
        cls,
        athlete_name: str,
        race_date: date,
        recent_race_distance_miles: float,
        recent_race_time: str,  # H:MM:SS
    ) -> "TrainingPlan":
        """Build a full periodized marathon training plan."""
        parts = recent_race_time.split(":")
        if len(parts) == 3:
            t_sec = hms_to_seconds(int(parts[0]), int(parts[1]), int(parts[2]))
        else:
            t_sec = hms_to_seconds(0, int(parts[0]), int(parts[1]))

        vdot = estimate_vdot(recent_race_distance_miles, t_sec)
        goal = predict_marathon(vdot)

        plan = cls(
            athlete_name=athlete_name,
            vdot=round(vdot, 1),
            race_date=race_date,
            goal_time=goal,
        )
        plan._build_weeks()
        return plan

    def _build_weeks(self):
        """Assign week phases working backward from race date."""
        today = date.today()
        total_days = (self.race_date - today).days
        total_weeks = max(4, total_days // 7)

        taper_weeks = 3
        peak_weeks = min(4, max(2, total_weeks // 5))
        build_weeks = min(6, max(2, total_weeks // 3))
        base_weeks = total_weeks - taper_weeks - peak_weeks - build_weeks

        schedule = (
            [("base", w) for w in range(base_weeks)] +
            [("build", w) for w in range(build_weeks)] +
            [("peak", w) for w in range(peak_weeks)] +
            [("taper", w) for w in range(taper_weeks)]
        )

        week_start = today - timedelta(days=today.weekday())  # last Monday
        for idx, (phase, _) in enumerate(schedule):
            template = WEEK_TEMPLATES[phase]
            week_miles = sum(d["miles"] for d in template)
            self.weeks.append({
                "week_number": idx + 1,
                "phase": phase,
                "start_date": (week_start + timedelta(weeks=idx)).isoformat(),
                "total_miles": week_miles,
                "days": [dict(d) for d in template],
            })

    def to_dict(self) -> dict:
        return {
            "athlete": self.athlete_name,
            "vdot": self.vdot,
            "goal_marathon_time": self.goal_time,
            "race_date": self.race_date.isoformat(),
            "zones": self.zones.display(),
            "weeks": self.weeks,
        }
