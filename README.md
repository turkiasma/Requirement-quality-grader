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
