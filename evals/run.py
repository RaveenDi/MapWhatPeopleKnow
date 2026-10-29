"""Paired, budgeted evaluation. Ground truth is used only after inference."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps' / 'api'))
from app import pipeline


def media(path, base):
    resolved = (base / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('Evaluation media must be inside the repository')
    return resolved.read_bytes()


def inputs(row, mode, base):
    # Explicit allowlist: never pass row or ground_truth to the pipeline/provider.
    raw_area = row['area']
    area = {'name': raw_area['name'], 'gazetteer': {key: {field: place[field] for field in ('name', 'lon', 'lat') if field in place} for key, place in raw_area['gazetteer'].items()}}
    sketch, labels, transcript, audio, audio_name = None, [], None, None, ''
    if mode in ('sketch', 'both'):
        source = row.get('sketch') or {}
        if isinstance(source, str):
            sketch = media(source, base)
        else:
            labels = [{k: label[k] for k in ('label', 'x', 'y', 'relations') if k in label} for label in source.get('labels', [])]
            if source.get('image'):
                sketch = media(source['image'], base)
    if mode in ('speech', 'both'):
        source = row.get('audio_or_transcript')
        if isinstance(source, str):
            transcript = source
        elif source:
            if 'transcript' in source:
                transcript = source['transcript']
            elif 'audio' in source:
                audio = media(source['audio'], base)
                audio_name = Path(source['audio']).name
    return area, transcript, audio, audio_name, sketch, labels


def pr(predicted, expected):
    tp = len(predicted & expected)
    return {'tp': tp, 'predicted': len(predicted), 'expected': len(expected),
            'precision': tp / len(predicted) if predicted else (1.0 if not expected else 0.0),
            'recall': tp / len(expected) if expected else 1.0}


def score(run, truth):
    entities = {o.entity for o in run['observations']}
    relations = {(o.entity, o.predicate, o.value) for o in run['observations'] if o.predicate != 'marked_on_sketch'}
    expected_relations = {(r['entity'], r['predicate'], str(r['value'])) for r in truth['relations']}
    surfaced = {(c.entity, c.predicate) for c in run['contradictions']}
    expected_c = {(c['entity'], c['predicate']) for c in truth['contradictions']}
    expected_a = {(a['entity'], a['gazetteer_id']) for a in truth['anchors']}
    wrong_accepted = sum((a.entity, a.entity) not in expected_a for a in run['anchors'] if a.status == 'confirmed')
    wrong_proposed = sum((a.entity, a.entity) not in expected_a for a in run['anchors'] if a.status == 'proposed')
    return {'entity': pr(entities, set(truth['entities'])), 'relation': pr(relations, expected_relations),
            'contradiction': pr(surfaced, expected_c), 'contradictions_surfaced': len(surfaced),
            'wrong_accepted_anchors': wrong_accepted, 'accepted_anchors': sum(a.status == 'confirmed' for a in run['anchors']),
            'wrong_proposed_anchors': wrong_proposed}


def evaluate(rows, provider, split, modes, max_calls, base=ROOT / 'evals'):
    if provider not in ('mock', 'replay', 'meta') or max_calls < 0:
        raise ValueError('Invalid provider or call cap')
    previous = os.environ.get('MODEL_PROVIDER')
    os.environ['MODEL_PROVIDER'] = provider
    results, used = [], 0
    try:
        for row in rows:
            if row['split'] != split:
                continue
            for mode in modes:
                start = time.perf_counter()
                run = pipeline.create_run(*inputs(row, mode, base), max_calls=max(0, max_calls-used))
                totals = run['_session'].totals()
                used += totals['calls']
                results.append({'id': row['id'], 'mode': mode, 'status': run['status'], 'metrics': score(run, row['ground_truth']),
                                'telemetry': totals, 'wall_latency_ms': round((time.perf_counter()-start)*1000, 3)})
                pipeline.RUNS.pop(run['id'], None)
    finally:
        if previous is None:
            os.environ.pop('MODEL_PROVIDER', None)
        else:
            os.environ['MODEL_PROVIDER'] = previous
    summary = {}
    for mode in modes:
        group = [r for r in results if r['mode'] == mode]
        aggregate = {}
        for metric in ('entity', 'relation', 'contradiction'):
            tp, pred, expected = (sum(r['metrics'][metric][key] for r in group) for key in ('tp', 'predicted', 'expected'))
            aggregate[metric] = {'precision': tp/pred if pred else (1.0 if not expected else 0.0), 'recall': tp/expected if expected else 1.0, 'tp': tp, 'predicted': pred, 'expected': expected}
        for metric in ('contradictions_surfaced', 'wrong_accepted_anchors', 'accepted_anchors', 'wrong_proposed_anchors'):
            aggregate[metric] = sum(r['metrics'][metric] for r in group)
        aggregate['telemetry'] = {k: sum(r['telemetry'][k] for r in group) for k in ('steps', 'calls', 'tokens', 'latency_ms', 'estimated_cost_usd')}
        aggregate['incomplete_runs'] = sum(r['status'].startswith('partial') or r['status'] == 'unresolved' for r in group)
        summary[mode] = aggregate
    return {'provider': provider, 'split': split, 'max_calls': max_calls, 'calls': used,
            'evidence_status': 'Synthetic/mock results test plumbing only; model accuracy and user benefit UNVERIFIED.',
            'pricing_status': 'Published Standard rates (verified 2026-10-30); missing usage/cost is incomplete, not measured zero.',
            'summary': summary, 'cases': results}


def markdown(report):
    lines = ['# Modality comparison', '', report['evidence_status'], '', report['pricing_status'], '',
             '| mode | entity P/R | relation P/R | contradictions surfaced | wrong accepted / accepted | steps | calls | tokens | provider ms | estimated USD | incomplete |',
             '|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|']
    for mode, s in report['summary'].items():
        t = s['telemetry']
        lines.append(f"| {mode} | {s['entity']['precision']:.3f}/{s['entity']['recall']:.3f} | {s['relation']['precision']:.3f}/{s['relation']['recall']:.3f} | {s['contradictions_surfaced']} | {s['wrong_accepted_anchors']}/{s['accepted_anchors']} | {t['steps']} | {t['calls']} | {t['tokens']} | {t['latency_ms']:.2f} | {t['estimated_cost_usd']:.8f} | {s['incomplete_runs']} |")
    lines += ['', 'No simulated user confirms anchors. Zero wrong accepted anchors with zero accepted anchors is not evidence of matching accuracy.', 'Full case-level metrics and usage completeness are in the JSON report.', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['mock', 'replay', 'meta'], required=True)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'evals' / 'manifest.jsonl')
    parser.add_argument('--split', choices=['dev', 'heldout'], required=True)
    parser.add_argument('--mode', choices=['sketch', 'speech', 'both'], help='Omit for paired three-mode comparison')
    parser.add_argument('--max-calls', type=int, required=True, help='Global cap including retries/repair across all cases and modes')
    args = parser.parse_args(argv)
    rows = [json.loads(line) for line in args.manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    report = evaluate(rows, args.provider, args.split, [args.mode] if args.mode else ['sketch', 'speech', 'both'], args.max_calls, args.manifest.resolve().parent)
    directory = ROOT / 'evals' / 'reports'
    directory.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = directory / f'{stamp}-{args.split}'
    output.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    output.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
    print(f'{output}.{{json,md}}; {report["calls"]}/{args.max_calls} calls')
    return report

if __name__ == '__main__':
    main()
