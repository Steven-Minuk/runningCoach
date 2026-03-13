-- V1: Create runs table
-- Created: 2026-03-11
-- Description: Initial schema for GPX run summaries

CREATE TABLE runs (
    run_id               VARCHAR(100)  PRIMARY KEY,
    source_file_name     VARCHAR(255)  NOT NULL,
    activity_name        VARCHAR(255)  NULL,
    start_time           DATETIME2     NOT NULL,
    end_time             DATETIME2     NOT NULL,
    duration_seconds     FLOAT         NOT NULL,
    total_distance_km    FLOAT         NOT NULL,
    total_distance_miles FLOAT         NOT NULL,
    avg_speed_kmh        FLOAT         NULL,
    avg_pace_min_per_km  FLOAT         NULL,
    elevation_gain_m     FLOAT         NULL,
    elevation_loss_m     FLOAT         NULL,
    calories_est         FLOAT         NULL,
    point_count          INT           NOT NULL,
    created_at           DATETIME2     DEFAULT SYSUTCDATETIME()
);