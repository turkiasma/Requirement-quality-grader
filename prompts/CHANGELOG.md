# Prompt Changelog

## Version 4 — 0-5 grade anchors, second assessor replaces answer-quality judge

- Rebuilt the scoring contract entirely: five criteria now each receive an
  integer grade 0-5 against the guide's grade-anchor table, not a binary
  violation flag. `overall_score = sum(5 grades)/5`, computed by
  `harness.scorer`, never by a model.
- LLM1 (`critique_prompt_v4.txt`, `harness/reviewer.py`): emits the five
  grades + explanations only. The `improved_requirement` rewrite is removed
  from the active workflow.
- The second assessor (`judge_prompt_v4.txt`, `harness/judge.py`) replaces
  the old 1-5 answer-quality rubric. It independently grades the original
  requirement, treating LLM1's proposal as a challengeable input, and
  receives **no human reference data** -- no gold grades, no gold total, no
  comparison results. It emits its own five grades, each marked retained or
  corrected with a reason.
- New comparison logic in `harness/scorer.py`: `compare_to_human` (exact/
  within-1/MAE/overall-error against gold) and `correction_direction`
  (per-criterion closer/farther/equal classification of the second
  assessor's grade relative to LLM1's, against the human reference) --
  measures whether the second stage actually helps instead of assuming it.
- Dataset rows now carry an explicit `scheme: "grade_0_5_v1"` marker
  alongside `criteria`/`gold_score`; the loader rejects any row where
  `scheme` is missing or doesn't match, rather than reinterpreting the old
  binary `violations` convention as grades. `data/golden_set.jsonl` (old
  scheme) is left as historical data; `data/golden_set_pending.jsonl` carries
  the same 20 requirement texts with no gold yet, for live runs until
  re-labelling under the new scheme is done.
- Model calls moved from local Ollama to the OpenRouter API
  (`harness/llm_client.py`), default model `openai/gpt-4o-mini`, configurable
  via `REVIEWER_MODEL`/`ASSESSOR_MODEL`. API key read from `OPENROUTER_API_KEY`
  (local `.env`, gitignored) -- never committed.
- Tests rewritten against synthetic fixtures (`tests/test_schemas.py` is new).
  They verify pipeline behaviour -- leakage prevention, scheme-version
  rejection, aggregation math, stage-failure handling -- not model quality or
  human agreement, since re-labelled human data doesn't exist yet.
- Not yet done: the 20-item pilot re-labelled by two humans under the new
  scheme, the reliability report (human agreement, position/verbosity bias,
  cost/latency), and the 150+ item expansion. See
  `docs/IMPLEMENTATION_PLAN.md`.

## Version 3 — scoped critiques and evidence-based judging

- Reviewer now receives the guide's criterion definitions, examples, and boundary
  rules, excluding pilot label assignments and the critique-scoring rubric.
- Reviewer instructions distinguish independent obligations from conditions,
  ambiguity from missing parameters, and infeasibility from non-testability.
  Require justified accusations, preservation of scope/values, and explicit
  placeholders or clarification instead of invented facts.
- Judge instructions explicitly check accusations, missed defects, unsupported
  additions, and remaining rewrite defects. Reasons must reference the actual item.
  The guide remains the grading authority; it has not been rewritten.
- Output schemas, model, temperature, thinking setting, and token limits are
  unchanged. New pipeline runs use a pipeline_v3 filename; v2 results are preserved.
- Full v2 dev baseline: 5/20 exact criterion matches (25%); 31 true positives,
  4 false negatives, 25 false positives, 40 true negatives. Judge assigned 5 to
  13/20 critiques and 4 to 7/20. These are provisional-label comparisons, not
  measured human agreement. See the
  [baseline review](../results/pipeline_v2_20260928T144121586894Z_a20c6fd2f59045f58fc3ef2aae92fa04_review.md).
- Full v3 before/after evaluation: not performed yet. No overall improvement or
  judge reliability is claimed from mocked tests or a small live check.

### Targeted v3 live check

Saved [four live calls on two selected dev cases](../results/prompt_v3_smoke_20260928T150352Z_34122568.jsonl).
Reviewer calls were scored against the same provisional labels. Judge calls used
the exact frozen v2 critiques, not newly generated v3 critiques.

- REQ-001 reviewer: still incorrect; false predictions increased from 2 to 3.
  It listed atomic while explaining that the requirement is atomic.
- REQ-010 reviewer: removed the false atomicity accusation and replaced the
  invented two-second threshold with [RESPONSE_TIME_LIMIT]; all five labels match.
- On both frozen critiques, judge scores changed from 5 to 4 and reasons became
  item-specific. However, it still endorsed unnecessary criticism on REQ-001 and
  treated REQ-010's false atomicity accusation/invented threshold as minor.
- All four calls returned valid structured output. These selected cases show
  mixed behaviour; they do not establish overall improvement or human agreement.

## Version 2 — rubric-based judging and canonical criteria

- Reviewer: use atomic, testable, feasible, clarity, complete; retain the
  improved_requirement field and restrictions on invented context.
- Judge: replace PASS/FAIL with a validated 1–5 score and reason; load criterion
  definitions and the scoring rubric directly from the labelling guide.
- The dataset-specific pilot grouping paragraph is excluded from judge context
  because it reveals reference labels. Gold labels and scorer output are not sent.
- Version 1 prompts remain unchanged for reference.
- Before/after quality scores: not measured yet. Mocked tests validate behaviour,
  not model quality or agreement with humans.

### Runtime follow-up

- Disable Qwen thinking explicitly for reviewer and judge structured responses;
  cap generated tokens at 1,024 and 512 respectively and set a 180-second
  network timeout. Prompt text and the grading rubric are unchanged.
- These inference-setting changes require new quality measurements; no score
  improvement is claimed.
