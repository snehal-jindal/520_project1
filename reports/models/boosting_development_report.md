# Gradient-boosting development result

This report records development selection followed by one locked 2024–2025
confirmation run. No model choice below was changed after that run.

## Model

The selected model averages two `HistGradientBoostingRegressor` components
trained to predict observed RDU temperature minus a training-only hourly
climatology. Each training block is a simulated 336-hour fixed-origin forecast.
All recent-weather summaries stop strictly before that simulated origin.

The stable component uses climatology, cyclic calendar values, forecast lead,
and origin-known temperature departures, dew point and pressure. The aligned
component adds 3-hour temperature departure, 24-hour pressure change, dew-point
depression, wind, clouds and rain, with explicit 12/48/168-hour decay
interactions. Their predictions receive equal weight. A 120-hour decay also
returns the overall predicted anomaly toward climatology with lead. The final
public prediction is temperature in degrees Fahrenheit.

## Development results

Results average the 21 forecast-level scores from the seven weekly late-summer
and autumn origins in each of 2021–2023. Every model uses the same valid-target
mask. MAE is the primary metric.

| Model | MAE (°F) | RMSE (°F) | Bias (°F) | Days 1–3 MAE | Days 4–7 MAE | Days 8–14 MAE |
|---|---:|---:|---:|---:|---:|---:|
| Climatology, 10 years | 5.019 | 6.072 | +0.005 | 4.973 | 4.819 | 5.153 |
| Climatology, 5 years | 4.949 | 6.083 | +0.946 | 4.930 | 4.716 | 5.089 |
| Gradient-boosting ensemble, 5 years | **4.696** | **5.787** | +0.494 | **4.062** | **4.471** | 5.096 |
| Persistence | 6.533 | 8.068 | +1.031 | 5.510 | 6.330 | 7.087 |

The selected model improves average MAE over the matched five-year climatology
by 0.252°F (5.10%) and over the original ten-year climatology by 0.323°F. It
helps mainly during days 1–7; its days 8–14 result is slightly worse than the
five-year climatology. It beats matched climatology at 14 of the 21 origins.
Mean improvement over matched climatology is +0.340°F in 2021, +0.466°F in
2022, and -0.048°F in 2023. The improvement remains modest and not uniform.

## Development-only decay check

The initial unshrunk ten-year boosted correction produced 5.286°F MAE and +1.070°F bias:
it improved days 1–3 but over-corrected later hours. A small declared check of
constant correction weights (0.25, 0.50, 0.75) and exponential time constants
(72, 120, 168, 240 hours) selected 72 hours by development MAE. This choice and
all other settings must be frozen before confirmation scoring.

The second declared comparison tested five versus ten years, removing origin
dew point and pressure, and reducing tree size. The full five-year candidate had
the lowest MAE. Removing dew point and pressure from that candidate increased
MAE from 4.777°F to 4.847°F, so the fields were retained.

The third iteration tested direct bias subtraction, absolute-error loss, three
extra origin-state features, correction decay, and a squared/absolute ensemble.
Bias subtraction, absolute loss, and the extra features did not improve MAE.
The ensemble improved by less than 0.001°F and was rejected as needless
complexity. Rechecking decay for the selected five-year model favored 120 hours
(4.745°F MAE) over 72 hours (4.777°F); this is the final development choice.

The fourth iteration tested denser training origins and a Ridge-aligned weather
feature set. Weekly and three-day practice origins worsened MAE and were
rejected. The aligned tree alone produced 4.737°F MAE with stronger short-range
error and bias but inconsistent per-origin gains. Averaging it with the stable
tree improved MAE to 4.696°F, RMSE to 5.787°F and bias to +0.494°F. This
ensemble is the final nonlinear development selection.

## Interpretation and limitation

The nonlinear model clears its matched development climatology, but overlapping
336-hour windows and only three development years mean that the hourly rows are
not independent evidence.

## Locked confirmation result

The selected nonlinear ensemble was run once on the 14 shared 2024–2025
confirmation origins. The teammate's locked Ridge results use the same origins
and target observations, although Ridge trains on ten years and boosting on five.

| Model | MAE (°F) | RMSE (°F) | Bias (°F) | Days 1–3 | Days 4–7 | Days 8–14 |
|---|---:|---:|---:|---:|---:|---:|
| Locked Ridge | **5.058** | **5.976** | +0.315 | **4.511** | **5.168** | **5.225** |
| Locked gradient boosting | 5.470 | 6.400 | **+0.093** | 5.212 | 5.598 | 5.504 |

Ridge improves confirmation MAE by 0.412°F (7.54% relative to the boosting
error) and is better in every horizon group. Boosting has the smaller signed
bias, but lower bias does not compensate for its larger absolute errors. The
development difference between the models was only 0.004°F in boosting's favor;
confirmation shows that difference was not a reliable performance advantage.
No further tuning should use these confirmation outcomes.
