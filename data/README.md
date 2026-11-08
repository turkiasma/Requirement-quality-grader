# Data and review

- `golden_set.jsonl`: canonical v2 dataset; 20 original dev texts + 130 new test texts.
- `labelling_guide.md`: `requirement_quality_v2`; detailed 0–5 criterion anchors.
- `reference_review.csv`: editable export of the proposed dataset, with source hashes.
- `model_pricing.json`: dated public model pricing, not reference annotation data.
- `history/`: preserved binary, dummy and pending representations and old guide;
  these are historical and rejected by the current loader.

Every active item has ID, text, split, `scheme`, `guide_version`, integer
`criteria`, `justifications`, calculated `gold_score`, `annotation_status` and
`provenance`. All initial annotations are AI-prepared `proposed` references.
No examples have yet been manually verified; none were dropped during creation.
Raw historical binary labels were not converted into reference scores.

Review the CSV against the guide, correct individual grades and explanations,
then set `verified` and your name only on reviewed rows. Import with
`python -m harness.review import --data data/golden_set.jsonl --csv YOUR.csv --output NEW.jsonl`.
Output is never overwritten. The import records timestamps, initial proposals
and the source review file hash. Export again from the latest output to continue
reviewing. No reviewer identity or agreement statistic is invented.

This project follows the user's reported instructor clarification permitting a
single manually verified reference set. The original assignment's two-annotator
protocol is not claimed to have been carried out. Do not tune prompts with the
130 held-out examples or promote provisional comparisons to human agreement.

Coverage spans functional and non-functional software requirements. Grade
frequencies are in `results/dataset_validation_v2.json`; all anchors occur, but
most atomicity and feasibility grades are 5. Feasibility grades 3–4 and other
borderline examples particularly need human judgment. Some defect examples
intentionally contain impossible guarantees or contradictions.

## Additional annotation review — 8 November 2026

`annotation_review_ai.jsonl` records a second AI rubric review of all 150 rows.
It flags 13 items for reconsideration and provides suggested grades where a
specific revision is supported. These suggestions are separate from the
canonical labels and the original `reference_review.csv`; they have not changed
the reference snapshot used for saved experiments. The file is not a record of
human annotation. Inspect its notes when completing the existing review workflow.
