"""Shared experiment inputs and persistence; never uses reference labels in requests."""
import json
from pathlib import Path
from harness.artifacts import read_jsonl, digest, new_path, write_json, timestamp, provenance
from harness.schemas import LLM1Output, CRITERIA
from harness.reviewer import PROMPT_PATH as REVIEWER_PROMPT
from harness.judge import PROMPT_PATH as JUDGE_PROMPT
from harness.metrics import usage_summary


def select_cases(source, limit):
    if type(limit) is not int or limit < 1:
        raise ValueError('limit must be positive.')
    rows = read_jsonl(source)
    if any(r.get('result_version') != 'pipeline_v5' for r in rows):
        raise ValueError('Use v5 results; historical grading conventions are incompatible.')
    chosen = [r for r in rows if r['split'] == 'dev' and r.get('llm1_output') and r.get('second_assessor_output')]
    if not chosen:
        raise ValueError('No complete development assessments available.')
    if len({r['id'] for r in chosen}) != len(chosen):
        raise ValueError('Duplicate case IDs.')
    return chosen[:limit]


def candidate_from_judge(output):
    return LLM1Output.model_validate({'criteria': {k: {'grade': output['criteria'][k]['grade'],
        'explanation': output['criteria'][k]['explanation']} for k in CRITERIA}}).model_dump()


def experiment_record(row, source, model, kind):
    return {'experiment': kind, 'id': row['id'], 'split': 'dev', 'requirement': row['requirement'],
            'timestamp': timestamp(), 'source_sha256': digest(Path(source)), 'model': model,
            'configuration': provenance(REVIEWER_PROMPT, JUDGE_PROMPT),
            'temperature': 0, 'calls': {}, 'errors': [], 'status': 'ok'}


def record_call(record, label, function):
    try:
        output, meta = function()
        record['calls'][label] = {'output': output.model_dump(), 'metadata': meta}
    except Exception as error:
        record['calls'][label] = {'output': None, 'metadata': getattr(error, 'metadata', {})}
        record['errors'].append({'condition': label, 'message': str(error)})
        record['status'] = 'error'


def persist_experiment(source, directory, model, limit, kind, case_function, summary_function):
    cases = select_cases(source, limit)
    path = new_path(directory, kind)
    records = []
    with path.open('x', encoding='utf-8') as stream:
        for index, row in enumerate(cases):
            record = experiment_record(row, source, model, kind)
            case_function(record, row, model, index)
            stream.write(json.dumps(record, ensure_ascii=False) + '\n'); stream.flush(); records.append(record)
            print(f"{kind}: {row['id']} {record['status']}", flush=True)
    summary = summary_function(records)
    summary['usage'] = usage_summary([c['metadata'] for r in records for c in r['calls'].values()])
    summary['source_sha256'] = digest(Path(source))
    write_json(path.with_suffix('.summary.json'), summary)
    print('Results:', path)
    return path
