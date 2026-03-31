# ai_coach/db_reader.py

import os
import pandas as pd
from sqlalchemy import create_engine, text
from langchain.tools import tool


def format_pace(decimal_pace: float) -> str:
    """Convert decimal pace (e.g. 5.58) to MM:SS string (e.g. '5:35').
    5.58 means 5 minutes + 0.58 * 60 = 34.8 seconds → 5:35 min/km."""
    if not decimal_pace or pd.isna(decimal_pace):
        return "N/A"
    mins = int(decimal_pace)
    secs = int(round((decimal_pace - mins) * 60))
    return f"{mins}:{secs:02d}"


def get_engine():
    server   = os.environ['AZURE_SQL_SERVER']
    database = os.environ['AZURE_SQL_DATABASE']
    user     = os.environ['AZURE_SQL_USER']
    password = os.environ['AZURE_SQL_PASSWORD']
    conn_str = (
        f"mssql+pyodbc://{user}:{password}@{server}/{database}"
        f"?driver=ODBC+Driver+18+for+SQL+Server"
        f"&Encrypt=yes&TrustServerCertificate=no"
    )
    return create_engine(conn_str)


@tool
def get_recent_runs(num_runs: int = 10) -> str:
    """Get the most recent runs from the database, including their run_id.
    Always call this first — the run_id returned here is required by
    get_run_pace_profile and get_elevation_profile."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(f"""
            SELECT TOP {num_runs}
                run_id,
                CONVERT(DATE, start_time)      AS date,
                total_distance_km,
                avg_pace_min_per_km,
                duration_seconds / 60.0        AS duration_minutes,
                elevation_gain_m,
                calories_est
            FROM runs
            ORDER BY start_time DESC
        """), conn)

    result  = f"Last {num_runs} runs:\n"
    result += "(pass run_id exactly as shown to get_run_pace_profile / get_elevation_profile)\n"
    result += "NOTE: pace is in MM:SS format (e.g. 5:35 means 5 minutes 35 seconds per km)\n\n"
    for _, row in df.iterrows():
        result += (
            f"- run_id={row['run_id']}  date={row['date']}  "
            f"{row['total_distance_km']:.2f} km "
            f"@ {format_pace(row['avg_pace_min_per_km'])} min/km "
            f"({row['duration_minutes']:.0f} mins)  "
            f"elev_gain={row['elevation_gain_m']:.0f} m\n"
        )
    return result


@tool
def get_training_stats() -> str:
    """Get overall training statistics — total distance, average pace,
    longest run, fastest pace, and weekly mileage for the last 4 weeks."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                COUNT(*)                   AS total_runs,
                SUM(total_distance_km)     AS total_km,
                AVG(total_distance_km)     AS avg_distance,
                AVG(avg_pace_min_per_km)   AS avg_pace,
                MAX(total_distance_km)     AS longest_run,
                MIN(avg_pace_min_per_km)   AS fastest_pace,
                SUM(elevation_gain_m)      AS total_elevation
            FROM runs
        """), conn)

        weekly = pd.read_sql(text("""
            SELECT
                DATEPART(WEEK, start_time) AS week,
                COUNT(*)                   AS runs,
                SUM(total_distance_km)     AS weekly_km
            FROM runs
            WHERE start_time >= DATEADD(WEEK, -4, GETDATE())
            GROUP BY DATEPART(WEEK, start_time)
            ORDER BY week DESC
        """), conn)

    s = df.iloc[0]
    result = f"""
OVERALL STATS:
NOTE: all paces are in MM:SS format (e.g. 5:35 means 5 minutes 35 seconds per km)
- Total runs      : {s['total_runs']}
- Total distance  : {s['total_km']:.1f} km
- Avg run distance: {s['avg_distance']:.2f} km
- Average pace    : {format_pace(s['avg_pace'])} min/km
- Longest run     : {s['longest_run']:.2f} km
- Fastest pace    : {format_pace(s['fastest_pace'])} min/km
- Total elev gain : {s['total_elevation']:.0f} m

RECENT WEEKLY MILEAGE:
"""
    for _, row in weekly.iterrows():
        result += f"- Week {int(row['week'])}: {row['runs']} runs, {row['weekly_km']:.1f} km\n"

    return result


@tool
def get_run_pace_profile(run_id: str) -> str:
    """Get the per-kilometre pace breakdown for a specific run.
    Use this to analyse pacing strategy — where the runner sped up or slowed
    down, positive/negative splits, and elevation context per km.
    IMPORTANT: call get_recent_runs first to get the exact run_id string."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("""
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
            WHERE run_id = :run_id
              AND instant_speed_kmh > 0
              AND cumulative_distance_m IS NOT NULL
            GROUP BY FLOOR(cumulative_distance_m / 1000)
            ORDER BY km_split
        """), conn, params={"run_id": run_id})

    if df.empty:
        return (
            f"No track point data found for run_id '{run_id}'.\n"
            "Double-check the run_id from get_recent_runs — it must match exactly."
        )

    result  = f"Per-km pace profile for run {run_id}:\n"
    result += "NOTE: pace is in MM:SS format (e.g. 5:35 means 5 minutes 35 seconds per km)\n"
    result += f"{'km':>4}  {'pace':>8}  {'speed kmh':>10}  {'elev delta':>10}  {'points':>7}\n"
    result += "-" * 50 + "\n"

    paces = []
    for _, row in df.iterrows():
        pace = row['avg_pace_min_per_km']
        elev = row['elevation_change_m']
        spd  = row['avg_speed_kmh']
        pts  = int(row['point_count'])
        if pace and not pd.isna(pace):
            pace_str = format_pace(pace)
            paces.append(pace)
        else:
            pace_str = "N/A"
        result += f"{int(row['km_split']):>4}  {pace_str:>8}  {spd:>10.2f}  {elev:>+10.1f}  {pts:>7}\n"

    if len(paces) >= 2:
        first_half  = paces[:len(paces) // 2]
        second_half = paces[len(paces) // 2:]
        avg_first   = sum(first_half)  / len(first_half)
        avg_second  = sum(second_half) / len(second_half)
        diff = avg_second - avg_first
        result += "\nSplit analysis:\n"
        result += f"  First half avg  : {format_pace(avg_first)} min/km\n"
        result += f"  Second half avg : {format_pace(avg_second)} min/km\n"
        if diff > 0.15:
            result += f"  WARNING: Positive split — faded by {format_pace(diff)} in second half\n"
        elif diff < -0.15:
            result += f"  GOOD: Negative split — stronger by {format_pace(abs(diff))} in second half\n"
        else:
            result += f"  GOOD: Even pacing — second half within {format_pace(abs(diff))} of first\n"

        min_pace   = min(paces)
        max_pace   = max(paces)
        fastest_km = int(df.iloc[paces.index(min_pace)]['km_split'])
        slowest_km = int(df.iloc[paces.index(max_pace)]['km_split'])
        result += f"  Fastest km: km {fastest_km} @ {format_pace(min_pace)} min/km\n"
        result += f"  Slowest km: km {slowest_km} @ {format_pace(max_pace)} min/km\n"

    return result


@tool
def get_elevation_profile(run_id: str) -> str:
    """Get the elevation and grade profile for a specific run in 500m segments.
    IMPORTANT: call get_recent_runs first to get the exact run_id string."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT
                segment_500m,
                AVG(elevation_m)                                          AS avg_elev_m,
                MAX(elevation_m)                                          AS max_elev_m,
                MIN(elevation_m)                                          AS min_elev_m,
                CASE
                    WHEN COUNT(*) > 1
                    THEN (MAX(elevation_m) - MIN(elevation_m)) / 500.0 * 100
                    ELSE 0
                END                                                       AS grade_pct,
                SUM(CASE WHEN elev_delta > 0 THEN elev_delta ELSE 0 END) AS gain_m
            FROM (
                SELECT
                    FLOOR(cumulative_distance_m / 500) + 1               AS segment_500m,
                    elevation_m,
                    elevation_m - LAG(elevation_m) OVER (ORDER BY point_index) AS elev_delta
                FROM track_points
                WHERE run_id = :run_id
                  AND elevation_m IS NOT NULL
                  AND cumulative_distance_m IS NOT NULL
            ) sub
            GROUP BY segment_500m
            ORDER BY segment_500m
        """), conn, params={"run_id": run_id})

        totals = pd.read_sql(text("""
            SELECT
                SUM(CASE WHEN seg_delta > 0 THEN  seg_delta ELSE 0 END) AS total_gain_m,
                SUM(CASE WHEN seg_delta < 0 THEN -seg_delta ELSE 0 END) AS total_loss_m,
                MAX(elevation_m)                                         AS peak_m,
                MIN(elevation_m)                                         AS low_m
            FROM (
                SELECT
                    elevation_m,
                    elevation_m - LAG(elevation_m) OVER (ORDER BY point_index) AS seg_delta
                FROM track_points
                WHERE run_id = :run_id
                  AND elevation_m IS NOT NULL
            ) sub
        """), conn, params={"run_id": run_id})

    if df.empty:
        return f"No elevation data found for run_id '{run_id}'."

    t = totals.iloc[0]
    result = (
        f"Elevation profile for run {run_id}:\n"
        f"  Total gain : {t['total_gain_m']:.1f} m\n"
        f"  Total loss : {t['total_loss_m']:.1f} m\n"
        f"  Peak       : {t['peak_m']:.1f} m\n"
        f"  Low point  : {t['low_m']:.1f} m\n\n"
        f"Per 500m segment:\n"
        f"{'seg':>5}  {'avg elev':>9}  {'max':>7}  {'min':>7}  {'grade%':>7}  {'gain m':>7}\n"
        + "-" * 54 + "\n"
    )
    for _, row in df.iterrows():
        result += (
            f"{int(row['segment_500m']):>5}  "
            f"{row['avg_elev_m']:>9.1f}m  "
            f"{row['max_elev_m']:>7.1f}m  "
            f"{row['min_elev_m']:>7.1f}m  "
            f"{row['grade_pct']:>+7.2f}%  "
            f"{row['gain_m']:>7.1f}m\n"
        )
    return result


@tool
def get_best_efforts(distances_km: list[float] = None) -> str:
    """Get the user's best (fastest) efforts over common race distances.
    Defaults to [1.0, 5.0, 10.0, 21.1] km."""
    if distances_km is None:
        distances_km = [1.0, 5.0, 10.0, 21.1]

    engine  = get_engine()
    results = []
    with engine.connect() as conn:
        for dist_km in distances_km:
            dist_m = dist_km * 1000
            df = pd.read_sql(text("""
                SELECT TOP 1
                    r.run_id,
                    CONVERT(DATE, r.start_time)         AS run_date,
                    t_end.cumulative_distance_m
                        - t_start.cumulative_distance_m AS actual_dist_m,
                    DATEDIFF(SECOND, t_start.point_time,
                                     t_end.point_time)  AS elapsed_seconds
                FROM track_points t_start
                JOIN track_points t_end
                    ON  t_end.run_id      = t_start.run_id
                    AND t_end.point_index > t_start.point_index
                    AND t_end.cumulative_distance_m - t_start.cumulative_distance_m
                        BETWEEN :dist_m * 0.995 AND :dist_m * 1.01
                JOIN runs r ON r.run_id = t_start.run_id
                WHERE t_start.cumulative_distance_m IS NOT NULL
                  AND t_end.cumulative_distance_m   IS NOT NULL
                  AND t_start.point_time IS NOT NULL
                  AND t_end.point_time   IS NOT NULL
                ORDER BY elapsed_seconds ASC
            """), conn, params={"dist_m": dist_m})
            results.append((dist_km, df))

    output = "Best efforts across all runs:\n"
    output += "NOTE: pace is in MM:SS format (e.g. 5:35 means 5 minutes 35 seconds per km)\n\n"
    found_any = False
    for dist_km, df in results:
        if df.empty or df.iloc[0]['elapsed_seconds'] is None:
            output += f"  {dist_km:5.1f} km : no complete effort found\n"
            continue
        found_any = True
        row      = df.iloc[0]
        secs     = int(row['elapsed_seconds'])
        mins_tot = secs // 60
        secs_rem = secs % 60
        pace_dec = secs / 60 / (row['actual_dist_m'] / 1000)
        output += (
            f"  {dist_km:5.1f} km : {mins_tot}:{secs_rem:02d}"
            f"  (pace {format_pace(pace_dec)} /km)"
            f"  — {row['run_date']}\n"
        )

    if not found_any:
        output += "No efforts found. Check that track_points has data.\n"

    return output