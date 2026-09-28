# Prompt Changelog

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
