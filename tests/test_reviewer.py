import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from harness.reviewer import GUIDE_PATH, PROMPT_PATH, load_prompt, review_requirement
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

    @patch('harness.reviewer.chat')
    def test_v3_request_includes_definitions_but_not_rubric_or_pilot_labels(self, chat):
        chat.return_value = SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            'issues': [], 'improved_requirement': 'Original requirement.'})))
        review_requirement('Original requirement.')
        system = chat.call_args.kwargs['messages'][0]['content']
        self.assertEqual(PROMPT_PATH.name, 'critique_prompt_v3.txt')
        self.assertIn(PROMPT_PATH.read_text(encoding='utf-8'), system)
        guide = GUIDE_PATH.read_text(encoding='utf-8')
        definitions = '## 1. Atomicity' + guide.split('## 1. Atomicity', 1)[1]
        definitions = definitions.split('## Critique Scoring Rubric', 1)[0]
        for paragraph in definitions.split('\n\n'):
            if not paragraph.lstrip().startswith('For the initial dev pilot,'):
                self.assertIn(paragraph, system)
        self.assertNotIn('REQ-001', system)
        self.assertNotIn('## Critique Scoring Rubric', system)
        self.assertNotIn('### Score 5', system)

    @patch('harness.reviewer.GUIDE_PATH')
    def test_missing_guide_sections_fail_explicitly(self, guide_path):
        guide_path.read_text.return_value = '# An incomplete guide'
        with self.assertRaisesRegex(ValueError, 'missing criterion or scoring'):
            load_prompt()


if __name__ == '__main__':
    unittest.main()
