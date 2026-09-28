import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from harness.reviewer import review_requirement
from harness.schemas import CRITERIA, RequirementCritique


class ReviewerTests(unittest.TestCase):
    @patch('harness.reviewer.chat')
    def test_canonical_response_and_request(self, chat):
        payload = {
            'issues': [{'criterion': key, 'explanation': 'A specific issue.'}
                       for key in CRITERIA],
            'improved_requirement': 'Clarified requirement.',
        }
        chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(payload)))
        result = review_requirement('  Original requirement.  ')
        self.assertEqual(result.model_dump(), payload)
        request = chat.call_args.kwargs
        self.assertEqual(request['model'], 'qwen3:8b')
        self.assertEqual(request['options'], {'temperature': 0, 'num_predict': 1024})
        self.assertFalse(request['think'])
        self.assertEqual(request['format'], RequirementCritique.model_json_schema())
        self.assertEqual(request['messages'][1]['content'], 'Original requirement.')
        self.assertIn('atomic:', request['messages'][0]['content'])

    @patch('harness.reviewer.chat')
    def test_old_and_unknown_criteria_rejected(self, chat):
        for key in ('atomicity', 'testability', 'feasibility', 'completeness', 'other'):
            with self.subTest(criterion=key):
                chat.return_value = SimpleNamespace(message=SimpleNamespace(
                    content=json.dumps({'issues': [{'criterion': key, 'explanation': 'x'}],
                                        'improved_requirement': 'x'})))
                with self.assertRaises(RuntimeError):
                    review_requirement('Original requirement.')

    @patch('harness.reviewer.chat')
    def test_good_requirement(self, chat):
        requirement = 'The API shall return HTTP 401 for an incorrect password.'
        chat.return_value = SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            'issues': [], 'improved_requirement': requirement})))
        self.assertEqual(review_requirement(requirement).issues, [])

    @patch('harness.reviewer.chat')
    def test_empty_input_does_not_call_model(self, chat):
        with self.assertRaises(ValueError):
            review_requirement('   ')
        chat.assert_not_called()


if __name__ == '__main__':
    unittest.main()
