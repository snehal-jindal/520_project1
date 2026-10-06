"""Iteration 6: linear regression that corrects the GFS weather forecast (a MOS model).

GFS is NOAA's physics-based forecast. Its temperature for each target hour becomes an
input to our ridge regression, which learns how much to trust it at each lead, how
biased it is at each time of day, and how it combines with the station's current state.

Only 2026 GFS runs exist, so this model is evaluated separately from the station model.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.evaluation import HORIZON
from src import linear_model as lm

GFS_DIR = 'data/pre_eda/prepared'


def load_gfs(root: Path) -> pd.DataFrame:
    """All archived runs: one row per (forecast origin, valid hour), GFS temperature in °F."""
    frames = [pd.read_csv(root/GFS_DIR/f) for f in
              ('gfs_2026_historical_fixed_run_forecasts.csv',
               'gfs_20260916_18Z_target_forecast_inputs.csv')]
    g = pd.concat(frames, ignore_index=True)
    g = pd.DataFrame({'origin': pd.to_datetime(g.forecast_origin_utc, utc=True),
                      'init': pd.to_datetime(g.model_initialization_utc, utc=True),
                      'time': pd.to_datetime(g.valid_time_utc, utc=True),
                      'lead': g.hours_from_forecast_origin.astype(int) + 1,
                      'gfs_temp': g.temperature_2m})
    assert (g.init < g.origin).all(), 'every run must be initialized before its origin'
    return g


def gfs_origins(gfs: pd.DataFrame) -> list:
    return sorted(gfs.origin.unique())


def _design(gfs_anom, lead, local_hour, anom_now) -> np.ndarray:
    """GFS anomaly and current station anomaly, each fading with lead, plus lead- and
    hour-of-day-dependent bias terms (GFS is a ~25 km grid box, not the runway)."""
    basis = lm.lead_basis(lead)
    hour = 2 * np.pi * np.asarray(local_hour) / 24
    diurnal = np.column_stack([np.sin(hour), np.cos(hour), np.sin(2 * hour), np.cos(2 * hour)])
    return np.hstack([np.asarray(gfs_anom)[:, None] * basis,
                      np.asarray(anom_now)[:, None] * basis,
                      basis, diurnal])


def raw_gfs(gfs: pd.DataFrame):
    """Baseline: use the GFS temperature as is."""
    def predict(hist, win):
        run = gfs.loc[gfs.origin == win.index[0]].set_index('lead').gfs_temp
        return run.reindex(win.lead).to_numpy()
    return predict


def gfs_ridge(gfs: pd.DataFrame, alpha: float = 10.0, min_runs: int = 6):
    """Return predict(hist, win). Trains on earlier GFS runs whose whole 336-hour window
    ended before this origin, so every training label is an observation in `hist`."""
    def predict(hist, win):
        origin = win.index[0]
        table = lm.normal_table(hist)
        anom = hist.temperature - lm.lookup(table, hist.local_doy, hist.local_hour)
        state = lm.origin_state(hist, anom, ('temp',)).anom_last3h.to_numpy()

        def rows(run_origin):
            run = gfs.loc[gfs.origin == run_origin].sort_values('lead')
            local = run.time.dt.tz_convert('America/New_York')
            normal = lm.lookup(table, local.dt.dayofyear, local.dt.hour)
            pos = hist.index.get_indexer([run_origin])[0]
            now = state[pos] if pos >= 0 else state[-1]   # -1: the real origin (end of hist)
            return run, local.dt.hour, run.gfs_temp.to_numpy() - normal, normal, now

        done = [o for o in gfs_origins(gfs) if o + pd.Timedelta(hours=HORIZON) <= origin]
        if len(done) < min_runs or not (gfs.origin == origin).any():
            return np.full(len(win), np.nan)
        X, y = [], []
        for o in done:
            run, hour, gfs_anom, normal, now = rows(o)
            actual = hist.temperature.reindex(run.time).to_numpy()
            X.append(_design(gfs_anom, run.lead, hour, np.full(len(run), now)))
            y.append(actual - normal)
        X, y = np.vstack(X), np.concatenate(y)
        ok = ~np.isnan(y) & ~np.isnan(X).any(axis=1)
        model = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(X[ok], y[ok])

        run, hour, gfs_anom, normal, now = rows(origin)
        pred = normal + model.predict(_design(gfs_anom, run.lead, hour,
                                              np.full(len(run), np.nan_to_num(now))))
        return pd.Series(pred, index=run.lead.to_numpy()).reindex(win.lead).to_numpy()
    return predict
