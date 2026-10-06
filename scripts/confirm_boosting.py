"""Reproduce the already locked boosting confirmation; never tune from these scores."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_access import load_observations
from src import evaluation as ev, boosting_model as bm


def main():
    models = {**ev.BASELINES, 'gradient_boosting_locked': bm.predict_selected}
    scores, predictions = ev.evaluate(load_observations(ROOT), models,
                                     ev.CONFIRM_ORIGINS, years=bm.SELECTED_HISTORY_YEARS)
    out = ROOT/'reports/models'
    scores.to_csv(out/'boosting_confirm_scores.csv', index=False)
    ev.save_predictions(predictions, out/'boosting_confirm_predictions.csv')
    print(ev.summarize(scores).to_string())


if __name__ == '__main__':
    main()
