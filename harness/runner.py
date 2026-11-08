"""Grade selected requirements, preserve partial failures, and summarize reference agreement."""
import argparse
import json
from pathlib import Path
from harness.artifacts import ROOT, digest, timestamp, new_path, provenance, write_json
from harness.dataset import DATA_PATH, load_dataset
from harness.reviewer import grade_requirement, DEFAULT_MODEL as REVIEWER_MODEL, PROMPT_PATH as REVIEWER_PROMPT
from harness.judge import assess_requirement, DEFAULT_MODEL as JUDGE_MODEL, PROMPT_PATH as JUDGE_PROMPT
from harness.schemas import GUIDE_VERSION, GOLD_SCHEME
from harness.scorer import compare_to_human, correction_direction, overall_score
from harness.metrics import summarize

RESULTS_DIR = ROOT / 'results'


def print_output(label, value):
    print(f'{label}: {json.dumps(value, ensure_ascii=False, indent=2)}', flush=True)


def configuration(data_path, reviewer_model, judge_model, reviewer_prompt, judge_prompt):
    return {'scheme': GOLD_SCHEME, 'guide_version': GUIDE_VERSION,
            'dataset_sha256': digest(Path(data_path)), 'pricing_sha256': digest(ROOT / 'data/model_pricing.json'), 'reviewer_model': reviewer_model,
            'judge_model': judge_model, 'temperature': 0, 'max_tokens': 1024,
            **provenance(reviewer_prompt, judge_prompt)}


def run(data_path=None, results_dir=None, limit=None, split='dev', reviewer_model=REVIEWER_MODEL,
        judge_model=JUDGE_MODEL, reviewer_prompt=None, judge_prompt=None, dry_run=False,
        frozen_config=None, freeze=False):
    data_path = Path(data_path or DATA_PATH)
    dataset = load_dataset(data_path, split)
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError('limit must be a positive integer.')
    # Require all test references reviewed, even when a limit is requested.
    if not dry_run and any(i['split'] == 'test' and i['annotation_status'] != 'verified' for i in dataset):
        raise ValueError('Held-out test execution is blocked until all selected test references are verified.')
    reviewer_prompt, judge_prompt = Path(reviewer_prompt or REVIEWER_PROMPT), Path(judge_prompt or JUDGE_PROMPT)
    config = configuration(data_path, reviewer_model, judge_model, reviewer_prompt, judge_prompt)
    directory = Path(results_dir or RESULTS_DIR)
    if frozen_config:
        previous = json.loads(Path(frozen_config).read_text())
        # Git commit/dirty status may change after committing a frozen configuration.
        relevant = lambda c: {k: v for k, v in c.items() if k not in ('git_commit', 'worktree_dirty')}
        if relevant(previous) != relevant(config):
            raise ValueError('Frozen configuration differs from data, implementation, pricing, prompts or models.')
    if not dry_run and any(i['split'] == 'test' for i in dataset) and not frozen_config:
        raise ValueError('Test execution requires --frozen-config from an offline --freeze run.')
    if limit:
        dataset = dataset[:limit]
    if dry_run:
        print_output('Validated selection', {'items': len(dataset), 'split': split,
                    'verified': sum(i['annotation_status'] == 'verified' for i in dataset), 'configuration': config})
        if freeze:
            path = new_path(directory, 'frozen_config', '.json'); write_json(path, config)
            print('Frozen configuration:', path); return path
        return None
    if freeze:
        raise ValueError('--freeze requires --dry-run.')
    output_path = new_path(directory, 'pipeline_v5')
    rows = []
    interrupted = False
    with output_path.open('x', encoding='utf-8') as stream:
        print('Results file:', output_path, flush=True)
        for item in dataset:
            result = {'result_version': 'pipeline_v5', 'run_id': output_path.stem,
                'timestamp': timestamp(), 'id': item['id'], 'split': item['split'], 'requirement': item['requirement'],
                'annotation_status': item['annotation_status'], 'reference': item,
                'gold_criteria': item['criteria'], 'gold_score': item['gold_score'],
                'configuration': config, 'llm1_output': None, 'llm1_meta': None, 'llm1_overall_score': None,
                'second_assessor_output': None, 'second_assessor_meta': None, 'judge_overall_score': None,
                'comparison': {'llm1_vs_reference': None, 'judge_vs_reference': None, 'correction_direction': None},
                'grade_changes': None, 'status': 'ok', 'error': None}
            print(f"\nID: {item['id']} | Split: {item['split']} | Reference: {item['annotation_status']}", flush=True)
            print('Input requirement:', item['requirement'], flush=True)
            stage = 'llm1'
            try:
                print('Waiting for LLM1...', flush=True)
                a, meta = grade_requirement(item['requirement'], model=reviewer_model, prompt_path=reviewer_prompt)
                result.update(llm1_output=a.model_dump(), llm1_meta=meta, llm1_overall_score=overall_score(a))
                print_output('LLM1 output', result['llm1_output'])
                print('LLM1 overall score:', result['llm1_overall_score'], flush=True)
                stage = 'second_assessor'
                print('Waiting for judge...', flush=True)
                b, meta = assess_requirement(item['requirement'], a, model=judge_model, prompt_path=judge_prompt)
                result.update(second_assessor_output=b.model_dump(), second_assessor_meta=meta, judge_overall_score=overall_score(b))
                result['comparison']['judge_vs_reference'] = compare_to_human(b, item['criteria'])
                result['comparison']['correction_direction'] = correction_direction(a, b, item['criteria'])
                result['grade_changes'] = {k: b.criteria[k].grade - v.grade for k, v in a.criteria.items()}
                print_output('Judge output', result['second_assessor_output'])
                print('Judge overall score:', result['judge_overall_score'], flush=True)
            except (Exception, KeyboardInterrupt) as error:
                interrupted = isinstance(error, KeyboardInterrupt)
                result['status'] = 'error'
                result['error'] = {'stage': stage, 'message': 'Interrupted by user.' if interrupted else str(error)}
                if hasattr(error, 'metadata'):
                    result[stage + '_meta'] = error.metadata
                print_output('Error', result['error'])
            if result['llm1_output'] is not None:
                result['comparison']['llm1_vs_reference'] = compare_to_human(result['llm1_output'], item['criteria'])
            stream.write(json.dumps(result, ensure_ascii=False) + '\n'); stream.flush(); rows.append(result)
            if interrupted:
                break
    summary_path = output_path.with_suffix('.summary.json')
    write_json(summary_path, summarize(rows))
    failed = sum(r['status'] != 'ok' for r in rows)
    print(f'Completed: {len(rows)-failed}; Failed: {failed}; Output: {output_path}', flush=True)
    print('Summary:', summary_path, flush=True)
    if interrupted:
        raise KeyboardInterrupt
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default=str(DATA_PATH))
    parser.add_argument('--split', choices=['dev', 'test', 'all'], default='dev')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--output-dir', default=str(RESULTS_DIR))
    parser.add_argument('--reviewer-model', default=REVIEWER_MODEL)
    parser.add_argument('--judge-model', default=JUDGE_MODEL)
    parser.add_argument('--reviewer-prompt', default=str(REVIEWER_PROMPT))
    parser.add_argument('--judge-prompt', default=str(JUDGE_PROMPT))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--frozen-config')
    args = vars(parser.parse_args())
    args['data_path'] = args.pop('data'); args['results_dir'] = args.pop('output_dir')
    run(**args)


if __name__ == '__main__':
    main()
