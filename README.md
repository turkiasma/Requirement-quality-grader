# Requirement Quality Grader

AI Engineering project for evaluating software requirement quality with two
independent LLM assessors, checked against human ground truth.

## Task

Given a software requirement, two independent models each grade it against
five quality criteria on a 0-5 scale:

1. LLM1 grades the requirement and explains each grade.
2. A second assessor independently grades the same requirement, treating
   LLM1's grades as a challengeable proposal it may retain or correct. It
   never sees human reference data.
3. The harness deterministically computes `overall_score = sum(5 grades)/5`
   for both, and compares both against the human reference where available.

This measures agreement on **requirement quality** — it is not a judge that
grades the quality of LLM1's answers. See `docs/IMPLEMENTATION_PLAN.md` for
the full design and open items.

## Quality Criteria

Each graded 0 (fundamentally fails) to 5 (fully satisfies), per
`data/labelling_guide.md`:

- Atomicity
- Testability
- Feasibility
- Clarity
- Completeness

## Evaluation Pipeline

```
Requirement → LLM1 (5 grades + explanations)
            → Second assessor (verify/correct LLM1's grades)
            → Harness (deterministic totals + human comparison)
```

## Project Structure

- `data/` — golden dataset(s) and labelling guide
- `prompts/` — versioned prompts + `CHANGELOG.md`
- `harness/` — evaluation pipeline (`reviewer.py`=LLM1, `judge.py`=second
  assessor, `scorer.py`=deterministic aggregation/comparison,
  `llm_client.py`=shared OpenRouter client, `schemas.py`, `runner.py`)
- `results/` — evaluation outputs, one row per item per run
- `tests/` — synthetic-fixture tests (pipeline behaviour, not model quality)
- `docs/IMPLEMENTATION_PLAN.md` — design, gap analysis, open items

## Dataset status

`data/golden_set.jsonl` (20 items) uses the **old binary scheme** and is kept
as historical data only — the runner rejects it outright rather than
reinterpreting its 0/1 values as 0-5 grades.

`data/golden_set_pending.jsonl` carries the same 20 requirement texts with
**no gold grades yet** — LLM1 and the second assessor run on it today; the
human-comparison fields are simply skipped until the 20-item pilot is
re-labelled by two humans under the `grade_0_5_v1` scheme (see
`docs/IMPLEMENTATION_PLAN.md` §4). The final project will contain 150+
double-labelled requirements under this scheme.

## Setup

Use Python 3.10+ and install dependencies in a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Model calls go through the OpenRouter API. Put your key in a local `.env`
(gitignored, never commit it) — copy `.env.example` and fill it in:

```sh
cp .env.example .env
# edit .env: OPENROUTER_API_KEY=sk-or-...
```

Default model is `openai/gpt-4o-mini` for both LLM1 and the second assessor;
override with the `REVIEWER_MODEL` / `ASSESSOR_MODEL` environment variables.

## Run the pipeline

```sh
python -m harness.runner
```

Runs every `dev`-split item in `data/golden_set.jsonl` by default. Point it
at the gold-pending dataset instead for a live run today:

```python
from harness.runner import run
run(data_path='data/golden_set_pending.jsonl')
```

For a quick check of one item:

```sh
python -m harness.runner --limit 1
```

The terminal shows the requirement, gold criteria (or "pending"), LLM1's
output and overall score, the second assessor's output and overall score,
and the human-comparison result when gold is available. Each saved JSONL row
in `results/` contains the full record — both model outputs, both computed
scores, the comparison, per-call latency/model metadata, and status/error.
Human reference grades are included in the saved record but are **never**
sent in a model request (structurally enforced — see
`harness/judge.py:assess_requirement`'s signature and
`harness/schemas.py:LLM1Output`'s `extra='forbid'`).

Ctrl+C saves whatever stage completed for the in-progress item before
stopping. Existing run files are never overwritten.

## Tests

```sh
python -m unittest discover -s tests
```

Tests use synthetic fixtures and mock model calls — no API key or network
access required. They verify pipeline behavior (leakage prevention, dataset
scheme-version rejection, aggregation math, stage-failure handling), not
model quality or human agreement.

## Current limits

No human agreement, judge reliability, bias studies, or aggregate quality
metrics have been measured yet — real re-labelled human data under
`grade_0_5_v1` doesn't exist. See `docs/IMPLEMENTATION_PLAN.md` for what's
left before those can be reported.
