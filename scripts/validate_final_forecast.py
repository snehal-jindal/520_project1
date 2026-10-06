"""Validate the final forecasts against post-period RDU routine observations.

The observations supplied to this script are outcomes, never model inputs. They
remain separate from the pre-origin training snapshots.
"""
import argparse
import os
from pathlib import Path
import tempfile
import sys
import numpy as np
import pandas as pd

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'rdu-mpl-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.final_evaluation import ALL_COLUMNS, validate_forecast, join_actuals, verify_frozen_forecast
from src.final_evaluation import metrics as checked_metrics
from scripts.download_final_actuals import OUTPUT, verify_snapshot
MODEL_COLUMNS = {
    'station_ridge_f': 'Station Ridge',
    'gfs_ridge_f': 'GFS-corrected Ridge',
    'gradient_boosting_f': 'Gradient Boosting',
}


def metrics(actual, predicted):
    return checked_metrics(actual, predicted)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actuals', type=Path, default=OUTPUT,
                        help='Default: bundled evaluation-only IEM routine-report CSV.')
    args = parser.parse_args()

    forecast_path = ROOT / 'reports/final/final_forecast_336h.csv'
    verify_frozen_forecast(forecast_path, ROOT / 'docs/FORECAST_RECORD.json')
    if args.actuals.resolve() == OUTPUT.resolve():
        verify_snapshot()
    forecast = validate_forecast(pd.read_csv(forecast_path))

    actual = pd.read_csv(args.actuals, dtype={'station': str, 'tmpf': str})
    joined = join_actuals(forecast, actual)

    day = (joined.lead_hours - 1) // 24 + 1
    horizon_groups = {
        'overall': np.ones(len(joined), dtype=bool),
        'days 1-3': day.le(3),
        'days 4-7': day.between(4, 7),
        'days 8-14': day.ge(8),
    }
    score_rows = []
    for column, label in ALL_COLUMNS.items():
        joined[f'{column}_error'] = joined[column] - joined.actual_f
        for horizon, mask in horizon_groups.items():
            score_rows.append({
                'model': label,
                'horizon': horizon,
                **metrics(joined.loc[mask, 'actual_f'], joined.loc[mask, column]),
            })

    output = ROOT / 'reports/final'
    joined.drop(columns='time').to_csv(
        output / 'final_forecast_with_actuals.csv', index=False
    )
    scores = pd.DataFrame(score_rows)
    scores.to_csv(output / 'final_validation_scores.csv', index=False)
    daily_rows, light_rows = [], []
    daylight = pd.to_datetime(joined.time_local).dt.hour.between(6, 17)
    for column, label in ALL_COLUMNS.items():
        for d in range(1, 15):
            mask = day.eq(d)
            daily_rows.append({'model': label, 'forecast_day': d, **metrics(joined.actual_f[mask], joined[column][mask])})
        for period, mask in [('day_06_to_17_local', daylight), ('night_other_hours', ~daylight)]:
            light_rows.append({'model': label, 'period': period, **metrics(joined.actual_f[mask], joined[column][mask])})
    pd.DataFrame(daily_rows).to_csv(output / 'final_validation_by_day.csv', index=False)
    pd.DataFrame(light_rows).to_csv(output / 'final_validation_day_night.csv', index=False)

    time_local = pd.to_datetime(joined.time_local)
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(time_local, joined.actual_f, color='black', lw=1.4,
            label='Observed RDU')
    colors = {
        'station_ridge_f': 'tab:blue',
        'gfs_ridge_f': 'tab:red',
        'gradient_boosting_f': 'tab:green',
    }
    for column, label in MODEL_COLUMNS.items():
        ax.plot(time_local, joined[column], lw=1.0, alpha=0.85,
                color=colors[column], label=label)
    ax.set_title('RDU final forecast validation: September 17–30, 2026')
    ax.set_ylabel('Temperature (°F)')
    ax.grid(alpha=0.25)
    ax.legend(ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(output / 'final_validation_plot.png', dpi=160)
    plt.close(fig)
    print(scores.to_string(index=False))


if __name__ == '__main__':
    main()
