import pytest
from datetime import datetime, timezone
from metrics import (
    haversine_distance_m,
    enrich_track_points,
    calculate_run_summary,
    estimate_calories
)

# ─────────────────────────────────────
# Test helpers
# ─────────────────────────────────────

def make_point(index, lat, lon, ele, hour, minute, second):
    """Helper to create a track point easily"""
    return {
        "point_index": index,
        "latitude": lat,
        "longitude": lon,
        "elevation_m": ele,
        "point_time": datetime(2021, 6, 8, hour, minute, second, tzinfo=timezone.utc)
    }


# ─────────────────────────────────────
# haversine_distance_m() tests
# ─────────────────────────────────────

def test_haversine_same_point_is_zero():
    dist = haversine_distance_m(35.0, 129.0, 35.0, 129.0)
    assert dist == 0.0

def test_haversine_returns_float():
    dist = haversine_distance_m(35.847781, 129.214460, 35.847830, 129.214387)
    assert isinstance(dist, float)

def test_haversine_is_positive():
    dist = haversine_distance_m(35.847781, 129.214460, 35.847830, 129.214387)
    assert dist > 0

def test_haversine_known_distance():
    """Two points roughly 9 meters apart"""
    dist = haversine_distance_m(35.847781, 129.214460, 35.847830, 129.214387)
    assert 8 < dist < 10

def test_haversine_is_symmetric():
    """Distance A→B should equal B→A"""
    dist_ab = haversine_distance_m(35.847781, 129.214460, 35.847830, 129.214387)
    dist_ba = haversine_distance_m(35.847830, 129.214387, 35.847781, 129.214460)
    assert abs(dist_ab - dist_ba) < 0.001


# ─────────────────────────────────────
# enrich_track_points() tests
# ─────────────────────────────────────

def test_enrich_empty_list():
    result = enrich_track_points([])
    assert result == []

def test_enrich_returns_same_count():
    points = [
        make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0),
        make_point(1, 35.847830, 129.214387, 42.3, 9, 0, 10),
    ]
    result = enrich_track_points(points)
    assert len(result) == 2

def test_enrich_first_point_distance_is_zero():
    points = [make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0)]
    result = enrich_track_points(points)
    assert result[0]["segment_distance_m"] == 0.0

def test_enrich_first_point_cumulative_is_zero():
    points = [make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0)]
    result = enrich_track_points(points)
    assert result[0]["cumulative_distance_m"] == 0.0

def test_enrich_first_point_speed_is_none():
    points = [make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0)]
    result = enrich_track_points(points)
    assert result[0]["instant_speed_kmh"] is None

def test_enrich_second_point_has_distance():
    points = [
        make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0),
        make_point(1, 35.847830, 129.214387, 42.3, 9, 0, 10),
    ]
    result = enrich_track_points(points)
    assert result[1]["segment_distance_m"] > 0

def test_enrich_cumulative_distance_increases():
    points = [
        make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0),
        make_point(1, 35.847830, 129.214387, 42.3, 9, 0, 10),
        make_point(2, 35.848023, 129.214098, 42.9, 9, 0, 20),
    ]
    result = enrich_track_points(points)
    assert result[0]["cumulative_distance_m"] == 0.0
    assert result[1]["cumulative_distance_m"] > result[0]["cumulative_distance_m"]
    assert result[2]["cumulative_distance_m"] > result[1]["cumulative_distance_m"]

def test_enrich_speed_is_positive():
    points = [
        make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0),
        make_point(1, 35.848781, 129.214460, 42.3, 9, 1, 0),
    ]
    result = enrich_track_points(points)
    assert result[1]["instant_speed_kmh"] > 0

def test_enrich_does_not_mutate_original():
    """Original points should not be modified"""
    points = [make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0)]
    original_keys = set(points[0].keys())
    enrich_track_points(points)
    assert set(points[0].keys()) == original_keys


# ─────────────────────────────────────
# calculate_run_summary() tests
# ─────────────────────────────────────

def make_enriched_points():
    """Two enriched points for summary testing"""
    from metrics import enrich_track_points
    points = [
        make_point(0, 35.847781, 129.214460, 42.2, 9, 0, 0),
        make_point(1, 35.848781, 129.214460, 42.5, 9, 5, 0),
        make_point(2, 35.849781, 129.214460, 43.0, 9, 10, 0),
    ]
    return enrich_track_points(points)

def test_summary_returns_dict():
    result = calculate_run_summary("Test Run", make_enriched_points())
    assert isinstance(result, dict)

def test_summary_has_required_fields():
    result = calculate_run_summary("Test Run", make_enriched_points())
    required = [
        "activity_name", "start_time", "end_time",
        "duration_seconds", "total_distance_km",
        "total_distance_miles", "avg_speed_kmh",
        "avg_pace_min_per_km", "elevation_gain_m",
        "elevation_loss_m", "calories_est", "point_count"
    ]
    for field in required:
        assert field in result, f"Missing field: {field}"

def test_summary_distance_is_positive():
    result = calculate_run_summary("Test Run", make_enriched_points())
    assert result["total_distance_km"] > 0

def test_summary_duration_is_positive():
    result = calculate_run_summary("Test Run", make_enriched_points())
    assert result["duration_seconds"] > 0

def test_summary_duration_correct():
    """3 points: 0min to 10min = 600 seconds"""
    result = calculate_run_summary("Test Run", make_enriched_points())
    assert result["duration_seconds"] == 600.0

def test_summary_miles_less_than_km():
    """Miles should always be less than km"""
    result = calculate_run_summary("Test Run", make_enriched_points())
    assert result["total_distance_miles"] < result["total_distance_km"]

def test_summary_point_count_correct():
    result = calculate_run_summary("Test Run", make_enriched_points())
    assert result["point_count"] == 3

def test_summary_empty_points_raises():
    with pytest.raises(ValueError):
        calculate_run_summary("Test Run", [])

def test_summary_activity_name_preserved():
    result = calculate_run_summary("My Test Run", make_enriched_points())
    assert result["activity_name"] == "My Test Run"


# ─────────────────────────────────────
# estimate_calories() tests
# ─────────────────────────────────────

def test_calories_positive():
    result = estimate_calories(weight_lb=165.0, distance_km=5.0)
    assert result > 0

def test_calories_reasonable_range():
    """5km run for 165lb person should be ~280-300 kcal"""
    result = estimate_calories(weight_lb=165.0, distance_km=5.0)
    assert 280 < result < 300

def test_calories_scales_with_distance():
    """More distance = more calories"""
    cal_5k = estimate_calories(weight_lb=165.0, distance_km=5.0)
    cal_10k = estimate_calories(weight_lb=165.0, distance_km=10.0)
    assert cal_10k > cal_5k

def test_calories_scales_with_weight():
    """Heavier person = more calories"""
    cal_light = estimate_calories(weight_lb=130.0, distance_km=5.0)
    cal_heavy = estimate_calories(weight_lb=200.0, distance_km=5.0)
    assert cal_heavy > cal_light