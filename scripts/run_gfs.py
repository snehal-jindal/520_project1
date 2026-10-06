"""Iteration 6: score raw GFS, the GFS-corrected ridge and the station models on 2026 origins.

Rolling evaluation: each origin is forecast using only GFS runs whose windows ended
before it. Origins without enough earlier runs are skipped. August is reported apart,
because it is closest to the September target and was the reserved confirmation set.
"""
import sys
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.data_access import load_observations
from src import evaluation as ev
from src import linear_model as lm
from src import gfs_model as gm

df = load_observations(root)
gfs = gm.load_gfs(root)
past_runs = [o for o in gm.gfs_origins(gfs) if o + pd.Timedelta(hours=ev.HORIZON) <= ev.FINAL_ORIGIN]
test_origins = past_runs[8:]   # each has >= 6 complete earlier runs to train on

models = {'climatology': ev.climatology,
          'station ridge (locked)': lm.locked_model(),
          'raw GFS': gm.raw_gfs(gfs),
          'GFS ridge': gm.gfs_ridge(gfs)}
scores, preds = ev.evaluate(df, models, test_origins, years=lm.LOCKED['years'])
ev.save_predictions(preds, root/'reports/models/gfs_2026_predictions.csv')

pd.set_option('display.width', 160, 'display.precision', 2)
august = scores.origin.map(lambda d: d.month == 8)
for label, part in (('May-Jul origins', scores[~august]), ('Aug origins', scores[august])):
    print(f'\n{label} ({part.origin.nunique()} forecasts):')
    print(ev.summarize(part).to_string())
wins = scores.pivot(index='origin', columns='model', values='MAE')
print('\nPer-origin MAE:')
print(wins.to_string())
