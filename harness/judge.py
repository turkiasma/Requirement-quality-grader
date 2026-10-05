"""Second assessor: independently grades the original requirement, treating
LLM1's output as a challengeable proposal it may retain or correct.

Never receives human reference grades, totals, or comparison results -- the
function signature has no parameter for them, and LLM1Output's extra='forbid'
means any accidentally-attached extra data fails validation rather than
silently reaching the model request.
"""

import json
import os
from pathlib import Path

from harness.llm_client import call_structured
from harness.schemas import LLM1Output, SecondAssessorOutput


DEFAULT_MODEL = os.environ.get('ASSESSOR_MODEL', 'openai/gpt-4o-mini')

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / 'prompts' / 'judge_prompt_v4.txt'
GUIDE_PATH = ROOT / 'data' / 'labelling_guide.md'


def load_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f'Prompt file not found: {PROMPT_PATH}')
    if not GUIDE_PATH.exists():
        raise FileNotFoundError(f'Guide file not found: {GUIDE_PATH}')
    guide = GUIDE_PATH.read_text(encoding='utf-8')
    return PROMPT_PATH.read_text(encoding='utf-8') + '\n\nCriterion guide:\n' + guide


def assess_requirement(requirement: str, llm1_output, model: str = DEFAULT_MODEL):
    """Independently assess the requirement, auditing LLM1's proposal.

    Args:
        requirement: The original software requirement (not LLM1's text).
        llm1_output: LLM1Output or an equivalent {"criteria": {...}} dict.
        model: OpenRouter model id. Default: openai/gpt-4o-mini.

    Returns:
        (SecondAssessorOutput, metadata).
    """
    if not isinstance(requirement, str) or not requirement.strip():
        raise ValueError('Requirement cannot be empty.')

    # Re-validating through LLM1Output (extra='forbid') is a structural
    # leakage guard: any field beyond `criteria` -- gold grades included --
    # raises here instead of silently reaching the model request below.
    if isinstance(llm1_output, LLM1Output):
        llm1_proposal = llm1_output.model_dump()
    else:
        llm1_proposal = LLM1Output.model_validate(llm1_output).model_dump()

    user_message = json.dumps({
        'requirement': requirement.strip(),
        'llm1_proposal': llm1_proposal,
    }, ensure_ascii=False)

    return call_structured(
        model=model,
        system=load_prompt(),
        user=user_message,
        schema_model=SecondAssessorOutput,
        max_tokens=1024,
    )
