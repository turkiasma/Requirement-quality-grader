# Requirement Quality Grader

AI Engineering project for evaluating LLM-generated critiques of software requirements.

## Task

Given a software requirement, the system:
1. Identifies violated requirement-quality criteria.
2. Explains each detected issue.
3. Proposes an improved requirement.

## Quality Criteria

- Atomicity
- Testability
- Feasibility
- Clarity
- Completeness

## Evaluation Pipeline

Requirement → Human-labelled golden set → LLM critique system → LLM judge → Evaluation against human judgement

## Project Structure

- `data/` — golden dataset and labelling guide
- `prompts/` — system and judge prompts
- `harness/` — evaluation pipeline
- `results/` — evaluation outputs
- `tests/` — tests

Golden-set labels use binary criterion violations: `true` means a problem is present, and `false` means the criterion is satisfied. The current 20 examples are an initial dev pilot with provisional labels awaiting human review. The final project will contain 150+ double-labelled requirements.

## Setup

Use Python 3.10+ and install the Python dependencies in a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For live runs, install and start Ollama separately, then download the default model:

```sh
ollama pull qwen3:8b
```

## Run the development pipeline

From the repository root with the virtual environment activated:

```sh
python -m harness.runner
```

For a quick live check of just one development requirement:

```sh
python -m harness.runner --limit 1
```

The terminal shows the results path and input immediately, then the reviewer
output as soon as it finishes, followed by the scorer and judge score/reason.
Waiting messages identify the active model stage. Each saved JSONL row contains
the complete result; Ctrl+C also saves available outputs for the interrupted item.
Qwen thinking is explicitly disabled for these structured responses. Each model
request has a 180-second network timeout, with generation capped at 1,024 tokens
for the reviewer and 512 for the judge. Invalid or truncated JSON is an error,
not a grade. These limits do not guarantee a particular total run duration.

Each development item is reviewed once and independently judged once. The scorer
compares predicted criteria with golden violations, reporting correct, missed,
incorrect, and correctly unflagged criteria plus TP/FN/FP/TN counts and exact match.
The reviewer receives the guide's criterion definitions and boundary rules, with
the critique-scoring rubric and pilot label assignments excluded. The judge
receives the requirement, critique, and labelling guide and returns a
validated 1–5 `score` and `reason`. Golden labels and scorer results are not sent to
it; the guide's paragraph revealing pilot category assignments is also excluded.

The runner prints the input and both evaluations, saves one row per item in a new
`results/pipeline_v3_<timestamp>_<suffix>.jsonl` file, and prints completion/failure
counts. Stage errors preserve available outputs and are not numeric grades.
Only `dev` rows are processed; existing run files are never overwritten.

## Tests and current limits

```sh
python -m unittest discover -s tests
```

Tests mock model calls and use temporary output directories; they require no
running Ollama server. They verify implementation behaviour, not model quality.
The active prompts are version 3; versions 1 and 2 remain available for reference.
Human agreement, judge reliability, bias studies, aggregate quality metrics,
and the final report remain future work.
