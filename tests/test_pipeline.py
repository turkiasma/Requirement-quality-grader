from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from harness.runner import load_dataset, run
from harness.schemas import CRITERIA, RequirementCritique


def item(identifier='REQ-001', split='dev'):
    return {'id': identifier, 'split': split, 'requirement': 'The API shall return HTTP 401.',
            'violations': {key: False for key in CRITERIA}}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.dataset = self.root / 'golden.jsonl'
        self.results = self.root / 'results'
        self.critique = RequirementCritique(issues=[], improved_requirement=item()['requirement'])
        self.judgment = {'score': 5, 'reason': 'The critique preserves a good requirement.'}
        self.write_items([item()])

    def write_items(self, items):
        self.dataset.write_text(''.join(json.dumps(row) + '\n' for row in items),
                                encoding='utf-8')

    def execute(self):
        console = io.StringIO()
        with redirect_stdout(console):
            path = run(self.dataset, self.results)
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        return path, rows, console.getvalue()

    @patch('harness.judge.chat')
    @patch('harness.reviewer.chat')
    def test_complete_pipeline_with_mocked_model_responses(self, reviewer_chat, judge_chat):
        reviewer_chat.return_value = SimpleNamespace(message=SimpleNamespace(
            content=self.critique.model_dump_json()))
        judge_chat.return_value = {'message': {'content': json.dumps(self.judgment)}}
        path, rows, console = self.execute()
        self.assertEqual(path.parent, self.results)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(set(row), {'id', 'split', 'requirement', 'gold_violations',
                                   'reviewer_output', 'scorer_output', 'judge_output',
                                   'status', 'error'})
        self.assertEqual(row['gold_violations'], item()['violations'])
        self.assertEqual(row['reviewer_output'], self.critique.model_dump())
        self.assertEqual(row['judge_output'], self.judgment)
        self.assertEqual(row['scorer_output']['counts'], {'tp': 0, 'fn': 0, 'fp': 0, 'tn': 5})
        self.assertEqual(row['status'], 'ok')
        self.assertIsNone(row['error'])
        for label in ('Input requirement:', 'Golden violations:', 'Reviewer output:',
                      'Scorer output:', 'Judge score: 5', 'Reason:', 'Status: ok',
                      'Completed: 1; Failed: 0; Total: 1', str(path)):
            self.assertIn(label, console)
        self.assertNotIn('Verdict:', console)

    @patch('harness.runner.judge_review')
    @patch('harness.runner.review_requirement')
    def test_only_dev_is_processed_and_files_are_not_overwritten(self, reviewer, judge):
        self.write_items([item(), item('REQ-002', 'test')])
        reviewer.return_value, judge.return_value = self.critique, self.judgment
        first, rows, _ = self.execute()
        original = first.read_bytes()
        second, _, _ = self.execute()
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual([row['id'] for row in rows], ['REQ-001'])
        self.assertEqual(reviewer.call_count, 2)
        self.assertEqual(judge.call_count, 2)
        judge.assert_called_with(item()['requirement'], self.critique)

    def test_stage_failures_preserve_completed_outputs_and_continue(self):
        self.write_items([item(), item('REQ-002')])
        for stage in ('reviewer', 'scorer', 'judge'):
            with self.subTest(stage=stage), \
                 patch('harness.runner.review_requirement', return_value=self.critique) as reviewer, \
                 patch('harness.runner.score_critique', return_value={'exact_match': True}) as scorer, \
                 patch('harness.runner.judge_review', return_value=self.judgment) as judge:
                target = {'reviewer': reviewer, 'scorer': scorer, 'judge': judge}[stage]
                target.side_effect = [RuntimeError('Stage unavailable'), target.return_value]
                _, rows, console = self.execute()
                failed, succeeded = rows
                self.assertEqual(failed['status'], 'error')
                self.assertEqual(failed['error'], {'stage': stage, 'message': 'Stage unavailable'})
                self.assertIsNone(failed['judge_output'])
                if stage == 'reviewer':
                    self.assertIsNone(failed['reviewer_output'])
                    self.assertIsNone(failed['scorer_output'])
                else:
                    self.assertEqual(failed['reviewer_output'], self.critique.model_dump())
                    if stage == 'scorer':
                        self.assertIsNone(failed['scorer_output'])
                    else:
                        self.assertEqual(failed['scorer_output'], {'exact_match': True})
                self.assertEqual(succeeded['status'], 'ok')
                self.assertEqual(succeeded['judge_output']['score'], 5)
                self.assertIn('Judge score: unavailable', console)
                self.assertIn('Completed: 1; Failed: 1; Total: 2', console)

    @patch('harness.runner.judge_review')
    @patch('harness.runner.review_requirement')
    def test_malformed_later_json_is_rejected_before_any_calls(self, reviewer, judge):
        with self.dataset.open('a', encoding='utf-8') as file:
            file.write('{invalid JSON}\n')
        with self.assertRaisesRegex(ValueError, 'line 2'):
            run(self.dataset, self.results)
        reviewer.assert_not_called()
        judge.assert_not_called()
        self.assertFalse(self.results.exists())

    @patch('harness.runner.review_requirement')
    def test_invalid_dataset_structures_are_rejected_before_calls(self, reviewer):
        invalid = [[], {}, dict(item('REQ-002'), requirement=' '),
                   dict(item('REQ-002'), violations={'clarity': False}),
                   dict(item('REQ-002'), violations={key: 0 for key in CRITERIA}),
                   dict(item('REQ-002'), split='train'), item()]
        for row in invalid:
            with self.subTest(row=row):
                self.write_items([item(), row])
                with self.assertRaisesRegex(ValueError, 'line 2'):
                    run(self.dataset, self.results)
        reviewer.assert_not_called()
        self.assertFalse(self.results.exists())

    @patch('harness.runner.review_requirement')
    def test_empty_or_test_only_dataset_does_not_start_run(self, reviewer):
        for items in ([], [item(split='test')]):
            self.write_items(items)
            with self.assertRaisesRegex(ValueError, 'no development items'):
                run(self.dataset, self.results)
        reviewer.assert_not_called()
        self.assertFalse(self.results.exists())

    def test_existing_pilot_loads(self):
        self.assertEqual(len(load_dataset()), 20)
        self.assertTrue(all(row['split'] == 'dev' for row in load_dataset()))

    def test_outputs_appear_before_next_model_call(self):
        console = io.StringIO()

        def review(requirement):
            self.assertIn('Input requirement:', console.getvalue())
            self.assertIn('Waiting for reviewer', console.getvalue())
            return self.critique

        def judge(requirement, critique):
            self.assertIn('Reviewer output:', console.getvalue())
            self.assertIn('Scorer output:', console.getvalue())
            self.assertIn('Waiting for judge', console.getvalue())
            return self.judgment

        with patch('harness.runner.review_requirement', side_effect=review), \
             patch('harness.runner.judge_review', side_effect=judge), redirect_stdout(console):
            run(self.dataset, self.results)
        self.assertIn('Judge score: 5', console.getvalue())

    @patch('harness.runner.judge_review', side_effect=KeyboardInterrupt)
    @patch('harness.runner.review_requirement')
    def test_interrupt_saves_partial_result_and_stops(self, reviewer, judge):
        reviewer.return_value = self.critique
        self.write_items([item(), item('REQ-002')])
        with redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            run(self.dataset, self.results)
        files = list(self.results.glob('*.jsonl'))
        self.assertEqual(len(files), 1)
        row = json.loads(files[0].read_text())
        self.assertEqual(row['reviewer_output'], self.critique.model_dump())
        self.assertTrue(row['scorer_output']['exact_match'])
        self.assertIsNone(row['judge_output'])
        self.assertEqual(row['error'], {'stage': 'judge', 'message': 'Interrupted by user.'})
        reviewer.assert_called_once()

    @patch('harness.runner.judge_review')
    @patch('harness.runner.review_requirement')
    def test_limit_processes_only_requested_dev_items(self, reviewer, judge):
        reviewer.return_value, judge.return_value = self.critique, self.judgment
        self.write_items([item(), item('REQ-002')])
        with redirect_stdout(io.StringIO()):
            path = run(self.dataset, self.results, limit=1)
        self.assertEqual(len(path.read_text().splitlines()), 1)
        reviewer.assert_called_once()


if __name__ == '__main__':
    unittest.main()
