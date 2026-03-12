import math
from typing import Any


EARTH_RADIUS_M = 6371000


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c


def enrich_track_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not points:
        return []

    enriched: list[dict[str, Any]] = []
    cumulative_distance_m = 0.0

    for i, point in enumerate(points):
        point_copy = point.copy()

        if i == 0:
            point_copy["segment_distance_m"] = 0.0
            point_copy["cumulative_distance_m"] = 0.0
            point_copy["segment_seconds"] = 0.0
            point_copy["instant_speed_kmh"] = None
        else:
            prev = points[i - 1]

            segment_distance_m = haversine_distance_m(
                prev["latitude"],
                prev["longitude"],
                point["latitude"],
                point["longitude"],
            )
            cumulative_distance_m += segment_distance_m

            if prev["point_time"] and point["point_time"]:
                segment_seconds = (point["point_time"] - prev["point_time"]).total_seconds()
            else:
                segment_seconds = 0.0

            if segment_seconds > 0:
                instant_speed_kmh = (segment_distance_m / 1000) / (segment_seconds / 3600)
            else:
                instant_speed_kmh = None

            point_copy["segment_distance_m"] = segment_distance_m
            point_copy["cumulative_distance_m"] = cumulative_distance_m
            point_copy["segment_seconds"] = segment_seconds
            point_copy["instant_speed_kmh"] = instant_speed_kmh

        enriched.append(point_copy)

    return enriched


def calculate_run_summary(
    activity_name: str,
    points: list[dict[str, Any]],
    weight_lb: float = 165.0,
) -> dict[str, Any]:
    if not points:
        raise ValueError("No track points found.")

    start_time = points[0]["point_time"]
    end_time = points[-1]["point_time"]

    if start_time is None or end_time is None:
        raise ValueError("Missing point_time values in track points.")

    total_distance_m = points[-1]["cumulative_distance_m"]
    total_distance_km = total_distance_m / 1000
    total_distance_miles = total_distance_km * 0.621371

    duration_seconds = (end_time - start_time).total_seconds()
    duration_hours = duration_seconds / 3600 if duration_seconds > 0 else 0
    duration_minutes = duration_seconds / 60 if duration_seconds > 0 else 0

    avg_speed_kmh = (total_distance_km / duration_hours) if duration_hours > 0 else 0
    avg_pace_min_per_km = (duration_minutes / total_distance_km) if total_distance_km > 0 else None

    elevation_gain_m = 0.0
    elevation_loss_m = 0.0

    for i in range(1, len(points)):
        prev_ele = points[i - 1]["elevation_m"]
        curr_ele = points[i]["elevation_m"]

        if prev_ele is None or curr_ele is None:
            continue

        diff = curr_ele - prev_ele
        if diff > 0:
            elevation_gain_m += diff
        elif diff < 0:
            elevation_loss_m += abs(diff)

    calories_est = estimate_calories(weight_lb=weight_lb, distance_km=total_distance_km)

    return {
        "activity_name": activity_name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": round(duration_seconds, 2),
        "total_distance_km": round(total_distance_km, 3),
        "total_distance_miles": round(total_distance_miles, 3),
        "avg_speed_kmh": round(avg_speed_kmh, 2),
        "avg_pace_min_per_km": round(avg_pace_min_per_km, 2) if avg_pace_min_per_km else None,
        "elevation_gain_m": round(elevation_gain_m, 2),
        "elevation_loss_m": round(elevation_loss_m, 2),
        "calories_est": round(calories_est, 2),
        "point_count": len(points),
    }


def estimate_calories(weight_lb: float, distance_km: float) -> float:
    weight_kg = weight_lb * 0.453592
    kcal_per_kg_per_km = 0.75
    return weight_kg * distance_km * kcal_per_kg_per_km