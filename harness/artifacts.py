"""Small reproducibility helpers shared by evaluation commands."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent


def digest(value):
    if isinstance(value, Path):
        value = value.read_bytes()
    elif not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(value).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def new_path(directory, prefix, suffix='.jsonl'):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / (prefix + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_' + uuid4().hex[:12] + suffix)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def provenance(reviewer_prompt, judge_prompt):
    paths = {'reviewer_prompt': Path(reviewer_prompt), 'judge_prompt': Path(judge_prompt),
             'guide': ROOT / 'data/labelling_guide.md'}
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    sources = {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / 'harness').glob('*.py'))}
    return {'git_commit': commit, 'worktree_dirty': dirty, 'implementation_sha256': digest(sources),
            **{key: {'name': path.name, 'sha256': digest(path)} for key, path in paths.items()}}
