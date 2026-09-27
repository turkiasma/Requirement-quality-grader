from typing import List, Literal
from pydantic import BaseModel


Criterion = Literal[
    "atomicity",
    "testability",
    "feasibility",
    "clarity",
    "completeness"
]


class Issue(BaseModel):
    criterion: Criterion
    explanation: str


class RequirementCritique(BaseModel):
    issues: List[Issue]
    improved_requirement: str