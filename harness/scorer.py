"""Deterministic criterion detection scoring; no model calls or critique grades."""

from harness.schemas import CRITERIA, RequirementCritique, validate_gold_violations


def score_critique(gold_violations, critique):
    """Compare distinct predicted criteria with the true golden violations."""
    validate_gold_violations(gold_violations)
    if isinstance(critique, RequirementCritique):
        critique = critique.model_dump()
    critique = RequirementCritique.model_validate(critique)
    predicted = {issue.criterion for issue in critique.issues}
    expected = {key for key in CRITERIA if gold_violations[key]}
    groups = {
        'correctly_identified': predicted & expected,
        'missed': expected - predicted,
        'incorrectly_predicted': predicted - expected,
        'correctly_unflagged': set(CRITERIA) - (expected | predicted),
    }
    result = {name: [key for key in CRITERIA if key in values]
              for name, values in groups.items()}
    result['counts'] = {
        'tp': len(groups['correctly_identified']),
        'fn': len(groups['missed']),
        'fp': len(groups['incorrectly_predicted']),
        'tn': len(groups['correctly_unflagged']),
    }
    result['exact_match'] = predicted == expected
    return result
