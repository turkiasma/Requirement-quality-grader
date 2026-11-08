"""Export editable CSV proposals and import explicit human review into a NEW dataset."""
import argparse
import csv
import json
from pathlib import Path
from harness.dataset import DATA_PATH, load_dataset
from harness.artifacts import digest, timestamp
from harness.schemas import CRITERIA

FIELDS = ['id', 'requirement', 'split', 'source_sha256', 'annotation_status', 'reviewed_by'] + [
    field for key in CRITERIA for field in (key + '_grade', key + '_explanation')]


def export_review(dataset, output):
    items = load_dataset(dataset, 'all')
    with Path(output).open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for item in items:
            row = {k: item[k] for k in ('id', 'requirement', 'split', 'annotation_status')}
            row.update(source_sha256=digest(item), reviewed_by=item['provenance'].get('reviewed_by', ''))
            for key in CRITERIA:
                row[key + '_grade'] = item['criteria'][key]
                row[key + '_explanation'] = item['justifications'][key]
            writer.writerow(row)


def import_review(dataset, review, output):
    items = load_dataset(dataset, 'all')
    with Path(review).open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError('CSV columns changed; use the exported header.')
        rows = list(reader)
    if len(rows) != len(items) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Review must contain each source item exactly once.')
    by_id = {r['id']: r for r in rows}
    from harness.dataset import validate_item
    for item in items:
        row = by_id.get(item['id'])
        if not row or row['source_sha256'] != digest(item) or any(row[k] != item[k] for k in ('requirement', 'split')):
            raise ValueError('Source changed or review text/split edited; export a fresh review.')
        if row['annotation_status'] not in ('proposed', 'verified'):
            raise ValueError('Status must be proposed or verified.')
        if row['annotation_status'] == 'verified' and not row['reviewed_by'].strip():
            raise ValueError('Explicit reviewer name required for verified annotations.')
        original = {'criteria': item['criteria'], 'justifications': item['justifications']}
        item['criteria'] = {key: int(row[key + '_grade']) for key in CRITERIA}
        item['justifications'] = {key: row[key + '_explanation'].strip() for key in CRITERIA}
        item['gold_score'] = sum(item['criteria'].values()) / 5
        item['annotation_status'] = row['annotation_status']
        item['provenance'].setdefault('initial_proposal', original)
        event = {'imported_at': timestamp(), 'reviewed_by': row['reviewed_by'].strip(),
                 'status': row['annotation_status'], 'review_sha256': digest(Path(review))}
        item['provenance'].setdefault('review_history', []).append(event)
        if row['annotation_status'] == 'verified':
            item['provenance'].update(reviewed_by=event['reviewed_by'], reviewed_at=event['imported_at'])
        else:
            item['provenance'].pop('reviewed_by', None)
            item['provenance'].pop('reviewed_at', None)
        validate_item(item)
    with Path(output).open('x', encoding='utf-8') as stream:
        for item in items:
            stream.write(json.dumps(item, ensure_ascii=False) + '\n')
    return len([item for item in items if item['annotation_status'] == 'verified'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', 'import'])
    parser.add_argument('--data', default=str(DATA_PATH))
    parser.add_argument('--csv', required=True)
    parser.add_argument('--output', help='New JSONL path for import (never overwrites).')
    args = parser.parse_args()
    if args.action == 'export':
        export_review(args.data, args.csv)
        print('Review CSV exported. Change only grades, explanations, status and reviewer name.')
    else:
        if not args.output:
            parser.error('--output is required for import')
        print('Verified items:', import_review(args.data, args.csv, args.output))


if __name__ == '__main__':
    main()
