"""Iteration 8: the 336-hour forecast issued at Sep 17, 2026 00:00 EDT.

Every model is refit on data strictly before the origin and makes one forecast that is
never updated. load_observations() refuses any observation at or after the origin.
"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.data_access import load_observations
from src import evaluation as ev
from src import linear_model as lm
from src import gfs_model as gm
from src import boosting_model as bm

out = root/'reports/final'
out.mkdir(parents=True, exist_ok=True)

df = load_observations(root)
gfs = gm.load_gfs(root)
origin = ev.FINAL_ORIGIN
hist = ev.history_before(df, origin, years=lm.LOCKED['years'])
boosting_hist = ev.history_before(df, origin, years=bm.SELECTED_HISTORY_YEARS)
win = ev.target_window(df, origin)
assert win.temperature.isna().all(), 'no observed truth may exist for the target window'
calendar = win.drop(columns='temperature')

models = {'station_ridge_f': lm.locked_model(), 'gfs_ridge_f': gm.gfs_ridge(gfs),
          'climatology_f': ev.climatology, 'raw_gfs_f': gm.raw_gfs(gfs)}
forecast = pd.DataFrame({
    'time_local': win.index.tz_convert(ev.NY).strftime('%Y-%m-%d %H:%M'),
    'time_utc': win.index.strftime('%Y-%m-%dT%H:%MZ'),
    'lead_hours': win.lead.to_numpy()})
for name, f in models.items():
    forecast[name] = np.round(f(hist, calendar), 1)
forecast['gradient_boosting_f'] = np.round(
    bm.predict_selected(boosting_hist, calendar), 1
)
forecast_columns = [*models, 'gradient_boosting_f']
# The team's submitted forecast, chosen from development/confirmation evidence
# before any September 2026 outcome was seen. The other columns are for comparison.
SUBMITTED = 'gfs_ridge_f'
forecast.insert(3, 'submitted_forecast_f', forecast[SUBMITTED])

# Checks on the deliverable itself.
assert len(forecast) == 336 and forecast.time_utc.is_unique
assert forecast.time_local.iloc[0] == '2026-09-17 00:00'
assert forecast.time_local.iloc[-1] == '2026-09-30 23:00'
assert not forecast[forecast_columns].isna().any().any()
assert hist.time.max() < origin and hist.observed_at.dropna().max() < origin
assert (boosting_hist.time.max() < origin and
        boosting_hist.observed_at.dropna().max() < origin)
assert gfs.loc[gfs.origin == origin, 'init'].max() < origin
forecast.to_csv(out/'final_forecast_336h.csv', index=False)

print(f'Origin {origin} | last observation used {hist.observed_at.max()} | '
      f'GFS run initialized {gfs.loc[gfs.origin == origin, "init"].max()}')
pd.set_option('display.width', 160)
daily = forecast.assign(date=forecast.time_local.str[:10]).groupby('date')[forecast_columns]
print('\nDaily min / max (°F):')
print(pd.concat({'min': daily.min(), 'max': daily.max()}, axis=1).round(0).to_string())
print('\nMean difference vs climatology (°F):')
print((forecast[forecast_columns].sub(forecast.climatology_f, axis=0)).mean().round(2).to_string())

t = pd.to_datetime(forecast.time_local)
fig, ax = plt.subplots(figsize=(13, 4.5))
ax.plot(t, forecast.climatology_f, color='0.6', lw=1, label='Climatology (10-yr normal)')
ax.plot(t, forecast.raw_gfs_f, color='tab:orange', lw=0.8, alpha=0.6, label='Raw GFS')
ax.plot(t, forecast.station_ridge_f, color='tab:blue', lw=1.4, label='Station ridge')
ax.plot(t, forecast.gfs_ridge_f, color='tab:red', lw=1.4, label='GFS ridge')
ax.plot(t, forecast.gradient_boosting_f, color='tab:green', lw=1.2,
        label='Gradient boosting')
recent = hist.loc[hist.time >= origin - pd.Timedelta(days=3)]
ax.plot(recent.time.dt.tz_convert(ev.NY).dt.tz_localize(None), recent.temperature,
        color='k', lw=1.2, label='Observed (before origin)')
ax.axvline(pd.Timestamp('2026-09-17'), color='k', ls='--', lw=0.8)
ax.set_ylabel('Temperature (°F)')
ax.set_title('RDU hourly temperature forecast, issued Sep 17 2026 00:00 EDT')
ax.legend(loc='lower left', fontsize=8, ncol=3)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(out/'final_forecast_336h.png', dpi=150)
print(f'\nWrote {out/"final_forecast_336h.csv"} and .png')
