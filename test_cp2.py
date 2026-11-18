import unittest
import numpy as np
import pandas as pd

from cp2 import FEATURES, development_rows, evaluate, metrics, day_bootstrap
from pipeline import split_labels


class CP2Checks(unittest.TestCase):
    def fixture(self):
        timestamps = pd.to_datetime(['2024-10-19 20:00', '2024-10-19 21:00',
            '2024-10-19 22:00', '2024-10-19 23:00', '2024-10-20 00:00',
            '2024-10-20 01:00', '2024-12-07 00:00'], utc=True)
        return pd.DataFrame(dict(timestamp=timestamps, split=split_labels(timestamps),
            valid_pm_pair=True, valid_temperature=True,
            pm25_reference=[1., 2., 3., 4., 5., 6., 7.],
            pm25_raw=[2., 4., 6., 8., 10., 12., 14.],
            temperature=[20., 21., 22., 23., 24., 25., 26.]))

    def test_metrics_are_errors_not_squared_correlation(self):
        m = metrics([1, 2, 3], [2, 2, 2])
        self.assertAlmostEqual(m['MAE'], 2/3)
        self.assertAlmostEqual(m['RMSE'], np.sqrt(2/3))
        self.assertEqual(m['bias'], 0)
        self.assertEqual(m['R2'], 0)
        self.assertLess(metrics([1, 2, 3], [20, 20, 20])['R2'], 0)

    def test_future_test_target_cannot_change_validation_results(self):
        d = self.fixture()
        params = dict(n_estimators=5, max_depth=2, min_samples_leaf=1, n_jobs=1)
        train, val = development_rows(d)
        first = evaluate(train, val, seeds=(42,), rf_params=params)[0]
        d.loc[d.split.eq('test'), ['pm25_reference', 'pm25_raw', 'temperature']] = -1e9
        train2, val2 = development_rows(d)
        second = evaluate(train2, val2, seeds=(42,), rf_params=params)[0]
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(len(train), 4)
        self.assertEqual(len(val), 2)

    def test_tampered_split_is_rejected(self):
        d = self.fixture()
        d.loc[0, 'split'] = 'validation'
        with self.assertRaises(ValueError):
            development_rows(d)

    def test_target_and_invalid_rh_cannot_be_predictors(self):
        self.assertEqual(FEATURES['R0'], ['pm25_raw'])
        self.assertEqual(FEATURES['R1'], ['pm25_raw', 'temperature'])
        self.assertNotIn('pm25_reference', FEATURES['R1'])
        self.assertNotIn('rh_raw', FEATURES['R1'])

    def test_paired_bootstrap_preserves_zero_difference(self):
        t = pd.to_datetime(['2024-10-20 00:00', '2024-10-20 01:00',
                            '2024-10-21 00:00'], utc=True)
        result = day_bootstrap(t, np.zeros(3), repetitions=20)
        self.assertEqual(result['ci95_low'], 0)
        self.assertEqual(result['ci95_high'], 0)
        self.assertEqual(result['days'], 2)


if __name__ == '__main__':
    unittest.main()
