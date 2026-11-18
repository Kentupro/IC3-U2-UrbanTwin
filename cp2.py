"""CP2: compare hourly representations on a fixed temporal validation split."""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from pipeline import TRAIN_END, VAL_END, run as ingest, split_labels

ROOT = Path(__file__).resolve().parent
SEEDS = (42, 7, 21, 84, 123)
FEATURES = {'R0': ['pm25_raw'], 'R1': ['pm25_raw', 'temperature']}
RF_PARAMS = dict(n_estimators=300, max_depth=8, min_samples_leaf=5,
                 max_features=1.0, bootstrap=True, n_jobs=1)


def metrics(y, prediction):
    y, prediction = np.asarray(y, dtype=float), np.asarray(prediction, dtype=float)
    if len(y) == 0 or y.shape != prediction.shape:
        raise ValueError('Metrics require non-empty, equally shaped arrays.')
    if not (np.isfinite(y).all() and np.isfinite(prediction).all()):
        raise ValueError('Non-finite target or prediction.')
    residual = prediction - y
    denominator = np.sum((y - y.mean()) ** 2)
    return dict(n=len(y), MAE=float(np.mean(np.abs(residual))),
                RMSE=float(np.sqrt(np.mean(residual ** 2))),
                bias=float(residual.mean()),
                R2=float(1 - np.sum(residual ** 2) / denominator) if denominator else None)


def development_rows(pairs):
    """Exclude the entire test period before accessing any modeling arrays."""
    d = pairs.loc[pairs['timestamp'] < VAL_END].copy()
    if not np.array_equal(d['split'].to_numpy(), split_labels(d['timestamp'])):
        raise ValueError('Split labels disagree with the frozen calendar boundaries.')
    d = d.loc[d['valid_pm_pair'] & d['valid_temperature']].copy()
    columns = ['pm25_reference', 'pm25_raw', 'temperature']
    if not np.isfinite(d[columns].to_numpy(dtype=float)).all():
        raise ValueError('Non-finite modeling variables after QC.')
    train = d.loc[d['timestamp'] < TRAIN_END].copy()
    validation = d.loc[d['timestamp'] >= TRAIN_END].copy()
    if train.empty or validation.empty or train.timestamp.max() >= validation.timestamp.min():
        raise ValueError('Invalid chronological split.')
    return train, validation


def evaluate(train, validation, seeds=SEEDS, rf_params=None):
    params = RF_PARAMS if rf_params is None else rf_params
    y_train = train['pm25_reference'].to_numpy()
    y = validation['pm25_reference'].to_numpy()
    predictions = {'raw': [validation['pm25_raw'].to_numpy()],
                   'train_mean': [np.full(len(validation), y_train.mean())]}
    fitted_info = {}
    for representation, features in FEATURES.items():
        x_train, x_val = train[features], validation[features]
        linear = LinearRegression().fit(x_train, y_train)
        predictions['linear_' + representation] = [linear.predict(x_val)]
        fitted_info['linear_' + representation] = {
            'features': features, 'coefficients': linear.coef_.tolist(),
            'intercept': float(linear.intercept_)}
        predictions['RF_' + representation] = []
        for seed in seeds:
            forest = RandomForestRegressor(**params, random_state=seed).fit(x_train, y_train)
            predictions['RF_' + representation].append(forest.predict(x_val))
    runs = []
    for name, arrays in predictions.items():
        for index, prediction in enumerate(arrays):
            runs.append(dict(model=name, seed=seeds[index] if name.startswith('RF_') else None,
                             **metrics(y, prediction)))
    return pd.DataFrame(runs), predictions, fitted_info


def day_bootstrap(timestamps, errors, repetitions=2000, seed=2026):
    """Resample paired UTC days; errors may be signed differences of absolute errors."""
    d = pd.DataFrame({'day': pd.DatetimeIndex(timestamps).floor('D'), 'error': errors})
    blocks = d.groupby('day')['error'].agg(['sum', 'count'])
    rng = np.random.default_rng(seed)
    indices = rng.integers(len(blocks), size=(repetitions, len(blocks)))
    draws = blocks['sum'].to_numpy()[indices].sum(axis=1) / blocks['count'].to_numpy()[indices].sum(axis=1)
    return {'estimate': float(d.error.mean()),
            'ci95_low': float(np.quantile(draws, .025)),
            'ci95_high': float(np.quantile(draws, .975)),
            'days': len(blocks), 'bootstrap_repetitions': repetitions, 'bootstrap_seed': seed}


def main(archive, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    audit = ingest(archive, ROOT / 'outputs')
    pairs = pd.read_csv(ROOT / 'outputs/pm25_pairs.csv', parse_dates=['timestamp'])
    train, val = development_rows(pairs)
    runs, predictions, fitted = evaluate(train, val)
    runs.to_csv(output / 'metrics_by_seed.csv', index=False, float_format='%.10f')
    rows = []
    for name in predictions:
        d = runs.loc[runs.model.eq(name)]
        row = dict(model=name, n=int(d.n.iloc[0]), runs=len(d))
        for key in ('MAE', 'RMSE', 'bias', 'R2'):
            row[key] = float(d[key].mean())
            row[key + '_sd'] = float(d[key].std(ddof=1)) if len(d) > 1 else 0.0
        rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(output / 'metrics.csv', index=False, float_format='%.10f')
    y = val.pm25_reference.to_numpy()
    # Compare mean per-observation absolute errors across independent RF fits.
    error0 = np.abs(np.stack(predictions['RF_R0']) - y).mean(axis=0)
    error1 = np.abs(np.stack(predictions['RF_R1']) - y).mean(axis=0)
    uncertainty = day_bootstrap(val.timestamp, error1 - error0)
    raw_error = np.abs(predictions['raw'][0] - y)
    skill = {}
    for representation, error in [('R0', error0), ('R1', error1)]:
        skill[representation] = day_bootstrap(val.timestamp, error - raw_error)
    selected = 'R1' if error1.mean() < error0.mean() - 1e-12 else 'R0'
    selected_predictions = predictions['RF_' + selected]
    diagnostic = val[['timestamp', 'pm25_reference', 'pm25_raw', 'temperature', 'rh_raw', 'valid_rh']].copy()
    # Store one explicitly identified RF run, not an unannounced ensemble.
    for name, arrays in predictions.items():
        diagnostic[name] = arrays[0]
    diagnostic.to_csv(output / 'validation_predictions.csv', index=False, float_format='%.8f')
    raw_mae = float(np.mean(raw_error))
    chosen = summary.loc[summary.model.eq('RF_' + selected)].iloc[0]
    # Derive an exploratory threshold for CP3; no test alarms are computed here.
    e = np.abs(selected_predictions[0] - y)
    daily = pd.DataFrame({'day': val.timestamp.dt.floor('D'), 'absolute_error': e})
    daily = daily.groupby('day').absolute_error.agg(['mean', 'count'])
    covered = daily.loc[daily['count'] >= 18]
    threshold = float(covered['mean'].quantile(.95)) if len(covered) else None
    manifest = dict(
        stage='CP2', source_cp1_commit='4a8175950c0beea91e7955943b64a75e32f558ae',
        dataset_doi=audit['dataset_doi'], dataset_version=audit['dataset_version'],
        archive_sha256=audit['archive_sha256'],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        pipeline_sha256=hashlib.sha256((ROOT / 'pipeline.py').read_bytes()).hexdigest(),
        python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
        scikit_learn=sklearn.__version__, features=FEATURES, rf_parameters=RF_PARAMS,
        seeds=list(SEEDS), train_rows=len(train), validation_rows=len(val),
        test_rows_reserved=audit['splits']['test']['n_pm_pairs'],
        train_end_exclusive=str(TRAIN_END), validation_end_exclusive=str(VAL_END),
        test_scored=False, test_used_for_selection=False, target_imputation=False,
        predictions_clipped=False, hyperparameter_search=False,
        metric_aggregation='RF table: mean of per-seed metrics; sd is sample SD, not CI',
        representation_selection='Minimum mean RF validation MAE; tie goes to R0',
        selected_representation=selected,
        selected_rf_validation_mae=float(chosen.MAE),
        relative_mae_reduction_vs_raw_pct=float((1 - chosen.MAE / raw_mae) * 100),
        delta_mae_R1_minus_R0=uncertainty,
        delta_mae_rf_minus_raw=skill,
        threshold_proposal=dict(seed=42, valid_validation_days=len(covered),
            q95_daily_mae_ug_m3=threshold, consecutive_calendar_days=3,
            minimum_hourly_pairs_per_day=18, missing_day_breaks_streak=True,
            status='Exploratory calibration on validation; no detector/test validation yet'),
        baseline_fit_count=2 + 2 * len(SEEDS),
    )
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False,
                                                   allow_nan=False) + '\n', encoding='utf-8')
    print(summary.to_string(index=False))
    print('Selected representation:', selected)
    print('Delta MAE R1-R0:', uncertainty)
    print('Test scored: False')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT / 'data/raw/moli-sol-dataset.zip')
    parser.add_argument('--out', type=Path, default=ROOT / 'results/cp2')
    args = parser.parse_args()
    main(args.archive, args.out)
