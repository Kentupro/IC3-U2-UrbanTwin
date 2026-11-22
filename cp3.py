"""CP3: frozen-model test evaluation, paired temporal CIs and a fixed alert rule."""
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

from cp2 import FEATURES, RF_PARAMS, SEEDS, development_rows, metrics
from pipeline import START, STOP, VAL_END, run as ingest, split_labels

ROOT = Path(__file__).resolve().parent
METRICS = ('MAE', 'RMSE', 'bias', 'R2')


def validate_protocol(protocol, archive):
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != protocol['archive_sha256']:
        raise ValueError('Dataset differs from the frozen protocol.')
    if protocol['representations'] != FEATURES or protocol['rf_parameters'] != RF_PARAMS:
        raise ValueError('Representations or RF settings changed after CP2.')
    if tuple(protocol['seeds']) != SEEDS or protocol['primary_method'] != 'RF_R1':
        raise ValueError('Frozen seeds or primary method changed.')
    for filename, digest in protocol['cp2_source_sha256'].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != digest:
            raise ValueError('CP2 source differs from the frozen version: ' + filename)


def fit_models(train, seeds=SEEDS, parameters=None):
    """Only this frame supplies targets for fitting. Validation/test never enter fit."""
    y = train.pm25_reference.to_numpy()
    fitted = {'raw': None, 'train_mean': float(y.mean())}
    for rep, features in FEATURES.items():
        fitted['linear_' + rep] = [LinearRegression().fit(train[features], y)]
        fitted['RF_' + rep] = [RandomForestRegressor(
            **(RF_PARAMS if parameters is None else parameters), random_state=seed
        ).fit(train[features], y) for seed in seeds]
    return fitted


def predict_models(fitted, frame):
    """Prediction deliberately needs no reference target column."""
    output = {}
    for name, model in fitted.items():
        if name == 'raw':
            output[name] = frame.pm25_raw.to_numpy()[None, :]
        elif name == 'train_mean':
            output[name] = np.full((1, len(frame)), model)
        else:
            features = FEATURES[name.rsplit('_', 1)[1]]
            output[name] = np.stack([estimator.predict(frame[features]) for estimator in model])
    return output


def calendar_blocks(timestamps, repetitions, block_days, seed):
    """Moving, non-circular blocks; also retain dates with no observed pair."""
    days = pd.DatetimeIndex(timestamps).floor('D')
    calendar = pd.date_range(days.min(), days.max(), freq='D')
    length = len(calendar)
    if not 1 <= block_days <= length:
        raise ValueError('Block length exceeds the evaluation calendar.')
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, length - block_days + 1,
                          size=(repetitions, int(np.ceil(length / block_days))))
    indices = (starts[:, :, None] + np.arange(block_days)).reshape(repetitions, -1)[:, :length]
    weights = np.zeros((repetitions, length), dtype=np.int64)
    np.add.at(weights, (np.arange(repetitions)[:, None], indices), 1)
    codes = calendar.get_indexer(days)
    return codes, calendar, indices, weights


def metric_draws(y, prediction, day_codes, weights):
    """Sufficient daily statistics avoid treating hours/seeds as IID observations."""
    prediction = np.asarray(prediction, dtype=float)
    y = np.asarray(y, dtype=float)
    if prediction.ndim == 1:
        prediction = prediction[None, :]
    if prediction.shape[1] != len(y) or not np.isfinite(prediction).all():
        raise ValueError('Invalid prediction matrix.')
    days = weights.shape[1]
    count = np.bincount(day_codes, minlength=days)
    n = weights @ count
    if np.any(n <= 0):
        raise ValueError('Bootstrap replicate has no observed pairs.')
    ys = weights @ np.bincount(day_codes, weights=y, minlength=days)
    y2s = weights @ np.bincount(day_codes, weights=y*y, minlength=days)
    sst = y2s - ys*ys/n
    sst = np.where(sst > 1e-12, sst, np.nan)
    residual = prediction - y[None, :]
    def aggregate(values):
        daily = np.stack([np.bincount(day_codes, weights=v, minlength=days) for v in values])
        return weights @ daily.T
    absolute = aggregate(np.abs(residual)) / n[:, None]
    squared_sum = aggregate(residual**2)
    return {'MAE': absolute, 'RMSE': np.sqrt(squared_sum/n[:, None]),
            'bias': aggregate(residual)/n[:, None],
            'R2': 1 - squared_sum/sst[:, None]}


def interval(values):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    return [float(np.quantile(finite, .025)), float(np.quantile(finite, .975))] if len(finite) else [None, None]


def result_tables(y, predictions, codes, weights, seeds=SEEDS):
    rows, aggregates, draws = [], {}, {}
    for name, prediction in predictions.items():
        draws[name] = metric_draws(y, prediction, codes, weights)
        points = [metrics(y, p) for p in prediction]
        aggregate = dict(row_type='aggregate', model=name,
                         seed='mean_of_5' if len(points) > 1 else 'deterministic',
                         split='test', n=len(y), runs=len(points))
        for key in METRICS:
            values = np.array([p[key] if p[key] is not None else np.nan for p in points])
            aggregate[key] = float(values.mean()) if np.isfinite(values).all() else None
            aggregate[key+'_seed_sd'] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            low, high = interval(draws[name][key].mean(axis=1))
            aggregate[key+'_ci95_low'], aggregate[key+'_ci95_high'] = low, high
        rows.append(aggregate)
        aggregates[name] = aggregate
        if len(points) > 1:
            for index, point in enumerate(points):
                row = dict(row_type='per_seed', model=name, seed=str(seeds[index]),
                           split='test', n=len(y), runs=1)
                for key in METRICS:
                    row[key] = point[key]
                    row[key+'_seed_sd'] = None
                    row[key+'_ci95_low'], row[key+'_ci95_high'] = interval(draws[name][key][:, index])
                rows.append(row)
    paired = []
    for baseline in ('raw', 'linear_R0', 'RF_R0'):
        for key in ('MAE', 'RMSE'):
            delta = draws['RF_R1'][key].mean(axis=1) - draws[baseline][key].mean(axis=1)
            low, high = interval(delta)
            paired.append(dict(method='RF_R1', baseline=baseline, metric=key,
                estimate=aggregates['RF_R1'][key]-aggregates[baseline][key],
                ci95_low=low, ci95_high=high, direction='negative favors RF_R1'))
    return pd.DataFrame(rows), pd.DataFrame(paired), aggregates


def daily_alerts(timestamps, reference, prediction, threshold, start, stop,
                 minimum_pairs=18, consecutive_days=3):
    """Missing/ineligible calendar dates break a streak; equality is no exceedance."""
    r = np.asarray(prediction) - np.asarray(reference)
    frame = pd.DataFrame({'day': pd.DatetimeIndex(timestamps).floor('D'),
                          'abs_error': np.abs(r), 'residual': r})
    grouped = frame.groupby('day').agg(pairs=('abs_error','count'),
        daily_MAE=('abs_error','mean'), daily_bias=('residual','mean'))
    calendar = pd.date_range(pd.Timestamp(start).floor('D'), pd.Timestamp(stop).floor('D'), freq='D')
    grouped = grouped.reindex(calendar).rename_axis('day')
    grouped['pairs'] = grouped['pairs'].fillna(0).astype(int)
    grouped['eligible'] = grouped['pairs'] >= minimum_pairs
    grouped['exceeds_q95'] = grouped['eligible'] & (grouped['daily_MAE'] > threshold)
    streak, streaks = 0, []
    for exceeds in grouped['exceeds_q95']:
        streak = streak + 1 if exceeds else 0
        streaks.append(streak)
    grouped['consecutive_exceedance_days'] = streaks
    grouped['verification_alert'] = grouped['consecutive_exceedance_days'] >= consecutive_days
    grouped['threshold'] = threshold
    return grouped.reset_index()


def main(archive, output, protocol_path):
    protocol_path, output = Path(protocol_path), Path(output)
    protocol = json.loads(protocol_path.read_text())
    validate_protocol(protocol, archive)
    output.mkdir(parents=True, exist_ok=True)
    ingest(archive, ROOT/'outputs')
    pairs = pd.read_csv(ROOT/'outputs/pm25_pairs.csv', parse_dates=['timestamp'])
    if not np.array_equal(pairs['split'].to_numpy(), split_labels(pairs.timestamp)):
        raise ValueError('Split labels were modified.')
    train, val = development_rows(pairs)
    test = pairs.loc[pairs.timestamp >= VAL_END].copy()
    if not (test.valid_pm_pair & test.valid_temperature).all():
        raise ValueError('Do not silently change the frozen test support.')
    for frame, key in [(train,'expected_train_rows'), (val,'expected_validation_rows'), (test,'expected_test_rows')]:
        if len(frame) != protocol[key]:
            raise ValueError('Observation count differs from CP2: '+key)
    models = fit_models(train)
    val_predictions = predict_models(models, val)
    cp2_metrics = pd.read_csv(ROOT/'results/cp2/metrics.csv').set_index('model')
    for name, prediction in val_predictions.items():
        score = np.mean([metrics(val.pm25_reference, p)['MAE'] for p in prediction])
        if not np.isclose(score, cp2_metrics.loc[name,'MAE'], atol=1e-8, rtol=0):
            raise ValueError('Frozen model no longer reproduces CP2: '+name)
    daily_val = daily_alerts(val.timestamp, val.pm25_reference, val_predictions['RF_R1'][0],
        np.inf, val.timestamp.min(), val.timestamp.max())
    threshold = float(daily_val.loc[daily_val.eligible, 'daily_MAE'].quantile(.95))
    if not np.isclose(threshold, protocol['alert_rule']['threshold_ug_m3'], atol=1e-8, rtol=0):
        raise ValueError('Validation alert threshold changed.')
    # First test scoring begins only after protocol and CP2 reproduction checks.
    predictions = predict_models(models, test)
    y = test.pm25_reference.to_numpy()
    config = protocol['bootstrap']
    codes, calendar, indices, weights = calendar_blocks(test.timestamp,
        config['repetitions'], config['block_days'], config['seed'])
    results, paired, summary = result_tables(y, predictions, codes, weights)
    results.to_csv(ROOT/'results_v1_U2.csv', index=False, float_format='%.10f')
    paired.to_csv(output/'paired_differences.csv', index=False, float_format='%.10f')
    diagnostic = test[['timestamp','pm25_reference','pm25_raw','temperature','rh_raw','valid_rh']].copy()
    for name, prediction in predictions.items():
        for index, values in enumerate(prediction):
            column = name+'_seed_'+str(SEEDS[index]) if len(prediction) > 1 else name
            diagnostic[column] = values
    diagnostic.to_csv(output/'test_predictions.csv', index=False, float_format='%.8f')
    daily = daily_alerts(test.timestamp, y, predictions['RF_R1'][0], threshold, VAL_END, STOP)
    daily.to_csv(output/'daily_monitoring.csv', index=False, float_format='%.10f')
    manifest = dict(stage='CP3', source_cp2_commit=protocol['source_cp2_commit'],
        protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        archive_sha256=protocol['archive_sha256'],
        software=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,scikit_learn=sklearn.__version__),
        train_rows=len(train), validation_rows=len(val), test_rows=len(test),
        train_last=str(train.timestamp.max()), test_first=str(test.timestamp.min()), test_last=str(test.timestamp.max()),
        test_scored=True, test_used_for_fit=False, test_used_for_selection=False,
        refit_on_validation=False, hyperparameter_search=False, cp2_validation_reproduced=True,
        primary_method=protocol['primary_method'], seeds=list(SEEDS),
        bootstrap=config, test_calendar_days=len(calendar), result_rows=len(results),
        verification_monitoring=dict(seed=42, threshold_ug_m3=threshold,
            eligible_test_days=int(daily.eligible.sum()),
            exceedance_days=int(daily.exceeds_q95.sum()),
            alert_days=int(daily.verification_alert.sum()),
            alert_dates=daily.loc[daily.verification_alert,'day'].dt.strftime('%Y-%m-%d').tolist(),
            status='Reference-based verification flags, not labeled drift detection'),
        relative_test_mae_reduction_vs_raw_pct=float((1-summary['RF_R1']['MAE']/summary['raw']['MAE'])*100),
        fitted_model_count=12)
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(results.loc[results.row_type.eq('aggregate'),['model','MAE','MAE_ci95_low','MAE_ci95_high','RMSE','R2']].to_string(index=False))
    print(paired.to_string(index=False))
    print('Monitoring:',manifest['verification_monitoring'])
    return manifest


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--archive', type=Path, default=ROOT/'data/raw/moli-sol-dataset.zip')
    cli.add_argument('--out', type=Path, default=ROOT/'results/cp3')
    cli.add_argument('--protocol', type=Path, default=ROOT/'protocol_cp3.json')
    args = cli.parse_args()
    main(args.archive, args.out, args.protocol)
