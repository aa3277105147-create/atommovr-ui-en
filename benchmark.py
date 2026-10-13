"""Public-facing repeated trials through the same audited simulation adapter."""
from __future__ import annotations

import copy
import csv
import json
import math
from pathlib import Path
import statistics
import time
import uuid

from comparison import compare_algorithms
import simulator

MAX_TRIALS = 20
BENCHMARK_BUDGET_SECONDS = 120
HEADERS = ["Algorithm", "Executed trials", "Full-target fraction", "Mean target fill", "Mean atoms lost",
           "Mean successful time (µs)", "Successful time samples", "Insufficient / Stopped / Other incomplete"]


def _mean(values):
    values = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    return statistics.fmean(values) if values else None


def aggregate(records):
    rows = []
    for key, label in simulator.ALGORITHM_NAMES.items():
        samples = [r for r in records if r['key'] == key and r['status'] not in ('skipped', 'not_run')]
        unsupported = any(r['key'] == key and r['status'] == 'skipped' for r in records)
        if not samples:
            rows.append([label, 0, "Unsupported pattern" if unsupported else "Not run"] + ["—"] * 5)
            continue
        successes = [r for r in samples if r.get('filled') == r.get('target_count') and r.get('target_count', 0) > 0]
        fill = _mean([r.get('fill_fraction') for r in samples])
        losses = _mean([r.get('losses') for r in samples])
        success_times = [r['simulated_time_us'] for r in successes if isinstance(r.get('simulated_time_us'), (int, float)) and math.isfinite(r['simulated_time_us'])]
        fill_samples = sum(r.get('fill_fraction') is not None for r in samples)
        missing = f" (recorded {fill_samples}/{len(samples)})" if fill_samples != len(samples) else ""
        insufficient = sum(r['status'] == 'insufficient' for r in samples)
        blocked = sum(r['status'] == 'blocked' for r in samples)
        # A stopped run that already filled the target belongs to the success group.
        blocked -= sum(r['status'] == 'blocked' for r in successes)
        other = len(samples) - len(successes) - insufficient - blocked
        mean_time = _mean(success_times)
        rows.append([label, len(samples), f"{len(successes)}/{len(samples)} ({len(successes)/len(samples):.1%})",
                     "—" if fill is None else f"{fill:.1%}{missing}", "—" if losses is None else f"{losses:.3f}" +
                     (f" (recorded {sum(r.get('losses') is not None for r in samples)}/{len(samples)})" if any(r.get('losses') is None for r in samples) else ""),
                     "—" if mean_time is None else round(mean_time, 3), len(success_times),
                     f"{insufficient} / {blocked} / {other}"])
    return rows


def benchmark_algorithms(config, trials=5, on_progress=None):
    if isinstance(trials, bool) or not isinstance(trials, (int, float)) or not 1 <= trials <= MAX_TRIALS or not math.isfinite(trials) or int(trials) != trials:
        return {"status": "invalid", "message": f"Trials must be an integer from 1 to {MAX_TRIALS}.", "rows": [], "records": []}
    base = simulator.preview(copy.deepcopy(config))
    normalized = copy.deepcopy(base['config'])
    result = {"config": normalized, "trials": int(trials), "records": [], "rows": [], "status": "complete", "message": ""}
    if base['summary']['status'] != 'preview':
        result.update(status='invalid', message=base['summary']['message'])
        return result
    deadline = time.monotonic() + BENCHMARK_BUDGET_SECONDS
    supported = sum(normalized['pattern'] in patterns for patterns in simulator.ALGORITHM_PATTERNS.values())
    completed = 0
    def progress(key):
        nonlocal completed
        completed += 1
        if on_progress:
            on_progress(completed / (supported * int(trials)), f"Completed {completed}/{supported * int(trials)} algorithm executions")
    for index in range(int(trials)):
        if time.monotonic() >= deadline:
            result['status'] = 'partial'
            break
        sample = copy.deepcopy(normalized)
        sample['seed'] = (normalized['seed'] + index) % 2**32
        compared = compare_algorithms(sample, deadline=deadline, on_progress=progress)
        for row in compared['rows']:
            result['records'].append(dict(row, trial=index + 1, seed=sample['seed']))
        if compared['status'] not in ('complete', 'partial'):
            result.update(status='partial', message=compared.get('message', 'Initial state generation failed.'))
            break
        if compared['status'] == 'partial' or any(row['status'] == 'not_run' for row in compared['rows']):
            result['status'] = 'partial'
            break
    result['rows'] = aggregate(result['records'])
    if result['status'] == 'partial' and not result['message']:
        result['message'] = 'The trial computation time budget was reached. Completed results are retained; sample counts may differ between algorithms, so direct ranking is inappropriate.'
    else:
        result['message'] = result['message'] or f"Statistics complete: {int(trials)} trials for each supported algorithm."
    return result


def export_csv(result, directory):
    if not result.get('records'):
        return None
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"atommovr_trials_{uuid.uuid4().hex}.csv"
    fields = ['trial', 'seed', 'algorithm', 'status_text', 'filled', 'target_count', 'fill_fraction', 'tweezer_count',
              'max_active_tweezers', 'executed_batches', 'successful_moves', 'successful_distance_um',
              'simulated_time_us', 'losses', 'message', 'config_json']
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for record in result['records']:
            config = dict(result.get('config', {}), seed=record['seed'], algorithm=record['key'])
            if record.get('tweezer_count') is not None:
                config['tweezer_count'] = record['tweezer_count']
            writer.writerow(dict(record, config_json=json.dumps(config, ensure_ascii=False)))
    return str(path)
