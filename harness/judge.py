"""Independent rubric-based evaluation of complete requirement critiques."""

import json
from pathlib import Path

import ollama

from harness.schemas import JudgeOutput, RequirementCritique


DEFAULT_MODEL = 'qwen3:8b'
ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / 'prompts' / 'judge_prompt_v2.txt'
GUIDE_PATH = ROOT / 'data' / 'labelling_guide.md'


def load_guide():
    """Load the actual rubric, excluding the paragraph revealing pilot labels."""
    guide = GUIDE_PATH.read_text(encoding='utf-8')
    return '\n\n'.join(
        paragraph for paragraph in guide.split('\n\n')
        if not paragraph.lstrip().startswith('For the initial dev pilot,')
    )


def judge_review(requirement, review, model=DEFAULT_MODEL):
    """Return a validated score/reason, independently of gold labels and scoring."""
    if not isinstance(requirement, str) or not requirement.strip():
        raise ValueError('Requirement cannot be empty.')
    if isinstance(review, RequirementCritique):
        review = review.model_dump()
    # Serialize only critique fields, even if the caller supplied extra metadata.
    critique = RequirementCritique.model_validate(review)
    system_message = (
        PROMPT_PATH.read_text(encoding='utf-8')
        + '\n\nLabelling guide:\n' + load_guide()
    )
    user_message = json.dumps({
        'requirement': requirement,
        'review': critique.model_dump(),
    }, ensure_ascii=False)
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': user_message},
            ],
            format=JudgeOutput.model_json_schema(),
            options={'temperature': 0},
        )
        return JudgeOutput.model_validate_json(
            response['message']['content']
        ).model_dump()
    except Exception as error:
        raise RuntimeError(f"Judge failed using model '{model}': {error}") from error
