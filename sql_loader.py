import os

import pyodbc

def get_db_connection() -> pyodbc.Connection:
    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DATABASE")
    username = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    driver = os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")

    if not all([server, database, username, password]):
        raise ValueError(
            "Missing one or more required environment variables: "
            "AZURE_SQL_SERVER, AZURE_SQL_DATABASE, AZURE_SQL_USER, AZURE_SQL_PASSWORD"
        )

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER=tcp:{server},1433;"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return pyodbc.connect(conn_str)


def insert_run_summary(conn: pyodbc.Connection, summary: dict) -> None:
    sql = """
    INSERT INTO runs (
        run_id,
        source_file_name,
        activity_name,
        start_time,
        end_time,
        duration_seconds,
        total_distance_km,
        total_distance_miles,
        avg_speed_kmh,
        avg_pace_min_per_km,
        elevation_gain_m,
        elevation_loss_m,
        calories_est,
        point_count
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    values = (
        summary["run_id"],
        summary["source_file_name"],
        summary.get("activity_name"),
        summary["start_time"],
        summary["end_time"],
        summary["duration_seconds"],
        summary["total_distance_km"],
        summary["total_distance_miles"],
        summary.get("avg_speed_kmh"),
        summary.get("avg_pace_min_per_km"),
        summary.get("elevation_gain_m"),
        summary.get("elevation_loss_m"),
        summary.get("calories_est"),
        summary["point_count"],
    )

    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()
    cursor.close()


def run_exists(conn: pyodbc.Connection, run_id: str) -> bool:
    sql = "SELECT 1 FROM runs WHERE run_id = ?"
    cursor = conn.cursor()
    cursor.execute(sql, (run_id,))
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def insert_run_summary_if_not_exists(conn: pyodbc.Connection, summary: dict) -> bool:
    if run_exists(conn, summary["run_id"]):
        return False

    insert_run_summary(conn, summary)
    return True


def track_points_exist(conn: pyodbc.Connection, run_id: str) -> bool:
    sql = "SELECT 1 FROM track_points WHERE run_id = ?"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (run_id,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def insert_track_points(conn: pyodbc.Connection, silver_records: list[dict]) -> None:
    if not silver_records:
        return

    sql = """
    INSERT INTO track_points (
        run_id,
        source_file_name,
        point_index,
        latitude,
        longitude,
        elevation_m,
        point_time,
        segment_distance_m,
        cumulative_distance_m,
        segment_seconds,
        instant_speed_kmh
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    values = [
        (
            r["run_id"],
            r["source_file_name"],
            r["point_index"],
            r["latitude"],
            r["longitude"],
            r.get("elevation_m"),
            r.get("point_time"),
            r.get("segment_distance_m"),
            r.get("cumulative_distance_m"),
            r.get("segment_seconds"),
            r.get("instant_speed_kmh"),
        )
        for r in silver_records
    ]

    cursor = conn.cursor()
    try:
        cursor.fast_executemany = True
        cursor.executemany(sql, values)
        conn.commit()
    finally:
        cursor.close()


def insert_track_points_if_not_exists(
    conn: pyodbc.Connection, run_id: str, silver_records: list[dict]
) -> bool:
    if track_points_exist(conn, run_id):
        return False

    insert_track_points(conn, silver_records)
    return True