import inspect
import json
import unittest
from unittest.mock import patch

from harness.judge import GUIDE_PATH, PROMPT_PATH, assess_requirement, load_prompt
from harness.schemas import CRITERIA, LLM1Output, SecondAssessorOutput


def llm1_payload(grade=5):
    return {'criteria': {key: {'grade': grade, 'explanation': 'A specific reason.'} for key in CRITERIA}}


def second_payload(grade=5, retained=True):
    return {'criteria': {key: {'grade': grade, 'retained': retained, 'reason': 'A specific reason.'}
                         for key in CRITERIA}}


class SecondAssessorTests(unittest.TestCase):
    def setUp(self):
        self.llm1_output = LLM1Output.model_validate(llm1_payload())

    @patch('harness.judge.call_structured')
    def test_valid_response_and_request_shape(self, call_structured):
        output = SecondAssessorOutput.model_validate(second_payload())
        call_structured.return_value = (output, {'model': 'x', 'latency_seconds': 0.2})
        result, meta = assess_requirement('Original requirement.', self.llm1_output)
        self.assertEqual(result, output)
        kwargs = call_structured.call_args.kwargs
        user = json.loads(kwargs['user'])
        self.assertEqual(user['requirement'], 'Original requirement.')
        self.assertEqual(user['llm1_proposal'], self.llm1_output.model_dump())
        self.assertIs(kwargs['schema_model'], SecondAssessorOutput)

    @patch('harness.judge.call_structured')
    def test_accepts_plain_dict_llm1_output(self, call_structured):
        call_structured.return_value = (SecondAssessorOutput.model_validate(second_payload()), {})
        assess_requirement('Requirement.', llm1_payload())
        call_structured.assert_called_once()

    @patch('harness.judge.call_structured')
    def test_rejects_llm1_output_carrying_extra_fields(self, call_structured):
        leaking = dict(llm1_payload(), gold_criteria={'atomicity': 5})
        with self.assertRaises(Exception):
            assess_requirement('Requirement.', leaking)
        call_structured.assert_not_called()

    def test_no_parameter_exists_for_human_reference_data(self):
        params = inspect.signature(assess_requirement).parameters
        for forbidden in ('gold_criteria', 'gold_score', 'human_reference', 'human_grades'):
            self.assertNotIn(forbidden, params)

    @patch('harness.judge.call_structured')
    def test_empty_requirement_does_not_call_model(self, call_structured):
        with self.assertRaises(ValueError):
            assess_requirement('   ', self.llm1_output)
        call_structured.assert_not_called()

    def test_prompt_includes_full_guide_and_no_human_reference_language(self):
        system = load_prompt()
        self.assertIn(PROMPT_PATH.read_text(encoding='utf-8'), system)
        self.assertIn(GUIDE_PATH.read_text(encoding='utf-8'), system)

    @patch('harness.judge.call_structured', side_effect=RuntimeError('Offline'))
    def test_transport_error_is_explicit(self, call_structured):
        with self.assertRaisesRegex(RuntimeError, 'Offline'):
            assess_requirement('Original requirement.', self.llm1_output)


if __name__ == '__main__':
    unittest.main()
