"""Run the dev pilot and preserve independent scoring and judging per item."""

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


def print_result(result):
    print(f"\nID: {result['id']} | Split: {result['split']}")
    print(f"Input requirement: {result['requirement']}")
    for label, key in (
        ('Golden violations', 'gold_violations'),
        ('Reviewer output', 'reviewer_output'),
        ('Scorer output', 'scorer_output'),
    ):
        print(f'{label}: {json.dumps(result[key], ensure_ascii=False, indent=2)}')
    judgment = result['judge_output']
    print(f"Judge score: {judgment['score'] if judgment else 'unavailable'}")
    print(f"Reason: {judgment['reason'] if judgment else 'unavailable'}")
    print(f"Status: {result['status']}")
    print(f"Error: {json.dumps(result['error'], ensure_ascii=False)}")


def run(data_path=None, results_dir=None):
    """Save one row per dev item, including stage errors, in a new run file."""
    dataset = load_dataset(data_path)
    directory = Path(results_dir or RESULTS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output_path = directory / f'pipeline_v2_{timestamp}_{uuid4().hex}.jsonl'
    completed = failed = 0

    with output_path.open('x', encoding='utf-8') as output_file:
        for item in dataset:
            result = {
                'id': item['id'], 'split': item['split'],
                'requirement': item['requirement'],
                'gold_violations': item['violations'],
                'reviewer_output': None, 'scorer_output': None,
                'judge_output': None, 'status': 'ok', 'error': None,
            }
            stage = 'reviewer'
            try:
                critique = review_requirement(item['requirement'])
                result['reviewer_output'] = critique.model_dump()
                stage = 'scorer'
                result['scorer_output'] = score_critique(item['violations'], critique)
                stage = 'judge'
                result['judge_output'] = judge_review(item['requirement'], critique)
            except Exception as error:
                result['status'] = 'error'
                result['error'] = {'stage': stage, 'message': str(error)}
                failed += 1
            else:
                completed += 1
            output_file.write(json.dumps(result, ensure_ascii=False) + '\n')
            output_file.flush()
            print_result(result)

    print(f'\nCompleted: {completed}; Failed: {failed}; Total: {len(dataset)}')
    print(f'Results saved to: {output_path}')
    return output_path


if __name__ == '__main__':
    run()
