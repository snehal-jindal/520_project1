# Data preparation checks, before EDA

The forecasting task has 336 hour labels, September 17, 2026, 00:00 through September 30, 23:00, America/New_York. The exclusive observation cutoff is 2026-09-17 04:00 UTC. No actual temperature from that final test period was collected.

| Check | Result |
|---|---:|
| Raw IEM routine reports | 137,529 |
| All-month archive expected hourly slots | 137,711 |
| All-month slots with a report | 137,514 |
| All-month missing temperature slots | 204 |
| All-month temperatures quarantined for source review | 202 |
| Seasonal 2011-onward expected slots | 34,248 |
| Seasonal missing temperatures | 38 |
| Seasonal temperatures quarantined for source review | 3 |
| Primary 2016-onward expected seasonal slots | 23,208 |
| Primary missing temperatures | 18 |
| Primary temperatures quarantined for source review | 3 |
| Primary temperature values available after provisional screening | 23,187 |
| Exact duplicate raw rows | 0 |
| Duplicate raw observation timestamps | 2 |
| Hours with multiple routine reports | 15 |
| Selected reports outside usual minute 51 | 30 |
| Broad physical-consistency flags | 0 |
| Exact-time NOAA temperature matches | 131,210 |
| Downloaded explicit GFS runs | 23 |
| GFS historical forecast rows in prepared 14-day windows | 7,392 |
| GFS final-window forecast input rows | 336 |

The primary candidate currently retains 99.910% of its expected hours as usable temperatures. This measures completeness under our rules, not forecasting accuracy and not proof of instrument accuracy.

The earliest IEM report is 2011-01-01 05:51:00+00:00; the last is 2026-09-17 03:51:00+00:00, nine minutes before the cutoff. Report timestamps are preserved separately from hour labels. They do not establish the exact delivery time or the absence of later archive corrections.

The three seasonal disagreements are at 2024-08-01 12:51 UTC and 2024-09-19 05:51/06:51 UTC. Both archives identify routine RDU observations, but reported temperature differs beyond the precision allowance. These are source conflicts, not evidence that unusual weather should be deleted. Original IEM temperatures, METAR precision temperatures and NOAA alternatives are preserved in the comparison report. Their final label resolution and sensitivity should be recorded before model scoring. A provisional usable column excludes them; the raw label remains available. Some other small differences are consistent with whole-Celsius rounding when the METAR precision remark is absent and are not quarantined just for that reason.

NOAA comparison data cover 2011–2025 UTC dates. The 2026 observations have no independent NOAA comparison here, and some historical report times lack a match. The crosscheck flag distinguishes those cases. Passing broad range checks alone is weaker evidence than an exact archive match. NOAA quality flags are source-specific and retrospective; no model is allowed to use them as predictors.

Yearly coverage, field completeness, all missing slots, selected off-schedule observations and report alternatives are provided as separate CSV audit files. Missing additional cloud layers and variable wind have different meanings from missing temperature; the data dictionary explains them. No targets were imputed and no fitted preprocessing was performed.

Historical test target availability after provisional screening is 336/336 for 2021–2023, 334/336 for 2024 (two source conflicts) and 334/336 for 2025 (two missing observations). These counts must be reported when scores are eventually calculated, and all compared models must use the same final eligible target mask. Any later resolution of source conflicts must update the mask consistently.

For the final GFS run, NOAA index headers checked at model leads 0, 120, 240, 345 and 384 all have last-modified times before the final cutoff. Historical GFS run publication was inferred conservatively using a ten-hour buffer, not individually proven from release logs. Open-Meteo's exact historical delivery times are not recorded. Hourly values after lead 120 hours are interpolated from coarser native output.

These checks stop at data integrity and coverage. They do not establish which training window or model predicts best. No EDA or model scores were generated.
