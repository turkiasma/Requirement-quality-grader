import json
from pathlib import Path

import ollama


DEFAULT_MODEL = "qwen3:8b"

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "prompts"
    / "judge_prompt_v1.txt"
)


def judge_review(requirement, review, model=DEFAULT_MODEL):
    """Evaluate the quality of a requirement review."""

    # Load the judge prompt
    judge_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    # Convert the review to JSON
    # Supports both Pydantic objects and normal dictionaries
    if hasattr(review, "model_dump_json"):
        review_json = review.model_dump_json(indent=2)
    else:
        review_json = json.dumps(review, indent=2)

    # Build the input for the judge
    user_message = f"""
Original requirement:
{requirement}

Review:
{review_json}

Evaluate this review according to the instructions.
"""

    # Send the request to the judge model
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": judge_prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        format="json"
    )

    # Parse the judge response
    result = json.loads(response["message"]["content"])

    return result