# Recorded v5 experiments — 2026-11-08

All requirement-reference comparisons below use **AI-prepared proposed labels**.
None is verified human-reference reliability. No held-out model calls were made.
Model: OpenRouter `openai/gpt-4o-mini`; temperature 0; rubric
`requirement_quality_v2`; prompts `critique_prompt_v5` and `judge_prompt_v5`.

## Artifacts

| Artifact | Role |
|---|---|
| `dataset_validation_v2.json` | 150 unique IDs/texts, 20 dev / 130 test, 0 verified, grade distributions. |
| `execution_plan_v5.json` | Authorized budget and pre-run cost estimate; six-case bias selection. |
| `pipeline_v5_20261108T142719572897Z_1f338e0aa9da.jsonl` | One-item live smoke, 1/1 successful. |
| `pipeline_v5_20261108T142826839338Z_61be63458235.jsonl` | Full development run, 20/20 successful. |
| `pipeline_v5_20261108T142826839338Z_61be63458235.summary.json` | Both stages' provisional agreement, corrections, cost and latency. |
| `bias_dev_cases_v5.jsonl` | Six exact copied dev rows for reproducible bias inputs; not an extra pipeline run. |
| `position_bias_v1_20261108T143114074158Z_1ab5e29e294f.jsonl` | Pairwise AB/BA calls and candidate identities. |
| `position_bias_v1_20261108T143114074158Z_1ab5e29e294f.summary.json` | Position metrics and accounting. |
| `verbosity_bias_v1_20261108T143115016927Z_16c621ec639b.jsonl` | Original, padded and repeated-control judge calls. |
| `verbosity_bias_v1_20261108T143115016927Z_16c621ec639b.summary.json` | Length/control deltas and accounting. |
| `completion_manifest_v5.json` | Execution totals, validation status and remaining evaluation gates. |

Run rows contain code and input hashes. The full dev/bias runs used the
implementation committed in `40a0cf1` (runs occurred immediately before that
commit, so their recorded Git base is `90d2902` with a dirty worktree). The
subsequent CSV line-ending change does not affect model inputs or scoring.
The earlier smoke predates some accounting refinements and is not a separate
performance baseline. Historical v2–v4 artifacts are retained, not combined
with v5: their schemes, prompts and sometimes providers differ.

## Provisional development comparison

| Metric | LLM1 | Judge |
|---|---:|---:|
| Criterion exact agreement | 48/100 (48%) | 50/100 (50%) |
| Criterion within-one agreement | 77/100 (77%) | 74/100 (74%) |
| Average criterion MAE | 0.83 | 0.85 |
| Overall-score MAE | 0.57 | 0.65 |
| Overall mean signed error | +0.19 | +0.07 |
| Exact overall agreement | 5/20 (25%) | 4/20 (20%) |
| Overall agreement within 0.2 | 7/20 (35%) | 6/20 (30%) |
| All five grades match | 4/20 (20%) | 4/20 (20%) |

| Criterion | LLM1 exact | Judge exact | LLM1 MAE | Judge MAE |
|---|---:|---:|---:|---:|
| Atomicity | 11/20 | 11/20 | 0.65 | 0.65 |
| Testability | 7/20 | 8/20 | 1.20 | 1.20 |
| Feasibility | 15/20 | 17/20 | 0.25 | 0.20 |
| Clarity | 7/20 | 7/20 | 1.15 | 1.15 |
| Completeness | 8/20 | 7/20 | 0.90 | 1.05 |

The judge retained 88/100 grades and changed 12/100. Of the changes, 5/12
(41.67%) moved closer to the proposals and 7/12 (58.33%) moved farther away.
Overall error improved on 1/20 requirements, worsened on 6/20 and was unchanged
on 13/20. The second stage did **not** improve overall MAE in this run.

Examples requiring review: REQ-009's feasibility dropped from 4 to 3 despite a
proposed reference of 5; REQ-017's feasibility corrected from 1 to 0, but its
completeness dropped from 4 to 3 against a proposed 5. REQ-015 and REQ-016 also
lost testability/completeness points. These may indicate cross-criterion penalties;
they are review leads, not proof that unverified references are correct.

## Bias pilots

Cases: REQ-001, REQ-005, REQ-010, REQ-015, REQ-017, REQ-020. Selection covers a
good requirement, ambiguity, vague performance, independent obligations,
infeasibility and multiple defects. Saved LLM1 outputs were reused.

Position: 6/6 valid swapped pairs, 0 failures. Candidate identity/tie changes:
0/6. Strict reversals among pairs non-tied in both orders: 0/3. First-position
choices among non-tied calls: 3/6 (50%). Three pairs were tied in both orders.

Verbosity: 6/6 complete cases, 0 failures. Padded versus original changed 0/30
criterion grades and 0/6 averages. Repeated original versus original also changed
0/30 grades and 0/6 averages. Mean signed and absolute deltas were zero for both.

These small pilots found no grade/preference sensitivity in the selected cases.
They do not establish general absence of bias. Position is an auxiliary pairwise
task; verbosity uses exact repetition, not every possible kind of longer prose.

## Usage and cost

| Run | Calls | Tokens | Estimated USD | Summed call latency |
|---|---:|---:|---:|---:|
| Smoke | 2 | 3,136 | 0.00063465 | 6.80 s |
| Development | 40 | 62,857 | 0.01277115 | 128.08 s |
| Position | 12 | 27,075 | 0.00435240 | 15.35 s |
| Verbosity + controls | 18 | 45,070 | 0.00836610 | 75.57 s |
| Total | 72 | 138,138 | **0.02612430** | 225.81 s |

These are token-based list-price estimates, not a statement of account charges.
No cost-unknown failures occurred. Live usage stayed below the US$2 authorization.
Position/verbosity commands ran concurrently; summed latency is not wall time.

Development: LLM1 used 14,191 tokens, $0.00366405 and 45.87 s across 20 calls.
The judge used 48,666 tokens, $0.00910710 and 82.21 s across 20 calls: about
$0.00045536 and 4.11 s per judged item. The full pipeline averaged 6.40 s/item.
At the same workload/prices, 1,000 requirements cost approximately **$0.63856**;
100× that volume (100,000 requirements) costs **$63.85575**, excluding additional
bias runs, retries, account fees and workload changes. Rates and their source
are recorded in `data/model_pricing.json`.

## Pending

Human review of all 150 annotations; any compatible dev-only prompt comparison;
a frozen, verified held-out evaluation; final interpretation and separate report.
No historical-to-v5 prompt improvement or final test reliability is claimed.
