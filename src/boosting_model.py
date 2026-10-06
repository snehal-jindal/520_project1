"""Leakage-safe gradient boosting for fixed-origin RDU temperature forecasts.

The fitted target is the departure from a training-only hourly climatology.  The
public prediction returned by this module is still RDU temperature in degrees F.
Every training example is built from a simulated 336-hour forecast whose weather
summaries use observations strictly before that simulated origin.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from . import evaluation as ev


@dataclass(frozen=True)
class BoostingConfig:
    """Small, deliberately conservative model configuration."""

    min_history_years: int = 3
    loss: str = 'squared_error'
    max_iter: int = 200
    learning_rate: float = 0.05
    max_leaf_nodes: int = 15
    min_samples_leaf: int = 40
    l2_regularization: float = 1.0
    correction_decay_hours: float = 72.0
    include_dew_point_pressure: bool = True
    include_enhanced_origin_features: bool = False
    include_linear_aligned_features: bool = False
    training_origin_stride_days: int | None = None
    random_state: int = 520


# Locked after the declared development-only comparison. Five years improved
# average MAE and year-to-year consistency; two years of warm-up history leaves
# three years in which to form simulated fixed-origin training forecasts.
SELECTED_HISTORY_YEARS = 5
SELECTED_CONFIG = BoostingConfig(
    min_history_years=2,
    correction_decay_hours=120.0,
)
SELECTED_ALIGNED_CONFIG = BoostingConfig(
    min_history_years=2,
    correction_decay_hours=120.0,
    include_linear_aligned_features=True,
)
SELECTED_ALIGNED_WEIGHT = 0.5


FEATURE_COLUMNS = [
    'climatology_f',
    'hour_sin',
    'hour_cos',
    'doy_sin',
    'doy_cos',
    'lead',
    'lead_fraction',
    'origin_last_departure_f',
    'origin_24h_departure_f',
    'origin_7d_departure_f',
    'origin_dew_point_f',
    'origin_pressure_hpa',
    'recent_same_hour_departure_f',
    'origin_24h_temperature_range_f',
    'origin_pressure_change_6h_hpa',
]

ALIGNED_STATE_COLUMNS = [
    'origin_3h_departure_f',
    'origin_pressure_change_24h_hpa',
    'origin_dew_point_depression_f',
    'origin_wind_east_6h_ms',
    'origin_wind_north_6h_ms',
    'origin_cloud_cover_6h',
    'origin_rain_24h_inches',
]
ALIGNED_DECAY_HOURS = (12, 48, 168)
for _state_name in ALIGNED_STATE_COLUMNS:
    FEATURE_COLUMNS.append(_state_name)
    FEATURE_COLUMNS.extend(
        f'{_state_name}_decay_{hours}h' for hours in ALIGNED_DECAY_HOURS
    )


def feature_columns(config: BoostingConfig) -> list[str]:
    """Feature names selected by a recorded model configuration."""
    selected = list(FEATURE_COLUMNS)
    if not config.include_dew_point_pressure:
        selected = [name for name in selected
                    if name not in {'origin_dew_point_f', 'origin_pressure_hpa'}]
    if not config.include_enhanced_origin_features:
        selected = [name for name in selected if name not in {
            'recent_same_hour_departure_f',
            'origin_24h_temperature_range_f',
            'origin_pressure_change_6h_hpa',
        }]
    if not config.include_linear_aligned_features:
        selected = [name for name in selected if name not in {
            state_name for state_name in ALIGNED_STATE_COLUMNS
        } and not any(
            name.startswith(f'{state_name}_decay_')
            for state_name in ALIGNED_STATE_COLUMNS
        )]
    return selected


def _calendar_features(win: pd.DataFrame, climatology_f) -> pd.DataFrame:
    """Features known for the complete target window at forecast issue time."""
    hour_angle = 2 * np.pi * win.local_hour.to_numpy() / 24
    doy_angle = 2 * np.pi * (win.local_doy.to_numpy() - 1) / 365.25
    lead = win.lead.to_numpy(dtype=float)
    return pd.DataFrame({
        'climatology_f': np.asarray(climatology_f, dtype=float),
        'hour_sin': np.sin(hour_angle),
        'hour_cos': np.cos(hour_angle),
        'doy_sin': np.sin(doy_angle),
        'doy_cos': np.cos(doy_angle),
        'lead': lead,
        'lead_fraction': (lead - 1) / (ev.HORIZON - 1),
    }, index=win.index)


def _reference_for_rows(reference_hist: pd.DataFrame, rows: pd.DataFrame) -> np.ndarray:
    """Training-only seasonal/hourly reference for already-observed rows."""
    if rows.empty:
        return np.array([], dtype=float)
    request = pd.DataFrame({
        'local_hour': rows.local_hour.to_numpy(),
        'local_doy': rows.local_doy.to_numpy(),
    }, index=rows.index)
    return ev.climatology(reference_hist, request)


def _origin_state(hist: pd.DataFrame, origin: pd.Timestamp) -> dict:
    """Summarize weather known at ``origin`` without using target-window data."""
    prior = hist.loc[hist.time.lt(origin)].copy()
    if prior.empty:
        raise ValueError('No history is available before the simulated origin.')

    usable = prior.loc[prior.temperature.notna()]
    if usable.empty:
        raise ValueError('No usable temperature is available before the origin.')

    # Keep the recent week out of the reference used to measure that week's
    # departure. This avoids allowing a value to help define its own normal.
    reference_hist = prior.loc[prior.time.lt(origin - pd.Timedelta(days=7))]
    if reference_hist.temperature.notna().sum() == 0:
        reference_hist = prior

    recent_7d = prior.loc[prior.time.ge(origin - pd.Timedelta(days=7))]
    recent_24h = prior.loc[prior.time.ge(origin - pd.Timedelta(hours=24))]
    recent_6h = prior.loc[prior.time.ge(origin - pd.Timedelta(hours=6))]
    recent_3h = prior.loc[prior.time.ge(origin - pd.Timedelta(hours=3))]

    def mean_departure(rows: pd.DataFrame) -> float:
        rows = rows.loc[rows.temperature.notna()]
        if rows.empty:
            return np.nan
        reference = _reference_for_rows(reference_hist, rows)
        return float(np.nanmean(rows.temperature.to_numpy(dtype=float) - reference))

    last = usable.iloc[-1]
    last_frame = usable.iloc[[-1]]
    last_reference = _reference_for_rows(reference_hist, last_frame)[0]

    # Dew point and pressure are taken from the latest report where each exists.
    dew = prior.dew_point_f.dropna()
    pressure = prior.sea_level_pressure_hpa.dropna()
    recent_temperature = recent_24h.temperature.dropna()
    recent_pressure = recent_24h.loc[
        recent_24h.time.ge(origin - pd.Timedelta(hours=6)),
        'sea_level_pressure_hpa',
    ].dropna()
    pressure_24h = recent_24h.sea_level_pressure_hpa.dropna()
    latest_temp = float(last.temperature)
    latest_dew = float(dew.iloc[-1]) if not dew.empty else np.nan
    wind_east = recent_6h.wind_east_ms.dropna()
    wind_north = recent_6h.wind_north_ms.dropna()
    cloud_mapping = {
        'CLR': 0.0, 'SKC': 0.0, 'FEW': 0.2, 'SCT': 0.45,
        'BKN': 0.75, 'OVC': 1.0, 'VV': 1.0,
    }
    cloud_layers = recent_6h[['skyc1', 'skyc2', 'skyc3']].apply(
        lambda column: column.map(cloud_mapping)
    )
    cloud_cover = cloud_layers.max(axis=1).dropna()
    rain = recent_24h.precipitation_1h_inches.dropna()
    return {
        'origin_last_departure_f': float(last.temperature - last_reference),
        'origin_24h_departure_f': mean_departure(recent_24h),
        'origin_7d_departure_f': mean_departure(recent_7d),
        'origin_dew_point_f': float(dew.iloc[-1]) if not dew.empty else np.nan,
        'origin_pressure_hpa': float(pressure.iloc[-1]) if not pressure.empty else np.nan,
        'origin_24h_temperature_range_f': (
            float(recent_temperature.max() - recent_temperature.min())
            if not recent_temperature.empty else np.nan
        ),
        'origin_pressure_change_6h_hpa': (
            float(recent_pressure.iloc[-1] - recent_pressure.iloc[0])
            if len(recent_pressure) >= 2 else np.nan
        ),
        'origin_3h_departure_f': mean_departure(recent_3h),
        'origin_pressure_change_24h_hpa': (
            float(pressure_24h.iloc[-1] - pressure_24h.iloc[0])
            if len(pressure_24h) >= 2 else np.nan
        ),
        'origin_dew_point_depression_f': latest_temp - latest_dew,
        'origin_wind_east_6h_ms': (
            float(wind_east.mean()) if not wind_east.empty else np.nan
        ),
        'origin_wind_north_6h_ms': (
            float(wind_north.mean()) if not wind_north.empty else np.nan
        ),
        'origin_cloud_cover_6h': (
            float(cloud_cover.mean()) if not cloud_cover.empty else np.nan
        ),
        'origin_rain_24h_inches': float(rain.sum()) if not rain.empty else np.nan,
    }


def _recent_same_hour_departure(hist: pd.DataFrame, win: pd.DataFrame,
                                climatology_f, origin: pd.Timestamp) -> np.ndarray:
    """Yesterday's same-hour temperature departure, repeated across the horizon."""
    recent = hist.loc[
        hist.time.ge(origin - pd.Timedelta(hours=24)) & hist.temperature.notna()
    ]
    latest_by_hour = recent.groupby('local_hour').temperature.last().to_dict()
    recent_temperature = np.array(
        [latest_by_hour.get(hour, np.nan) for hour in win.local_hour], dtype=float
    )
    return recent_temperature - np.asarray(climatology_f, dtype=float)


def features_for_origin(hist: pd.DataFrame, win: pd.DataFrame, origin: pd.Timestamp):
    """Return target-window features and the climatology used as model offset."""
    permitted = hist.loc[hist.time.lt(origin)]
    if permitted.time.ge(origin).any():
        raise AssertionError('Target-window observations leaked into features.')
    climatology_f = ev.climatology(permitted, win)
    features = _calendar_features(win, climatology_f)
    state = _origin_state(permitted, origin)
    for name, value in state.items():
        features[name] = value
    lead = win.lead.to_numpy(dtype=float)
    for state_name in ALIGNED_STATE_COLUMNS:
        for hours in ALIGNED_DECAY_HOURS:
            features[f'{state_name}_decay_{hours}h'] = (
                state[state_name] * np.exp(-lead / hours)
            )
    features['recent_same_hour_departure_f'] = _recent_same_hour_departure(
        permitted, win, climatology_f, origin
    )
    return features[FEATURE_COLUMNS], np.asarray(climatology_f, dtype=float)


def _candidate_training_origins(hist: pd.DataFrame, config: BoostingConfig):
    """Late-summer/autumn practice origins fully contained in ``hist``."""
    first_time = hist.time.min()
    last_time = hist.time.max()
    first_year = int(first_time.tz_convert(ev.NY).year)
    last_year = int(last_time.tz_convert(ev.NY).year)
    if config.training_origin_stride_days is None:
        candidates = ev.origins(range(first_year, last_year + 1))
    else:
        if config.training_origin_stride_days < 1:
            raise ValueError('training_origin_stride_days must be positive.')
        candidates = []
        for year in range(first_year, last_year + 1):
            local = pd.date_range(
                f'{year}-08-01', f'{year}-10-17',
                freq=f'{config.training_origin_stride_days}D', tz=ev.NY,
            )
            candidates.extend(local.tz_convert('UTC'))
    minimum = first_time + pd.DateOffset(years=config.min_history_years)
    maximum = last_time - pd.Timedelta(hours=ev.HORIZON - 1)
    return [origin for origin in candidates if minimum <= origin <= maximum]


def build_training_table(hist: pd.DataFrame, config: BoostingConfig):
    """Construct fixed-origin examples using only data contained in ``hist``."""
    feature_blocks, targets, origin_ids = [], [], []
    for origin in _candidate_training_origins(hist, config):
        win = ev.target_window(hist, origin)
        before = hist.loc[hist.time.lt(origin)]
        features, climatology_f = features_for_origin(before, win, origin)
        residual = win.temperature.to_numpy(dtype=float) - climatology_f
        valid = np.isfinite(residual) & np.isfinite(climatology_f)
        if valid.any():
            feature_blocks.append(features.loc[valid])
            targets.append(residual[valid])
            origin_ids.extend([origin] * int(valid.sum()))

    if not feature_blocks:
        raise ValueError('No complete simulated forecast origins are available for training.')
    return (
        pd.concat(feature_blocks, ignore_index=True),
        np.concatenate(targets),
        pd.Series(origin_ids, name='training_origin_utc'),
    )


def fit_model(hist: pd.DataFrame, config: BoostingConfig = BoostingConfig()):
    """Fit one conservative boosted-tree residual model."""
    x_train, y_train, training_origins = build_training_table(hist, config)
    model = HistGradientBoostingRegressor(
        loss=config.loss,
        max_iter=config.max_iter,
        learning_rate=config.learning_rate,
        max_leaf_nodes=config.max_leaf_nodes,
        min_samples_leaf=config.min_samples_leaf,
        l2_regularization=config.l2_regularization,
        early_stopping=False,
        random_state=config.random_state,
    )
    selected = feature_columns(config)
    model.fit(x_train[selected], y_train)
    model.training_origins_ = training_origins
    model.feature_names_ = tuple(selected)
    return model


def predict(hist: pd.DataFrame, win: pd.DataFrame,
            config: BoostingConfig = BoostingConfig()) -> np.ndarray:
    """Return 336 RDU temperature forecasts in degrees Fahrenheit."""
    origin = win.index[0]
    if hist.time.ge(origin).any():
        raise AssertionError('History must end strictly before the forecast origin.')
    model = fit_model(hist, config)
    features, climatology_f = features_for_origin(hist, win, origin)
    # Recent weather helps most near the issue time. Shrink the learned anomaly
    # smoothly toward the stable climatology as the two-week horizon increases.
    # The decay was selected from a small declared development-only set.
    decay = np.exp(-(win.lead.to_numpy(dtype=float) - 1) /
                   config.correction_decay_hours)
    return climatology_f + decay * model.predict(features[list(model.feature_names_)])


def predict_selected(hist: pd.DataFrame, win: pd.DataFrame) -> np.ndarray:
    """Average the stable and weather-aligned boosted-tree configurations."""
    stable = predict(hist, win, SELECTED_CONFIG)
    aligned = predict(hist, win, SELECTED_ALIGNED_CONFIG)
    return ((1 - SELECTED_ALIGNED_WEIGHT) * stable +
            SELECTED_ALIGNED_WEIGHT * aligned)
