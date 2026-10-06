"""Run the initial gradient-boosting candidate on development origins only."""
from dataclasses import asdict
from pathlib import Path
import json
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from src.data_access import load_observations
from src import boosting_model as boosting
from src import evaluation as ev


def main():
    df = load_observations(root)
    models = {**ev.BASELINES, 'gradient_boosting': boosting.predict_selected}
    scores, predictions = ev.evaluate(
        df, models, ev.DEV_ORIGINS, years=boosting.SELECTED_HISTORY_YEARS
    )
    summary = ev.summarize(scores)

    output = root / 'reports/models'
    output.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output / 'boosting_dev_scores_by_origin.csv', index=False)
    summary.to_csv(output / 'boosting_dev_summary.csv')
    ev.save_predictions(predictions, output / 'boosting_dev_predictions.csv')
    (output / 'boosting_selected_configuration.json').write_text(
        json.dumps({
            'history_years': boosting.SELECTED_HISTORY_YEARS,
            'stable_component': asdict(boosting.SELECTED_CONFIG),
            'weather_aligned_component': asdict(
                boosting.SELECTED_ALIGNED_CONFIG
            ),
            'weather_aligned_weight': boosting.SELECTED_ALIGNED_WEIGHT,
        }, indent=2) + '\n'
    )
    print(summary.to_string())


if __name__ == '__main__':
    main()
