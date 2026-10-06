# Final forecast validation

The three submitted model forecasts were evaluated against all 336 routine RDU
airport reports from September 17, 2026 at 00:00 EDT through September 30 at
23:00 EDT. Reports were retrieved after the forecast period from the Iowa
Environmental Mesonet NC ASOS archive. The same project convention was used: a
routine report near minute 51 is assigned to its clock-hour label.

These observations are post-period outcomes. They are stored only in the final
validation output and were never available to model fitting or forecast
generation.

## Overall results

| Model | MAE (°F) | RMSE (°F) | Bias (°F) |
|---|---:|---:|---:|
| GFS-corrected Ridge | **5.393** | **7.200** | +2.284 |
| Station Ridge | 5.578 | 7.257 | +1.857 |
| Gradient Boosting | 6.369 | 7.761 | **+0.146** |

GFS-corrected Ridge has the lowest final-period MAE and RMSE. Gradient Boosting
has the smallest overall signed bias, but this masks large cold errors early and
warm errors later.

## Performance by forecast horizon

| Model | Days 1–3 | Days 4–7 | Days 8–14 |
|---|---:|---:|---:|
| GFS-corrected Ridge | **2.818** | **5.976** | 6.163 |
| Station Ridge | 3.856 | 5.991 | 6.080 |
| Gradient Boosting | 7.142 | 6.544 | **5.938** |

GFS guidance is most valuable during days 1–3. Station Ridge is slightly better
than GFS-corrected Ridge during days 8–14, while Gradient Boosting has the lowest
late-horizon MAE but performs poorly during the first week.

## Limitations

- This is one fourteen-day weather episode, not a replacement for the historical
  development and confirmation experiments.
- The actuals come from the current IEM archive and have not received the same
  independent NOAA cross-check used for 2011–2025 training observations.
- Archive values can receive retrospective corrections.
- Model selection must not be revised using these final outcomes and then
  presented as if the resulting model had been evaluated independently.
