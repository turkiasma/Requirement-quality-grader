"""Pairwise order-swap diagnostic, separate from production requirement grading."""
import argparse
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator
from harness.schemas import _nonblank
from harness.artifacts import ROOT, digest
from harness.llm_client import call_structured
from harness.judge import DEFAULT_MODEL, GUIDE_PATH
from harness.bias_common import candidate_from_judge, record_call, persist_experiment
from harness.metrics import fraction

PROMPT_PATH = ROOT / 'prompts/position_prompt_v1.txt'


class PairwiseOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    winner: Literal['A', 'B', 'tie']
    reason: str
    @field_validator('reason')
    @classmethod
    def nonblank(cls, value):
        return _nonblank(value)


def identity(winner, order):
    return 'tie' if winner == 'tie' else order[0 if winner == 'A' else 1]


def compare(requirement, a, b, model):
    return call_structured(model=model, system=PROMPT_PATH.read_text() + '\n\n' + GUIDE_PATH.read_text(),
        user=json.dumps({'requirement': requirement, 'A': a, 'B': b}), schema_model=PairwiseOutput, max_tokens=512)


def run_case(record, row, model, index):
    candidates = {'initial': row['llm1_output'], 'corrected': candidate_from_judge(row['second_assessor_output'])}
    record.update(candidates=candidates, candidate_sha256={k: digest(v) for k,v in candidates.items()},
                  prompt_sha256=digest(PROMPT_PATH), orders={'AB': ['initial','corrected'], 'BA':['corrected','initial']})
    # Counterbalance which ordering is requested first; content remains fixed.
    schedule = ['AB', 'BA'] if index % 2 == 0 else ['BA', 'AB']
    record['schedule'] = schedule
    for label in schedule:
        order = record['orders'][label]
        record_call(record, label, lambda: compare(row['requirement'], candidates[order[0]], candidates[order[1]], model))
    record['preferences'] = {label: identity(call['output']['winner'], record['orders'][label])
                              if call['output'] else None for label, call in record['calls'].items()}


def summarize(records):
    valid = [r for r in records if r['status'] == 'ok']
    non_tie_pairs = [r for r in valid if 'tie' not in r['preferences'].values()]
    choices = [c['output']['winner'] for r in valid for c in r['calls'].values() if c['output']['winner'] != 'tie']
    changed = [r for r in valid if r['preferences']['AB'] != r['preferences']['BA']]
    return {'interpretation': 'Auxiliary pairwise position sensitivity, not production single-assessment bias.',
            'cases': len(records), 'valid': len(valid), 'failed': len(records)-len(valid),
            'preference_reversal': fraction(sum(r['preferences']['AB'] != r['preferences']['BA'] for r in non_tie_pairs), len(non_tie_pairs)),
            'identity_or_tie_change': fraction(len(changed), len(valid)),
            'tie_change': fraction(sum(('tie' in r['preferences'].values()) for r in changed), len(valid)),
            'first_position_preference': fraction(choices.count('A'), len(choices)),
            'inconsistent_case_ids': [r['id'] for r in changed]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--model', default=DEFAULT_MODEL); parser.add_argument('--output-dir', default='results')
    args = parser.parse_args()
    persist_experiment(args.source, args.output_dir, args.model, args.limit, 'position_bias_v1', run_case, summarize)


if __name__ == '__main__':
    main()
