"""Deterministic aggregation and human-reference comparison. No model calls.

overall_score is always computed here from per-criterion grades -- never
trusted as a number a model invented.
"""

from harness.schemas import (
    CRITERIA, LLM1Output, SecondAssessorOutput, validate_gold_criteria,
)


def _as_grade_dict(output):
    """Accept an LLM1Output/SecondAssessorOutput, a raw dict, or a plain {criterion: int}."""
    if isinstance(output, (LLM1Output, SecondAssessorOutput)):
        return {key: verdict.grade for key, verdict in output.criteria.items()}
    if isinstance(output, dict) and 'criteria' in output:
        return {key: output['criteria'][key]['grade'] for key in CRITERIA}
    return dict(output)


def overall_score(criteria_grades):
    """Unrounded overall score: sum of the five criterion grades divided by 5."""
    grades = _as_grade_dict(criteria_grades)
    return sum(grades[key] for key in CRITERIA) / 5


def compare_to_human(candidate, gold_criteria):
    """Compare one candidate's per-criterion grades against the human reference."""
    validate_gold_criteria(gold_criteria)
    candidate_grades = _as_grade_dict(candidate)
    if set(candidate_grades) != set(CRITERIA):
        raise ValueError('candidate must contain exactly the five canonical criteria.')

    per_criterion = {}
    exact = within_one = 0
    absolute_errors = []
    for key in CRITERIA:
        diff = candidate_grades[key] - gold_criteria[key]
        per_criterion[key] = {
            'candidate_grade': candidate_grades[key],
            'human_grade': gold_criteria[key],
            'diff': diff,
        }
        absolute_errors.append(abs(diff))
        if diff == 0:
            exact += 1
        if abs(diff) <= 1:
            within_one += 1

    candidate_overall = overall_score(candidate_grades)
    human_overall = overall_score(gold_criteria)
    return {
        'per_criterion': per_criterion,
        'exact_match_count': exact,
        'within_one_count': within_one,
        'mean_absolute_error': sum(absolute_errors) / len(CRITERIA),
        'overall_score': candidate_overall,
        'human_overall_score': human_overall,
        'overall_absolute_error': abs(candidate_overall - human_overall),
        'overall_exact_match': candidate_overall == human_overall,
        'all_five_match': exact == len(CRITERIA),
    }


def correction_direction(llm1, second_assessor, gold_criteria):
    """Per criterion, did the second assessor move closer to, farther from,
    or stay equally distant from the human reference, compared to LLM1?
    """
    validate_gold_criteria(gold_criteria)
    llm1_grades = _as_grade_dict(llm1)
    second_grades = _as_grade_dict(second_assessor)
    if set(llm1_grades) != set(CRITERIA) or set(second_grades) != set(CRITERIA):
        raise ValueError('llm1 and second_assessor must each contain exactly the five criteria.')

    per_criterion = {}
    tally = {'closer': 0, 'farther': 0, 'equal': 0}
    for key in CRITERIA:
        llm1_distance = abs(llm1_grades[key] - gold_criteria[key])
        second_distance = abs(second_grades[key] - gold_criteria[key])
        if second_distance < llm1_distance:
            direction = 'closer'
        elif second_distance > llm1_distance:
            direction = 'farther'
        else:
            direction = 'equal'
        tally[direction] += 1
        per_criterion[key] = {
            'llm1_grade': llm1_grades[key],
            'second_grade': second_grades[key],
            'human_grade': gold_criteria[key],
            'llm1_distance': llm1_distance,
            'second_distance': second_distance,
            'direction': direction,
        }
    return {'per_criterion': per_criterion, 'tally': tally}
