# debug_silver.py
# Run this from your project root to test silver tools directly.
# Usage: python debug_silver.py
#
# This bypasses the agent entirely so you can see the exact error
# if track_points data can't be read.

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "ai_coach"))

from dotenv import load_dotenv
load_dotenv()

import pyodbc
import pandas as pd


def get_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={os.environ['AZURE_SQL_SERVER']};"
        f"DATABASE={os.environ['AZURE_SQL_DATABASE']};"
        f"UID={os.environ['AZURE_SQL_USER']};"
        f"PWD={os.environ['AZURE_SQL_PASSWORD']};"
        f"Encrypt=yes;TrustServerCertificate=no;"
    )


def test_1_latest_run_id():
    """Step 1: Get the run_id for the most recent run."""
    print("\n── Step 1: Latest run ──────────────────────────")
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT TOP 1 run_id, source_file_name, start_time,
                         total_distance_km, avg_pace_min_per_km
            FROM runs
            ORDER BY start_time DESC
        """, conn)
    finally:
        conn.close()

    if df.empty:
        print("ERROR: No rows in runs table.")
        return None

    row = df.iloc[0]
    print(f"  run_id          : {row['run_id']}")
    print(f"  source_file_name: {row['source_file_name']}")
    print(f"  start_time      : {row['start_time']}")
    print(f"  distance        : {row['total_distance_km']:.2f} km")
    print(f"  avg pace        : {row['avg_pace_min_per_km']:.2f} min/km")
    return str(row['run_id'])


def test_2_track_points_exist(run_id):
    """Step 2: Check whether track_points rows exist for this run_id."""
    print("\n── Step 2: track_points row count ─────────────")
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT COUNT(*) AS cnt FROM track_points WHERE run_id = ?
        """, conn, params=[run_id])
    finally:
        conn.close()

    count = df.iloc[0]['cnt']
    print(f"  track_points rows for run_id {run_id}: {count}")

    if count == 0:
        print("\n  !! PROBLEM: No track_points rows for this run.")
        print("     This means function_app.py didn't insert them yet,")
        print("     or the backfill didn't include this run.")
        print("     Fix: re-upload the GPX, or run backfill_track_points.py again.")
    return count


def test_3_sample_points(run_id):
    """Step 3: Show the first 5 raw track_points rows to check column values."""
    print("\n── Step 3: Sample track_points rows ───────────")
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT TOP 5
                point_id, point_index, latitude, longitude,
                elevation_m, cumulative_distance_m,
                instant_speed_kmh, point_time
            FROM track_points
            WHERE run_id = ?
            ORDER BY point_index
        """, conn, params=[run_id])
    finally:
        conn.close()

    if df.empty:
        print("  No rows returned.")
        return

    print(df.to_string(index=False))

    # Check for nulls in critical columns
    nulls = {
        "cumulative_distance_m": df['cumulative_distance_m'].isna().sum(),
        "instant_speed_kmh":     df['instant_speed_kmh'].isna().sum(),
        "elevation_m":           df['elevation_m'].isna().sum(),
        "point_time":            df['point_time'].isna().sum(),
    }
    print("\n  Null counts in sample (out of 5 rows):")
    for col, n in nulls.items():
        flag = " ← !! ALL NULL" if n == 5 else ""
        print(f"    {col}: {n}{flag}")


def test_4_pace_profile(run_id):
    """Step 4: Run the exact pace profile SQL and show result."""
    print("\n── Step 4: Pace profile query ──────────────────")
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT
                FLOOR(cumulative_distance_m / 1000) + 1  AS km_split,
                COUNT(*)                                  AS point_count,
                AVG(instant_speed_kmh)                    AS avg_speed_kmh,
                CASE
                    WHEN AVG(instant_speed_kmh) > 0
                    THEN 60.0 / AVG(instant_speed_kmh)
                    ELSE NULL
                END                                       AS avg_pace_min_per_km,
                MAX(elevation_m) - MIN(elevation_m)       AS elevation_change_m
            FROM track_points
            WHERE run_id = ?
              AND instant_speed_kmh > 0
              AND cumulative_distance_m IS NOT NULL
            GROUP BY FLOOR(cumulative_distance_m / 1000)
            ORDER BY km_split
        """, conn, params=[run_id])
    except Exception as e:
        print(f"  SQL ERROR: {e}")
        return
    finally:
        conn.close()

    if df.empty:
        print("  No rows returned — check Step 3 null counts above.")
        return

    print(df.to_string(index=False))


def test_5_elevation_profile(run_id):
    """Step 5: Run the fixed elevation profile SQL and show result."""
    print("\n── Step 5: Elevation profile query ────────────")
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT
                segment_500m,
                AVG(elevation_m)   AS avg_elev_m,
                MAX(elevation_m)   AS max_elev_m,
                MIN(elevation_m)   AS min_elev_m,
                CASE
                    WHEN COUNT(*) > 1
                    THEN (MAX(elevation_m) - MIN(elevation_m)) / 500.0 * 100
                    ELSE 0
                END                AS grade_pct,
                SUM(CASE WHEN elev_delta > 0 THEN elev_delta ELSE 0 END) AS gain_m
            FROM (
                SELECT
                    FLOOR(cumulative_distance_m / 500) + 1 AS segment_500m,
                    elevation_m,
                    elevation_m - LAG(elevation_m) OVER (ORDER BY point_index) AS elev_delta
                FROM track_points
                WHERE run_id = ?
                  AND elevation_m IS NOT NULL
                  AND cumulative_distance_m IS NOT NULL
            ) sub
            GROUP BY segment_500m
            ORDER BY segment_500m
        """, conn, params=[run_id])
    except Exception as e:
        print(f"  SQL ERROR: {e}")
        return
    finally:
        conn.close()

    if df.empty:
        print("  No rows returned.")
        return

    print(df.to_string(index=False))


if __name__ == "__main__":
    run_id = test_1_latest_run_id()
    if not run_id:
        sys.exit(1)

    count = test_2_track_points_exist(run_id)

    test_3_sample_points(run_id)

    if count > 0:
        test_4_pace_profile(run_id)
        test_5_elevation_profile(run_id)
    else:
        print("\n⛔ Skipping pace/elevation tests — no track_points rows to query.")

    print("\n── Done ────────────────────────────────────────")
    print("Paste the full output above into the chat so we can diagnose the issue.")