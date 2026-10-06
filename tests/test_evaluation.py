"""Leakage checks for the shared evaluation harness and every model run through it."""
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from src.data_access import load_observations
from src import evaluation as ev
from src import linear_model as lm
from src import gfs_model as gm

ROOT = Path(__file__).resolve().parents[1]
MODELS = {**ev.BASELINES, 'ridge_cal': lm.calendar_ridge(), 'ridge_anom': lm.anomaly_ridge(),
          'ridge_anom+all': lm.anomaly_ridge(groups=lm.FEATURE_GROUPS)}


class EvaluationLeakage(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.df = load_observations(ROOT)

    def test_future_data_cannot_change_predictions(self):
        """Replace every temperature at/after the origin with noise: predictions must not move."""
        for origin in (ev.DEV_ORIGINS[0], ev.DEV_ORIGINS[-1]):
            noisy = self.df.copy()
            after = noisy.time >= origin
            noisy.loc[after, 'temperature'] = np.random.default_rng(0).uniform(-100, 200, after.sum())
            for name, f in MODELS.items():
                with self.subTest(origin=origin, model=name):
                    a = f(ev.history_before(self.df, origin),
                          ev.target_window(self.df, origin).drop(columns='temperature'))
                    b = f(ev.history_before(noisy, origin),
                          ev.target_window(noisy, origin).drop(columns='temperature'))
                    np.testing.assert_allclose(a, b)

    def test_gfs_model_uses_only_the_past(self):
        """Same noise test for the GFS ridge, at an August 2026 origin."""
        gfs = gm.load_gfs(ROOT)
        origin = pd.Timestamp('2026-08-28T04:00:00Z')
        noisy = self.df.copy()
        after = noisy.time >= origin
        noisy.loc[after, 'temperature'] = np.random.default_rng(0).uniform(-100, 200, after.sum())
        f = gm.gfs_ridge(gfs)
        a = f(ev.history_before(self.df, origin), ev.target_window(self.df, origin).drop(columns='temperature'))
        b = f(ev.history_before(noisy, origin), ev.target_window(noisy, origin).drop(columns='temperature'))
        self.assertFalse(np.isnan(a).any())
        np.testing.assert_allclose(a, b)

    def test_origin_state_uses_only_earlier_hours(self):
        """Training features at hour t must not change when hour t or later changes.

        The noise test above cannot catch this: it only scrambles data after the real
        origin, while pseudo-origins live inside the history.
        """
        hist = ev.history_before(self.df, ev.DEV_ORIGINS[0]).iloc[-2000:].copy()
        anom = hist.temperature - hist.temperature.mean()
        before = lm.origin_state(hist, anom, lm.FEATURE_GROUPS)
        t = 1500
        hist.iloc[t:, hist.columns.get_indexer(['temperature', 'dew_point_f',
                                                'sea_level_pressure_hpa'])] += 50
        anom.iloc[t:] += 50
        after = lm.origin_state(hist, anom, lm.FEATURE_GROUPS)
        pd.testing.assert_frame_equal(before.iloc[:t + 1], after.iloc[:t + 1])
        self.assertFalse(before.iloc[t + 1:].equals(after.iloc[t + 1:]))

    def test_models_never_receive_target_temperatures(self):
        seen = []
        ev.evaluate(self.df, {'spy': lambda hist, win: seen.append(win) or np.zeros(len(win))},
                    ev.DEV_ORIGINS[:1])
        self.assertNotIn('temperature', seen[0].columns)

    def test_window_is_336_hours_from_local_midnight(self):
        for origin in ev.DEV_ORIGINS + ev.CONFIRM_ORIGINS:
            win = ev.target_window(self.df, origin)
            self.assertEqual(len(win), 336)
            self.assertEqual(win.local_hour.iloc[0], 0)


if __name__ == '__main__':
    unittest.main()
