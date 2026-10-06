"""Iteration 7: one-time confirmation of the locked station model on 2024-2025 origins.

Run only after LOCKED in src/linear_model.py is final. Do not tune anything based on
this output; that would turn the confirmation set into another development set.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.data_access import load_observations
from src import evaluation as ev
from src import linear_model as lm

models = {**ev.BASELINES, 'station ridge (locked)': lm.locked_model()}
df = load_observations(root)
scores, preds = ev.evaluate(df, models, ev.CONFIRM_ORIGINS, years=lm.LOCKED['years'])
ev.save_predictions(preds, root/'reports/models/confirm_predictions_linear.csv')
scores.to_csv(root/'reports/models/confirm_scores_linear.csv', index=False)

pd.set_option('display.width', 160, 'display.precision', 2)
print(f'Locked config: {lm.LOCKED}')
print(f'\nMean over {len(ev.CONFIRM_ORIGINS)} confirmation origins (2024-2025):')
print(ev.summarize(scores).to_string())
mae = scores.pivot(index='origin', columns='model', values='MAE')
diff = mae['station ridge (locked)'] - mae.climatology
print(f'\nRidge minus climatology MAE: {diff.mean():+.2f} (SE {diff.std() / np.sqrt(len(diff)):.2f}),'
      f' ridge better on {int((diff < 0).sum())} of {len(diff)} origins')
print('\nPer-origin MAE:')
print(mae.to_string())
