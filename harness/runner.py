"""Run LLM1 then the second assessor on the dev set, scoring both against
human references when available (gold-pending items still run LLM1 and the
second assessor; only the human-comparison fields are skipped), and saving
one row per item.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from harness.reviewer import grade_requirement
from harness.judge import assess_requirement
from harness.scorer import compare_to_human, correction_direction, overall_score
from harness.schemas import GOLD_SCHEME, validate_gold_criteria


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / 'data' / 'golden_set.jsonl'
RESULTS_DIR = ROOT / 'results'


def load_dataset(data_path=None):
    """Validate the whole dataset before any model call; select only dev rows.

    A row carries usable gold grades only if it has BOTH `scheme` ==
    GOLD_SCHEME and a `criteria` dict of five 0-5 integers -- a mismatched or
    missing scheme is rejected, never silently reinterpreted. A row with
    neither field is gold-pending: LLM1 and the second assessor still run,
    human-comparison is just skipped for it.
    """
    items, seen = [], set()
    with Path(data_path or DATA_PATH).open(encoding='utf-8') as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if not isinstance(item, dict) or not {'id', 'requirement', 'split'} <= set(item):
                    raise ValueError('Expected at least id, requirement, and split fields.')
                for key in ('id', 'requirement'):
                    if not isinstance(item[key], str) or not item[key].strip():
                        raise ValueError(f'{key} must be a nonblank string.')
                if item['id'] in seen:
                    raise ValueError(f"Duplicate ID: {item['id']}")
                if item['split'] not in ('dev', 'test'):
                    raise ValueError('split must be dev or test.')

                has_scheme = 'scheme' in item
                has_criteria = 'criteria' in item
                if has_scheme != has_criteria:
                    raise ValueError('scheme and criteria must both be present or both absent.')
                if has_scheme:
                    if item['scheme'] != GOLD_SCHEME:
                        raise ValueError(
                            f"Unsupported or mismatched scheme {item['scheme']!r}; "
                            f'expected {GOLD_SCHEME!r}. Refusing to reinterpret it.'
                        )
                    validate_gold_criteria(item['criteria'])
                    extra = set(item) - {'id', 'requirement', 'split', 'scheme', 'criteria', 'gold_score'}
                else:
                    extra = set(item) - {'id', 'requirement', 'split'}
                if extra:
                    raise ValueError(f'Unexpected fields: {sorted(extra)}')
            except (ValueError, TypeError) as error:
                raise ValueError(f'Invalid dataset line {line_number}: {error}') from error
            seen.add(item['id'])
            if item['split'] == 'dev':
                items.append(item)
    if not items:
        raise ValueError('Dataset contains no development items.')
    return items


def print_output(label, value):
    print(f'{label}: {json.dumps(value, ensure_ascii=False, indent=2)}', flush=True)


def run(data_path=None, results_dir=None, limit=None):
    """Save one row per dev item, including stage errors, in a new run file."""
    dataset = load_dataset(data_path)
    if limit is not None:
        if type(limit) is not int or limit < 1:
            raise ValueError('limit must be a positive integer.')
        dataset = dataset[:limit]
    directory = Path(results_dir or RESULTS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output_path = directory / f'pipeline_v4_{timestamp}_{uuid4().hex}.jsonl'
    completed = failed = 0
    interrupted = False

    with output_path.open('x', encoding='utf-8') as output_file:
        print(f'Results file: {output_path}', flush=True)
        print(f'Development items selected: {len(dataset)}', flush=True)
        for item in dataset:
            gold_criteria = item.get('criteria')
            result = {
                'id': item['id'], 'split': item['split'],
                'requirement': item['requirement'],
                'gold_criteria': gold_criteria,
                'gold_score': overall_score(gold_criteria) if gold_criteria else None,
                'llm1_output': None, 'llm1_meta': None,
                'second_assessor_output': None, 'second_assessor_meta': None,
                'comparison': None,
                'status': 'ok', 'error': None,
            }
            print(f"\nID: {item['id']} | Split: {item['split']}", flush=True)
            print(f"Input requirement: {item['requirement']}", flush=True)
            if gold_criteria:
                print_output('Gold criteria', gold_criteria)
            else:
                print('Gold criteria: pending (not yet human-labelled under grade_0_5_v1)', flush=True)
            stage = 'llm1'
            try:
                print('Waiting for LLM1...', flush=True)
                llm1_output, llm1_meta = grade_requirement(item['requirement'])
                result['llm1_output'] = llm1_output.model_dump()
                result['llm1_meta'] = llm1_meta
                print_output('LLM1 output', result['llm1_output'])
                print(f"LLM1 overall_score: {overall_score(llm1_output)}", flush=True)

                stage = 'second_assessor'
                print('Waiting for second assessor...', flush=True)
                second_output, second_meta = assess_requirement(item['requirement'], llm1_output)
                result['second_assessor_output'] = second_output.model_dump()
                result['second_assessor_meta'] = second_meta
                print_output('Second assessor output', result['second_assessor_output'])
                print(f"Second assessor overall_score: {overall_score(second_output)}", flush=True)

                if gold_criteria:
                    stage = 'comparison'
                    result['comparison'] = {
                        'llm1_vs_human': compare_to_human(llm1_output, gold_criteria),
                        'second_vs_human': compare_to_human(second_output, gold_criteria),
                        'correction_direction': correction_direction(
                            llm1_output, second_output, gold_criteria),
                    }
                    print_output('Comparison', result['comparison'])
            except (Exception, KeyboardInterrupt) as error:
                interrupted = isinstance(error, KeyboardInterrupt)
                result['status'] = 'error'
                result['error'] = {
                    'stage': stage,
                    'message': 'Interrupted by user.' if interrupted else str(error),
                }
                print(f'Failed at {stage}: {result["error"]["message"]}', flush=True)
                failed += 1
            else:
                completed += 1
            output_file.write(json.dumps(result, ensure_ascii=False) + '\n')
            output_file.flush()
            print(f"Status: {result['status']}", flush=True)
            print_output('Error', result['error'])
            print(f"Saved {item['id']} to: {output_path}", flush=True)
            if interrupted:
                break

    print(f'\nCompleted: {completed}; Failed: {failed}; Total: {completed + failed}', flush=True)
    print(f'Results saved to: {output_path}', flush=True)
    if interrupted:
        raise KeyboardInterrupt
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, help='Run only the first N dev items.')
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be a positive integer')
    run(limit=args.limit)
