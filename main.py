import json
from pathlib import Path

from gpx_parser import parse_gpx
from metrics import enrich_track_points, calculate_run_summary


def main() -> None:
    file_path = "2021-06-08-180353.gpx"  # change this to your GPX file name/path
    input_path = Path(file_path)

    source_file_name = input_path.name
    run_id = input_path.stem

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    parsed = parse_gpx(file_path)
    activity_name = parsed["activity_name"]
    points = parsed["points"]

    enriched_points = enrich_track_points(points)
    summary = calculate_run_summary(
        activity_name=activity_name,
        points=enriched_points,
        weight_lb=165.0,
    )

    summary["run_id"] = run_id
    summary["source_file_name"] = source_file_name

    silver_path = output_dir / f"{run_id}_track_points.json"
    gold_path = output_dir / f"{run_id}_summary.json"

    silver_records = []
    for point in enriched_points:
        silver_records.append(
            {
                "run_id": run_id,
                "source_file_name": source_file_name,
                "point_index": point["point_index"],
                "latitude": point["latitude"],
                "longitude": point["longitude"],
                "elevation_m": point["elevation_m"],
                "point_time": point["point_time"].isoformat() if point["point_time"] else None,
                "segment_distance_m": point["segment_distance_m"],
                "cumulative_distance_m": point["cumulative_distance_m"],
                "segment_seconds": point["segment_seconds"],
                "instant_speed_kmh": point["instant_speed_kmh"],
            }
        )

    with open(silver_path, "w", encoding="utf-8") as f:
        json.dump(silver_records, f, indent=2)

    with open(gold_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("=== Run Summary ===")
    print(json.dumps(summary, indent=2))
    print()
    print(f"Silver output saved to: {silver_path}")
    print(f"Gold output saved to: {gold_path}")


if __name__ == "__main__":
    main()