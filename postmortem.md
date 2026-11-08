# Postmortem

## Problems observed

- The previous default runner selected binary-era data that its newer loader
  rejected. Migration now uses one versioned canonical dataset, with historical
  variants preserved separately. Offline validation catches incompatibility
  before requests are sent.
- The local environment initially lacked provider dependencies. A clean virtual
  environment and pinned requirements now support the documented offline tests.
- The former reviewer received the same detailed guide as the judge, contrary
  to the clarified experiment. v5 isolates the reviewer to short definitions;
  mocked request tests check both context boundaries.
- `retained` was a model-reported flag that could contradict a numerical change.
  Python now derives it from the two scores. Both changed and unchanged cases
  are covered by tests.
- Binary-to-score dummy labels were not a valid human reference set. New labels
  remain explicitly AI-prepared proposals, and review imports require a named
  reviewer. The software refuses unverified held-out model evaluation.
- The first CSV export used conventional CRLF line endings, which the repository's
  whitespace check flagged. Exports now use LF, with round-trip tests retained.
- More context and a second assessment did not guarantee better agreement. In
  the provisional 20-item run, overall MAE increased from 0.57 to 0.65. Some
  judge changes appear to penalize completeness/testability for other defects.
  The proposed references themselves still require human checking.

## What the measurements support

All 20 dev items completed. Six-case position and verbosity pilots completed
without failures and found no changes in the measured preference/grade outcomes.
Their sample is too small to claim general robustness. The repeated-input
control also showed no grade changes, but temperature 0 is not a determinism
promise. Reference agreement is provisional, not verified human reliability.

## What remains

A human must review the 150 proposals before final claims. Use the reviewed dev
references for any further controlled prompt work, then freeze the configuration
and run the 130 held-out requirements. Do not tune on their results. Preserve
unfavourable outcomes, failure counts, cost assumptions and the distinction
between requirement grading and grading the quality of an assessor's answer.
The four-page university report is submitted separately, not committed here.
