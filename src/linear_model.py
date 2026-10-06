"""Linear regression forecaster. Evaluation and baselines live in src/evaluation.py.

Iteration 2: calendar-only ridge regression. Features describe *when* an hour is
(time of day, time of year), not what the weather is doing, so the model can at best
learn the typical temperature for that hour and date, i.e. reproduce climatology.

Iteration 3: anomaly ridge regression. prediction = normal + predicted anomaly, where
the anomaly (actual - normal) is predicted from how unusual the weather was just
before the origin, with weights that fade as the lead time grows.
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.evaluation import HORIZON


def calendar_features(local_hour, local_doy, n_harmonics: int = 2) -> pd.DataFrame:
    """Cyclic encodings of hour of day and day of year, plus their interactions.

    sin/cos keep 23:00 next to 00:00 and Dec 31 next to Jan 1. Extra harmonics let the
    daily curve be asymmetric (fast morning warm-up, slow evening cool-down). The
    hour x season products let the size of the daily swing change through the season.
    """
    hour = 2 * np.pi * np.asarray(local_hour) / 24
    doy = 2 * np.pi * np.asarray(local_doy) / 365.25
    f = {}
    for k in range(1, n_harmonics + 1):
        f[f'hour_sin{k}'], f[f'hour_cos{k}'] = np.sin(k * hour), np.cos(k * hour)
    f['doy_sin'], f['doy_cos'] = np.sin(doy), np.cos(doy)
    for name in [c for c in f if c.startswith('hour_')]:
        f[f'{name}_x_doy_sin'] = f[name] * f['doy_sin']
        f[f'{name}_x_doy_cos'] = f[name] * f['doy_cos']
    return pd.DataFrame(f)


def calendar_ridge(n_harmonics: int = 2, months=(8, 9, 10), alpha: float = 1.0):
    """Return a predict(hist, win) function for the shared evaluation harness.

    Training rows: every usable hour in `hist` (already strictly before the origin)
    whose local month is in `months`. Target: temperature in °F.
    """
    def predict(hist: pd.DataFrame, win: pd.DataFrame) -> np.ndarray:
        train = hist.loc[hist.local_month.isin(months)].dropna(subset=['temperature'])
        model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
        model.fit(calendar_features(train.local_hour, train.local_doy, n_harmonics),
                  train.temperature)
        return model.predict(calendar_features(win.local_hour, win.local_doy, n_harmonics))
    return predict


# ---------------------------------------------------------------- iteration 3

def normal_table(hist: pd.DataFrame, half_window: int = 7) -> np.ndarray:
    """Typical temperature for every (day of year, local hour): a 366 x 24 lookup.

    Same definition as the climatology baseline: mean at that hour within
    +-half_window days, wrapping around the year end.
    """
    h = hist.dropna(subset=['temperature'])
    total, count = np.zeros((366, 24)), np.zeros((366, 24))
    np.add.at(total, (h.local_doy - 1, h.local_hour), h.temperature)
    np.add.at(count, (h.local_doy - 1, h.local_hour), 1)
    win_total, win_count = np.zeros_like(total), np.zeros_like(count)
    for shift in range(-half_window, half_window + 1):
        win_total += np.roll(total, shift, axis=0)
        win_count += np.roll(count, shift, axis=0)
    return win_total / win_count


def lookup(table: np.ndarray, local_doy, local_hour) -> np.ndarray:
    return table[np.asarray(local_doy) - 1, np.asarray(local_hour)]


# How quickly each kind of "unusual weather" fades: e-folding times in hours, plus a
# constant (1.0) for anything that persists for the whole fortnight.
DECAY_HOURS = (12, 48, 168)


def lead_basis(lead) -> np.ndarray:
    lead = np.asarray(lead, dtype=float)[:, None]
    return np.hstack([np.exp(-lead / np.array(DECAY_HOURS)), np.ones_like(lead)])


CLOUD_COVER = {'CLR': 0.0, 'SKC': 0.0, 'FEW': 0.2, 'SCT': 0.45, 'BKN': 0.75, 'OVC': 1.0, 'VV': 1.0}
# Iteration 4: weather groups that may hint at what comes next. 'temp' is iteration 3.
FEATURE_GROUPS = ('temp', 'pressure', 'humidity', 'wind', 'cloud')


def origin_state(hist: pd.DataFrame, anom: pd.Series, groups=('temp',)) -> pd.DataFrame:
    """For every hour t, weather summaries known just before t (i.e. up to t-1h).

    shift(1) is what makes these "known at the origin": the value at t never uses t.
    Works on positions, so `hist` and `anom` must be the same continuous hourly grid.
    Returns len(hist) + 1 rows: the extra last row is the state at the hour right after
    `hist` ends, i.e. at the real forecast origin.
    """
    def past(s): return pd.Series(np.append(np.asarray(s, dtype=float), np.nan)).shift(1)
    def recent(s, hours, min_periods=1): return past(s).rolling(hours, min_periods=min_periods).mean()
    f = {}
    if 'temp' in groups:            # how unusual the temperature has been
        f['anom_last3h'] = recent(anom, 3)
        f['anom_24h'] = recent(anom, 24, 18)
        f['anom_7d'] = recent(anom, 168, 120)
    if 'pressure' in groups:        # falling pressure: a front or storm approaching
        p = recent(hist.sea_level_pressure_hpa, 3)
        f['pressure'] = p
        f['pressure_change_24h'] = p - p.shift(24)
    if 'humidity' in groups:        # moist air keeps nights warm; dry air cools fast
        f['dew_point'] = recent(hist.dew_point_f, 3)
        f['dew_point_depression'] = recent(hist.temperature - hist.dew_point_f, 3)
    if 'wind' in groups:            # which way air is moving (north component < 0: from the north)
        f['wind_east'] = recent(hist.wind_east_ms, 6)
        f['wind_north'] = recent(hist.wind_north_ms, 6)
    if 'cloud' in groups:           # clouds cap daytime highs and keep nights warm; rain cools
        layers = hist[['skyc1', 'skyc2', 'skyc3']].apply(lambda c: c.map(CLOUD_COVER))
        f['cloud_cover'] = recent(layers.max(axis=1), 6)
        f['rain_24h'] = past(hist.precipitation_1h_inches).rolling(24, min_periods=1).sum()
    return pd.DataFrame(f)


def anomaly_design(state: np.ndarray, lead: np.ndarray) -> np.ndarray:
    """Each origin summary times each decay curve: lets every summary fade at its own rate."""
    basis = lead_basis(lead)
    return (state[:, :, None] * basis[:, None, :]).reshape(len(lead), -1)


def fit_anomaly_model(hist: pd.DataFrame, months=(8, 9, 10), alpha: float = 1.0,
                      groups=('temp',)):
    """Fit the anomaly regression on pseudo-forecasts inside `hist`.

    Every local midnight in `hist` within `months` acts as a past origin, paired with the
    anomalies of the following 336 hours. Hours that are not in `hist` (at/after the real
    origin) simply do not exist, so no training label can come from the forecast period.
    Returns (normal table, fitted model, origin state at the end of `hist`).
    """
    table = normal_table(hist)
    anom = hist.temperature - lookup(table, hist.local_doy, hist.local_hour)
    state = origin_state(hist, anom, groups)
    names = list(state.columns)

    is_origin = (hist.local_hour == 0) & hist.local_month.isin(months)
    pos = np.flatnonzero(is_origin.to_numpy())
    origins = state.iloc[pos]
    # Center every summary on its training-origin mean, so 0 means "typical" and the
    # fading curves shrink a departure from typical, not the raw level (e.g. 1015 hPa).
    # A missing weather reading then becomes 0 = typical; missing temperature history
    # drops the example instead.
    center = origins.mean()
    S = (origins - center)
    temp_cols = [c for c in names if c.startswith('anom_')]
    keep = S[temp_cols].notna().all(axis=1).to_numpy() if temp_cols else np.ones(len(S), bool)
    S, pos = S.fillna(0.0).to_numpy()[keep], pos[keep]

    padded = np.concatenate([anom.to_numpy(), np.full(HORIZON, np.nan)])
    y = sliding_window_view(padded, HORIZON)[pos].ravel()         # next 336 anomalies
    X_state = np.repeat(S, HORIZON, axis=0)
    lead = np.tile(np.arange(1, HORIZON + 1), len(pos))
    ok = ~np.isnan(y)

    model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    model.fit(anomaly_design(X_state[ok], lead[ok]), y[ok])
    model.state_names = names

    # Last row of `state` = summaries at the real origin, centered the same way.
    origin_now = (state.iloc[[-1]] - center).fillna(0.0).to_numpy()
    return table, model, origin_now


def anomaly_ridge(months=(8, 9, 10), alpha: float = 1.0, groups=('temp',)):
    """Return predict(hist, win): normal + ridge-predicted anomaly."""
    def predict(hist: pd.DataFrame, win: pd.DataFrame) -> np.ndarray:
        table, model, s = fit_anomaly_model(hist, months, alpha, groups)
        pred_anom = model.predict(anomaly_design(np.repeat(s, len(win), axis=0), win.lead))
        return lookup(table, win.local_doy, win.local_hour) + pred_anom
    return predict


# Iteration 5: locked after tuning on the 2021-2023 development origins only
# (scripts/tune_linear.py). Use with ev.evaluate(..., years=LOCKED['years']).
LOCKED = {'groups': FEATURE_GROUPS, 'alpha': 1e4, 'months': (8, 9, 10), 'years': 10}


def locked_model():
    return anomaly_ridge(LOCKED['months'], LOCKED['alpha'], LOCKED['groups'])
