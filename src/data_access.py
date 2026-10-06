"""Load and partition observations without exposing protected test outcomes."""
from pathlib import Path
import numpy as np
import pandas as pd

NY = 'America/New_York'
FINAL_ORIGIN = pd.Timestamp('2026-09-17T04:00:00Z')
EDA_ORIGIN = pd.Timestamp('2021-09-17T04:00:00Z')

def load_observations(root: Path) -> pd.DataFrame:
    """Retain the continuous hour grid. The target is provisionally a routine report."""
    path = root/'data/pre_eda/prepared/rdu_all_months_hourly_2011_to_cutoff.csv'
    if not path.exists():
        raise FileNotFoundError('Run python scripts/unpack_data.py before EDA.')
    df = pd.read_csv(path, low_memory=False, dtype={'noaa_temperature_quality_code': str})
    df['time'] = pd.to_datetime(df.hour_label_utc, utc=True)
    df['observed_at'] = pd.to_datetime(df.observation_time_utc, utc=True)
    if not df.time.is_unique or not df.time.diff().dropna().eq(pd.Timedelta(hours=1)).all():
        raise ValueError('The input must have unique, continuous UTC hour keys.')
    if df.time.ge(FINAL_ORIGIN).any() or df.observed_at.dropna().ge(FINAL_ORIGIN).any():
        raise ValueError('Final-test observations are forbidden.')
    if not df.station.eq('RDU').all(): raise ValueError('Unexpected station.')
    df = df.set_index('time', drop=False)
    local = df.time.dt.tz_convert(NY)
    df['local_year'], df['local_month'] = local.dt.year, local.dt.month
    df['local_day'], df['local_hour'] = local.dt.day, local.dt.hour
    df['local_doy'] = local.dt.dayofyear
    df['local_date'] = local.dt.date
    df['temperature'] = df.temperature_usable_f
    speed, direction = df.wind_speed_ms, np.deg2rad(df.wind_direction_deg)
    df['wind_east_ms'] = -speed*np.sin(direction)
    df['wind_north_ms'] = -speed*np.cos(direction)
    # A measured zero wind has zero components even without a defined direction.
    df.loc[speed.eq(0), ['wind_east_ms','wind_north_ms']] = 0.0
    return df

def training_eda_scope(df: pd.DataFrame) -> pd.DataFrame:
    """Retain the original EDA cutoff; early August 2021 development partly overlaps it."""
    core = df.loc[df.time.lt(EDA_ORIGIN)].copy()
    assert core.time.lt(EDA_ORIGIN).all()
    assert core.observed_at.dropna().lt(EDA_ORIGIN).all()
    return core

def current_context_scope(df: pd.DataFrame) -> pd.DataFrame:
    """2026 weather already known at the final origin; separate descriptive scope."""
    return df.loc[df.local_year.eq(2026) & df.local_month.ge(8)].copy()

def pairwise_lag_correlation(series: pd.Series, lag: int, eligible=None):
    """Exact elapsed-time pairs on a continuous grid; never concatenate seasons."""
    if lag < 1: raise ValueError('Lag must be positive.')
    if not isinstance(series.index, pd.DatetimeIndex): raise ValueError('UTC time index required.')
    earlier = series.reindex(series.index-pd.Timedelta(hours=lag))
    earlier.index = series.index
    mask = series.notna() & earlier.notna()
    if eligible is not None:
        old = eligible.reindex(series.index-pd.Timedelta(hours=lag), fill_value=False)
        old.index = series.index
        mask &= eligible & old
    n = int(mask.sum())
    return (float(series.loc[mask].corr(earlier.loc[mask])) if n > 2 else np.nan), n

def missing_runs(df: pd.DataFrame) -> pd.DataFrame:
    missing = df.temperature.isna()
    groups = missing.ne(missing.shift()).cumsum()
    rows = []
    for _, block in df.loc[missing].groupby(groups.loc[missing]):
        rows.append({'start_utc':block.time.iloc[0].isoformat(),
                     'end_utc':block.time.iloc[-1].isoformat(),
                     'hours':len(block),
                     'raw_missing_hours':int(block.temperature_f.isna().sum()),
                     'review_flag_hours':int(block.temperature_archive_review_flag.sum())})
    return pd.DataFrame(rows)
