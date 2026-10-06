"""Shared fixed-origin evaluation for every model, so results are directly comparable.

A forecast is issued once at an origin (local midnight) and covers the next 336 hours.
Nothing observed at or after the origin may be used. A model is any function

    predict(hist, win) -> array of 336 temperatures (°F)

where `hist` = observations strictly before the origin and `win` = the 336 target hours.
"""
from pathlib import Path
import numpy as np
import pandas as pd

NY = 'America/New_York'
HORIZON = 336
FINAL_ORIGIN = pd.Timestamp('2026-09-17T04:00:00Z')
# Weekly origins around the Sep 17 target date: Aug 27, Sep 3, ..., Oct 8 (7 per year).
ORIGIN_OFFSETS_DAYS = (-21, -14, -7, 0, 7, 14, 21)


def origins(years) -> list:
    """Local-midnight origins (as UTC) for each year in `years`."""
    out = []
    for y in years:
        sep17 = pd.Timestamp(f'{y}-09-17', tz=NY)
        out += [(sep17 + pd.Timedelta(days=d)).tz_convert('UTC') for d in ORIGIN_OFFSETS_DAYS]
    return out


DEV_ORIGINS = origins((2021, 2022, 2023))      # model development
CONFIRM_ORIGINS = origins((2024, 2025))        # locked: score once, after choices are final


def target_window(df: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    """The 336 hourly labels to predict, with actual temperature (NaN if unusable)."""
    times = pd.date_range(origin, periods=HORIZON, freq='h')
    win = df.reindex(times)[['temperature']].copy()
    local = times.tz_convert(NY)
    win['local_hour'], win['local_doy'] = local.hour, local.dayofyear
    win['lead'] = np.arange(1, HORIZON + 1)  # hours ahead; lead 1 = 00:00 local
    return win


def history_before(df: pd.DataFrame, origin: pd.Timestamp, years: int = 10) -> pd.DataFrame:
    """Observations strictly before the origin, limited to the last `years` years."""
    start = origin - pd.DateOffset(years=years)
    hist = df.loc[(df.time >= start) & (df.time < origin)]
    assert hist.time.lt(origin).all() and hist.observed_at.dropna().lt(origin).all()
    return hist


# ---------------------------------------------------------------- baselines

def climatology(hist: pd.DataFrame, win: pd.DataFrame, half_window: int = 7) -> np.ndarray:
    """Mean temperature at the same local hour within +-half_window days of the date."""
    h = hist.dropna(subset=['temperature'])
    out = np.empty(len(win))
    for i, (doy, hour) in enumerate(zip(win.local_doy, win.local_hour)):
        near = (h.local_hour == hour) & ((h.local_doy - doy).abs() <= half_window)
        out[i] = h.temperature[near].mean()
    return out


def persistence(hist: pd.DataFrame, win: pd.DataFrame) -> np.ndarray:
    """Repeat the last observed day (the 24 hours before the origin) for all 14 days."""
    last = hist.iloc[-24:]
    by_hour = dict(zip(last.local_hour, last.temperature))
    return np.array([by_hour[h] for h in win.local_hour])


BASELINES = {'climatology': climatology, 'persistence': persistence}


# ---------------------------------------------------------------- scoring

def score(actual, pred, lead) -> dict:
    """MAE (primary), RMSE and bias = pred - actual. Caller supplies the shared mask."""
    err = np.asarray(pred) - np.asarray(actual)
    day = (np.asarray(lead) - 1) // 24 + 1
    groups = {'d1-3': day <= 3, 'd4-7': (day >= 4) & (day <= 7), 'd8-14': day >= 8}
    res = {'n': len(err), 'MAE': np.abs(err).mean(),
           'RMSE': np.sqrt((err ** 2).mean()), 'bias': err.mean()}
    res.update({f'MAE {k}': np.abs(err[m]).mean() for k, m in groups.items()})
    return res


def evaluate(df: pd.DataFrame, models: dict, origin_list, years: int = 10):
    """Run every model at every origin; score all of them on one shared valid-target mask.

    Returns (per-origin scores, long-format predictions in the agreed output format).
    """
    scores, preds = [], []
    for origin in origin_list:
        hist = history_before(df, origin, years)
        win = target_window(df, origin)
        # Models see only the calendar of the target hours, never the actual temperatures.
        calendar = win.drop(columns='temperature')
        p = {name: np.asarray(f(hist, calendar), dtype=float) for name, f in models.items()}
        mask = win.temperature.notna().to_numpy()
        for v in p.values():
            mask &= ~np.isnan(v)
        for name, v in p.items():
            scores.append({'origin': origin.tz_convert(NY).date(), 'model': name,
                           **score(win.temperature[mask], v[mask], win.lead[mask])})
            preds.append(pd.DataFrame({
                'origin_utc': origin, 'time_utc': win.index,
                'time_local': win.index.tz_convert(NY), 'lead': win.lead,
                'observed_f': win.temperature, 'predicted_f': v, 'model': name,
                'scored': mask}))
    return pd.DataFrame(scores), pd.concat(preds, ignore_index=True)


def summarize(scores: pd.DataFrame) -> pd.DataFrame:
    """Average of per-origin scores (each forecast counts once; hours are not independent)."""
    return scores.drop(columns='origin').groupby('model').mean()


def save_predictions(preds: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    preds.to_csv(path, index=False)
