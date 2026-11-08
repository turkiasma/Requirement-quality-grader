"""Offline reliability summaries, partitioned by split and reference review status."""
import argparse
import json
from pathlib import Path
from harness.schemas import CRITERIA
from harness.scorer import _as_grade_dict, overall_score
from harness.artifacts import read_jsonl, new_path, write_json


def fraction(count, denominator):
    return {'count': count, 'denominator': denominator,
            'percent': 100 * count / denominator if denominator else None}


def mean(values):
    return sum(values) / len(values) if values else None


def stage_metrics(rows, field, tolerance=0.2):
    valid = [row for row in rows if row.get(field) is not None]
    differences = {key: [] for key in CRITERIA}
    totals, all_match = [], 0
    for row in valid:
        grades = _as_grade_dict(row[field])
        gold = row['gold_criteria']
        for key in CRITERIA:
            differences[key].append(grades[key] - gold[key])
        totals.append(overall_score(grades) - overall_score(gold))
        all_match += grades == gold
    n = len(valid)
    return {'valid': n, 'unavailable': len(rows) - n,
            'per_criterion': {key: {
                'exact': fraction(sum(d == 0 for d in ds), n),
                'within_one': fraction(sum(abs(d) <= 1 for d in ds), n),
                'disagreement': fraction(sum(d != 0 for d in ds), n),
                'mae': mean([abs(d) for d in ds])} for key, ds in differences.items()},
            'overall': {'mae': mean([abs(d) for d in totals]), 'mean_signed_error': mean(totals),
                        'exact': fraction(sum(abs(d) < 1e-12 for d in totals), n),
                        'tolerance': tolerance,
                        'within_tolerance': fraction(sum(abs(d) <= tolerance + 1e-12 for d in totals), n),
                        'all_five_match': fraction(all_match, n)}}


def correction_metrics(rows):
    paired = [r for r in rows if r.get('llm1_output') and r.get('second_assessor_output')]
    retained = closer = farther = equal = 0
    overall = {'improved': 0, 'worsened': 0, 'unchanged': 0}
    for row in paired:
        a, b = _as_grade_dict(row['llm1_output']), _as_grade_dict(row['second_assessor_output'])
        gold = row['gold_criteria']
        for key in CRITERIA:
            if a[key] == b[key]:
                retained += 1
            else:
                delta = abs(b[key] - gold[key]) - abs(a[key] - gold[key])
                closer += delta < 0; farther += delta > 0; equal += delta == 0
        delta = abs(overall_score(b) - overall_score(gold)) - abs(overall_score(a) - overall_score(gold))
        overall['unchanged' if abs(delta) < 1e-12 else 'improved' if delta < 0 else 'worsened'] += 1
    total = len(paired) * 5
    corrected = total - retained
    return {'paired_requirements': len(paired), 'retained': fraction(retained, total),
            'corrected': fraction(corrected, total), 'closer': fraction(closer, corrected),
            'farther': fraction(farther, corrected), 'equal_error_corrections': fraction(equal, corrected),
            'overall_error': {k: fraction(v, len(paired)) for k, v in overall.items()}}


def usage_summary(metadata):
    calls = [m for m in metadata if m]
    known = [m for m in calls if m.get('estimated_cost_usd') is not None]
    cost = sum(m['estimated_cost_usd'] for m in known)
    return {'calls_recorded': len(calls), 'costed_calls': len(known),
            'unknown_cost_calls': len(calls) - len(known),
            'estimated_cost_usd': cost,
            'unknown_cost_reservations_usd': sum(m.get('budget_reserved_usd', 0) for m in calls if m.get('estimated_cost_usd') is None),
            'prompt_tokens': sum(m.get('prompt_tokens') or 0 for m in calls),
            'completion_tokens': sum(m.get('completion_tokens') or 0 for m in calls),
            'total_tokens': sum(m.get('total_tokens') or 0 for m in calls),
            'summed_latency_seconds': sum(m.get('latency_seconds') or 0 for m in calls)}


def summarize(rows, tolerance=0.2):
    if tolerance < 0:
        raise ValueError('Tolerance must be nonnegative.')
    # Historical formats cannot silently become reference reliability evidence.
    if any(r.get('result_version') != 'pipeline_v5' for r in rows):
        raise ValueError('Only versioned v5 pipeline results can be summarized.')
    groups = {}
    for split in ('dev', 'test'):
        for status in ('proposed', 'verified'):
            subset = [r for r in rows if r['split'] == split and r['annotation_status'] == status]
            if subset:
                groups[f'{split}/{status}'] = {
                    'interpretation': 'human-reference agreement' if status == 'verified' else 'provisional AI-reference comparison',
                    'items': len(subset), 'failed': fraction(sum(r['status'] != 'ok' for r in subset), len(subset)),
                    'llm1': stage_metrics(subset, 'llm1_output', tolerance),
                    'judge': stage_metrics(subset, 'second_assessor_output', tolerance),
                    'corrections': correction_metrics(subset)}
    usage = usage_summary([r.get(stage + '_meta') for r in rows for stage in ('llm1', 'second_assessor')])
    complete = [r for r in rows if r['status'] == 'ok' and all(
        (r.get(s + '_meta') or {}).get('estimated_cost_usd') is not None for s in ('llm1', 'second_assessor'))]
    per_item_cost = mean([sum(r[s + '_meta']['estimated_cost_usd'] for s in ('llm1', 'second_assessor')) for r in complete])
    return {'result_version': 'summary_v1', 'items': len(rows), 'groups': groups, 'usage': usage,
            'usage_by_stage': {s: usage_summary([r.get(s + '_meta') for r in rows]) for s in ('llm1', 'second_assessor')},
            'latency_per_completed_requirement_seconds': mean([sum((r.get(s + '_meta') or {}).get('latency_seconds', 0) for s in ('llm1', 'second_assessor')) for r in rows if r['status'] == 'ok']),
            'cost_projection': {'basis_complete_items': len(complete), 'per_requirement_usd': per_item_cost,
                'per_1000_requirements_usd': per_item_cost * 1000 if per_item_cost is not None else None,
                'at_100x_1000_requirements_usd': per_item_cost * 100000 if per_item_cost is not None else None,
                'assumptions': 'Two calls per requirement; fixed observed workload/prices, no retries, no bias runs; not a scaling benchmark.'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results')
    parser.add_argument('--tolerance', type=float, default=0.2)
    parser.add_argument('--output-dir', default='results')
    args = parser.parse_args()
    report = summarize(read_jsonl(args.results), args.tolerance)
    path = new_path(args.output_dir, 'metrics', '.json')
    write_json(path, report)
    print(json.dumps(report, indent=2)); print('Summary:', path)


if __name__ == '__main__':
    main()
