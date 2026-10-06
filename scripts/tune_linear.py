"""Iteration 5: compare settings of the anomaly ridge on the development origins only.

Every configuration is scored on the same 21 forecasts. Differences are reported per
origin against a reference configuration (paired), because the year-to-year weather
swings are much larger than the differences between settings.
"""
import itertools
import sys
from pathlib import Path
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.data_access import load_observations
from src import evaluation as ev
from src import linear_model as lm

FEATURES = {'pressure': ('temp', 'pressure'), 'all': lm.FEATURE_GROUPS}
ALPHAS = (1, 1e3, 1e4, 1e5)
YEARS = (5, 10)
MONTHS = {'Sep': (9,), 'Aug-Oct': (8, 9, 10), 'Jul-Nov': (7, 8, 9, 10, 11)}
REFERENCE = 'all | a=1 | 10y | Aug-Oct'   # the iteration 4 model

df = load_observations(root)
scores = []
for years in YEARS:
    models = {f'{f} | a={a:g} | {years}y | {m}': lm.anomaly_ridge(MONTHS[m], a, FEATURES[f])
              for f, a, m in itertools.product(FEATURES, ALPHAS, MONTHS)}
    models['climatology'] = ev.climatology
    s, _ = ev.evaluate(df, models, ev.DEV_ORIGINS, years=years)
    scores.append(s.assign(model=s.model.where(s.model != 'climatology', f'climatology {years}y')))
scores = pd.concat(scores)

summary = ev.summarize(scores)[['MAE', 'RMSE', 'bias', 'MAE d1-3', 'MAE d4-7', 'MAE d8-14']]
by_origin = scores.pivot(index='origin', columns='model', values='MAE')
diff = by_origin.sub(by_origin[REFERENCE], axis=0)
summary['vs ref'] = diff.mean()
summary['SE'] = diff.std() / np.sqrt(len(diff))       # rough: origins overlap in time
summary['wins vs ref'] = (diff < 0).sum()
summary = summary.sort_values('MAE')
summary.to_csv(root/'reports/models/tuning_linear.csv')

pd.set_option('display.width', 200, 'display.precision', 2, 'display.max_rows', 100)
print(f'Reference: {REFERENCE}. "vs ref" < 0 means better; SE = standard error of that difference.\n')
print(summary.to_string())
