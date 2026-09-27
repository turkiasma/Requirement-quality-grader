from pathlib import Path

from ollama import chat

from harness.schemas import RequirementCritique


# Default local model used for requirement reviews
DEFAULT_MODEL = "qwen3:8b"

# Path to the baseline reviewer prompt
PROMPT_PATH = (
    Path(__file__).parent.parent
    / "prompts"
    / "critique_prompt_v1.txt"
)


def load_prompt() -> str:
    """
    Load the requirement-review prompt from the prompts directory.
    """

    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {PROMPT_PATH}"
        )

    return PROMPT_PATH.read_text(encoding="utf-8")


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

            # Low temperature for more reproducible evaluation
            options={
                "temperature": 0
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