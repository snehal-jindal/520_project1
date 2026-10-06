# Final forecast validation

The fixed forecasts are evaluated against all 336 routine RDU airport reports from September 17, 2026 00:00 through September 30 23:00 Raleigh time. The target is the routine report, usually at :51, assigned to its clock-hour label in Fahrenheit. The forecasts were simulated using only pre-cutoff inputs; this is not a claim they were issued in real time on September 17.

GFS-corrected Ridge was marked as the submitted forecast in commit 3f3dc0b before the final-validation commit. No models were retuned from these final outcomes. The immutable forecast file hash is recorded in [FORECAST_RECORD](../../docs/FORECAST_RECORD.json).

## Overall results

| Model | Scored hours | MAE (°F) | RMSE (°F) | Bias (°F) |
|---|---:|---:|---:|---:|
| GFS-corrected Ridge | 336 | 5.393 | 7.200 | +2.284 |
| Station Ridge | 336 | 5.578 | 7.257 | +1.857 |
| Gradient Boosting | 336 | 6.369 | 7.761 | +0.146 |
| Climatology | 336 | 6.288 | 7.682 | +0.182 |
| Raw GFS | 336 | 6.366 | 7.824 | -0.313 |

GFS-corrected Ridge has the lowest overall final MAE and RMSE among these candidates and baselines. Gradient boosting has the lowest signed bias, but warm and cold errors cancel; that does not imply the lowest absolute error. The selected forecast remains GFS-corrected Ridge.

## Performance by forecast horizon

| Model | Days 1–3 MAE | Days 4–7 MAE | Days 8–14 MAE |
|---|---:|---:|---:|
| GFS-corrected Ridge | 2.818 | 5.976 | 6.162 |
| Station Ridge | 3.856 | 5.991 | 6.080 |
| Gradient Boosting | 7.142 | 6.544 | 5.938 |
| Climatology | 7.103 | 6.739 | 5.682 |
| Raw GFS | 3.061 | 6.115 | 7.926 |

GFS-corrected Ridge performs best on days 1–3. Gradient boosting has lower MAE on days 8–14 but higher overall error. This pattern is descriptive; it was not used to create a new hybrid after final answers were known.

## Reproduce offline

Run `python scripts/validate_final_forecast.py` after installing dependencies. It defaults to the committed [IEM input](iem_rdu_final_actuals.csv), verifies its [download manifest](final_observation_manifest.json), verifies the frozen forecasts, and recreates the joined table, score tables and plot. No live request or external input file is needed. `--actuals` remains available for an explicit alternative source file.

The preserved input includes raw routine METAR text. It is a new retrieval whose 336 target values and observation timestamps matched the previously committed final evaluation, not the teammate's unretained original download. The manifest records the exact URL/parameters, retrieval time, units and SHA-256. `python scripts/download_final_actuals.py` verifies it offline; `--refresh` explicitly re-downloads the mutable archive.

[Per-hour predictions/actuals/errors](final_forecast_with_actuals.csv), [all metric rows](final_validation_scores.csv), [per-day metrics](final_validation_by_day.csv) and [day/night metrics](final_validation_day_night.csv) accompany the report. Day/night means local hours 06–17 versus the other hours, not astronomical daylight.

![Observed and predicted RDU temperatures](final_validation_plot.png)

## Limitations and separation from training

These observations are post-period outcomes stored only under reports/final. The model loader reads only the pre-origin snapshot and rejects measurements at or after the cutoff. The final scorer imports no model-fitting code. Missing targets are not filled; this saved episode has 336 usable reports.

This is one fourteen-day weather episode, not a replacement for historical development/confirmation. Weekly historical windows overlap. The actuals are a revised IEM archive snapshot and have not received the same NOAA archive cross-check used for 2011–2025. Clock-hour GFS temperatures are predictors of the report target; the raw-GFS benchmark retains that timing difference. Historical serving-time limitations and Ridge reference/selection decisions are disclosed in [MODEL_AUDIT](../../docs/MODEL_AUDIT.md).

The graded presentation and writeup must remain student-authored. This report is working project evidence.
