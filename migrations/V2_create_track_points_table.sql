-- V2: Create track_points table for silver layer data
-- Created: 2026-03-26
-- Reason: Enable per-point analysis for AI coach and Tableau

CREATE TABLE track_points (
    point_id              BIGINT IDENTITY PRIMARY KEY,
    run_id                VARCHAR(100) NOT NULL,
    source_file_name      VARCHAR(255) NOT NULL,
    point_index           INT NOT NULL,
    latitude              FLOAT NULL,
    longitude             FLOAT NULL,
    elevation_m           FLOAT NULL,
    point_time            DATETIME2 NULL,
    segment_distance_m    FLOAT NULL,
    cumulative_distance_m FLOAT NULL,
    segment_seconds       FLOAT NULL,
    instant_speed_kmh     FLOAT NULL,
    created_at            DATETIME2 DEFAULT SYSUTCDATETIME(),

    CONSTRAINT fk_track_points_run
        FOREIGN KEY (run_id)
        REFERENCES runs(run_id)
)

-- Index for fast queries by run
CREATE INDEX idx_track_points_run_id
    ON track_points(run_id)

-- Index for time-based queries
CREATE INDEX idx_track_points_time
    ON track_points(point_time)