"""Run the dev pilot and preserve independent scoring and judging per item."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from harness.reviewer import review_requirement
from harness.judge import judge_review
from harness.scorer import score_critique
from harness.schemas import validate_gold_violations


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / 'data' / 'golden_set.jsonl'
RESULTS_DIR = ROOT / 'results'


def load_dataset(data_path=None):
    """Validate the whole dataset before model calls; select only dev rows."""
    items, seen = [], set()
    with Path(data_path or DATA_PATH).open(encoding='utf-8') as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if not isinstance(item, dict) or set(item) != {
                    'id', 'requirement', 'violations', 'split'
                }:
                    raise ValueError('Expected id, requirement, violations, and split fields.')
                for key in ('id', 'requirement'):
                    if not isinstance(item[key], str) or not item[key].strip():
                        raise ValueError(f'{key} must be a nonblank string.')
                if item['id'] in seen:
                    raise ValueError(f"Duplicate ID: {item['id']}")
                if item['split'] not in ('dev', 'test'):
                    raise ValueError('split must be dev or test.')
                validate_gold_violations(item['violations'])
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
    output_path = directory / f'pipeline_v3_{timestamp}_{uuid4().hex}.jsonl'
    completed = failed = 0
    interrupted = False

    with output_path.open('x', encoding='utf-8') as output_file:
        print(f'Results file: {output_path}', flush=True)
        print(f'Development items selected: {len(dataset)}', flush=True)
        for item in dataset:
            result = {
                'id': item['id'], 'split': item['split'],
                'requirement': item['requirement'],
                'gold_violations': item['violations'],
                'reviewer_output': None, 'scorer_output': None,
                'judge_output': None, 'status': 'ok', 'error': None,
            }
            print(f"\nID: {item['id']} | Split: {item['split']}", flush=True)
            print(f"Input requirement: {item['requirement']}", flush=True)
            print_output('Golden violations', item['violations'])
            stage = 'reviewer'
            try:
                print('Waiting for reviewer (qwen3:8b)...', flush=True)
                critique = review_requirement(item['requirement'])
                result['reviewer_output'] = critique.model_dump()
                print_output('Reviewer output', result['reviewer_output'])
                stage = 'scorer'
                result['scorer_output'] = score_critique(item['violations'], critique)
                print_output('Scorer output', result['scorer_output'])
                stage = 'judge'
                print('Waiting for judge (qwen3:8b)...', flush=True)
                result['judge_output'] = judge_review(item['requirement'], critique)
                print(f"Judge score: {result['judge_output']['score']}", flush=True)
                print(f"Reason: {result['judge_output']['reason']}", flush=True)
            except (Exception, KeyboardInterrupt) as error:
                interrupted = isinstance(error, KeyboardInterrupt)
                result['status'] = 'error'
                result['error'] = {
                    'stage': stage,
                    'message': 'Interrupted by user.' if interrupted else str(error),
                }
                print(f'Failed at {stage}: {result["error"]["message"]}', flush=True)
                print('Judge score: unavailable', flush=True)
                print('Reason: unavailable', flush=True)
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
