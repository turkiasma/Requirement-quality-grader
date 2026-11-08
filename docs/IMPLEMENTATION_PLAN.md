# Completion status (v5)

The former v4 planning document is superseded; its prior contents remain in Git.

Implemented: short-definition initial assessor; detailed-guide correction judge;
strict schemas; migrated 150-item proposed reference set (20 dev, 130 test);
CSV review/import; version checks; CLI split selection and dry-run; test gate and
frozen configuration checks; persisted totals/provenance/partial errors; grouped
reliability and correction metrics; paired position and verbosity experiments;
repeated-input control; cumulative budget and dated pricing; offline tests.

Execution evidence and exact artifact paths: `results/README.md`.
Manual verification: pending for every reference. Held-out model evaluation:
blocked until review. No independent two-human agreement study is implemented,
in accordance with the user's reported instructor clarification.

Remaining sequence: review the reference CSV, import a new versioned dataset,
finish any dev-only prompt comparisons under compatible references, freeze the
configuration, execute the held-out test once, and use the saved summaries to
prepare the separate university PDF. Do not infer verified reliability from the
provisional development run. The current two-stage contract measures requirement
assessment agreement, not a separate answer-quality grade for LLM1's writing.
