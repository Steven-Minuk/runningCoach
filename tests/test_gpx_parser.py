import pytest
from datetime import datetime, timezone
from gpx_parser import parse_gpx, parse_time


FIXTURE_PATH = "tests/fixtures/sample.gpx"


# ─────────────────────────────────────
# parse_time() tests
# ─────────────────────────────────────

def test_parse_time_valid():
    result = parse_time("2021-06-08T09:03:53Z")
    assert result.year == 2021
    assert result.month == 6
    assert result.day == 8

def test_parse_time_returns_datetime():
    result = parse_time("2021-06-08T09:03:53Z")
    assert isinstance(result, datetime)

def test_parse_time_is_utc():
    result = parse_time("2021-06-08T09:03:53Z")
    assert result.tzinfo is not None

def test_parse_time_none_returns_none():
    result = parse_time(None)
    assert result is None

def test_parse_time_empty_returns_none():
    result = parse_time("")
    assert result is None


# ─────────────────────────────────────
# parse_gpx() tests
# ─────────────────────────────────────

def test_parse_gpx_returns_dict():
    result = parse_gpx(FIXTURE_PATH)
    assert isinstance(result, dict)

def test_parse_gpx_has_required_keys():
    result = parse_gpx(FIXTURE_PATH)
    assert "activity_name" in result
    assert "track_time" in result
    assert "points" in result

def test_parse_gpx_has_points():
    result = parse_gpx(FIXTURE_PATH)
    assert len(result["points"]) > 0

def test_parse_gpx_activity_name_is_string():
    result = parse_gpx(FIXTURE_PATH)
    assert isinstance(result["activity_name"], str)
    assert len(result["activity_name"]) > 0

def test_parse_gpx_point_has_required_fields():
    result = parse_gpx(FIXTURE_PATH)
    first_point = result["points"][0]
    for field in ["point_index", "latitude", "longitude", "elevation_m", "point_time"]:
        assert field in first_point, f"Missing field: {field}"

def test_parse_gpx_coordinates_are_floats():
    result = parse_gpx(FIXTURE_PATH)
    point = result["points"][0]
    assert isinstance(point["latitude"], float)
    assert isinstance(point["longitude"], float)

def test_parse_gpx_latitude_in_valid_range():
    result = parse_gpx(FIXTURE_PATH)
    for point in result["points"]:
        assert -90 <= point["latitude"] <= 90

def test_parse_gpx_longitude_in_valid_range():
    result = parse_gpx(FIXTURE_PATH)
    for point in result["points"]:
        assert -180 <= point["longitude"] <= 180

def test_parse_gpx_point_index_sequential():
    result = parse_gpx(FIXTURE_PATH)
    for i, point in enumerate(result["points"]):
        assert point["point_index"] == i

def test_parse_gpx_elevation_is_float():
    result = parse_gpx(FIXTURE_PATH)
    for point in result["points"]:
        if point["elevation_m"] is not None:
            assert isinstance(point["elevation_m"], float)

def test_parse_gpx_timestamps_are_datetime():
    result = parse_gpx(FIXTURE_PATH)
    for point in result["points"]:
        if point["point_time"] is not None:
            assert isinstance(point["point_time"], datetime)

def test_parse_gpx_invalid_file_raises():
    with pytest.raises(Exception):
        parse_gpx("tests/fixtures/nonexistent.gpx")