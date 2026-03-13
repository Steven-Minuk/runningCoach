CREATE TABLE runs (
    run_id VARCHAR(100) PRIMARY KEY,
    source_file_name VARCHAR(255) NOT NULL,
    activity_name VARCHAR(255) NULL,
    start_time DATETIME2 NOT NULL,
    end_time DATETIME2 NOT NULL,
    duration_seconds FLOAT NOT NULL,
    total_distance_km FLOAT NOT NULL,
    total_distance_miles FLOAT NOT NULL,
    avg_speed_kmh FLOAT NULL,
    avg_pace_min_per_km FLOAT NULL,
    elevation_gain_m FLOAT NULL,
    elevation_loss_m FLOAT NULL,
    calories_est FLOAT NULL,
    point_count INT NOT NULL,
    created_at DATETIME2 DEFAULT SYSUTCDATETIME()
);

SELECT * FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME = 'runs';

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
VALUES (
    '2021-06-08-180353',
    '2021-06-08-180353.gpx',
    'Running 6/8/21 6:03 pm',
    '2021-06-08T09:03:53',
    '2021-06-08T09:13:33',
    580.0,
    0.675,
    0.420,
    4.19,
    14.31,
    4.4,
    5.9,
    37.91,
    63
);

Select * from runs;

Delete from runs where run_id = '2021-06-08-180353';