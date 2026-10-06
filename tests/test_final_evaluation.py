"""Protect frozen forecasts, exact target alignment and evaluation-only actuals."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from src import final_evaluation as fe
from src.data_access import load_observations

ROOT = Path(__file__).resolve().parents[1]


class FinalEvaluationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forecast = pd.read_csv(ROOT/'reports/final/final_forecast_336h.csv')
        cls.actual = pd.read_csv(ROOT/'reports/final/iem_rdu_final_actuals.csv', dtype={'tmpf': str})

    def test_missing_shifted_or_nonfinite_predictions_rejected(self):
        cases = [self.forecast.iloc[:-1].copy(), self.forecast.copy(), self.forecast.copy()]
        cases[1].loc[0, 'time_utc'] = '2026-09-17T05:00Z'
        cases[2].loc[0, 'station_ridge_f'] = np.inf
        for bad in cases:
            with self.assertRaises(ValueError):
                fe.validate_forecast(bad)

    def test_changed_forecast_cannot_be_scored_as_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'forecast.csv'
            bad = self.forecast.copy()
            bad.loc[0, 'gfs_ridge_f'] += 1
            bad.to_csv(p, index=False)
            with self.assertRaises(ValueError):
                fe.verify_frozen_forecast(p, ROOT/'docs/FORECAST_RECORD.json')

    def test_actual_matching_preserves_all_336_and_rejects_missing(self):
        forecast = fe.validate_forecast(self.forecast)
        joined = fe.join_actuals(forecast, self.actual)
        self.assertEqual(len(joined), 336)
        self.assertTrue(np.isfinite(joined.actual_f).all())
        missing = self.actual.copy()
        missing.loc[0, 'tmpf'] = 'M'
        with self.assertRaises(ValueError):
            fe.join_actuals(forecast, missing)

    def test_final_observation_in_training_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root/'data/pre_eda/prepared/rdu_all_months_hourly_2011_to_cutoff.csv'
            p.parent.mkdir(parents=True)
            pd.DataFrame({'hour_label_utc': ['2026-09-17T04:00:00Z'],
                          'observation_time_utc': ['2026-09-17T04:51:00Z'],
                          'station': ['RDU']}).to_csv(p, index=False)
            with self.assertRaisesRegex(ValueError, 'Final-test observations are forbidden'):
                load_observations(root)

    def test_final_snapshot_and_training_paths_are_distinct(self):
        manifest = json.loads((ROOT/'reports/final/final_observation_manifest.json').read_text())
        self.assertTrue(manifest['output_file'].startswith('reports/final/'))
        history = load_observations(ROOT)
        self.assertLess(history.observed_at.dropna().max(), fe.EXPECTED_TIMES[0])


if __name__ == '__main__':
    unittest.main()
