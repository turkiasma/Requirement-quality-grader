import unittest

from pydantic import ValidationError

from harness.schemas import CRITERIA, LLM1Output, SecondAssessorOutput, validate_gold_criteria


def llm1_payload(**overrides):
    criteria = {key: {'grade': 5, 'explanation': 'Reason.'} for key in CRITERIA}
    criteria.update(overrides)
    return {'criteria': criteria}


def second_payload(**overrides):
    criteria = {key: {'grade': 5, 'retained': True, 'reason': 'Reason.'} for key in CRITERIA}
    criteria.update(overrides)
    return {'criteria': criteria}


class LLM1OutputTests(unittest.TestCase):
    def test_valid_payload(self):
        LLM1Output.model_validate(llm1_payload())

    def test_rejects_missing_criterion(self):
        payload = llm1_payload()
        del payload['criteria']['atomicity']
        with self.assertRaises(ValidationError):
            LLM1Output.model_validate(payload)

    def test_rejects_unknown_criterion(self):
        payload = llm1_payload()
        payload['criteria']['unknown'] = {'grade': 5, 'explanation': 'x'}
        with self.assertRaises(ValidationError):
            LLM1Output.model_validate(payload)

    def test_rejects_out_of_range_or_non_integer_grades(self):
        for bad in (-1, 6, 2.5, '3', True, None):
            payload = llm1_payload(atomicity={'grade': bad, 'explanation': 'x'})
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                LLM1Output.model_validate(payload)

    def test_rejects_blank_explanation(self):
        payload = llm1_payload(atomicity={'grade': 5, 'explanation': '   '})
        with self.assertRaises(ValidationError):
            LLM1Output.model_validate(payload)

    def test_rejects_extra_top_level_field_structural_leakage_guard(self):
        payload = dict(llm1_payload(), gold_criteria={'atomicity': 5})
        with self.assertRaises(ValidationError):
            LLM1Output.model_validate(payload)

    def test_no_rewrite_or_total_field_accepted(self):
        payload = dict(llm1_payload(), improved_requirement='x')
        with self.assertRaises(ValidationError):
            LLM1Output.model_validate(payload)
        payload = dict(llm1_payload(), score=5)
        with self.assertRaises(ValidationError):
            LLM1Output.model_validate(payload)


class SecondAssessorOutputTests(unittest.TestCase):
    def test_valid_payload(self):
        SecondAssessorOutput.model_validate(second_payload())

    def test_rejects_missing_criterion(self):
        payload = second_payload()
        del payload['criteria']['clarity']
        with self.assertRaises(ValidationError):
            SecondAssessorOutput.model_validate(payload)

    def test_rejects_out_of_range_grade(self):
        payload = second_payload(clarity={'grade': 7, 'retained': True, 'reason': 'x'})
        with self.assertRaises(ValidationError):
            SecondAssessorOutput.model_validate(payload)

    def test_rejects_blank_reason(self):
        payload = second_payload(clarity={'grade': 5, 'retained': True, 'reason': ''})
        with self.assertRaises(ValidationError):
            SecondAssessorOutput.model_validate(payload)

    def test_requires_retained_flag(self):
        payload = second_payload(clarity={'grade': 5, 'reason': 'x'})
        with self.assertRaises(ValidationError):
            SecondAssessorOutput.model_validate(payload)


class GoldCriteriaTests(unittest.TestCase):
    def test_accepts_valid(self):
        validate_gold_criteria({key: 3 for key in CRITERIA})

    def test_rejects_bool_as_int(self):
        with self.assertRaises(ValueError):
            validate_gold_criteria(dict({key: 3 for key in CRITERIA}, atomicity=True))

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            validate_gold_criteria(dict({key: 3 for key in CRITERIA}, atomicity=6))

    def test_rejects_missing_or_unknown_criteria(self):
        missing = {key: 3 for key in CRITERIA}
        del missing['atomicity']
        with self.assertRaises(ValueError):
            validate_gold_criteria(missing)
        with self.assertRaises(ValueError):
            validate_gold_criteria(dict({key: 3 for key in CRITERIA}, unknown=3))


if __name__ == '__main__':
    unittest.main()
