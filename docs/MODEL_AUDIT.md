# Model decisions and audit closure

This is working project documentation. Model settings and all 336 selected forecasts were preserved; no tuning used final September outcomes during this audit.

## Station Ridge selection: reason and evidence

The linear teammate supplied the selection explanation through the project coordinator: the best five-year candidate's small MAE advantage was treated as a practical tie, and the ten-year reference was preferred for lower warm bias, reference stability, and avoidance of choosing a lucky minimum among 48 settings. The teammate reports this was locked before 2024–2025 confirmation and that the five-year alternative was not subsequently scored on confirmation to choose again.

The saved development tuning table verifies:

| Configuration | MAE, °F | RMSE, °F | Signed bias, °F |
|---|---:|---:|---:|
| Lowest-MAE candidate: temperature/pressure, five years, alpha=1, Aug–Oct | 4.6636 | 5.8076 | +0.6634 |
| Locked candidate: all selected weather groups, ten years, alpha=10000, Aug–Oct | 4.7004 | 5.7860 | −0.0247 |

The MAE difference is 0.0369°F. The lowest candidate is not the selected candidate, and the selection is not described as strict MAE minimization. Twenty leading settings span about 0.0538°F in MAE. A ten-year hourly/date reference generally has approximately twice the contributing observations of a five-year one; missing data and partial years affect exact counts.

The quoted standard error around 0.10°F is the best five-year candidate's comparison with the earlier reference configuration, not a directly computed standard error of five-year versus the locked ten-year candidate. Origins overlap and there are only three development years. Do not use “less than two standard errors” as a formal proof of equivalence or a significance test. The rationale is a stability/bias tradeoff supported by observed results. Across all 48 settings the five-year biases range about +0.315 to +0.871°F, so “every five-year candidate is +0.6 to +0.9°F” would be too narrow. Five-year development climatology bias is +0.946°F.

Decision chronology beyond the repository is reported by the team; it cannot be independently established from all local experiment histories. No settings were changed to manufacture a lower final error.

## Historical reference inside Ridge training

At each real historical test origin, only earlier observations enter the outer training history. Ridge fits its hourly/day-of-year normal table and preprocessing from that entire training history. It then constructs simulated starts inside the history and fits departures from that fixed reference. Recent weather summaries are shifted so their measured weather stops before each simulated start.

The normal table itself includes observations later than an internal simulated start, while still earlier than the actual outer test origin. Thus it is full-training preprocessing, not a separate historically available normal for every internal practice start. Do not claim every component of each internal training example was available at that internal time. This differs from boosting, which builds pre-start references for its simulated training forecasts.

The outer testing and final outcomes are excluded. Their prediction errors remain genuine out-of-outer-training results. The difference in internal reference construction is retained and disclosed, not silently “fixed” after final outcomes became known. Scaling and Ridge fitting also occur within the outer training history.

## GFS timing and availability

GFS-corrected Ridge uses clock-hour GFS temperatures as predictors of the airport's routine-report temperature, typically measured 51 minutes into the labeled hour. A predictor need not be an observation of the target at the same instant. The regression is explicitly calibrated against that report target. The raw-GFS baseline retains the clock-hour/report-time mismatch, so its improvement comparison includes correction of timing effects as well as station/grid and lead-dependent bias. Do not describe raw GFS as an exact :51 forecast.

The original EDA GFS diagnostic interpolates the same frozen run to actual report timestamps. It is a different diagnostic from the fitted model's clock-hour-feature evaluation. Its pooled MAE of 5.69°F is not directly interchangeable with the fitted model's final MAE of 5.393°F.

The final run is initialized September 16, 2026 at 18:00 UTC. The recorded NOAA publication headers show sampled native GFS objects, including long leads, present before the September 17 04:00 UTC cutoff. The code verifies initialization before the forecast start. Every historical publication time and original Open-Meteo serving time was not individually verified; do not claim full verified point-in-time serving history.

GFS regression uses a rolling training set of earlier runs whose complete 336-hour windows ended before the current forecast origin, with at least six runs. Completed earlier August outcomes may enter later August training. This is legitimate rolling updating of known past data, but is not a permanently untouched August calibration set. Model settings remain fixed. The original EDA excludes July 30; the later rolling model can use it only after its entire label window is in the past.

## Historical comparisons and EDA scope

Station development uses seven weekly late-summer/autumn starts per year in 2021–2023; confirmation repeats them in 2024–2025. Station Ridge uses ten years and boosting five. Scores average forecast-level errors; averaged RMSE is not pooled RMSE. Weekly windows overlap, so hourly rows and origins are not independent evidence.

The first implemented development origin is August 27, 2021; the original EDA ends September 17, 2021. Some early development windows were inside EDA. This disclosure replaces the incorrect claim that the entire development cohort was untouched. The 2024–2025 confirmation period is outside that original EDA.

The exact September 17 confirmation starts yield average MAE 5.262°F for station Ridge, 5.946°F for boosting, and 5.055°F for ten-year climatology. The linear/nonlinear comparison should disclose that neither beats this baseline on those two exact windows. Broader seasonal confirmation favors station Ridge, 5.058°F versus 5.470°F. The GFS evidence uses different 2026 dates; its scores cannot be ranked against 2024–2025 scores as matched tests.

The primary forecast was marked as GFS-corrected Ridge in commit 3f3dc0b, preceding the final-validation commit 678f704. Final results do not reopen that selection. The August three-way comparison was not completed before final evaluation; do not fabricate it or claim it justified the selection.

## Final input provenance and reproducibility

The teammate's original actual-observation input was not committed. A new IEM retrieval is now preserved with its raw METAR records, exact URL/parameters, UTC retrieval time, units, byte count and SHA-256. All 336 selected actual temperatures and original timestamps match the previously committed final evaluation. This proves reproduction from the preserved retrieval, not possession of the teammate's original download bytes.

The observations live under reports/final, outside the immutable pre-origin snapshots. The training loader continues to reject final outcomes. The scorer has no model-fitting dependency, verifies forecast/snapshot hashes, checks every target timestamp and finite prediction, and scores all candidates and baselines on the same 336 observations. Missing targets are not invented or imputed.

The final prediction CSV exactly reproduced from a fresh remote clone and freshly installed pinned dependencies. Original model scores also reproduced. The audit adds baseline, per-day and day/night tables; “day” here means local hours 06–17, not calculated daylight. No calibrated prediction intervals are claimed.

The archived actuals can be revised and have not had the NOAA cross-check used for 2011–2025. One fortnight is not broad evidence of superiority in other weather periods. These limits remain explicit after closure of the code/reproducibility findings.
