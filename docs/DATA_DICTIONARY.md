# Data dictionary

Blank numeric values are missing, not zeros. Dates retain timezone offsets. Temperature observations, published normals and model forecasts are different data types and remain separate. No feature or target imputation has been performed.

## rdu_primary_candidate_2016_to_cutoff.csv

| Column | Plain-English definition |
|---|---|
| hour_label_utc | Unique hour-grid key in UTC; provisional floor of the routine report time, not proof the reading was taken at the clock hour. |
| observation_time_utc | Actual source timestamp of the selected routine airport report; empty when no report exists. |
| station | RDU; this identifies the target airport. |
| temperature_f | Original IEM parsed air temperature in degrees Fahrenheit, unchanged even if flagged. |
| dew_point_f | Historical dew-point temperature, Fahrenheit. Same-hour dew point is not an available future feature at a fixed forecast origin. |
| relative_humidity_pct | Historical relative humidity, percent; typically related to temperature and dew point. |
| wind_direction_deg | Historical direction in degrees from true north; missing/variable direction is not assumed north. |
| wind_speed_knots | Historical wind speed, knots. |
| sea_level_pressure_hpa | Historical mean sea-level pressure, hPa (equivalent to millibars). |
| precipitation_1h_inches | Reported routine precipitation amount, inches; retain original reporting interval and reset convention. |
| precipitation_trace | True when raw precipitation code is T (trace); numeric precipitation remains empty rather than an invented zero. |
| variable_wind | True when original METAR encodes VRB wind; false in missing-report slots does not establish known wind. |
| skyc1 | First reported cloud layer category: CLR, FEW, SCT, BKN, OVC etc.; preserve source category. |
| skyc2 | Second reported cloud layer, if present. Empty does not by itself imply instrument failure. |
| skyc3 | Third reported cloud layer, if present. Empty does not by itself imply instrument failure. |
| metar | Original airport report text; provenance and quality review only. Do not feed an unfiltered report containing target temperature into same-hour prediction. |
| metar_temperature_c | Higher-precision temperature decoded from METAR T remark, when present; alternate target precision, not a same-hour predictive feature. |
| metar_temperature_f | METAR T-remark temperature converted to Fahrenheit. |
| source_file | Raw file containing the report/run. |
| source_row | CSV line number including header; locates the exact raw record. |
| minutes_after_hour | Actual minute within the provisionally labelled hour, generally 51. |
| hour_label_local | Same hour key in Raleigh civil time with UTC offset; September uses EDT. |
| observation_time_local | Actual report timestamp in Raleigh civil time, including daylight-saving offset. |
| report_present | True if an actual report was selected for this grid hour. |
| temperature_missing | True if the original IEM target temperature is missing, including hours with no report. |
| year | Year of the Raleigh local hour; selection metadata. |
| month | Month of the Raleigh local hour; selection metadata. |
| primary_season | True for local August, September or October. |
| candidate_final_training | True for the initial 2016-onward seasonal final-fit candidate; still subject to each historical fold cutoff. |
| archive_role | Older backtest support or recent history; not a model feature. |
| temperature_c | Unit conversion of original IEM air temperature to Celsius; conversion does not add precision. |
| dew_point_c | Celsius conversion of historical dew point. |
| wind_speed_ms | Historical wind speed converted to metres per second. |
| precipitation_1h_mm | Reported precipitation converted to millimetres. |
| temperature_archive_review_flag | True for a source-quality failure or disagreement beyond precision rules. Temporary review state, not a forecast predictor. |
| temperature_usable_f | Original IEM temperature in Fahrenheit with unresolved NOAA disagreements/quality failures temporarily set empty. No imputation. |
| temperature_usable_c | Celsius conversion of the provisionally usable temperature. |
| noaa_temperature_quality_code | NOAA code at the exact report time. Interpret jointly with its source in the comparison report, never as a universal numeric scale or model feature. |
| noaa_temperature_crosscheck_present | True if exact-time NOAA temperature was available; false is not a failed temperature measurement. |

## target_336_hour_index_and_normals.csv

| Column | Plain-English definition |
|---|---|
| hour_label_utc | Unique hour-grid key in UTC; provisional floor of the routine report time, not proof the reading was taken at the clock hour. |
| hour_label_local | Same hour key in Raleigh civil time with UTC offset; September uses EDT. |
| forecast_slot | Output index 1 through 336, in chronological order. |
| hours_from_cutoff | Clock-hour displacement 0 through 335 from final origin. First requested slot is at the origin itself. |
| forecast_day | Calendar forecast day 1 through 14. |
| normal_lookup_local_standard_time | Month/day/hour key after UTC to fixed UTC−5 conversion. Distinct from Raleigh EDT; may refer to previous date. |
| normal_temperature_f | Published 1991–2020 normal air temperature, Fahrenheit; benchmark lookup, not an observed 2026 temperature. |

## noaa_hourly_temperature_normals_local_standard_time.csv

| Column | Plain-English definition |
|---|---|
| month | Month of the Raleigh local hour; selection metadata. |
| day | Day of month in the normals time convention. |
| hour | Hour of day in the normals time convention: local standard time. |
| normal_temperature_f | Published 1991–2020 normal air temperature, Fahrenheit; benchmark lookup, not an observed 2026 temperature. |
| comp_flag_HLY-TEMP-NORMAL | NOAA normal completeness flag, retained unchanged. |
| years_HLY-TEMP-NORMAL | Reported years contributing to the normal; not additional model training rows. |

## gfs_20260916_18Z_target_forecast_inputs.csv

| Column | Plain-English definition |
|---|---|
| temperature_2m | GFS predicted near-surface air temperature in Fahrenheit. A future forecast, not actual airport temperature. |
| dew_point_2m | GFS predicted dew point in Fahrenheit; provider-derived from model temperature/humidity. |
| relative_humidity_2m | GFS predicted relative humidity, percent. |
| cloud_cover | GFS predicted total cloud-cover fraction, percent; not the station cloud-layer category. |
| pressure_msl | GFS predicted sea-level pressure, hPa. |
| precipitation | GFS predicted preceding-hour precipitation, mm; distinct from measured station precipitation. |
| wind_speed_10m | GFS predicted ten-metre wind speed, metres per second; converted/derived by provider. |
| wind_direction_10m | GFS predicted wind direction, degrees. |
| valid_time_utc | Clock time to which an archived GFS predicted value applies; UTC. |
| model_initialization_utc | GFS run initialization time. It precedes computation/publication and is not its public release time. |
| forecast_origin_utc | Simulated decision time for that prepared 336-hour forecast; ten hours after the 18 UTC run. |
| lead_hours_from_model_initialization | Elapsed hours from GFS initialization; final run covers leads 10 through 345. |
| hours_from_forecast_origin | Elapsed hours 0 through 335 from simulated forecast decision time. |
| valid_time_local | GFS validity time in Raleigh civil time. |
| role | Historical calibration candidate or final forecast input; do not combine final target inputs with historical labels. |
| source_file | Raw file containing the report/run. |
| grid_latitude | Latitude returned for the forecast grid selection; not station coordinates. |
| grid_longitude | Longitude returned for the forecast grid selection; not station coordinates. |
| api_elevation_m | Elevation returned by Open-Meteo; documented provider adjustment context. |
| native_temporal_resolution_hours | One hour through model lead 120; three hours afterwards. |
| api_hourly_interpolation_after_120h | True where hourly outputs derive from native three-hour model output. |

The all-month, full seasonal and initial EDA-training files use the same observation schema. Historical GFS files use the same forecast schema. The validation plan records test year, role, exact origin/end boundaries, five- or ten-year history, month selection and usable training/test counts; these are split instructions, not performance scores. Raw IEM files preserve M for missing values and T for trace rainfall. NOAA PSV files preserve their original source/measurement/quality/report codes, defined in the saved NOAA documentation. Audit comparison files retain both temperatures, differences, rounding consistency and review flags.

## Final evaluation-only files

reports/final/iem_rdu_final_actuals.csv contains station=RDU, valid (original UTC report time), tmpf (archive Fahrenheit target), and raw metar text. Its request, retrieval time and checksum are in final_observation_manifest.json. This file is never part of data/pre_eda or model fitting.

The final forecast columns contain Fahrenheit temperatures. submitted_forecast_f equals gfs_ridge_f and is the preselected answer. lead_hours is an ordinal (1–336), not elapsed time from the first label. final_forecast_with_actuals.csv adds observed_at_utc, minutes_after_hour, actual_f and prediction-minus-actual errors. All candidates/baselines share the 336 observed reports. Per-day and day/night score tables include MAE, RMSE, signed bias and n; day/night is local 06–17 versus other hours.
