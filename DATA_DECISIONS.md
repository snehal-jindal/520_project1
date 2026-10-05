# RDU temperature project: data decisions before EDA

This is a working record of data preparation, not the graded project writeup. No exploratory plots, correlations, forecasting models or performance scores have been produced. The choices below are reasoned starting choices; historical forecasting tests must establish which choices work best.

## 1. What we must predict

The deck asks for hourly temperature measured at RDU airport, September 17 at 12 a.m. through September 30 at 11 p.m. You confirmed 2026 and Raleigh civil time.

| Item | Exact interpretation |
|---|---|
| Location | RDU / KRDU, Raleigh–Durham International Airport; NOAA USW00013722, WBAN 13722 |
| Forecast origin and information cutoff | September 17, 2026, 00:00 America/New_York |
| UTC cutoff | September 17, 2026, 04:00 UTC; observations must be strictly earlier |
| First requested hour | September 17, 2026, 00:00 EDT / 04:00 UTC |
| Last requested hour | September 30, 2026, 23:00 EDT / October 1, 03:00 UTC |
| Number of outputs | 14 days × 24 hours = 336 |
| Operating scenario | One fixed forecast at the cutoff; do not update it using later actual weather |

Raleigh observes **EDT, UTC−4, in September**, despite the earlier use of the word EST. A fixed EST assumption would shift the task by one hour. UTC timestamps are the storage and joining keys; local timestamps with their UTC offsets are retained for interpretation. This also keeps the two repeated fall clock hours distinct and avoids inventing a spring clock hour.

One grading detail is still unspecified: the deck does not define “hourly temperature” as a precise clock-hour reading, an hourly average, or a routine airport report. RDU routine reports are overwhelmingly at minute 51. Our **provisional** preparation labels a report at 00:51 as belonging to the 00:00 hour, while retaining 00:51 as its actual measurement time. This is a report in that hour, not a measurement taken at 00:00. The final label convention must match the instructor's evaluation data before models are scored. Exact times and raw METAR reports remain available to change that mapping without downloading again. Clock-hour GFS forecasts and normals also need alignment to the eventual target convention; they are not yet silently treated as exact `:51` readings.

The final 2026 test observations have **not** been downloaded. Forecast values describing future dates are allowed only when they come from a run issued before the cutoff; they are predictions, not later measured weather. Although the calendar has now passed the test period, we preserve the project's original information boundary.

## 2. Which sources we selected, and why

The relevant public source families were compared on location match, hourly detail, quality information, historical coverage, cutoff availability, forecast horizon and access effort. These criteria matter more than collecting every possible weather dataset.

| Source | Decision and actual collection | Why, and what we give up |
|---|---|---|
| [Iowa Environmental Mesonet airport METAR/ASOS archive](https://mesonet.agron.iastate.edu/request/download.phtml?network=NC_ASOS) | Primary observation archive: RDU routine reports, January 1, 2011 to the cutoff, all months | Direct airport measurements; exact timestamps and original report text; straightforward, reproducible access. IEM provides limited quality control, so an independent archive check is necessary. |
| [NOAA GHCN hourly](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly) | Quality comparison and backup: USW00013722, 2011–2025 | Official harmonized observations with source-specific quality codes. Match exact observation times, station and temperature units. Its report mixture is not automatically the same hourly target definition. It shares underlying airport observations with IEM: agreement is an archive consistency check, not independent physical measurement. No whole-year 2026 file was collected, to avoid bringing final test observations into the workspace. |
| [NOAA hourly climate normals](https://www.ncei.noaa.gov/pub/data/cdo/documentation/normals-hourly-1991-2020_documentation.pdf) | RDU 1991–2020 hourly normals | A published “usual temperature for this date and hour” benchmark. It supplies no new storm information and can underrepresent recent warming. It is not 30 additional training years. Normals are in local **standard** time; September EDT midnight corresponds to 23:00 EST the previous date. Use only for validation years after 2020. |
| [NOAA HOMR station history](https://www.ncei.noaa.gov/access/homr/api) and [IEM station metadata](https://mesonet.agron.iastate.edu/sites/site.php?network=NC_ASOS&station=RDU) | Downloaded station history and identifiers | Lets us distinguish equipment/site history from climate change and confirms that both archives refer to RDU. Metadata are documentation, not predictive target-weather measurements. |
| [NOAA GFS, through Open-Meteo Single Runs](https://open-meteo.com/en/docs/single-runs-api) | Separate forecast input: September 16, 2026, 18 UTC run; plus 22 weekly historical 18 UTC runs April 2–August 27, 2026 | GFS covers the whole 14-day target period and contains information about expected weather systems that old temperature observations cannot reveal. Explicit runs preserve the forecast information boundary. This access route has only a short GFS run history, grid forecasts are not airport measurements, and later hours are interpolated. Keep separate from the long station-only comparison. |

The GFS query requests the RDU coordinates. Its returned grid location is nearby, not identical to the station; returned coordinates and elevation are preserved per run. Open-Meteo also performs interpolation/downscaling. After model lead 120 hours, hourly GFS values are interpolated from native three-hour output, as its [GFS documentation](https://open-meteo.com/en/docs/gfs-api) explains. An hourly file therefore does not imply 336 independently computed hourly forecasts.

For the final GFS run, the first target clock hour is model lead 10 hours and the last is lead 345 hours, within the [384-hour GFS horizon](https://www.nco.ncep.noaa.gov/pmb/products/gfs/). NOAA S3 index-file timestamps were checked at leads 0, 120, 240, 345 and 384: all were last modified on September 16 between 21:36 and 23:17 UTC, before the 04:00 UTC cutoff. Those headers are saved. This supports original NOAA run availability; it does not establish the exact time Open-Meteo served its processed version. We deliberately avoid the September 17 00 UTC run: initialization alone does not prove its complete output was public before 04 UTC. The provider documents typical global-run publication delays of four to six hours. Historical 2026 runs have the same conservative ten-hour buffer but have not individually had original publication logs verified; treat that limitation explicitly in later backtesting.

## 3. Why other sources are not in the starting dataset

| Candidate | Reason for not selecting it now |
|---|---|
| [NOAA LCD version 2](https://www.ncei.noaa.gov/products/land-based-station/local-climatological-data) | Useful official presentation of station observations, but its hourly data derive from GHCNh. Downloading both adds little independent information. GHCNh retains the quality/source detail needed for our audit. |
| Legacy NOAA ISD / LCD version 1 | Superseded sources complicate coverage of 2026. NOAA reports that LCDv1 stopped updating in August 2025. Use the current GHCNh source rather than splice retired and current products. |
| [Meteostat point data](https://dev.meteostat.net/api/point) | Convenient for estimating weather at coordinates, but may use nearby stations and spatial adjustments. Our target is a particular airport's measured temperature, so direct station reports are easier to defend and trace. This does not mean all Meteostat station data are unusable. |
| [ERA5 / ERA5-Land historical weather](https://open-meteo.com/en/docs/historical-weather-api) | Reanalysis combines observations with a model on a grid; it is not RDU measurement truth. It can be useful later for regional context, but duplicates much of the initial local information and has publication delays. Future-period reanalysis would leak actual future weather into this task. |
| [NASA POWER hourly data](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/) | A gridded product providing hourly averages; less closely matched to an airport report than the available station archive. No initial need to add it when the location and target resolution are already served directly. |
| NOAA daily climate observations | Daily maxima/minima and totals do not supply 24 hourly temperatures. Useful for other tasks, not a replacement for this target. |
| Nearby airports | Potential regional context or corroboration for gaps, but their temperature is not RDU's label. Add only if later validation shows value; never substitute a neighbor's value and call it an RDU observation. |
| HRRR, NAM, NBM and extended-range MOS | Useful shorter-range products, but the documented forecast horizons do not cover the entire two-week task from one cutoff. Adding short-horizon branches increases pipeline complexity. GFS is the coherent full-horizon starting choice. |
| ECMWF HRES 9 km | The Single Runs provider documents a ten-day horizon for this product, so it cannot alone cover this fourteen-day forecast. Other ECMWF products are not interchangeable; their exact archive and complete horizon would need verification before adding them. |
| Stitched historical forecast APIs or today's live forecast | They can combine later forecast runs, including information issued after our original cutoff. Explicit initialization runs are required for this experiment. |
| ENSO indices, global CO₂, land-use and urbanization products | Worth considering as climate context, but not automatically useful for one airport's 14-day hourly forecast. They add alignment, publication-time and interpretation burdens. We have no validated RDU-specific break date or demonstrated forecast benefit that warrants adding them now. |
| Radar, satellite and high-dimensional regional fields | Potential short-range signal, but much larger processing burden and limited direct support for days 8–14. GFS already assimilates many observing systems; adding their raw fields is not the starting priority. |

These are scope decisions, not claims that excluded sources contain no information. Revisit a source only with a concrete feature hypothesis and a historical forecast test.

## 4. Exactly how much history, and which months

**Raw observation coverage:** every month from January 1, 2011 through September 16, 2026, ending strictly before September 17 midnight Raleigh time. This preserves a continuous record for quality checks, valid lag construction and an all-months comparison. It has 137,711 expected hourly slots. Only one airport is extracted; we are not collecting the entire state or country.

**Primary seasonal preparation:** August 1–October 31 in each year 2011–2025, plus August 1–September 16 in 2026. That is 34,248 expected hourly slots. Historical October is allowed because it was already known before the 2026 origin; current-year September 17 onward and October are excluded as observations.

**Initial final-training candidate:** the same seasonal window from 2016 onward: ten complete historical seasons, 2016–2025, plus the observed portion of 2026. This is 23,208 expected hours before quality exclusions. It is not just the September 17–30 dates from prior years.

Why August–October? September lies between the warmer late-summer and cooler autumn regimes. Adjacent months provide examples of that transition and many more daily cycles without requiring the initial model to learn winter and spring as well. September-only is more focused but supplies fewer weather episodes; all months supply more data but require a better model of the annual cycle. Both alternatives remain available in the raw archive. More hourly rows are not the same as more independent climate years: ten seasons remain only ten separate Septembers.

Why roughly ten years? Five years adapt more closely to recent climate but give fewer unusual Septembers and storm examples. Ten years provide more weather variation while avoiding the much longer, less representative historic record. Fifteen or more years can stabilize averages but risk placing too much weight on older climate and instrument/reporting regimes. **Neither 2011 nor 2016 is claimed to be a physical climate breakpoint.** The ten-year seasonal choice is a starting hypothesis, not a proven optimum.

Why extract 2011 if the 2026 training candidate starts in 2016? To simulate a ten-year training window at earlier forecasting dates. The 2021 historical test needs 2011–2020 history; otherwise the ten-year and five-year candidates would be compared with inconsistent coverage. The older archive is therefore useful for choosing the final window, even if it is absent from the initial 2026 fit. This dataset does not support a strict fifteen-year window for every 2021–2025 test; do not claim that comparison without acquiring earlier history.

After EDA, compare six observation-history candidates: September-only, August–October and all months, each with five or ten complete prior years plus the current pre-cutoff period. Hold the model and evaluation periods consistent while changing coverage. All-months models must include annual seasonality; seasonal models still need time-of-day and within-season timing. Choose using the historical September forecasts, not training error or whichever dataset has the most rows. If results are close or inconsistent, retain the simpler, relevant seasonal choice and report the uncertainty.

## 5. Environmental and observing-system context

The [NOAA North Carolina climate summary](https://statesummaries.ncics.org/chapter/nc/) documents long-term warming, warmer recent summers and more very warm nights. This supports testing shorter history and time/trend features; it does not prove an abrupt RDU change in 2016, nor justify manually adding an assumed warming amount to temperatures. Nighttime forecast errors deserve their own later check.

Downloaded HOMR records state that RDU ASOS was commissioned **February 1, 1996** and, according to a later correction note, has not moved since commissioning. They document a rain-gauge replacement in 2004, a rain-gauge shield in August 2010, and an obstruction/tower entry effective February 2018. Location/elevation metadata were corrected in 2021–2022. These are useful audit milestones; the corrections must not be interpreted as a new temperature-site move, and an obstruction entry is not proof of a temperature discontinuity. Metadata from different products report somewhat different elevations, so no automatic temperature adjustment has been made from those discrepancies.

Keep real heat waves and storms. For example, [Hurricane Florence in September 2018](https://www.weather.gov/rah/Florence) represents actual weather that the forecast might encounter, not an observation to remove merely because it is unusual. Distinguish a meteorological extreme from a failed measurement. NOAA quality flags that mark a climatological outlier require review rather than an assumption that the event never occurred.

The NOAA data-product transition in August 2025 is an archive milestone, not a warming milestone. Weather-model upgrades are likewise changes to GFS, not changes to the climate. Do not merge forecasts across model versions or providers as though they were one unchanged historical series. The collected GFS runs are a separate 2026 archive; check provider/model updates before any calibration analysis. ENSO phase changes and urban development may provide context, but without publication-safe, local evidence they do not define our training start date.

## 6. What preparation does, and does not, do

1. Download routine RDU reports only. Special reports are issued more often during unusual weather; averaging all reports would give those hours different sampling. Routine reports provide a more consistent target series. Original text, missing codes and units remain in raw files.
2. Use a complete UTC hour grid. Missing observations appear as empty values with flags rather than making two nonconsecutive hours appear consecutive. Filter by local month only after building that continuous grid. Any later lag must be based on elapsed time in the continuous archive, never the previous row in a seasonal table.
3. Resolve multiple routine reports in one hour with a fixed rule: closest to expected minute 51, then target availability, then deterministic timestamp/source order. Preserve all alternatives in the audit. This is a provisional mapping pending the grading definition, not a temperature average or a choice of the most convenient temperature value.
4. Preserve Fahrenheit source values, and also provide Celsius, wind in metres per second and precipitation in millimetres. Converted decimals do not create extra measurement precision. Higher-precision temperature encoded in the original METAR remark is retained separately; it is not used as a predictor of the same hour's target.
5. Check schemas, station identity, timestamps, duplicates, gaps, units and broad physical consistency. These are data-integrity checks, not EDA. No means, correlations, temperature distributions or fitted climate trends have been examined.
6. Compare NOAA and IEM at **exact observation times**, converting NOAA Celsius to Fahrenheit. A tolerance of 0.6°F allows ordinary whole-Fahrenheit rounding relative to tenths-Celsius records. When the higher-precision METAR remark is absent, a difference up to 0.9°F is consistent with whole-Celsius reporting precision and is separately marked rather than quarantined just for rounding. Larger differences and source quality failures are retained for review; agreement cannot prove both archives are correct. Quality codes must be interpreted in relation to source, not as one universal number scale.
7. Retain original temperatures and a separate `temperature_usable_f` column. Suspect/error flags and unresolved source discrepancies are temporarily quarantined in the usable column, not erased from history. Examine those cases during the next data-review/EDA stage; verified real extremes must be restored. The absence of a NOAA match, especially in 2026, is explicitly flagged and is not treated as a successful crosscheck.
8. Do not fill missing targets, interpolate across test periods, clip extreme temperatures or fit any preprocessing yet. A model may later need a train-only missing-predictor rule. Missing/invalid test targets must never be manufactured merely to calculate a score.

Missing second or third cloud layers often mean there is no additional reported layer; that does not automatically mean a broken sensor or clear sky. Missing/variable wind direction is not north, and calm wind needs its own interpretation. Trace rainfall is retained as a separate flag, not silently replaced with a measured zero amount. The weather fields are collected because they may describe the state at the forecast origin; collecting them does not authorize using their actual future values.

Retrospective archives can contain corrections made after original observation times. Our downloads reproduce the current archived history, not a complete real-time snapshot of what every historical forecaster saw. NOAA quality screening is also retrospective. Keep that qualification in later performance reporting; do not use quality flags or other hindsight metadata as model features.

## 7. Evaluation and metrics planned before looking at results

**Station-only experiments:** simulate September 17 midnight forecasts in 2021, 2022 and 2023 for model/window development. Reserve September 17–30 in 2024 and 2025 for confirmation after choices are fixed. Each run predicts all 336 hours without receiving any actual weather from its own forecast period. Historical rows after each origin must be removed from that fold's training, even though they precede the final 2026 cutoff. Test targets are separate from inputs. The prepared validation table records the boundaries and available label counts.

The initial EDA-safe training file ends before the 2021 forecast origin. The full archive and final-fit candidate contain later historical targets and should not be indiscriminately explored while claiming to have untouched confirmation periods. Each later training/EDA operation must respect the appropriate fold boundary.

**GFS-assisted experiments:** the convenient explicit-run archive starts April 2026, so it cannot be fairly evaluated on the same 2021–2025 folds. It has 22 weekly runs, each with a prepared 336-hour window: 7,392 historical forecast rows. These overlap in valid dates, so they are not 7,392 independent weather events. Use runs April 2–July 23 for calibration candidates and August 6–27 for temporal confirmation; exclude the July 30 run from that split because its labels overlap the first confirmation window. Compare GFS alone, a correction model and station baselines on those same available 2026 windows. This short April–September history does not establish multi-year September skill. Do not compare a GFS-assisted score on one set of dates to a station-only score on another and declare a winner.

| Metric | Planned use and plain-English meaning |
|---|---|
| MAE, in °F | Primary selection measure: the average size of an hourly mistake, ignoring whether it is too warm or cold. |
| RMSE, in °F | Secondary measure: gives unusually large hourly mistakes more weight. Useful when missing a heat spike or front matters. |
| Mean signed error, in °F | Diagnosis: positive means forecasts run too warm; negative means too cold. A near-zero bias can still hide large errors. |
| MAPE | Do not use for temperature: percentages depend on the arbitrary Celsius/Fahrenheit zero and behave badly near zero. |
| R² / training fit | At most supplementary; fitting known temperatures well does not establish 14-day forecast skill. |

Report overall and per-year errors, each forecast day's errors, days 1–3 versus 4–7 versus 8–14, and daytime/nighttime errors. Use the same available valid target hours for every model in a comparison, publish the scored count out of 336, and show why any targets are missing or excluded. Revisit unresolved target quality flags consistently before scoring. Do not replace missing targets with fitted values. Forecast-day slices diagnose horizon loss; they are not separate tuning targets to cherry-pick.

For each historical fold, preprocessing, feature selection and any fitted averages must use training history only. Uncertainty is limited by the small number of September years and temporal dependence; do not treat thousands of correlated hours as thousands of independent replications. The principle is [multi-step evaluation from historical forecasting origins](https://otexts.com/fpp3/tscv.html).

The published 1991–2020 normals and a training-only seasonal/hourly average are useful benchmarks. Repeating the most recent observed day is another simple origin-safe reference. None is assumed to be a good two-week forecast; they tell us whether added complexity improves on simple information available at the cutoff.

## 8. Features and models later: what this data supports

Calendar inputs such as hour, day of year and forecast lead are known for all target hours. Recent temperature/dew point/wind/pressure/cloud/rain summaries may be computed from pre-origin observations and held fixed or combined with lead. At late leads, yesterday's true temperature is unknown: do not use a target-relative lag that points inside the forecast period. Recursive models must feed their own predictions, while a direct model uses only origin-known inputs. Pre-issued GFS temperature, cloud, humidity, pressure, wind and rain forecasts are distinct from observed future versions of those variables.

The model plan includes an explicitly fitted **linear regression** and a separate fitted nonlinear model, initially **gradient-boosted trees**, satisfying the deck's two-model rule. GFS is an external weather-model input/benchmark; it will not be used as an excuse to omit our own required models. Station-only variants provide a consistent long-history comparison. Whether a GFS-assisted correction is worth including depends on the separate, shorter archive validation. No architecture is claimed optimal before evaluation.

## 9. Requirements covered and remaining work

| Requirement from the slide deck | How it is covered |
|---|---|
| RDU hourly target, September 17–30 | Station IDs verified; exact 2026 local/UTC boundaries and 336-hour index prepared. Hourly measurement convention remains an explicit grading clarification. |
| Data from before September 17 midnight | Observation downloads end at the exclusive cutoff; final actual temperatures absent. Forecast run chosen earlier, with sampled NOAA publication evidence saved. Every historical fold repeats its own cutoff. |
| Any inputs/features | Local observations, calendar/time keys, normals and separate GFS forecast variables collected; their allowed availability is documented. More features are optional, not a requirement to collect everything. |
| At least one linear regression and one other model | Planned linear regression and gradient-boosted trees after EDA; not yet fitted. |
| Presentation covering inputs, pipeline, features, models, evaluation and performance | Input/pipeline provenance and evaluation design documented. Feature/model choices and actual performance require later work. |
| Code repository | Reproducible download/preparation scripts retained; not yet turned into the final project repository. |
| Two-to-four-page writeup explaining the approach and class concepts | This data memo provides working context, not the graded writeup. The deck says writing and slides must be your own. |
| Deliverables due October 7 | Date recorded from the deck. Remaining sequence: EDA, feature construction, validation, final models/predictions, then your writeup/presentation and repository packaging. |

Data acquisition, preparation and an evaluation specification are the first stages. EDA comes next, before choosing fitted features and models. Data selection may be revised only for a clear quality issue or after the predeclared historical comparison. Current scope stops here: **no EDA, model fitting, final predictions or project submission materials have been produced.**
