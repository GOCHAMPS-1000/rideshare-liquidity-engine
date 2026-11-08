-- 02 WAIT-TIME PERCENTILES BY HOUR  (DuckDB)
-- Pandas twin: liquidity/metrics.py :: eta_summary(df, "hour")
--
-- Concepts: CTE (WITH), derived column, quantile_cont (continuous percentile),
-- boolean-to-int trick for "share of rows that satisfy a condition".

WITH trips AS (
    SELECT
        hour(request_datetime)                                              AS hr,
        date_diff('second', request_datetime, on_scene_datetime) / 60.0     AS eta_min
    FROM read_parquet('data/raw/fhvhv_tripdata_2024-01.parquet')
    WHERE on_scene_datetime IS NOT NULL
),
valid AS (
    SELECT * FROM trips WHERE eta_min BETWEEN 0 AND 30
)
SELECT
    hr,
    COUNT(*)                                   AS trips,
    ROUND(AVG(eta_min), 2)                     AS mean_eta,
    ROUND(quantile_cont(eta_min, 0.50), 2)     AS p50,
    ROUND(quantile_cont(eta_min, 0.90), 2)     AS p90,
    ROUND(AVG((eta_min > 8)::INT), 4)          AS long_wait_share
FROM valid
GROUP BY hr
ORDER BY hr;
