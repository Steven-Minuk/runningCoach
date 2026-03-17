# ai_coach/db_reader.py

import pyodbc
import os
import pandas as pd
from langchain.tools import tool


def get_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={os.environ['AZURE_SQL_SERVER']};"
        f"DATABASE={os.environ['AZURE_SQL_DATABASE']};"
        f"UID={os.environ['AZURE_SQL_USER']};"
        f"PWD={os.environ['AZURE_SQL_PASSWORD']};"
        f"Encrypt=yes;TrustServerCertificate=no;"
    )


@tool
def get_recent_runs(num_runs: int = 10) -> str:
    """Get the most recent runs from the database.
    Use this to understand the user's recent training."""
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT TOP {num_runs}
            run_id,
            CONVERT(DATE, start_time) as date,
            total_distance_km,
            avg_pace_min_per_km,
            duration_seconds / 60.0 as duration_minutes,
            elevation_gain_m,
            calories_est
        FROM runs
        ORDER BY start_time DESC
    """, conn)
    conn.close()

    result = f"Last {num_runs} runs:\n"
    for _, row in df.iterrows():
        result += (
            f"- {row['date']}: "
            f"{row['total_distance_km']:.2f}km "
            f"@ {row['avg_pace_min_per_km']:.2f} min/km "
            f"({row['duration_minutes']:.0f} mins)\n"
        )
    return result


@tool
def get_training_stats() -> str:
    """Get overall training statistics.
    Use this to understand the user's fitness level and training history."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT
            COUNT(*) as total_runs,
            SUM(total_distance_km) as total_km,
            AVG(total_distance_km) as avg_distance,
            AVG(avg_pace_min_per_km) as avg_pace,
            MAX(total_distance_km) as longest_run,
            MIN(avg_pace_min_per_km) as fastest_pace,
            SUM(elevation_gain_m) as total_elevation
        FROM runs
    """, conn)

    # Weekly mileage last 4 weeks
    weekly = pd.read_sql("""
        SELECT
            DATEPART(WEEK, start_time) as week,
            COUNT(*) as runs,
            SUM(total_distance_km) as weekly_km
        FROM runs
        WHERE start_time >= DATEADD(WEEK, -4, GETDATE())
        GROUP BY DATEPART(WEEK, start_time)
        ORDER BY week DESC
    """, conn)
    conn.close()

    s = df.iloc[0]
    result = f"""
OVERALL STATS:
- Total runs: {s['total_runs']}
- Total distance: {s['total_km']:.1f} km
- Average run distance: {s['avg_distance']:.2f} km
- Average pace: {s['avg_pace']:.2f} min/km
- Longest run: {s['longest_run']:.2f} km
- Fastest pace: {s['fastest_pace']:.2f} min/km
- Total elevation gain: {s['total_elevation']:.0f} m

RECENT WEEKLY MILEAGE:
"""
    for _, row in weekly.iterrows():
        result += f"- Week {int(row['week'])}: {row['runs']} runs, {row['weekly_km']:.1f} km\n"

    return result