from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Criterion = Literal['atomic', 'testable', 'feasible', 'clarity', 'complete']
CRITERIA = ('atomic', 'testable', 'feasible', 'clarity', 'complete')


def validate_gold_violations(value):
    """Reject missing/unknown labels and non-boolean values."""
    if not isinstance(value, dict) or set(value) != set(CRITERIA):
        raise ValueError('Gold violations must contain exactly the five canonical criteria.')
    if any(type(label) is not bool for label in value.values()):
        raise ValueError('Gold violation values must be booleans.')


class Issue(BaseModel):
    criterion: Criterion
    explanation: str


class RequirementCritique(BaseModel):
    issues: List[Issue]
    improved_requirement: str


class JudgeOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    score: int = Field(strict=True, ge=1, le=5)
    reason: str = Field(strict=True, min_length=1)

    @field_validator('reason')
    @classmethod
    def nonblank_reason(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Judge reason must not be blank.')
        return value
