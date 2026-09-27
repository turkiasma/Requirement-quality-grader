import json
from pathlib import Path

from harness.reviewer import review_requirement


DATA_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "golden_set.jsonl"
)

RESULTS_DIR = (
    Path(__file__).parent.parent
    / "results"
)

OUTPUT_PATH = RESULTS_DIR / "reviewer_v1.jsonl"


def load_dataset():
    """Load requirements from the JSONL golden dataset."""

    items = []

    with DATA_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                items.append(json.loads(line))

    return items


def run():
    """Run Reviewer V1 on every requirement in the dataset."""

    dataset = load_dataset()

    RESULTS_DIR.mkdir(exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for item in dataset:
            requirement = item["requirement"]

            print(f"Reviewing {item['id']}...")

            critique = review_requirement(requirement)

            result = {
                "id": item["id"],
                "requirement": requirement,
                "gold_violations": item["violations"],
                "reviewer_output": critique.model_dump(),
            }

            output_file.write(
                json.dumps(result, ensure_ascii=False) + "\n"
            )

    print(f"\nFinished. Results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    run()