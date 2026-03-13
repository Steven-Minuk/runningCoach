# data_quality.py

from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────
# Constants — human limits for running
# ─────────────────────────────────────

MIN_PACE_MIN_PER_KM   = 2.5   # world record ~2:55/km
MAX_PACE_MIN_PER_KM   = 30.0  # very slow walk
MAX_SPEED_KMH         = 30.0  # sprinting max
MIN_DISTANCE_KM       = 0.01  # at least 10 meters
MAX_DISTANCE_KM       = 150.0 # ultramarathon max
MIN_DURATION_SECONDS  = 60    # at least 1 minute
MAX_DURATION_SECONDS  = 86400 # 24 hours max
MIN_POINTS            = 2     # need at least 2 points
MAX_ELEVATION_CHANGE  = 5000  # Everest is 8849m
VALID_LAT_RANGE       = (-90, 90)
VALID_LON_RANGE       = (-180, 180)


# ─────────────────────────────────────
# Data Quality Result
# ─────────────────────────────────────

class QualityCheckResult:
    def __init__(self):
        self.passed  = True
        self.errors  = []
        self.warnings = []

    def add_error(self, message: str):
        self.passed = False
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        lines = [f"Quality Check: {status}"]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return "\n".join(lines)


# ─────────────────────────────────────
# Level 1: GPX Input Validation
# ─────────────────────────────────────

def validate_gpx_points(points: list) -> QualityCheckResult:
    """Validate raw GPX track points before processing"""
    result = QualityCheckResult()

    # Check minimum points
    if len(points) < MIN_POINTS:
        result.add_error(
            f"Too few points: {len(points)} (minimum {MIN_POINTS})"
        )
        return result  # no point checking further

    # Check each point
    null_coords   = 0
    null_times    = 0
    invalid_coords = 0

    for i, point in enumerate(points):

        # Check coordinates exist
        if point.get("latitude") is None or point.get("longitude") is None:
            null_coords += 1
            continue

        lat = point["latitude"]
        lon = point["longitude"]

        # Check coordinate ranges
        if not (VALID_LAT_RANGE[0] <= lat <= VALID_LAT_RANGE[1]):
            result.add_error(f"Point {i}: invalid latitude {lat}")
            invalid_coords += 1

        if not (VALID_LON_RANGE[0] <= lon <= VALID_LON_RANGE[1]):
            result.add_error(f"Point {i}: invalid longitude {lon}")
            invalid_coords += 1

        # Check null island (0,0) — GPS glitch
        if lat == 0.0 and lon == 0.0:
            result.add_error(f"Point {i}: coordinates are 0,0 (null island)")
            invalid_coords += 1

        # Check timestamp
        if point.get("point_time") is None:
            null_times += 1

    # Add warnings for batches of issues
    if null_coords > 0:
        result.add_warning(f"{null_coords} points have missing coordinates")

    if null_times > 0:
        result.add_warning(f"{null_times} points have missing timestamps")

    if invalid_coords > 5:
        result.add_error(
            f"Too many invalid coordinates: {invalid_coords}"
        )

    return result


# ─────────────────────────────────────
# Level 2: Run Summary Validation
# ─────────────────────────────────────

def validate_run_summary(summary: dict) -> QualityCheckResult:
    """Validate calculated run summary before saving"""
    result = QualityCheckResult()

    # Check required fields exist
    required_fields = [
        "run_id", "source_file_name", "activity_name",
        "start_time", "end_time", "duration_seconds",
        "total_distance_km", "avg_pace_min_per_km",
        "point_count"
    ]
    for field in required_fields:
        if field not in summary or summary[field] is None:
            result.add_error(f"Missing required field: {field}")

    if not result.passed:
        return result  # stop here if missing fields

    # Check distance
    dist = summary["total_distance_km"]
    if dist < MIN_DISTANCE_KM:
        result.add_error(f"Distance too short: {dist:.3f} km")
    if dist > MAX_DISTANCE_KM:
        result.add_error(f"Distance too long: {dist:.1f} km")

    # Check duration
    duration = summary["duration_seconds"]
    if duration < MIN_DURATION_SECONDS:
        result.add_error(f"Duration too short: {duration:.0f} seconds")
    if duration > MAX_DURATION_SECONDS:
        result.add_error(f"Duration too long: {duration:.0f} seconds")

    # Check pace
    pace = summary["avg_pace_min_per_km"]
    if pace is not None and pace > 0:
        if pace < MIN_PACE_MIN_PER_KM:
            result.add_error(f"Pace too fast: {pace:.2f} min/km (superhuman)")
        if pace > MAX_PACE_MIN_PER_KM:
            result.add_error(f"Pace very slow: {pace:.2f} min/km (walking?)")

    # Check timestamps
    start = summary["start_time"]
    end   = summary["end_time"]
    if start and end:
        if start >= end:
            result.add_error(
                f"start_time {start} is not before end_time {end}"
            )

    # Check point count
    if summary["point_count"] < MIN_POINTS:
        result.add_error(
            f"Too few points: {summary['point_count']}"
        )

    # Check elevation (warning only)
    gain = summary.get("elevation_gain_m", 0) or 0
    loss = summary.get("elevation_loss_m", 0) or 0
    if gain > MAX_ELEVATION_CHANGE:
        result.add_warning(f"Unusual elevation gain: {gain:.0f}m")
    if loss > MAX_ELEVATION_CHANGE:
        result.add_warning(f"Unusual elevation loss: {loss:.0f}m")

    # Short run warning
    if dist < 0.5:
        result.add_warning(
            f"Very short run: {dist:.2f}km — warm up or GPS glitch?"
        )

    return result