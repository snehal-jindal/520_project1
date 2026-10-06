"""Structural and leakage checks for the nonlinear forecasting model."""
import unittest
from pathlib import Path

import numpy as np

from src.data_access import load_observations
from src import boosting_model as boosting
from src import evaluation as ev


ROOT = Path(__file__).resolve().parents[1]


class BoostingModelContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_observations(ROOT)
        cls.origin = ev.DEV_ORIGINS[0]
        cls.hist = ev.history_before(cls.df, cls.origin)
        cls.win = ev.target_window(cls.df, cls.origin)

    def test_features_have_expected_shape_and_no_future_rows(self):
        features, climatology = boosting.features_for_origin(
            self.hist, self.win, self.origin
        )
        self.assertEqual(features.shape, (ev.HORIZON, len(boosting.FEATURE_COLUMNS)))
        self.assertEqual(len(climatology), ev.HORIZON)
        self.assertTrue(self.hist.time.lt(self.origin).all())

    def test_training_origins_end_before_evaluation_origin(self):
        _, _, origins = boosting.build_training_table(
            self.hist, boosting.BoostingConfig()
        )
        self.assertTrue(origins.lt(self.origin).all())
        self.assertGreater(origins.nunique(), 1)

    def test_predict_returns_finite_336_hour_temperature_forecast(self):
        config = boosting.BoostingConfig(max_iter=2)
        prediction = boosting.predict(self.hist, self.win, config)
        self.assertEqual(prediction.shape, (ev.HORIZON,))
        self.assertTrue(np.isfinite(prediction).all())

    def test_recent_weather_correction_decays_with_lead(self):
        config = boosting.BoostingConfig()
        lead = self.win.lead.to_numpy(dtype=float)
        decay = np.exp(-(lead - 1) / config.correction_decay_hours)
        self.assertEqual(decay[0], 1.0)
        self.assertLess(decay[-1], 0.01)
        self.assertTrue((np.diff(decay) < 0).all())

    def test_optional_weather_fields_are_recorded_and_removed(self):
        full = boosting.feature_columns(boosting.BoostingConfig())
        reduced = boosting.feature_columns(
            boosting.BoostingConfig(include_dew_point_pressure=False)
        )
        self.assertIn('origin_dew_point_f', full)
        self.assertIn('origin_pressure_hpa', full)
        self.assertNotIn('origin_dew_point_f', reduced)
        self.assertNotIn('origin_pressure_hpa', reduced)

    def test_enhanced_origin_features_are_opt_in(self):
        ordinary = boosting.feature_columns(boosting.BoostingConfig())
        enhanced = boosting.feature_columns(
            boosting.BoostingConfig(include_enhanced_origin_features=True)
        )
        additions = {
            'recent_same_hour_departure_f',
            'origin_24h_temperature_range_f',
            'origin_pressure_change_6h_hpa',
        }
        self.assertTrue(additions.isdisjoint(ordinary))
        self.assertTrue(additions.issubset(enhanced))

    def test_linear_aligned_weather_and_decay_features_are_opt_in(self):
        ordinary = boosting.feature_columns(boosting.BoostingConfig())
        aligned = boosting.feature_columns(
            boosting.BoostingConfig(include_linear_aligned_features=True)
        )
        expected = {
            'origin_3h_departure_f',
            'origin_pressure_change_24h_hpa',
            'origin_dew_point_depression_f',
            'origin_wind_north_6h_ms_decay_48h',
            'origin_cloud_cover_6h_decay_168h',
            'origin_rain_24h_inches_decay_12h',
        }
        self.assertTrue(expected.isdisjoint(ordinary))
        self.assertTrue(expected.issubset(aligned))

    def test_selected_configuration_is_the_five_year_candidate(self):
        self.assertEqual(boosting.SELECTED_HISTORY_YEARS, 5)
        self.assertEqual(boosting.SELECTED_CONFIG.min_history_years, 2)
        self.assertEqual(boosting.SELECTED_CONFIG.correction_decay_hours, 120.0)
        self.assertTrue(boosting.SELECTED_CONFIG.include_dew_point_pressure)
        self.assertTrue(
            boosting.SELECTED_ALIGNED_CONFIG.include_linear_aligned_features
        )
        self.assertEqual(boosting.SELECTED_ALIGNED_WEIGHT, 0.5)

    def test_loss_is_explicitly_recorded(self):
        self.assertEqual(boosting.BoostingConfig().loss, 'squared_error')
        self.assertEqual(
            boosting.BoostingConfig(loss='absolute_error').loss,
            'absolute_error',
        )

    def test_denser_training_origins_are_opt_in(self):
        ordinary = boosting._candidate_training_origins(
            self.hist, boosting.BoostingConfig()
        )
        weekly = boosting._candidate_training_origins(
            self.hist,
            boosting.BoostingConfig(training_origin_stride_days=7),
        )
        every_three_days = boosting._candidate_training_origins(
            self.hist,
            boosting.BoostingConfig(training_origin_stride_days=3),
        )
        self.assertGreater(len(weekly), len(ordinary))
        self.assertGreater(len(every_three_days), len(weekly))
        self.assertTrue(all(origin < self.origin for origin in every_three_days))


if __name__ == '__main__':
    unittest.main()
