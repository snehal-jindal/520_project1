"""Checks for forecast leakage and timestamp semantics, not model accuracy."""
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from src.data_access import *
from src.eda import gfs_calibration_pairs
ROOT=Path(__file__).resolve().parents[1]
class ForecastContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.df=load_observations(ROOT)
    def test_final_truth_excluded(self):
        self.assertTrue(self.df.time.lt(FINAL_ORIGIN).all())
        self.assertTrue(self.df.observed_at.dropna().lt(FINAL_ORIGIN).all())
    def test_first_origin_boundary(self):
        core=training_eda_scope(self.df)
        self.assertEqual(core.time.max(),EDA_ORIGIN-pd.Timedelta(hours=1))
        self.assertTrue(core.observed_at.dropna().lt(EDA_ORIGIN).all())
    def test_elapsed_lag_does_not_bridge_a_missing_hour(self):
        t=pd.date_range('2020-01-01',periods=6,freq='h',tz='UTC')
        s=pd.Series([1,2,np.nan,10,12,16],index=t)
        _,n=pairwise_lag_correlation(s,1)
        self.assertEqual(n,3)
        s=s.drop(t[2]);_,n=pairwise_lag_correlation(s,1)
        self.assertEqual(n,3)
    def test_dst_fall_back_has_distinct_elapsed_hours(self):
        t=pd.date_range('2020-11-01T04:00Z',periods=5,freq='h')
        self.assertTrue(t.is_unique)
        self.assertEqual(list(t.tz_convert(NY).hour),[0,1,1,2,3])
    def test_target_index_exact(self):
        d=pd.read_csv(ROOT/'data/pre_eda/prepared/target_336_hour_index_and_normals.csv')
        t=pd.to_datetime(d.hour_label_utc,utc=True)
        self.assertEqual(len(t),336);self.assertTrue(t.is_unique)
        self.assertEqual(t.min(),FINAL_ORIGIN)
        self.assertEqual(t.max(),FINAL_ORIGIN+pd.Timedelta(hours=335))
        self.assertTrue(t.diff().dropna().eq(pd.Timedelta(hours=1)).all())
        local=t.dt.tz_convert(NY)
        self.assertEqual(local.iloc[0].isoformat(),'2026-09-17T00:00:00-04:00')
        self.assertEqual(local.iloc[-1].isoformat(),'2026-09-30T23:00:00-04:00')
        self.assertEqual(d.normal_lookup_local_standard_time.iloc[0],'09-16T23:00:00')
    def test_gfs_heldout_origins_excluded_and_report_alignment(self):
        pairs=gfs_calibration_pairs(ROOT,self.df)
        self.assertEqual(pairs.origin_utc.nunique(),17)
        self.assertEqual(len(pairs),17*336)
        self.assertEqual(pd.to_datetime(pairs.origin_utc,utc=True).max(),pd.Timestamp('2026-07-24T04:00Z'))
        row=pairs.loc[pairs.error_f.notna()].iloc[0]
        import json
        p=json.loads((ROOT/'data/pre_eda/raw/gfs_single_runs'/row.source_file).read_text())
        times=pd.to_datetime(p['hourly']['time'],utc=True)
        obs=pd.Timestamp(row.actual_report_utc)
        i=times.searchsorted(obs,side='right')-1
        fraction=(obs-times[i])/(times[i+1]-times[i])
        expected=p['hourly']['temperature_2m'][i]+fraction*(p['hourly']['temperature_2m'][i+1]-p['hourly']['temperature_2m'][i])
        self.assertAlmostEqual(row.prediction_f,expected,places=8)
    def test_quarantined_targets_not_used(self):
        self.assertTrue(self.df.loc[self.df.temperature_archive_review_flag,'temperature'].isna().all())
if __name__=='__main__':unittest.main()
