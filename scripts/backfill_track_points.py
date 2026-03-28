# scripts/backfill_track_points.py

import json
import os
import pyodbc
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

def get_db_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={os.environ['AZURE_SQL_SERVER']};"
        f"DATABASE={os.environ['AZURE_SQL_DATABASE']};"
        f"UID={os.environ['AZURE_SQL_USER']};"
        f"PWD={os.environ['AZURE_SQL_PASSWORD']};"
        f"Encrypt=yes;TrustServerCertificate=no;"
    )

def get_blob_client():
    return BlobServiceClient.from_connection_string(
        os.environ["AzureWebJobsStorage"]
    )

def run_already_loaded(cursor, run_id):
    cursor.execute(
        "SELECT COUNT(*) FROM track_points WHERE run_id = ?",
        run_id
    )
    return cursor.fetchone()[0] > 0

def backfill_track_points():
    blob_client = get_blob_client()
    container = blob_client.get_container_client("silver-track-points")
    conn = get_db_connection()
    cursor = conn.cursor()

    blobs = list(container.list_blobs())
    print(f"Found {len(blobs)} Silver blobs")

    success = 0
    skipped = 0
    failed  = 0

    for blob in blobs:
        run_id = blob.name.replace("_track_points.json", "")

        # Skip if already loaded
        if run_already_loaded(cursor, run_id):
            print(f"Skipping {run_id} - already loaded")
            skipped += 1
            continue

        try:
            # Download Silver JSON
            data = container.download_blob(blob.name).readall()
            points = json.loads(data)

            # Insert each point
            for point in points:
                cursor.execute("""
                    INSERT INTO track_points (
                        run_id, source_file_name, point_index, latitude, longitude,
                        elevation_m, point_time, segment_distance_m,
                        cumulative_distance_m, segment_seconds,
                        instant_speed_kmh
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    run_id,
                    point["source_file_name"],    # ← read directly from JSON
                    point["point_index"],
                    point["latitude"],
                    point["longitude"],
                    point.get("elevation_m"),
                    point.get("point_time"),
                    point.get("segment_distance_m"),
                    point.get("cumulative_distance_m"),
                    point.get("segment_seconds"),
                    point.get("instant_speed_kmh")
                )

            conn.commit()
            print(f"✅ Loaded {len(points)} points for {run_id}")
            success += 1

        except Exception as e:
            print(f"❌ Failed {run_id}: {e}")
            conn.rollback()
            failed += 1

    conn.close()
    print(f"""
Backfill complete!
✅ Success: {success}
⏭️  Skipped: {skipped}
❌ Failed:  {failed}
    """)

if __name__ == "__main__":
    backfill_track_points()