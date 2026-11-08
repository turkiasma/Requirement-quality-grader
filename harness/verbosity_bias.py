"""Controlled redundant explanations, with a repeated-input baseline."""
import argparse
from copy import deepcopy
from harness.schemas import CRITERIA, LLM1Output
from harness.judge import assess_requirement, DEFAULT_MODEL
from harness.scorer import overall_score
from harness.bias_common import record_call, persist_experiment
from harness.metrics import mean, fraction
from harness.artifacts import digest


def pad_assessment(assessment):
    output = deepcopy(LLM1Output.model_validate(assessment).model_dump())
    for value in output['criteria'].values():
        value['explanation'] = ' '.join([value['explanation']] * 3)
    return output


def run_case(record, row, model, index):
    original = row['llm1_output']
    padded = pad_assessment(original)
    record.update(original=original, padded=padded,
        original_sha256=digest(original), padded_sha256=digest(padded),
        padding='Each explanation repeated verbatim three times; grades unchanged.')
    inputs = {'original': original, 'padded': padded, 'repeat_control': original}
    schedule = ['original','padded','repeat_control'] if index % 2 == 0 else ['padded','repeat_control','original']
    record['schedule'] = schedule
    for label in schedule:
        record_call(record, label, lambda: assess_requirement(row['requirement'], inputs[label], model=model))


def changes(records, condition):
    valid = [r for r in records if r['calls'].get('original',{}).get('output') and r['calls'].get(condition,{}).get('output')]
    per = {key: [] for key in CRITERIA}
    totals, examples = [], []
    for r in valid:
        a, b = r['calls']['original']['output'], r['calls'][condition]['output']
        for key in CRITERIA:
            per[key].append(b['criteria'][key]['grade'] - a['criteria'][key]['grade'])
        delta = overall_score(b) - overall_score(a)
        totals.append(delta)
        if a['criteria'] != b['criteria']:
            if any(a['criteria'][k]['grade'] != b['criteria'][k]['grade'] for k in CRITERIA):
                examples.append(r['id'])
    all_deltas = [v for values in per.values() for v in values]
    def describe(ds):
        return {'increased': fraction(sum(d>0 for d in ds), len(ds)),
                'decreased': fraction(sum(d<0 for d in ds), len(ds)),
                'unchanged': fraction(sum(d==0 for d in ds), len(ds)),
                'mean_signed_change': mean(ds), 'mean_absolute_change': mean([abs(d) for d in ds])}
    return {'valid_pairs': len(valid), 'failed_pairs': len(records)-len(valid),
            'criterion_scores': describe(all_deltas), 'overall_scores': describe(totals),
            'per_criterion': {k: describe(v) for k,v in per.items()}, 'affected_case_ids': examples}


def summarize(records):
    return {'interpretation': 'Length sensitivity of requirement grades; repetition may itself affect model behaviour. Small pilot, not causal proof.',
            'cases': len(records), 'valid_complete_cases': sum(r['status']=='ok' for r in records),
            'failed_cases': sum(r['status']!='ok' for r in records),
            'padding_effect': changes(records, 'padded'), 'repeat_control': changes(records, 'repeat_control')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--model', default=DEFAULT_MODEL); parser.add_argument('--output-dir', default='results')
    args = parser.parse_args()
    persist_experiment(args.source, args.output_dir, args.model, args.limit, 'verbosity_bias_v1', run_case, summarize)


if __name__ == '__main__':
    main()
