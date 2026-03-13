# tests/test_data_quality.py

import pytest
from datetime import datetime, timezone
from data_quality import (
    validate_gpx_points,
    validate_run_summary,
    QualityCheckResult
)


# ─────────────────────────────────────
# Helpers
# ─────────────────────────────────────

def make_point(lat=35.847781, lon=129.214460, ele=42.2, hour=9, minute=0, second=0):
    return {
        "point_index": 0,
        "latitude":    lat,
        "longitude":   lon,
        "elevation_m": ele,
        "point_time":  datetime(2021, 6, 8, hour, minute, second, tzinfo=timezone.utc)
    }

def make_summary(**kwargs):
    base = {
        "run_id":               "2021-06-08-180353",
        "source_file_name":     "2021-06-08-180353.gpx",
        "activity_name":        "Test Run",
        "start_time":           datetime(2021, 6, 8, 9, 0, 0, tzinfo=timezone.utc),
        "end_time":             datetime(2021, 6, 8, 9, 30, 0, tzinfo=timezone.utc),
        "duration_seconds":     1800.0,
        "total_distance_km":    5.0,
        "total_distance_miles": 3.1,
        "avg_speed_kmh":        10.0,
        "avg_pace_min_per_km":  6.0,
        "elevation_gain_m":     50.0,
        "elevation_loss_m":     50.0,
        "calories_est":         280.0,
        "point_count":          100
    }
    base.update(kwargs)
    return base


# ─────────────────────────────────────
# QualityCheckResult tests
# ─────────────────────────────────────

def test_result_passes_by_default():
    result = QualityCheckResult()
    assert result.passed is True

def test_result_fails_on_error():
    result = QualityCheckResult()
    result.add_error("something wrong")
    assert result.passed is False

def test_result_warning_does_not_fail():
    result = QualityCheckResult()
    result.add_warning("something suspicious")
    assert result.passed is True

def test_result_summary_contains_status():
    result = QualityCheckResult()
    assert "PASSED" in result.summary()
    result.add_error("bad data")
    assert "FAILED" in result.summary()


# ─────────────────────────────────────
# validate_gpx_points() tests
# ─────────────────────────────────────

def test_valid_points_pass():
    points = [make_point(), make_point(lat=35.848, lon=129.215)]
    result = validate_gpx_points(points)
    assert result.passed is True

def test_empty_points_fails():
    result = validate_gpx_points([])
    assert result.passed is False

def test_single_point_fails():
    result = validate_gpx_points([make_point()])
    assert result.passed is False

def test_null_island_fails():
    points = [make_point(lat=0.0, lon=0.0), make_point()]
    result = validate_gpx_points(points)
    assert result.passed is False

def test_invalid_latitude_fails():
    points = [make_point(lat=999.0), make_point()]
    result = validate_gpx_points(points)
    assert result.passed is False

def test_invalid_longitude_fails():
    points = [make_point(lon=999.0), make_point()]
    result = validate_gpx_points(points)
    assert result.passed is False

def test_valid_korean_coordinates_pass():
    points = [
        make_point(lat=35.847781, lon=129.214460),
        make_point(lat=35.848023, lon=129.214098)
    ]
    result = validate_gpx_points(points)
    assert result.passed is True

def test_valid_austin_coordinates_pass():
    points = [
        make_point(lat=30.270, lon=-97.770),
        make_point(lat=30.271, lon=-97.771)
    ]
    result = validate_gpx_points(points)
    assert result.passed is True


# ─────────────────────────────────────
# validate_run_summary() tests
# ─────────────────────────────────────

def test_valid_summary_passes():
    result = validate_run_summary(make_summary())
    assert result.passed is True

def test_missing_run_id_fails():
    result = validate_run_summary(make_summary(run_id=None))
    assert result.passed is False

def test_missing_distance_fails():
    result = validate_run_summary(make_summary(total_distance_km=None))
    assert result.passed is False

def test_zero_distance_fails():
    result = validate_run_summary(make_summary(total_distance_km=0.0))
    assert result.passed is False

def test_too_long_distance_fails():
    result = validate_run_summary(make_summary(total_distance_km=200.0))
    assert result.passed is False

def test_too_short_duration_fails():
    result = validate_run_summary(make_summary(duration_seconds=30.0))
    assert result.passed is False

def test_superhuman_pace_fails():
    result = validate_run_summary(make_summary(avg_pace_min_per_km=1.0))
    assert result.passed is False

def test_start_after_end_fails():
    result = validate_run_summary(make_summary(
        start_time=datetime(2021, 6, 8, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2021, 6, 8, 9, 0, 0, tzinfo=timezone.utc)
    ))
    assert result.passed is False

def test_short_run_gives_warning():
    result = validate_run_summary(make_summary(total_distance_km=0.3))
    assert result.passed is True        # warning not error
    assert len(result.warnings) > 0

def test_slow_pace_fails():
    result = validate_run_summary(make_summary(avg_pace_min_per_km=31.0))
    assert result.passed is False