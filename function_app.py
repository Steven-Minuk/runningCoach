import json
import logging
import os
from pathlib import Path

import azure.functions as func
from azure.storage.blob import BlobServiceClient

from gpx_parser import parse_gpx
from metrics import enrich_track_points, calculate_run_summary
from sql_loader import get_db_connection, insert_run_summary_if_not_exists
from data_quality import validate_gpx_points, validate_run_summary

app = func.FunctionApp()


def upload_json_to_blob(
    connection_string: str,
    container_name: str,
    blob_name: str,
    payload,
) -> None:
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name,
    )
    blob_client.upload_blob(
        json.dumps(payload, indent=2),
        overwrite=True,
    )


@app.event_grid_trigger(arg_name="event")
def process_gpx_blob(event: func.EventGridEvent) -> None:
    logging.info(f"Event Grid trigger fired: {event.event_type}")

    # --- Extract blob URL and name from event ---
    try:
        data = event.get_json()
        blob_url = data["url"]
        blob_name = blob_url.split("/bronze-gpx/")[1]
    except (KeyError, IndexError) as e:
        logging.error(f"Failed to parse event data: {e}")
        return

    # --- Only process .gpx files ---
    if not blob_name.endswith(".gpx"):
        logging.info(f"Skipping non-GPX file: {blob_name}")
        return

    logging.info(f"Processing blob: {blob_name}")

    source_file_name = Path(blob_name).name
    run_id = Path(source_file_name).stem

    # --- Download blob content ---
    try:
        storage_connection = os.environ["AzureWebJobsStorage"]
        blob_service = BlobServiceClient.from_connection_string(storage_connection)
        blob_client = blob_service.get_blob_client(
            container="bronze-gpx",
            blob=blob_name
        )
        content = blob_client.download_blob().readall()
    except Exception as e:
        logging.error(f"Failed to download blob {blob_name}: {e}")
        raise

    # --- Write to temp file for parser ---
    try:
        temp_input_path = Path("/tmp") / source_file_name
        temp_input_path.write_bytes(content)
        parsed = parse_gpx(str(temp_input_path))
    except Exception as e:
        logging.error(f"Failed to parse GPX {blob_name}: {e}")
        raise

    activity_name = parsed["activity_name"]
    points = parsed["points"]

    # --- GPX Input Validation ---
    quality = validate_gpx_points(points)
    logging.info(quality.summary())
    if not quality.passed:
        raise ValueError(f"GPX quality check failed: {quality.errors}")

    # --- Transform ---
    try:
        enriched_points = enrich_track_points(points)
        summary = calculate_run_summary(
            activity_name=activity_name,
            points=enriched_points,
            weight_lb=float(os.environ.get("RUNNER_WEIGHT_LB", 165.0)),
        )
    except Exception as e:
        logging.error(f"Failed to transform data for {run_id}: {e}")
        raise

    summary["run_id"] = run_id
    summary["source_file_name"] = source_file_name

    # --- Build silver records ---
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

    # --- Validating Summary ---
    quality = validate_run_summary(summary)
    logging.info(quality.summary())
    if not quality.passed:
        raise ValueError(f"Summary quality check failed: {quality.errors}")

    # --- Upload to Silver and Gold ---
    silver_blob_name = f"{run_id}_track_points.json"
    gold_blob_name = f"{run_id}_summary.json"

    try:
        upload_json_to_blob(
            connection_string=storage_connection,
            container_name="silver-track-points",
            blob_name=silver_blob_name,
            payload=silver_records,
        )
        logging.info(f"Written silver blob: {silver_blob_name}")

        upload_json_to_blob(
            connection_string=storage_connection,
            container_name="gold-run-summary",
            blob_name=gold_blob_name,
            payload=summary,
        )
        logging.info(f"Written gold blob: {gold_blob_name}")
    except Exception as e:
        logging.error(f"Failed to upload blobs for {run_id}: {e}")
        raise    

    # --- Load to SQL ---
    try:
        conn = get_db_connection()
        try:
            inserted = insert_run_summary_if_not_exists(conn, summary)
            if inserted:
                logging.info(f"Inserted run_id={run_id} into Azure SQL.")
            else:
                logging.info(f"Skipped SQL insert for run_id={run_id}, already exists.")
        finally:
            conn.close()
    except Exception as e:
        logging.error(f"Failed to insert SQL for {run_id}: {e}")
        raise

    logging.info(f"Finished processing run_id={run_id}")