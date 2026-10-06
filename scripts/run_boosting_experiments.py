"""Run the small, declared second-round boosting comparison on development only."""
from dataclasses import asdict
from pathlib import Path
import json
import sys

import pandas as pd

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from src.data_access import load_observations
from src import boosting_model as boosting
from src import evaluation as ev


def predictor(config):
    """Bind a configuration to the shared ``predict(hist, win)`` interface."""
    def run(hist, win):
        return boosting.predict(hist, win, config)
    return run


def evaluate_candidate(df, name, config, years):
    models = {'climatology': ev.climatology, name: predictor(config)}
    scores, predictions = ev.evaluate(df, models, ev.DEV_ORIGINS, years=years)
    candidate_scores = scores.loc[scores.model.eq(name)].copy()
    candidate_scores['history_years'] = years
    return candidate_scores, predictions.loc[predictions.model.eq(name)].copy()


def main():
    df = load_observations(root)
    candidates = [
        ('boost_10y_initial', boosting.BoostingConfig(), 10),
        ('boost_5y_initial', boosting.BoostingConfig(min_history_years=2), 5),
        ('boost_10y_no_dew_pressure',
         boosting.BoostingConfig(include_dew_point_pressure=False), 10),
        ('boost_10y_shallow',
         boosting.BoostingConfig(max_leaf_nodes=7), 10),
    ]

    all_scores, all_predictions, manifest = [], [], {}
    for name, config, years in candidates:
        print(f'Running {name} ...', flush=True)
        scores, predictions = evaluate_candidate(df, name, config, years)
        all_scores.append(scores)
        all_predictions.append(predictions)
        manifest[name] = {'history_years': years, **asdict(config)}

    scores = pd.concat(all_scores, ignore_index=True)
    predictions = pd.concat(all_predictions, ignore_index=True)
    summary = ev.summarize(scores)
    baseline_scores, _ = ev.evaluate(
        df, {'climatology_10y': ev.climatology}, ev.DEV_ORIGINS, years=10
    )
    summary = pd.concat([summary, ev.summarize(baseline_scores)])

    output = root / 'reports/models'
    scores.to_csv(output / 'boosting_iteration2_scores_by_origin.csv', index=False)
    summary.to_csv(output / 'boosting_iteration2_summary.csv')
    ev.save_predictions(
        predictions, output / 'boosting_iteration2_predictions.csv'
    )
    (output / 'boosting_iteration2_manifest.json').write_text(
        json.dumps(manifest, indent=2) + '\n'
    )
    print(summary.sort_values('MAE').to_string())


if __name__ == '__main__':
    main()
