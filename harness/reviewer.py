from pathlib import Path

from ollama import Client

from harness.schemas import RequirementCritique


# Default local model used for requirement reviews
DEFAULT_MODEL = "qwen3:8b"
# Bound an unresponsive local request rather than waiting indefinitely.
chat = Client(timeout=180).chat

# Path to the current reviewer prompt
PROMPT_PATH = (
    Path(__file__).parent.parent
    / "prompts"
    / "critique_prompt_v3.txt"
)
GUIDE_PATH = Path(__file__).resolve().parent.parent / "data" / "labelling_guide.md"


def load_prompt() -> str:
    """
    Load the reviewer instructions and the guide's criterion decision rules.
    """

    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {PROMPT_PATH}"
        )

    guide = GUIDE_PATH.read_text(encoding="utf-8")
    _, start, definitions = guide.partition("## 1. Atomicity")
    definitions, end, _ = definitions.partition("## Critique Scoring Rubric")
    if not start or not end:
        raise ValueError("Labelling guide is missing criterion or scoring section headings.")
    definitions = "\n\n".join(
        paragraph for paragraph in (start + definitions).split("\n\n")
        if not paragraph.lstrip().startswith("For the initial dev pilot,")
    )
    return (
        PROMPT_PATH.read_text(encoding="utf-8")
        + "\n\nCriterion definitions and boundary rules:\n" + definitions
    )


def review_requirement(
    requirement: str,
    model: str = DEFAULT_MODEL
) -> RequirementCritique:
    """
    Review one software requirement using a local Ollama model.

    Args:
        requirement:
            The software requirement to review.

        model:
            Ollama model to use.
            Default: qwen3:8b

    Returns:
        RequirementCritique:
            Structured critique containing detected issues
            and an improved requirement.
    """

    # Validate input
    if not requirement or not requirement.strip():
        raise ValueError("Requirement cannot be empty.")

    try:
        response = chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": load_prompt()
                },
                {
                    "role": "user",
                    "content": requirement.strip()
                }
            ],

            # Force the model to follow our Pydantic JSON schema
            format=RequirementCritique.model_json_schema(),

            # Return the structured answer without a separate thinking phase.
            think=False,

            # Low temperature for more reproducible evaluation
            options={
                "temperature": 0,
                "num_predict": 1024,
            }
        )

        # Validate the returned JSON against our schema
        critique = RequirementCritique.model_validate_json(
            response.message.content
        )

        return critique

    except Exception as error:
        raise RuntimeError(
            f"Requirement review failed using model '{model}': {error}"
        ) from error
