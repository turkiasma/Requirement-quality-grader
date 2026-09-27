import json
from pathlib import Path

from harness.reviewer import review_requirement
from harness.judge import judge_review


DATA_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "golden_set.jsonl"
)

RESULTS_DIR = (
    Path(__file__).parent.parent
    / "results"
)

OUTPUT_PATH = RESULTS_DIR / "pipeline_v1.jsonl"


def load_dataset():
    """Load requirements from the JSONL golden dataset."""

    items = []

    with DATA_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                items.append(json.loads(line))

    return items


def run():
    """Run Reviewer V1 and Judge V1 on every requirement."""

    dataset = load_dataset()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:

        for item in dataset:
            requirement = item["requirement"]

            # Step 1: Reviewer
            print(f"Reviewing {item['id']}...")

            critique = review_requirement(requirement)

            # Step 2: Judge
            print(f"Judging {item['id']}...")

            judgment = judge_review(
                requirement,
                critique
            )

            # Step 3: Save result
            result = {
                "id": item["id"],
                "requirement": requirement,
                "gold_violations": item["violations"],
                "reviewer_output": critique.model_dump(),
                "judge_output": judgment,
            }

            output_file.write(
                json.dumps(
                    result,
                    ensure_ascii=False
                ) + "\n"
            )

    print(
        f"\nFinished. Results saved to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    run()