# Evidence index for the separately submitted report

This is an index to reproducible evidence, not the university report. Do not
create or commit the final PDF here. The user will submit it separately.

## Information for the six required topics

1. **Task and exact match:** README architecture and criterion definitions.
   Both LLM stages assess original requirement quality; Python compares five
   ordinal grades and their mean. Matching totals do not imply matching criteria.
2. **Dataset:** `data/golden_set.jsonl`, `data/labelling_guide.md`,
   `data/reference_review.csv`, `results/dataset_validation_v2.json`.
   150 unique requirements: 20 dev / 130 test, all proposed, 0 verified at delivery.
   Retained 150, dropped 0 during preparation. Review provenance is still pending.
   Follow the reported instructor clarification permitting one verified reference
   set; do not claim a two-annotator study or inter-annotator agreement.
3. **Harness:** README CLI, `harness/runner.py`, `harness/schemas.py`,
   `harness/dataset.py`, and per-item v5 JSONL results. Include schema validation,
   explicit failures, partial output preservation, hashes and split/test gates.
4. **Judge reliability and bias:** exact artifact paths and counts in
   `results/README.md`. Current dev overall MAE is 0.57 initial / 0.65 judge;
   5/12 corrections closer and 7/12 farther from **proposed** references.
   Position: 0/6 identity/tie changes; 0/3 non-tied reversals. Verbosity and repeated
   control: each 0/30 changed criterion grades. These are small dev pilots.
   Replace provisional agreement figures with verified results after review.
5. **Prompt history:** `prompts/CHANGELOG.md`, preserved v1–v4 files and active v5.
   No comparable v4→v5 improvement is claimed because the grading contract and
   references changed. Further comparisons must use the same verified dev
   references, guide, models and scorer, changing only the prompt under study.
6. **Cost:** `data/model_pricing.json`, each `.summary.json`, and
   `results/completion_manifest_v5.json`. Total recorded execution: 72 calls,
   138,138 tokens, estimated $0.02612430. Dev workload projects to $0.63856 per
   1,000 requirements and $63.85575 at 100× volume. Include the assumptions and
   stage-specific judge cost/latency in `results/README.md`.

## Commands after human review

From the repository root, using the installed virtual environment:

```bash
.venv/bin/python -m harness.review import --data data/golden_set.jsonl --csv data/reference_review.csv --output data/golden_set_reviewed.jsonl
.venv/bin/python -m harness.runner --data data/golden_set_reviewed.jsonl --split all --dry-run
.venv/bin/python -m unittest discover -s tests
```

Finish any dev-only comparisons before final testing. Then freeze the reviewed
data, implementation, pricing, guide, prompts and model configuration:

```bash
.venv/bin/python -m harness.runner --data data/golden_set_reviewed.jsonl --split all --dry-run --freeze
.venv/bin/python -m harness.runner --data data/golden_set_reviewed.jsonl --split test --frozen-config results/ACTUAL_FROZEN_CONFIG.json
.venv/bin/python -m harness.metrics results/ACTUAL_TEST_RUN.jsonl --tolerance 0.2
```

Replace uppercase paths with the actual paths printed by the commands. Every
output has a unique filename. Use the `test/verified` group for final test
agreement, include valid/failure denominators, and report per-criterion results
alongside overall MAE. Do not change prompts in response to the test scores.

For four pages, allocate space to task/dataset, harness/reliability, bias/prompt
history, and cost/limitations. Supporting detail remains in the repository.
Review notes and correction decisions belong with the data; the final narrative
and PDF remain outside GitHub.
