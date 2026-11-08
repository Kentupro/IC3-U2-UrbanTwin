"""CP1: reproducible ingestion/QC of MOLI-SOL; no model fitting or test scoring."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import platform
import zipfile

import numpy as np
import pandas as pd

EXPECTED_MD5 = '3bda941929caf4090819569399326f16'
START = pd.Timestamp('2024-05-31 08:00:00', tz='UTC')
STOP = pd.Timestamp('2025-01-23 09:00:00', tz='UTC')
# Fixed calendar boundaries, defined before filtering and model development.
TRAIN_END = pd.Timestamp('2024-10-20', tz='UTC')
VAL_END = pd.Timestamp('2024-12-07', tz='UTC')


def split_labels(t):
    return np.where(t < TRAIN_END, 'train', np.where(t < VAL_END, 'validation', 'test'))


def load_csv(raw):
    df = pd.read_csv(io.BytesIO(raw))
    # The publisher stores Unix ns in scientific notation. Hour-aligned values
    # in this archive are exactly representable; verify rather than round.
    df['timestamp'] = pd.to_datetime(df['rounded_datetime'], unit='ns', utc=True, errors='coerce')
    invalid = df['timestamp'].isna()
    rejected = df.loc[invalid].copy()
    df = df.loc[~invalid].sort_values('timestamp').copy()
    if df['timestamp'].duplicated().any():
        raise ValueError('Duplicate timestamps: inspect source; no silent aggregation.')
    if not (df['timestamp'].dt.floor('h') == df['timestamp']).all():
        raise ValueError('Off-hour timestamps: alignment requires explicit review.')
    return df, rejected


def make_pairs(node, reference):
    n = node[['timestamp', 'PM2_5', 'Temp', 'HR']].rename(columns={
        'PM2_5': 'pm25_raw', 'Temp': 'temperature', 'HR': 'rh_raw'})
    g = reference[['timestamp', 'PM2,5']].rename(columns={'PM2,5': 'pm25_reference'})
    p = n.merge(g, on='timestamp', how='inner', validate='one_to_one')
    p['valid_pm_pair'] = (np.isfinite(p['pm25_raw']) & np.isfinite(p['pm25_reference'])
                          & p['pm25_raw'].ge(0) & p['pm25_reference'].ge(0))
    p['valid_rh'] = np.isfinite(p['rh_raw']) & p['rh_raw'].between(0, 100)
    p['rh_qc'] = p['rh_raw'].where(p['valid_rh'])
    p['valid_temperature'] = np.isfinite(p['temperature'])
    p['split'] = split_labels(p['timestamp'])
    return p


def run(archive, out):
    archive, out = Path(archive), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    contents = archive.read_bytes()
    md5 = hashlib.md5(contents).hexdigest()
    if md5 != EXPECTED_MD5:
        raise ValueError('Archive differs from verified Zenodo v1.0.0; review before use.')
    inventory, loaded, source_audit = [], {}, {}
    with zipfile.ZipFile(io.BytesIO(contents)) as z:
        for name in sorted(z.namelist()):
            if name.endswith('.csv'):
                raw = z.read(name)
                inventory.append({'file': name, 'bytes': len(raw),
                                  'sha256': hashlib.sha256(raw).hexdigest(),
                                  'rows': len(pd.read_csv(io.BytesIO(raw)))})
        for key in ('gva', 'n1', 'n2'):
            df, rejected = load_csv(z.read(f'moli/{key}_60.csv'))
            rejected.to_csv(out / f'{key}_rejected_timestamp.csv', index=False)
            loaded[key] = df
            grid = pd.date_range(START, STOP, freq='h')
            source_audit[key] = {
                'rows_original': len(df) + len(rejected), 'invalid_timestamp': len(rejected),
                'rows_timestamp_valid': len(df),
                'missing_hours': len(grid.difference(df['timestamp'])),
                'first_timestamp': str(df['timestamp'].min()),
                'last_timestamp': str(df['timestamp'].max()),
                'na_by_column': {k: int(v) for k, v in df.isna().sum().items()},
            }
    pairs = make_pairs(loaded['n1'], loaded['gva'])
    pairs.to_csv(out / 'aligned_n1_gva.csv', index=False)
    valid = pairs.loc[pairs['valid_pm_pair']].copy()
    valid.to_csv(out / 'pm25_pairs.csv', index=False)
    for label in ('train', 'validation', 'test'):
        valid.loc[valid['split'].eq(label)].to_csv(out / f'{label}.csv', index=False)
    # Explicit missing hourly grid. Never interpolate target or cross a split.
    grid = pd.DataFrame({'timestamp': pd.date_range(START, STOP, freq='h')})
    grid = grid.merge(pairs, on='timestamp', how='left', validate='one_to_one')
    grid['split'] = split_labels(grid['timestamp'])
    grid.to_csv(out / 'hourly_grid.csv', index=False)
    split_stats = {}
    for label in ('train', 'validation', 'test'):
        d = valid.loc[valid['split'].eq(label)]
        split_stats[label] = {'n_pm_pairs': len(d), 'n_rh_valid': int(d['valid_rh'].sum()),
                              'first': str(d['timestamp'].min()), 'last': str(d['timestamp'].max())}
    audit = {
        'dataset_doi': '10.5281/zenodo.17044034', 'dataset_version': '1.0.0',
        'archive_md5': md5, 'archive_sha256': hashlib.sha256(contents).hexdigest(),
        'license': 'CC-BY-4.0', 'python': platform.python_version(),
        'pandas': pd.__version__, 'numpy': np.__version__,
        'timezone_policy': 'Unix epoch decoded as UTC; source local acquisition timezone not documented',
        'sources': source_audit, 'expected_hourly_grid': len(grid),
        'aligned_rows': len(pairs), 'valid_pm_pairs': len(valid),
        'unusable_grid_hours': int((~grid['valid_pm_pair'].eq(True)).sum()),
        'rh_above_100_timestamp_valid_n1': int(loaded['n1']['HR'].gt(100).sum()),
        'rh_above_100_valid_pm_pairs': int(valid['rh_raw'].gt(100).sum()),
        'rh_above_100_pct_valid_pm_pairs': float(valid['rh_raw'].gt(100).mean()*100),
        'gva_hr_equals_pm1': bool(loaded['gva']['HR'].equals(loaded['gva']['PM1'])),
        'splits': split_stats,
        'train_end_exclusive': str(TRAIN_END), 'validation_end_exclusive': str(VAL_END),
        'models_fitted': 0,
    }
    (out / 'audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    pd.DataFrame(inventory).to_csv(out / 'inventory.csv', index=False)
    print(json.dumps({k: audit[k] for k in ('valid_pm_pairs', 'unusable_grid_hours', 'splits')}, indent=2))
    return audit


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--archive', default='data/raw/moli-sol-dataset.zip')
    cli.add_argument('--out', default='outputs')
    args = cli.parse_args()
    run(args.archive, args.out)
