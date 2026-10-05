from typing import Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Criterion = Literal['atomicity', 'testability', 'feasibility', 'clarity', 'completeness']
CRITERIA = ('atomicity', 'testability', 'feasibility', 'clarity', 'completeness')

# Marks the 0-5 grade-anchor scoring convention so a dataset row can never be
# silently misread under the old binary (0/1 violation) convention.
GOLD_SCHEME = 'grade_0_5_v1'


def _nonblank(value):
    value = value.strip() if isinstance(value, str) else value
    if not isinstance(value, str) or not value:
        raise ValueError('Text field must not be blank.')
    return value


def _exactly_five(value):
    if not isinstance(value, dict) or set(value) != set(CRITERIA):
        raise ValueError('criteria must contain exactly the five canonical criteria.')
    return value


def validate_gold_criteria(value):
    """Reject missing/unknown criteria and non-integer or out-of-range grades."""
    if not isinstance(value, dict) or set(value) != set(CRITERIA):
        raise ValueError('Gold criteria must contain exactly the five canonical criteria.')
    if any(type(grade) is not int or not (0 <= grade <= 5) for grade in value.values()):
        raise ValueError('Gold criteria values must be integers 0-5.')


class CriterionGrade(BaseModel):
    """LLM1's independent grade for one criterion."""

    model_config = ConfigDict(extra='forbid')

    grade: int = Field(strict=True, ge=0, le=5)
    explanation: str

    @field_validator('explanation')
    @classmethod
    def nonblank_explanation(cls, value):
        return _nonblank(value)


class SecondAssessorGrade(BaseModel):
    """The second assessor's final grade for one criterion: retain or correct LLM1's proposal."""

    model_config = ConfigDict(extra='forbid')

    grade: int = Field(strict=True, ge=0, le=5)
    retained: bool
    reason: str

    @field_validator('reason')
    @classmethod
    def nonblank_reason(cls, value):
        return _nonblank(value)


class LLM1Output(BaseModel):
    """LLM1's full output: five independent criterion grades, nothing else.

    No rewrite, no self-computed total. extra='forbid' doubles as a
    structural leakage guard: a dict carrying any field beyond `criteria`
    (e.g. accidentally-included gold data) fails validation rather than
    silently passing through.
    """

    model_config = ConfigDict(extra='forbid')

    criteria: Dict[Criterion, CriterionGrade]

    @field_validator('criteria')
    @classmethod
    def exactly_five_criteria(cls, value):
        return _exactly_five(value)


class SecondAssessorOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    criteria: Dict[Criterion, SecondAssessorGrade]

    @field_validator('criteria')
    @classmethod
    def exactly_five_criteria(cls, value):
        return _exactly_five(value)
