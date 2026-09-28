import json
import unittest
from unittest.mock import patch

from harness.judge import GUIDE_PATH, PROMPT_PATH, judge_review
from harness.schemas import JudgeOutput, RequirementCritique


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.review = {'issues': [], 'improved_requirement': 'Original requirement.'}

    @patch('harness.judge.chat')
    def test_valid_scores(self, chat):
        for score in range(1, 6):
            with self.subTest(score=score):
                chat.return_value = {'message': {'content': json.dumps({
                    'score': score, 'reason': ' Specific reasoning. '})}}
                self.assertEqual(judge_review('Original requirement.', self.review),
                                 {'score': score, 'reason': 'Specific reasoning.'})

    @patch('harness.judge.chat')
    def test_invalid_outputs_raise_instead_of_fabricating_grade(self, chat):
        invalid = [{'score': score, 'reason': 'Reason.'}
                   for score in (0, 6, True, False, 2.5, 3.0, '3', None)]
        invalid += [
            {'score': 3}, {'reason': 'Reason.'},
            {'score': 3, 'reason': ''}, {'score': 3, 'reason': ' \n\t'},
            {'score': 3, 'reason': 123}, {'score': 3, 'reason': None},
            {'score': 3, 'reason': 'Reason.', 'verdict': 'PASS'},
            {'verdict': 'PASS', 'explanation': 'Old schema.'}, [],
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                chat.return_value = {'message': {'content': json.dumps(payload)}}
                with self.assertRaises(RuntimeError):
                    judge_review('Original requirement.', self.review)
        chat.return_value = {'message': {'content': 'not JSON'}}
        with self.assertRaises(RuntimeError):
            judge_review('Original requirement.', self.review)

    @patch('harness.judge.chat')
    def test_request_uses_guide_and_excludes_reference_information(self, chat):
        chat.return_value = {'message': {'content': '{"score":5,"reason":"No issues."}'}}
        review = dict(self.review, gold_violations={'clarity': True},
                      scorer_output={'missed': ['clarity']})
        judge_review('Original requirement.', review, model='custom-model')
        request = chat.call_args.kwargs
        self.assertEqual(request['model'], 'custom-model')
        self.assertEqual(request['format'], JudgeOutput.model_json_schema())
        self.assertEqual(request['options'], {'temperature': 0, 'num_predict': 512})
        self.assertFalse(request['think'])
        system = request['messages'][0]['content']
        self.assertEqual(PROMPT_PATH.name, 'judge_prompt_v3.txt')
        self.assertIn(PROMPT_PATH.read_text(encoding='utf-8'), system)
        guide = GUIDE_PATH.read_text(encoding='utf-8')
        for paragraph in guide.split('\n\n'):
            if not paragraph.startswith('For the initial dev pilot,'):
                self.assertIn(paragraph, system)
        self.assertNotIn('REQ-001', system)
        user = json.loads(request['messages'][1]['content'])
        self.assertEqual(user, {'requirement': 'Original requirement.', 'review': self.review})
        for forbidden in ('gold_violations', 'scorer_output'):
            self.assertNotIn(forbidden, json.dumps(request['messages']))

    @patch('harness.judge.chat')
    def test_accepts_pydantic_critique(self, chat):
        chat.return_value = {'message': {'content': '{"score":5,"reason":"No issues."}'}}
        result = judge_review('Original requirement.', RequirementCritique(**self.review))
        self.assertEqual(result['score'], 5)

    @patch('harness.judge.chat', side_effect=ConnectionError('Offline'))
    def test_transport_error_is_explicit(self, chat):
        with self.assertRaisesRegex(RuntimeError, 'Offline'):
            judge_review('Original requirement.', self.review)


if __name__ == '__main__':
    unittest.main()
