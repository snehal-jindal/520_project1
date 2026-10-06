"""Evaluation-only checks; this module never imports or fits forecasting models."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

MODEL_COLUMNS = {'station_ridge_f': 'Station Ridge', 'gfs_ridge_f': 'GFS-corrected Ridge',
                 'gradient_boosting_f': 'Gradient Boosting'}
BASELINES = {'climatology_f': 'Climatology', 'raw_gfs_f': 'Raw GFS'}
ALL_COLUMNS = {**MODEL_COLUMNS, **BASELINES}
EXPECTED_TIMES = pd.date_range('2026-09-17T04:00:00Z', periods=336, freq='h')


def verify_frozen_forecast(path, record_path):
    record = json.loads(Path(record_path).read_text())
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != record['forecast_sha256']:
        raise ValueError('Predictions differ from the recorded pre-outcome forecast.')


def validate_forecast(forecast):
    required = {'time_utc', 'time_local', 'lead_hours', 'submitted_forecast_f', *ALL_COLUMNS}
    if not required.issubset(forecast.columns):
        raise ValueError('Missing required forecast columns.')
    forecast = forecast.copy()
    forecast['time'] = pd.to_datetime(forecast.time_utc, utc=True)
    if not pd.DatetimeIndex(forecast.time).equals(EXPECTED_TIMES):
        raise ValueError('Forecast must contain the 336 exact, ordered UTC target hours.')
    if forecast.time_local.tolist() != EXPECTED_TIMES.tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M').tolist():
        raise ValueError('Local labels disagree with Raleigh time.')
    if not np.array_equal(forecast.lead_hours.to_numpy(), np.arange(1, 337)):
        raise ValueError('lead_hours must be target-hour ordinals 1 through 336.')
    if not np.isfinite(forecast[[*ALL_COLUMNS, 'submitted_forecast_f']].to_numpy(dtype=float)).all():
        raise ValueError('Every model must have 336 finite predictions.')
    if not np.array_equal(forecast.submitted_forecast_f, forecast.gfs_ridge_f):
        raise ValueError('Submitted forecast must preserve the selected GFS Ridge values.')
    return forecast


def join_actuals(forecast, actual):
    if not {'station', 'valid', 'tmpf'}.issubset(actual.columns) or not actual.station.eq('RDU').all():
        raise ValueError('Expected an RDU IEM CSV with station, valid and tmpf.')
    actual = actual.copy()
    actual['observed_at_utc'] = pd.to_datetime(actual.valid, utc=True)
    actual['time'] = actual.observed_at_utc.dt.floor('h')
    actual['minutes_after_hour'] = actual.observed_at_utc.dt.minute
    actual['actual_f'] = pd.to_numeric(actual.tmpf.replace({'M': None, '': None}), errors='coerce')
    actual['distance_from_routine_minute'] = (actual.minutes_after_hour - 51).abs()
    actual = actual.sort_values(['time', 'distance_from_routine_minute', 'observed_at_utc'], kind='stable').drop_duplicates('time')
    joined = forecast.merge(actual[['time', 'observed_at_utc', 'minutes_after_hour', 'actual_f']], on='time', how='left', validate='one_to_one')
    if not np.isfinite(joined.actual_f.to_numpy(dtype=float)).all():
        raise ValueError('The saved final evaluation requires 336 finite actuals; do not fill missing targets.')
    if not joined.observed_at_utc.dt.floor('h').equals(joined.time):
        raise ValueError('An observation was assigned to the wrong UTC hour.')
    return joined


def metrics(actual, predicted):
    error = np.asarray(predicted, dtype=float) - np.asarray(actual, dtype=float)
    if len(error) == 0 or not np.isfinite(error).all():
        raise ValueError('Score only a nonempty shared set of finite targets/predictions.')
    return {'n': int(len(error)), 'MAE': float(np.abs(error).mean()),
            'RMSE': float(np.sqrt(np.square(error).mean())), 'bias': float(error.mean())}
