import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pipeline import load_csv, make_pairs, split_labels


class PipelineChecks(unittest.TestCase):
    def test_missing_timestamp_is_quarantined(self):
        good, rejected = load_csv(b'rounded_datetime,PM2_5\n1717142400000000000,8\n,12\n')
        self.assertEqual(len(good), 1)
        self.assertEqual(len(rejected), 1)

    def test_qc_preserves_pm_pair_and_raw_rh(self):
        t = pd.to_datetime(['2024-06-01'], utc=True)
        n = pd.DataFrame(dict(timestamp=t, PM2_5=[12], Temp=[20], HR=[118]))
        g = pd.DataFrame({'timestamp': t, 'PM2,5': [8]})
        p = make_pairs(n, g)
        self.assertTrue(p.valid_pm_pair.iloc[0])
        self.assertFalse(p.valid_rh.iloc[0])
        self.assertEqual(p.rh_raw.iloc[0], 118)
        self.assertTrue(pd.isna(p.rh_qc.iloc[0]))

    def test_split_boundaries_cannot_leak(self):
        t = pd.to_datetime(['2024-10-19 23:00', '2024-10-20 00:00',
                            '2024-12-06 23:00', '2024-12-07 00:00'], utc=True)
        self.assertEqual(list(split_labels(t)), ['train', 'validation', 'validation', 'test'])


if __name__ == '__main__':
    unittest.main()
