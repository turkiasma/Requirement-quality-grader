"""LLM1: independently grades the original requirement on five criteria.

Outputs five 0-5 grades with explanations only -- no rewrite, no
self-computed total. The harness (harness.scorer) computes the overall
score deterministically from these grades.
"""

import os
from pathlib import Path

from harness.llm_client import call_structured
from harness.schemas import LLM1Output


# Default OpenRouter model used for requirement grading; override with
# REVIEWER_MODEL if needed.
DEFAULT_MODEL = os.environ.get('REVIEWER_MODEL', 'openai/gpt-4o-mini')

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / 'prompts' / 'critique_prompt_v4.txt'
GUIDE_PATH = ROOT / 'data' / 'labelling_guide.md'


def load_prompt() -> str:
    """Load the grading instructions plus the full criterion guide."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f'Prompt file not found: {PROMPT_PATH}')
    if not GUIDE_PATH.exists():
        raise FileNotFoundError(f'Guide file not found: {GUIDE_PATH}')
    guide = GUIDE_PATH.read_text(encoding='utf-8')
    return PROMPT_PATH.read_text(encoding='utf-8') + '\n\nCriterion guide:\n' + guide


def grade_requirement(requirement: str, model: str = DEFAULT_MODEL):
    """Grade one software requirement on the five criteria via the OpenRouter API.

    Args:
        requirement: The software requirement to grade.
        model: OpenRouter model id. Default: openai/gpt-4o-mini.

    Returns:
        (LLM1Output, metadata) -- metadata carries latency and token usage.
    """
    if not requirement or not requirement.strip():
        raise ValueError('Requirement cannot be empty.')

    return call_structured(
        model=model,
        system=load_prompt(),
        user=requirement.strip(),
        schema_model=LLM1Output,
        max_tokens=1024,
    )
