import unittest
import numpy as np
import pandas as pd
from cp3 import fit_models, predict_models, calendar_blocks, metric_draws, daily_alerts
from cp2 import metrics


class CP3Checks(unittest.TestCase):
    def test_bootstrap_draws_match_explicit_hour_resampling(self):
        dates = pd.to_datetime(['2024-12-07 00:00','2024-12-07 01:00',
            '2024-12-08 00:00','2024-12-10 00:00'],utc=True)
        y = np.array([1.,4.,2.,7.]); p = np.array([2.,3.,5.,6.])
        codes, calendar, indices, weights = calendar_blocks(dates,30,2,2026)
        self.assertEqual(len(calendar),4)  # Missing 09 December remains in calendar.
        draws = metric_draws(y,p,codes,weights)
        for b, days in enumerate(indices):
            observations = np.concatenate([np.flatnonzero(codes==day) for day in days])
            expected=metrics(y[observations],p[observations])
            for key in ['MAE','RMSE','bias']:
                self.assertAlmostEqual(draws[key][b,0],expected[key])

    def test_block_indices_preserve_consecutive_days(self):
        t=pd.date_range('2024-12-07',periods=12,freq='D',tz='UTC')
        codes,calendar,indices,weights=calendar_blocks(t,10,3,42)
        for offset in (0,3,6,9):
            self.assertTrue(np.all(np.diff(indices[:,offset:offset+3],axis=1)==1))
        self.assertTrue(np.all(weights.sum(axis=1)==12))

    def test_prediction_needs_no_test_targets(self):
        train=pd.DataFrame({'pm25_raw':[2.,4.,6.,8.], 'temperature':[10.,11.,12.,13.],
                            'pm25_reference':[1.,2.,3.,4.]})
        fitted=fit_models(train,seeds=(42,),parameters=dict(n_estimators=5,max_depth=2,min_samples_leaf=1,n_jobs=1))
        test=pd.DataFrame({'pm25_raw':[3.,5.],'temperature':[11.,12.]})
        first=predict_models(fitted,test)
        test['pm25_reference']=[-1e9,1e9]
        second=predict_models(fitted,test)
        for key in first:np.testing.assert_array_equal(first[key],second[key])

    def daily_fixture(self,days):
        timestamps=[]
        for day,count in days:
            timestamps.extend(pd.date_range(day,periods=count,freq='h',tz='UTC'))
        return timestamps,np.zeros(len(timestamps)),np.full(len(timestamps),10.)

    def test_third_calendar_day_triggers_alert(self):
        t,y,p=self.daily_fixture([('2024-12-07',18),('2024-12-08',18),('2024-12-09',18)])
        d=daily_alerts(t,y,p,5.,'2024-12-07T00:00Z','2024-12-09T23:00Z')
        self.assertEqual(d.verification_alert.tolist(),[False,False,True])

    def test_missing_day_breaks_streak(self):
        t,y,p=self.daily_fixture([('2024-12-07',18),('2024-12-08',18),('2024-12-10',18)])
        d=daily_alerts(t,y,p,5.,'2024-12-07T00:00Z','2024-12-10T23:00Z')
        self.assertEqual(d.consecutive_exceedance_days.tolist(),[1,2,0,1])
        self.assertFalse(d.verification_alert.any())

    def test_insufficient_coverage_and_threshold_equality_do_not_alert(self):
        t,y,p=self.daily_fixture([('2024-12-07',18),('2024-12-08',17),('2024-12-09',18)])
        d=daily_alerts(t,y,p,5.,'2024-12-07T00:00Z','2024-12-09T23:00Z')
        self.assertEqual(d.consecutive_exceedance_days.tolist(),[1,0,1])
        d=daily_alerts(t,y,p,10.,'2024-12-07T00:00Z','2024-12-09T23:00Z')
        self.assertFalse(d.exceeds_q95.any())


if __name__=='__main__':unittest.main()
