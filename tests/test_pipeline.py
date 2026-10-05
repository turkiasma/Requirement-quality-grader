"""Runner integration tests against synthetic fixtures. These verify pipeline
behaviour, not model quality or agreement with humans -- real human labels
under the grade_0_5_v1 scheme do not exist yet (see docs/IMPLEMENTATION_PLAN.md).
"""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harness.runner import load_dataset, run
from harness.schemas import CRITERIA, GOLD_SCHEME, LLM1Output, SecondAssessorOutput


def item(identifier='REQ-001', split='dev', with_gold=False):
    row = {'id': identifier, 'split': split, 'requirement': 'The API shall return HTTP 401.'}
    if with_gold:
        row['scheme'] = GOLD_SCHEME
        row['criteria'] = {key: 5 for key in CRITERIA}
    return row


def llm1_output(grade=5):
    return LLM1Output.model_validate(
        {'criteria': {key: {'grade': grade, 'explanation': 'Reason.'} for key in CRITERIA}})


def second_output(grade=5):
    return SecondAssessorOutput.model_validate(
        {'criteria': {key: {'grade': grade, 'retained': True, 'reason': 'Reason.'} for key in CRITERIA}})


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.dataset = self.root / 'golden.jsonl'
        self.results = self.root / 'results'
        self.llm1 = llm1_output()
        self.second = second_output()
        self.write_items([item()])

    def write_items(self, items):
        self.dataset.write_text(''.join(json.dumps(row) + '\n' for row in items), encoding='utf-8')

    def execute(self):
        console = io.StringIO()
        with redirect_stdout(console):
            path = run(self.dataset, self.results)
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        return path, rows, console.getvalue()

    @patch('harness.runner.assess_requirement')
    @patch('harness.runner.grade_requirement')
    def test_complete_pipeline_gold_pending(self, grade_requirement, assess_requirement):
        grade_requirement.return_value = (self.llm1, {'model': 'x', 'latency_seconds': 0.1})
        assess_requirement.return_value = (self.second, {'model': 'x', 'latency_seconds': 0.1})
        path, rows, console = self.execute()
        self.assertTrue(path.name.startswith('pipeline_v4_'))
        row = rows[0]
        self.assertIsNone(row['gold_criteria'])
        self.assertIsNone(row['gold_score'])
        self.assertIsNone(row['comparison'])
        self.assertEqual(row['llm1_output'], self.llm1.model_dump())
        self.assertEqual(row['second_assessor_output'], self.second.model_dump())
        self.assertEqual(row['status'], 'ok')
        self.assertIn('Gold criteria: pending', console)

    @patch('harness.runner.assess_requirement')
    @patch('harness.runner.grade_requirement')
    def test_complete_pipeline_with_gold(self, grade_requirement, assess_requirement):
        self.write_items([item(with_gold=True)])
        grade_requirement.return_value = (self.llm1, {})
        assess_requirement.return_value = (self.second, {})
        _, rows, _ = self.execute()
        row = rows[0]
        self.assertEqual(row['gold_score'], 5.0)
        self.assertTrue(row['comparison']['llm1_vs_human']['all_five_match'])
        self.assertTrue(row['comparison']['second_vs_human']['all_five_match'])
        self.assertEqual(row['comparison']['correction_direction']['tally'],
                          {'closer': 0, 'farther': 0, 'equal': 5})

    @patch('harness.runner.assess_requirement')
    @patch('harness.runner.grade_requirement')
    def test_second_assessor_never_receives_gold(self, grade_requirement, assess_requirement):
        self.write_items([item(with_gold=True)])
        grade_requirement.return_value = (self.llm1, {})
        assess_requirement.return_value = (self.second, {})
        self.execute()
        args, kwargs = assess_requirement.call_args
        self.assertEqual(args, ('The API shall return HTTP 401.', self.llm1))
        self.assertEqual(kwargs, {})

    @patch('harness.runner.assess_requirement')
    @patch('harness.runner.grade_requirement')
    def test_only_dev_is_processed_and_files_are_not_overwritten(self, grade_requirement, assess_requirement):
        self.write_items([item(), item('REQ-002', 'test')])
        grade_requirement.return_value = (self.llm1, {})
        assess_requirement.return_value = (self.second, {})
        first, rows, _ = self.execute()
        original = first.read_bytes()
        second, _, _ = self.execute()
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual([row['id'] for row in rows], ['REQ-001'])

    def test_stage_failures_preserve_completed_outputs_and_continue(self):
        self.write_items([item(), item('REQ-002')])
        for stage in ('llm1', 'second_assessor'):
            with self.subTest(stage=stage), \
                 patch('harness.runner.grade_requirement', return_value=(self.llm1, {})) as g, \
                 patch('harness.runner.assess_requirement', return_value=(self.second, {})) as a:
                target = {'llm1': g, 'second_assessor': a}[stage]
                target.side_effect = [RuntimeError('Stage unavailable'), target.return_value]
                _, rows, console = self.execute()
                failed, succeeded = rows
                self.assertEqual(failed['status'], 'error')
                self.assertEqual(failed['error'], {'stage': stage, 'message': 'Stage unavailable'})
                if stage == 'llm1':
                    self.assertIsNone(failed['llm1_output'])
                else:
                    self.assertEqual(failed['llm1_output'], self.llm1.model_dump())
                self.assertIsNone(failed['second_assessor_output'])
                self.assertEqual(succeeded['status'], 'ok')
                self.assertEqual(console.count('Waiting for LLM1'), 2)

    def test_rejects_unversioned_criteria_old_binary_scheme(self):
        self.write_items([dict(item(), criteria={key: 0 for key in CRITERIA})])
        with self.assertRaisesRegex(ValueError, 'scheme and criteria'):
            run(self.dataset, self.results)

    def test_rejects_mismatched_scheme(self):
        self.write_items([dict(item(), scheme='violations_v1', criteria={key: 0 for key in CRITERIA})])
        with self.assertRaisesRegex(ValueError, 'Unsupported or mismatched scheme'):
            run(self.dataset, self.results)

    def test_rejects_invalid_gold_criteria_values(self):
        self.write_items([dict(item(), scheme=GOLD_SCHEME, criteria={key: 1 for key in CRITERIA[:4]})])
        with self.assertRaisesRegex(ValueError, 'line 1'):
            run(self.dataset, self.results)

    @patch('harness.runner.grade_requirement')
    def test_invalid_dataset_structures_are_rejected_before_calls(self, grade_requirement):
        invalid = [[], {}, dict(item('REQ-002'), requirement=' '), dict(item('REQ-002'), split='train')]
        for row in invalid:
            with self.subTest(row=row):
                self.write_items([item(), row])
                with self.assertRaisesRegex(ValueError, 'line 2'):
                    run(self.dataset, self.results)
        grade_requirement.assert_not_called()

    def test_empty_or_test_only_dataset_does_not_start_run(self):
        for items in ([], [item(split='test')]):
            self.write_items(items)
            with self.assertRaisesRegex(ValueError, 'no development items'):
                run(self.dataset, self.results)

    def test_existing_pending_dataset_loads(self):
        items = load_dataset(Path('data') / 'golden_set_pending.jsonl')
        self.assertEqual(len(items), 20)
        self.assertTrue(all(row['split'] == 'dev' for row in items))

    @patch('harness.runner.assess_requirement', side_effect=KeyboardInterrupt)
    @patch('harness.runner.grade_requirement')
    def test_interrupt_saves_partial_result_and_stops(self, grade_requirement, assess_requirement):
        grade_requirement.return_value = (self.llm1, {})
        self.write_items([item(), item('REQ-002')])
        with redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            run(self.dataset, self.results)
        files = list(self.results.glob('*.jsonl'))
        self.assertEqual(len(files), 1)
        row = json.loads(files[0].read_text())
        self.assertEqual(row['llm1_output'], self.llm1.model_dump())
        self.assertIsNone(row['second_assessor_output'])
        self.assertEqual(row['error'], {'stage': 'second_assessor', 'message': 'Interrupted by user.'})

    @patch('harness.runner.assess_requirement')
    @patch('harness.runner.grade_requirement')
    def test_limit_processes_only_requested_dev_items(self, grade_requirement, assess_requirement):
        grade_requirement.return_value = (self.llm1, {})
        assess_requirement.return_value = (self.second, {})
        self.write_items([item(), item('REQ-002')])
        with redirect_stdout(io.StringIO()):
            path = run(self.dataset, self.results, limit=1)
        self.assertEqual(len(path.read_text().splitlines()), 1)
        grade_requirement.assert_called_once()


if __name__ == '__main__':
    unittest.main()
