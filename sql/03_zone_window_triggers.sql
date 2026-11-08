-- 03 PRD TRIGGER REPLAY AT ZONE x 10-MINUTE-WINDOW LEVEL  (DuckDB)
-- Pandas twin: liquidity/simulate.py :: build_windows() + simulate_policy()
--
-- Concepts: time_bucket, GROUP BY + HAVING (reliability guard), window
-- functions (LAG, rolling AVG), PARTITION BY.
--
-- NOTE ON LAG: LAG looks at the previous ROW, not the previous 10 minutes.
-- If a window had too few trips and was filtered out, the "previous row" can
-- be 20+ minutes earlier. The pandas version joins on exact timestamps
-- instead. Being able to explain this difference is a good interview answer.

WITH trips AS (
    SELECT
        PULocationID                                                         AS zone,
        time_bucket(INTERVAL '10 minutes', request_datetime)                 AS window_start,
        date_diff('second', request_datetime, on_scene_datetime) / 60.0      AS eta_min
    FROM read_parquet('data/raw/fhvhv_tripdata_2024-01.parquet')
    WHERE hvfhs_license_num = 'HV0003'          -- Uber: the company that reports on_scene_datetime
      AND on_scene_datetime IS NOT NULL
),
valid AS (
    SELECT * FROM trips WHERE eta_min BETWEEN 0 AND 30
),
windows AS (
    SELECT
        zone,
        window_start,
        COUNT(*)                         AS trips,
        AVG((eta_min > 8)::INT)          AS stress        -- proxy for "unfulfilled rate"
    FROM valid
    GROUP BY zone, window_start
    HAVING COUNT(*) >= 5                                   -- small-sample guard
),
flagged AS (
    SELECT
        *,
        (stress > 0.20)                                                       AS is_trigger,
        LAG((stress > 0.20)::INT) OVER (PARTITION BY zone ORDER BY window_start) AS prev_is_trigger,
        AVG(stress) OVER (PARTITION BY zone ORDER BY window_start
                          ROWS BETWEEN 5 PRECEDING AND CURRENT ROW)           AS rolling_stress_1h
    FROM windows
)
SELECT
    zone,
    COUNT(*)                                          AS windows,
    SUM(is_trigger::INT)                              AS triggers,
    ROUND(AVG(is_trigger::INT), 4)                    AS trigger_rate,
    SUM((is_trigger AND COALESCE(prev_is_trigger, 0) = 1)::INT) AS back_to_back_triggers
FROM flagged
GROUP BY zone
HAVING COUNT(*) >= 200
ORDER BY trigger_rate DESC
LIMIT 20;
