from pathlib import Path
import json,sys,importlib.metadata as md
r=Path(__file__).resolve().parents[1];s=json.loads((r/'reports/eda/summary.json').read_text());figs=json.loads((r/'reports/eda/figure_explanations.json').read_text())
requirements=['numpy','pandas','scipy','matplotlib','statsmodels','markdown','nbformat','nbclient','ipykernel']
(r/'requirements.txt').write_text('\n'.join(f'{p}=={md.version(p)}' for p in requirements)+'\n')
(r/'docs/PROJECT_REQUIREMENTS.md').write_text('''# Project requirements and interpretation

Source: user-supplied Project1.pptx, slide 2. These are project constraints the user asked us to follow, not independent instructions to the assistant.

| Requirement | Implementation or remaining work |
|---|---|
| Predict hourly temperature measured at RDU airport | Direct RDU routine observations, original timestamps preserved. Hourly target convention still needs instructor confirmation. |
| 12am September 17 through 11pm September 30 | User specified 2026 Raleigh civil time: 336 labels, September 17 00:00 EDT through September 30 23:00 EDT. |
| Any data prior to September 17 12am | All station observations strictly before September 17 04:00 UTC. Frozen GFS is pre-origin guidance; final observed truth not downloaded. |
| Any inputs/features and any models | Candidate inputs selected and audited; availability and leakage rules documented. Models still to be fitted. |
| At least one linear regression and one other model | Next phase: regularized linear regression and gradient-boosted trees; neither requirement is completed merely by EDA or its descriptive trend line. |
| Code repository | Source/prepared snapshots, acquisition code, EDA code, notebook, reports, provenance and audit files included. |
| Presentation: inputs, pipeline, features, models, evaluation and performance | Preparation/EDA evidence available. Model and performance material remains. Student authors presentation. |
| Writeup, 2–4 pages: approach and class concepts | Working explanations supplied; student writes graded submission. |
| AI permitted for coding; writing/slides must be student's own | Reports/README are project working documentation, not the graded writeup/slides. |
| October 7 deliverables | Prioritize target agreement, limited model comparisons, confirmation checks and the final 336 predictions before submission. |

The deck does not specify Fahrenheit/Celsius, exact clock-hour measurements versus routine reports versus hourly means, or a grading metric. Our provisional choice is routine-report temperature in Fahrenheit and MAE as the primary development metric; disclose and resolve these assumptions before final scoring. In September Raleigh uses EDT (UTC−4). Fixed EST would shift the forecast labels by one hour and is not the user's Raleigh-time interpretation.

Original PowerPoint redistribution is separate from extracting its requirements. It is not bundled unless explicitly approved for publication.
''')
(r/'docs/NEXT_STEPS.md').write_text('''# Modeling plan after EDA

The remaining task is to turn pre-origin information into one 336-hour forecast, not 336 forecasts updated using observations acquired during the test fortnight.

1. **Settle the target and scoring contract.** Confirm units and hourly convention. Review source-disagreement flags using raw evidence; document a consistent label/source policy without examining confirmation weather to choose models. For missing or unresolved targets, report exclusions and score every candidate on the same mask.
2. **Implement simple baselines first.** Hour/day seasonal climatology fitted on each training fold; NOAA fixed normals only for origins after their 2021 publication; persistence and an origin-known recent daily-cycle baseline. They tell us whether added complexity actually helps.
3. **Build two required models.** Regularized linear regression with cyclic calendar features, hour-by-season interactions, lead time, and origin-known weather summaries; a gradient-boosted tree regression using the same permitted information. Fit preprocessing and any feature selection solely within the fold. Test the linear model and tree model against baselines; a descriptive EDA trend does not satisfy the required linear forecasting model.
4. **Compare history and seasons economically.** Use 2021–2023 September origins for five vs ten complete prior years, September vs Aug–Oct vs all months. Include the current-origin year only up to its cutoff using the chosen months. Continuous raw history supplies elapsed-time lags. Keep features and scoring masks matched. Prefer the simpler configuration if average improvements are small or inconsistent across years. The initial Aug–Oct ten-year candidate is justified, but not yet proven best.
5. **Keep fixed-origin features honest.** A training row must represent information available at its forecast origin. For hour 200, yesterday's actual target-window temperature is unavailable. Use summaries calculated at the origin, recursive predictions if explicitly designed, or frozen forecast inputs. Do not use same-hour observed humidity, rain, pressure, wind, clouds, or METAR target precision as predictors. Calendar features for future hours are known; actual future weather is not.
6. **Evaluate GFS corrections separately.** April 2–July 23, 2026 initializations are calibration candidates; July 30 is excluded because its valid labels overlap the first August confirmation origin; August 6/13/20/27 runs are reserved confirmation. Fit modest lead/hour-dependent bias correction or residual models only on calibration data and compare with uncorrected guidance on matched August origins. The current diagnostic fits no correction. All runs must be demonstrably or conservatively available before their simulated origins; historical API-serving times remain unverified.
7. **Lock choices before confirmation.** Station-history models have September 2024 and 2025 confirmation folds. GFS starts in April 2026, so there is no matched 2021–2025 GFS comparison. Do not rank a spring/summer GFS score against a September station-model score as if they were the same test. A decision to include GFS in the final model must acknowledge this limitation.
8. **Report relevant metrics.** Primary MAE in °F; secondary RMSE and signed bias (prediction minus observation). Report each origin and pooled results, sample counts, each of days 1–14, groups 1–3/4–7/8–14, and daytime/nighttime. Use matched masks. Report improvements over baselines. No temperature MAPE or training R² claims. Weekly GFS windows overlap; use per-origin summaries and avoid treating thousands of hourly pairs as independent samples.
9. **Create and verify the final file.** Refit chosen station model with permitted history through September 16, 2026; any GFS-based feature comes from the September 16 18Z frozen run. Produce exactly 336 unique ordered labels and temperatures, with model/source metadata. Verify UTC/local conversion, completeness, no final actuals, and no updating during the fortnight. Optional intervals need genuine calibration; one GFS run or historical quantile ribbon is not calibrated uncertainty.
10. **Complete the student's own deliverables.** Use the evidence and reproducible code to prepare the presentation and 2–4 page writeup, including class concepts, model comparison, final limitations and performance. EDA is complete; modeling, final forecasts and graded submissions remain.

A small set of well-validated candidates is preferable to a large search on only three development Septembers. Existing EDA does not decide an empirical winner. Climate context justifies the history-length comparison; it is not a separate modeling objective.
''')
rows='\n'.join(f'| {i+1} | [{f["question"]}](reports/eda/EDA_REPORT.md#{f["title"].lower().replace(" ","-")}) | {f["implication"]} |' for i,f in enumerate(figs))
# Main README includes decisions and a guide to every diagnostic; report is detailed evidence.
readme=f'''# RDU hourly temperature forecasting — Project 1

Reproducible data selection, acquisition, quality screening and exploratory analysis for a **336-hour forecast at Raleigh–Durham International Airport (RDU)**. The focus is forecast accuracy, permitted inputs and reliable ML evaluation. This repository currently completes preparation and EDA; it does not contain the required trained models or final predictions.

## The forecast we must produce

Issue one forecast at **September 17, 2026, 00:00 Raleigh civil time**, covering every hourly label through **September 30, 2026, 23:00**. September is EDT (UTC−4), so the exclusive observation cutoff is **September 17 04:00 UTC** and the final label is **October 1 03:00 UTC**. There are exactly **336 hours**. Inputs must be known before the origin; later observations may not update the forecast. The PowerPoint requires **linear regression plus another model**, a code repository, a presentation and a 2–4 page writeup. [All requirements and assumptions](docs/PROJECT_REQUIREMENTS.md).

**Resolve before scoring:** routine RDU observations usually arrive at **:51**. We retain their actual times and provisionally assign each routine report to its clock-hour label. That is not an exact on-the-hour reading or an hourly average. The deck leaves this definition and units unspecified; current analysis uses °F. NOAA normals use local standard time (UTC−5), correctly adjusted for EDT. The deck permits AI coding but requires the student's own graded writing/slides; this README and report are working documentation.

## Data sources: what we chose and why

| Selected source | Role | Coverage and tradeoff |
|---|---|---|
| [Iowa Environmental Mesonet RDU routine METAR archive](https://mesonet.agron.iastate.edu/request/download.phtml?network=NC_ASOS) | Airport temperature target, observed dew point, RH, wind, pressure, rain, clouds and raw METAR trace | All months, January 1, 2011 to the exclusive 2026 cutoff. Direct airport observations with consistent routine-report sampling; archive QC is limited, so cross-checks are necessary. |
| [NOAA GHCN-hourly](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly) | Exact-timestamp temperature verification, source codes and quality flags | 2011–2025 yearly files. The 2026 full-year archive was not fetched because it would include final-test truth. It shares underlying airport measurements with IEM, so it is verification rather than an independent target dataset. |
| [NOAA 1991–2020 hourly normals](https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals) | Fixed seasonal/hourly climatology benchmark | 8,760 calendar-hour values and all 336 final lookups. Published in 2021: not valid as a historical as-of benchmark before publication, and not 30 extra training years. Local-standard-time mapping retained. |
| [Open-Meteo single-run GFS archive](https://open-meteo.com/en/docs/single-runs-api) | Frozen future weather inputs, raw forecast benchmark, separate 2026 calibration candidates | 22 historical weekly April–August 2026 runs plus the September 16 18Z final-input run. GFS covers the entire 14 days; selected final leads 10–345h. Gridded/downscaled, with hourly interpolation after native hourly resolution ends at lead 120. |
| [NOAA station history/HOMR](https://www.ncei.noaa.gov/access/homr/) and GFS publication headers | Provenance and availability checks | Used for instrument/site context and sampled original-file publication checks. They do not supply extra temperature training rows. |

**Why ignore other sources initially?** Daily products cannot supply hourly labels; reanalysis and NASA POWER are grid estimates rather than direct airport truth; Meteostat point series may interpolate or fill with models; LCD largely duplicates NOAA observations; nearby airports are different targets. HRRR/NAM/NBM/MOS and the ECMWF archive candidate have shorter horizons than the full 14 days. Adding them now would increase alignment, missingness and leakage risks without solving a clear unmet requirement. This is a documented review of practical authoritative candidates, not a claim to have exhaustively searched every weather dataset. [Full source comparison, acquisition details, station milestones and caveats](docs/DATA_DECISIONS.md).

## How far back, and which months?

**Extract all months from 2011 onward; initially propose Aug–Oct from 2016 onward for the final station fit.** These are different decisions:

- **2011 extraction start:** testing a ten-year history at the first 2021 forecast origin needs 2011–2020. Starting the download at 2016 would prevent that fair comparison. Continuous all-month storage also prevents incorrect lags formed by stitching separate seasonal blocks together.
- **Initial final-fit candidate:** Aug–Oct 2016–2025 plus Aug 1–Sep 16, 2026. This brackets the target's autumn transition and offers more weather episodes than September alone. It contains **23,208 expected hours, 23,187 usable targets** after the provisional screen: 18 absent temperatures and 3 unresolved source discrepancies.
- **Tradeoffs to test:** five versus ten complete prior years and September-only versus Aug–Oct versus all months. All months can help a season-aware model learn daily cycles but bring winter/summer regimes far from the target. Shorter history may represent recent conditions better but estimates rare events less reliably. **No option is proven best until matched September backtests.**
- **Environmental context stays bounded:** regional warming motivates recency sensitivity; it does not identify 2016 as a climate break. Station metadata does not justify assuming a move at that year. Retain plausible weather extremes; quarantine supported source discrepancies separately. No arbitrary warming offset is applied.

## Preparation already completed

Original source files, request manifests, raw METAR text, station metadata and acquisition/preparation scripts are retained. The master grid has **137,711 expected UTC hourly slots**. Routine reports are selected consistently and duplicates/off-schedule reports are audited. Celsius/Fahrenheit, knots/metres per second, and inches/millimetres conversions are documented. Missing temperatures and source disagreements remain unavailable; none are interpolated. Exact NOAA matching retains quality/source codes and distinguishes rounding from disagreements. Calendar labels use Raleigh time; elapsed lags use UTC.

Covariates preserve reporting meaning: trace rain is distinct from zero, variable wind from north, and blank higher cloud layers from sensor failure. Wind components represent direction where measured speed/direction permit. Some parsed calm speeds are missing, so calm is only set to zero when actually measured. Source precision is retained; the parsed METAR T-group is an alternate target representation, never a same-hour predictor. [Data dictionary](docs/DATA_DICTIONARY.md), [preparation audit](docs/PREPARATION_QUALITY_REPORT.md).

## EDA completed and its scope

The main model-design EDA stops **before September 17, 2021**, the earliest development origin. Complete-year comparisons use **2011–2020**, with **{s['core']['usable']:,} usable temperatures across {s['core']['hours']:,} core hourly slots**. This preserves later September test weather for evaluation. Separate sections inspect permissible Aug 1–Sep 16, 2026 observations and pre-issued forecast inputs. GFS errors use April–July calibration runs only; July 30 and August confirmation runs are excluded. General preparation QC may flag reserved-period missingness/source disagreements, but EDA does not use their weather patterns to choose models.

**Results that matter for prediction:**

- The exact historical target fortnight has **3,355 usable hours across ten Septembers**; these are ten annual weather windows, not thousands of independent events. Its median is **70°F**, with a middle 80% range of **59–81°F**.
- Daily and seasonal cycles are strong, but individual fortnights have very different weather paths. Use calendar features and evaluate whole 14-day forecasts, not random hourly splits.
- Five-/ten-year target hourly means differ by **{s['five_vs_ten_mean_abs_hourly_difference_f']:.2f}°F** on average. This supports a controlled history-length test, not an immediate recency winner.
- Removing the training month/hour mean sharply reduces long-lag temperature correlation. A recent observed temperature can help near the origin, but actual future temperatures cannot become later-hour lag inputs.
- Same-hour dew point/humidity/cloud relationships are descriptive. Their actual future observations are prohibited; use origin-known summaries or frozen forecast guidance. Predictive usefulness still requires validation.
- The core has **175 unavailable/quarantined temperatures**, a longest unavailable run of **12 hours**, and **37 archive disagreements**. Median absolute IEM/NOAA difference across matched core reports is **0.04°F**; agreement is not independent-sensor validation.
- All **336 final GFS temperature inputs and normal lookups** are present. In **17 calibration-only GFS origins**, interpolated to actual routine-report timestamps, pooled **MAE is {s['gfs_exploratory_benchmark']['mae_f']:.2f}°F**, **RMSE {s['gfs_exploratory_benchmark']['rmse_f']:.2f}°F**, **bias {s['gfs_exploratory_benchmark']['bias_f']:+.2f}°F**. Errors increase with lead. **These are exploratory spring/summer benchmark results, not September/final model performance.** The 5,700 scored pairs share only 3,016 distinct report times because weekly windows overlap.

Every figure explains its question, data scope, actual finding, forecast implication and limitations in the **[complete EDA report](reports/eda/EDA_REPORT.md)**. For easier offline reading, open **[EDA_REPORT.html](reports/eda/EDA_REPORT.html)** beside its figures. The **[executed notebook](notebooks/01_rdu_eda.ipynb)**, [numeric tables](reports/eda/tables), PNG/SVG figures and [computed summary](reports/eda/summary.json) accompany the report.

| Diagnostic | Question answered | Consequence for forecasting |
|---|---|---|
{rows}

## Availability and evaluation rules

Use one fixed origin for all 336 forecasts. Calendar features are known ahead of time; target-window actual temperature, humidity, wind, pressure, rain and clouds are not. Frozen GFS values are eligible only from a run available before the origin. Historical station archives are revised snapshots, not proof of exact historical release-time data. Final sampled NOAA GFS files were published before the cutoff; original Open-Meteo serving times and every historical run's publication time were not individually verified. Avoid claims stronger than the retained evidence.

**Development:** September 2021–2023. **Station confirmation:** September 2024–2025, only after locking choices. **GFS calibration:** April 2–July 23 initializations; **GFS confirmation:** August 6/13/20/27 initializations. Exclude July 30 because of label overlap with confirmation origins. Never compare different cohorts' errors as if they were matched tests.

**Metrics:** primary MAE; secondary RMSE and signed bias in °F, with scored counts; per origin, each forecast day, days 1–3/4–7/8–14, and day/night. Every candidate shares the same valid-target mask. Two September 2024 targets have unresolved archive conflicts and two September 2025 targets are missing; document their treatment before scoring. MAPE on temperature and training R² are not measures of 14-day forecast quality. Fit imputation/scaling/feature selection only within each training fold. Report overlap and use origin/year-level summaries rather than assuming hourly independence.

## Files and reproducibility

All acquired weather/metadata files and the earlier preparation outputs are bundled in **three self-contained ZIP snapshots**, rather than omitted or replaced with external download links. They contain **97 files** including their checksum manifest. Original measurement files are unchanged; only a private local pathname in metadata was removed and the public-copy manifest refreshed. The extracted `data/pre_eda/` directory is ignored to avoid duplicating roughly 300MiB of uncompressed data in Git. This is storage packaging, not data exclusion. The [complete inventory](reports/FILE_INVENTORY.csv) lists every committed file and every bundled member. Runtime caches, installed third-party packages and Git internals are housekeeping files, not project deliverables; package versions are recorded. The original deck is subject to separate publication permission; requirements are included.

| Location | Contents |
|---|---|
| `data/snapshots/` | Complete raw, prepared and records snapshots; original acquisition/preparation scripts inside records ZIP |
| `docs/` | Source decisions, dictionary, quality report, requirements, next modeling steps and contracts |
| `src/`, `scripts/`, `tests/` | EDA/data-access code, unpack/rebuild utilities, leakage/time-alignment tests |
| `notebooks/` | Executed, explained EDA notebook |
| `reports/eda/` | Markdown/HTML reports, 24 figures in PNG/SVG, numeric tables and computed summaries |
| `reports/` | File inventory, checksums and completion audit |
| `requirements.txt` | Exact versions of direct Python dependencies used |

From the repository root, use **Python 3.12 or later**:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/unpack_data.py
python -m unittest discover -s tests -v
python scripts/run_eda.py
python scripts/build_notebook.py
```

Unpacking verifies every bundled file checksum. EDA runs entirely from the saved snapshot, without downloading final outcomes or using live forecast values. Regenerate files before comparing checksums; visual formats can differ with fonts/plotting platforms. To rerun acquisition, see the original snapshot's `reproducibility/README.md`; preserved downloads are more stable than mutable endpoints. The saved history contains reserved historical outcomes for later evaluation; scope guards exclude them from the initial EDA. The executed notebook deliberately displays only permitted scopes.

## Next phase

Confirm the hourly target/units and source-conflict policy, establish baselines, fit the required regularized linear regression and a gradient-boosted tree model, compare history/month choices on development folds, then run locked confirmation checks. Evaluate GFS corrections in their separate chronology. Finally refit with permitted history and produce/audit the 336 predictions. The **[detailed next-step plan](docs/NEXT_STEPS.md)** explains feature availability, fair comparisons, uncertainty and the student's remaining presentation/writeup. EDA conclusions guide these tests; they do not replace them.
'''
# Avoid brittle auto-generated anchors: each diagnostic links to the complete report.
import re
readme=re.sub(r'\]\(reports/eda/EDA_REPORT\.md#[^)]+\)','](reports/eda/EDA_REPORT.md)',readme)
(r/'README.md').write_text(readme)
(r/'docs/EDA_SCOPE.json').write_text(json.dumps({'final_origin_utc':'2026-09-17T04:00:00Z','final_hours':336,'initial_eda_exclusive_cutoff_utc':'2021-09-17T04:00:00Z','full_year_comparisons':'2011–2020','known_context':'2026 Aug 1–Sep 16','gfs_calibration_latest_initialization':'2026-07-23T18:00:00Z','no_final_actuals':True,'forecast_target_definition':'routine report provisionally assigned to clock-hour; instructor confirmation pending'},indent=2)+'\n')
