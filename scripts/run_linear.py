"""Score baselines and linear regression variants on the development origins."""
import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.data_access import load_observations
from src import evaluation as ev
from src import linear_model as lm

models = {**ev.BASELINES,
          # Iteration 2: calendar only. How many daily harmonics does the curve need?
          'ridge_cal_h2': lm.calendar_ridge(n_harmonics=2),
          # Iteration 3: normal + anomaly persistence that fades with lead time.
          'ridge_anom': lm.anomaly_ridge(),
          # Iteration 4: add one weather group at a time, then all of them.
          **{f'ridge_anom+{g}': lm.anomaly_ridge(groups=('temp', g))
             for g in lm.FEATURE_GROUPS[1:]},
          'ridge_anom+all': lm.anomaly_ridge(groups=lm.FEATURE_GROUPS),
          # Iteration 5: the locked configuration (see scripts/tune_linear.py).
          'ridge_locked': lm.locked_model()}

df = load_observations(root)
scores, preds = ev.evaluate(df, models, ev.DEV_ORIGINS, years=lm.LOCKED['years'])
ev.save_predictions(preds, root/'reports/models/dev_predictions_linear.csv')

pd.set_option('display.width', 160, 'display.precision', 2)
print(f'Mean over {len(ev.DEV_ORIGINS)} development origins:')
print(ev.summarize(scores).to_string())
wins = scores.pivot(index='origin', columns='model', values='MAE')
print()
for m in [c for c in wins.columns if c.startswith('ridge')]:
    print(f'{m:<20} beats climatology on {int((wins[m] < wins.climatology).sum()):>2} of {len(wins)}'
          f' origins, beats ridge_anom on {int((wins[m] < wins.ridge_anom).sum()):>2}')
