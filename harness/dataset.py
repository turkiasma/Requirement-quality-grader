"""Validate versioned references before model calls; no provider dependencies."""
import json
import math
from pathlib import Path
from harness.schemas import CRITERIA, GOLD_SCHEME, GUIDE_VERSION, validate_gold_criteria
from harness.artifacts import ROOT

DATA_PATH = ROOT / 'data/golden_set.jsonl'


def validate_item(item):
    required = {'id', 'requirement', 'split', 'scheme', 'guide_version', 'criteria',
                'justifications', 'gold_score', 'annotation_status', 'provenance'}
    if not isinstance(item, dict) or set(item) != required:
        raise ValueError('Expected exactly the versioned reference fields; scheme and criteria are required.')
    for field in ('id', 'requirement'):
        if not isinstance(item[field], str) or not item[field].strip():
            raise ValueError(f'{field} must be nonblank.')
    if item['scheme'] != GOLD_SCHEME or item['guide_version'] != GUIDE_VERSION:
        raise ValueError('Unsupported or mismatched scheme/guide version; historical data must be migrated.')
    if item['split'] not in ('dev', 'test'):
        raise ValueError('split must be dev or test.')
    validate_gold_criteria(item['criteria'])
    reasons = item['justifications']
    if not isinstance(reasons, dict) or set(reasons) != set(CRITERIA) or any(
            not isinstance(v, str) or not v.strip() for v in reasons.values()):
        raise ValueError('Five nonblank reference justifications are required.')
    score = item['gold_score']
    if type(score) not in (int, float) or not math.isfinite(score) or score != sum(item['criteria'].values()) / 5:
        raise ValueError('gold_score must equal the unrounded five-grade mean.')
    if item['annotation_status'] not in ('proposed', 'verified'):
        raise ValueError('Invalid annotation_status.')
    source = item['provenance']
    if not isinstance(source, dict) or not source.get('prepared_by') or not source.get('prepared_at'):
        raise ValueError('Annotation preparation provenance is required.')
    if item['annotation_status'] == 'verified' and not all(source.get(k) for k in ('reviewed_by', 'reviewed_at')):
        raise ValueError('Verified references require named human review and timestamp.')
    return item


def load_dataset(data_path=None, split='dev'):
    if split not in ('dev', 'test', 'all'):
        raise ValueError('split must be dev, test, or all.')
    items, ids, texts = [], set(), set()
    with Path(data_path or DATA_PATH).open(encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = validate_item(json.loads(line))
                text = ' '.join(item['requirement'].casefold().split())
                if item['id'] in ids or text in texts:
                    raise ValueError('Duplicate ID or normalized requirement text (including cross-split duplicates).')
                ids.add(item['id']); texts.add(text); items.append(item)
            except (ValueError, TypeError, KeyError) as error:
                raise ValueError(f'Invalid dataset line {number}: {error}') from error
    selected = [item for item in items if split == 'all' or item['split'] == split]
    if not selected:
        raise ValueError('Dataset contains no development items.' if split == 'dev' else 'No selected items.')
    return selected
