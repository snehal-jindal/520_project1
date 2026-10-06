"""Validate the final forecasts against post-period RDU routine observations.

The observations supplied to this script are outcomes, never model inputs. They
remain separate from the pre-origin training snapshots.
"""
import argparse
import os
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'rdu-mpl-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
MODEL_COLUMNS = {
    'station_ridge_f': 'Station Ridge',
    'gfs_ridge_f': 'GFS-corrected Ridge',
    'gradient_boosting_f': 'Gradient Boosting',
}


def metrics(actual, predicted):
    error = predicted - actual
    return {
        'n': int(error.notna().sum()),
        'MAE': float(error.abs().mean()),
        'RMSE': float(np.sqrt((error ** 2).mean())),
        'bias': float(error.mean()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actuals', type=Path, required=True,
                        help='IEM routine-report CSV with station, valid and tmpf')
    args = parser.parse_args()

    forecast_path = ROOT / 'reports/final/final_forecast_336h.csv'
    forecast = pd.read_csv(forecast_path)
    forecast['time'] = pd.to_datetime(forecast.time_utc, utc=True)
    if len(forecast) != 336 or not forecast.time.is_unique:
        raise ValueError('Final forecast must contain 336 unique hours.')

    actual = pd.read_csv(args.actuals, dtype={'station': str, 'tmpf': str})
    required = {'station', 'valid', 'tmpf'}
    if not required.issubset(actual.columns) or not actual.station.eq('RDU').all():
        raise ValueError('Expected an RDU IEM routine-report CSV.')
    actual['observed_at_utc'] = pd.to_datetime(actual.valid, utc=True)
    actual['time'] = actual.observed_at_utc.dt.floor('h')
    actual['minutes_after_hour'] = actual.observed_at_utc.dt.minute
    actual['actual_f'] = pd.to_numeric(actual.tmpf.replace({'M': None, '': None}))
    actual['distance_from_routine_minute'] = (
        actual.minutes_after_hour - 51
    ).abs()
    actual = actual.sort_values(
        ['time', 'distance_from_routine_minute', 'observed_at_utc'],
        kind='stable',
    ).drop_duplicates('time')

    joined = forecast.merge(
        actual[['time', 'observed_at_utc', 'minutes_after_hour', 'actual_f']],
        on='time', how='left', validate='one_to_one',
    )
    if joined.actual_f.isna().any():
        missing = joined.loc[joined.actual_f.isna(), 'time_utc'].tolist()
        raise ValueError(f'Missing final observations: {missing}')

    day = (joined.lead_hours - 1) // 24 + 1
    horizon_groups = {
        'overall': np.ones(len(joined), dtype=bool),
        'days 1-3': day.le(3),
        'days 4-7': day.between(4, 7),
        'days 8-14': day.ge(8),
    }
    score_rows = []
    for column, label in MODEL_COLUMNS.items():
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
