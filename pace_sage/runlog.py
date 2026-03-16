"""
Run log: persistent storage and analytics for recorded runs.
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Optional

from .engine import (
    pace_to_seconds, seconds_to_pace, miles_to_km,
    hms_to_seconds, seconds_to_hms
)

DEFAULT_LOG_PATH = Path.home() / ".pace_sage" / "runs.json"


@dataclass
class Run:
    run_date: str          # ISO date YYYY-MM-DD
    distance_miles: float
    duration_seconds: float
    run_type: str          # easy | long | threshold | interval | race
    notes: str = ""
    heart_rate_avg: Optional[int] = None
    elevation_ft: Optional[float] = None

    @property
    def pace_per_mile(self) -> str:
        spm = self.duration_seconds / self.distance_miles
        return seconds_to_pace(spm)

    @property
    def pace_per_km(self) -> str:
        spkm = self.duration_seconds / miles_to_km(self.distance_miles)
        return seconds_to_pace(spkm)

    @property
    def duration_hms(self) -> str:
        return seconds_to_hms(self.duration_seconds)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pace_per_mile"] = self.pace_per_mile
        d["pace_per_km"] = self.pace_per_km
        d["duration_hms"] = self.duration_hms
        return d


class RunLog:
    def __init__(self, path: Path = DEFAULT_LOG_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._runs: list[Run] = []
        self._load()

    def _load(self):
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            self._runs = [Run(**{k: v for k, v in r.items()
                                 if k in Run.__dataclass_fields__})
                          for r in raw]

    def _save(self):
        self.path.write_text(
            json.dumps([asdict(r) for r in self._runs], indent=2)
        )

    def add(self, run: Run):
        self._runs.append(run)
        self._save()

    def all_runs(self) -> list[Run]:
        return sorted(self._runs, key=lambda r: r.run_date)

    def recent(self, n: int = 10) -> list[Run]:
        return self.all_runs()[-n:]

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def total_miles(self) -> float:
        return sum(r.distance_miles for r in self._runs)

    def weekly_mileage(self) -> dict[str, float]:
        """Return {ISO week string: total miles} dict."""
        from collections import defaultdict
        from datetime import date as _date
        weekly: dict[str, float] = defaultdict(float)
        for r in self._runs:
            d = _date.fromisoformat(r.run_date)
            iso_week = d.strftime("%G-W%V")
            weekly[iso_week] += r.distance_miles
        return dict(sorted(weekly.items()))

    def avg_pace(self, run_type: Optional[str] = None) -> str:
        """Average pace per mile across filtered runs."""
        runs = self._runs if run_type is None else [
            r for r in self._runs if r.run_type == run_type
        ]
        if not runs:
            return "--:--"
        total_sec = sum(r.duration_seconds for r in runs)
        total_miles = sum(r.distance_miles for r in runs)
        return seconds_to_pace(total_sec / total_miles)

    def longest_run(self) -> Optional[Run]:
        if not self._runs:
            return None
        return max(self._runs, key=lambda r: r.distance_miles)

    def pr_pace(self, run_type: str = "race") -> Optional[str]:
        """Best (fastest) pace for a given run type."""
        runs = [r for r in self._runs if r.run_type == run_type]
        if not runs:
            return None
        best = min(runs, key=lambda r: r.duration_seconds / r.distance_miles)
        return best.pace_per_mile

    def summary(self) -> dict:
        return {
            "total_runs": len(self._runs),
            "total_miles": round(self.total_miles(), 1),
            "avg_easy_pace": self.avg_pace("easy"),
            "avg_long_pace": self.avg_pace("long"),
            "longest_run_miles": self.longest_run().distance_miles if self.longest_run() else 0,
            "race_pr_pace": self.pr_pace("race") or "N/A",
        }

    def export_json(self, path: str):
        out = [r.to_dict() for r in self.all_runs()]
        Path(path).write_text(json.dumps(out, indent=2))
        return path
