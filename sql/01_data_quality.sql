-- 01 DATA QUALITY AUDIT  (DuckDB)
-- Run from the repo root:  python -m liquidity.sql_runner sql/01_data_quality.sql
-- Pandas twin: liquidity/quality.py :: audit()
--
-- Question answered: for each company, how many trips can we actually use for
-- wait-time analysis?  (Lyft is expected to have a very high null rate.)

SELECT
    CASE hvfhs_license_num
        WHEN 'HV0003' THEN 'Uber'
        WHEN 'HV0005' THEN 'Lyft'
        WHEN 'HV0002' THEN 'Juno'
        WHEN 'HV0004' THEN 'Via'
        ELSE 'Other'
    END                                                        AS company,
    COUNT(*)                                                   AS trips,
    ROUND(100 * AVG((on_scene_datetime IS NULL)::INT), 2)      AS null_on_scene_pct,
    ROUND(100 * AVG((date_diff('second', request_datetime, on_scene_datetime) / 60.0
                     BETWEEN 0 AND 30)::INT), 2)               AS usable_eta_pct,
    ROUND(100 * AVG(((base_passenger_fare - driver_pay) < 0)::INT), 2) AS negative_margin_pct
FROM read_parquet('data/raw/fhvhv_tripdata_2024-01.parquet')
GROUP BY 1
ORDER BY trips DESC;
