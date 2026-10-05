import unittest
from unittest.mock import patch

from harness.reviewer import GUIDE_PATH, PROMPT_PATH, load_prompt, grade_requirement
from harness.schemas import CRITERIA, LLM1Output


def payload(grade=5):
    return {'criteria': {key: {'grade': grade, 'explanation': 'A specific reason.'} for key in CRITERIA}}


class ReviewerTests(unittest.TestCase):
    @patch('harness.reviewer.call_structured')
    def test_valid_response_and_request_shape(self, call_structured):
        output = LLM1Output.model_validate(payload())
        call_structured.return_value = (output, {'model': 'x', 'latency_seconds': 0.1})
        result, meta = grade_requirement('  Original requirement.  ')
        self.assertEqual(result, output)
        self.assertEqual(meta['latency_seconds'], 0.1)
        kwargs = call_structured.call_args.kwargs
        self.assertEqual(kwargs['user'], 'Original requirement.')
        self.assertIs(kwargs['schema_model'], LLM1Output)
        self.assertIn('atomicity', kwargs['system'])
        self.assertNotIn('improved_requirement', kwargs['system'])

    @patch('harness.reviewer.call_structured')
    def test_empty_input_does_not_call_model(self, call_structured):
        with self.assertRaises(ValueError):
            grade_requirement('   ')
        call_structured.assert_not_called()

    def test_prompt_includes_full_guide_and_criteria(self):
        system = load_prompt()
        self.assertIn(PROMPT_PATH.read_text(encoding='utf-8'), system)
        self.assertIn(GUIDE_PATH.read_text(encoding='utf-8'), system)
        for key in CRITERIA:
            self.assertIn(key, system)

    @patch('harness.reviewer.GUIDE_PATH')
    def test_missing_guide_fails_explicitly(self, guide_path):
        guide_path.exists.return_value = False
        with self.assertRaises(FileNotFoundError):
            load_prompt()

    @patch('harness.reviewer.call_structured', side_effect=RuntimeError('Offline'))
    def test_transport_error_is_explicit(self, call_structured):
        with self.assertRaisesRegex(RuntimeError, 'Offline'):
            grade_requirement('Original requirement.')


if __name__ == '__main__':
    unittest.main()
