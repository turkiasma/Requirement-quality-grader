"""Offline regression tests for references, experiments, accounting and failure paths."""
import csv
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from harness.artifacts import digest, read_jsonl
from harness.dataset import load_dataset, validate_item
from harness.review import export_review, import_review
from harness.schemas import CRITERIA, LLM1Output, SecondAssessorOutput
from harness.scorer import overall_score, compare_to_human
from harness.metrics import summarize, correction_metrics, stage_metrics
from harness.costs import Budget, estimate_cost
from harness.llm_client import call_structured, output_schema, ModelCallError
from harness.position_bias import identity, summarize as position_summary, run_case as position_case, PairwiseOutput
from harness.verbosity_bias import pad_assessment, run_case as verbosity_case, summarize as verbosity_summary
from harness.bias_common import select_cases
from harness.runner import run
from test_pipeline import item, llm1_output, second_output


def result(a=5, b=5):
    return {'result_version':'pipeline_v5', 'id':'CASE', 'split':'dev', 'annotation_status':'proposed',
            'requirement':'The API shall return HTTP 401.', 'gold_criteria':{k:5 for k in CRITERIA},
            'llm1_output': llm1_output(a).model_dump(), 'second_assessor_output':second_output(b).model_dump(),
            'llm1_meta':{}, 'second_assessor_meta':{}, 'status':'ok'}


class Files(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.data = self.root/'data.jsonl'
        self.data.write_text(json.dumps(item())+'\n')

    def test_dataset_has_150_unique_items_and_exact_split(self):
        rows=load_dataset(split='all')
        self.assertEqual(len(rows),150)
        self.assertEqual(sum(r['split']=='dev' for r in rows),20)
        self.assertEqual(sum(r['split']=='test' for r in rows),130)
        self.assertEqual(len({r['requirement'].casefold() for r in rows}),150)
        self.assertTrue(all(r['annotation_status'] in ('proposed', 'verified') for r in rows))
        for key in CRITERIA:
            self.assertTrue({r['criteria'][key] for r in rows} <= set(range(6)))

    def test_test_text_not_copied_into_prompts_or_guide(self):
        text=Path('data/labelling_guide.md').read_text()+''.join(p.read_text() for p in Path('prompts').glob('*v5.txt'))
        for row in load_dataset(split='test'):
            self.assertNotIn(row['requirement'],text)

    def test_split_selection_and_duplicate_rejection(self):
        self.data.write_text('\n'.join(json.dumps(r) for r in [item(),item('OTHER','test')]))
        self.assertEqual(len(load_dataset(self.data,'all')),2)
        self.assertEqual(load_dataset(self.data,'test')[0]['id'],'OTHER')
        duplicate=item('OTHER','test'); duplicate['requirement']=item()['requirement']
        self.data.write_text('\n'.join(json.dumps(r) for r in [item(),duplicate]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            load_dataset(self.data,'all')

    def test_reference_validation(self):
        mutations=[('gold_score',True),('gold_score',999),('annotation_status','human'),
                   ('scheme','grade_0_5_v1'),('guide_version','stale'),('criteria',{k:True for k in CRITERIA}),
                   ('justifications',{k:' ' for k in CRITERIA})]
        for key,value in mutations:
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                validate_item(dict(item(),**{key:value}))

    def test_verified_requires_human_provenance(self):
        row=item(); row['annotation_status']='verified'; row['provenance'].pop('reviewed_by')
        with self.assertRaises(ValueError): validate_item(row)

    def test_review_export_import_preserves_proposal_until_explicit_review(self):
        review=self.root/'review.csv'; output=self.root/'reviewed.jsonl'
        export_review(self.data,review)
        self.assertNotIn(b'\r\n', review.read_bytes())
        self.assertEqual(import_review(self.data,review,output),0)
        self.assertEqual(load_dataset(output)[0]['annotation_status'],'proposed')
        with review.open(newline='') as stream:
            reader=csv.DictReader(stream); rows=list(reader); fields=reader.fieldnames
        rows[0].update(annotation_status='verified',reviewed_by='Test reviewer',testability_grade='3',testability_explanation='A missing bound.')
        with review.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        output2=self.root/'reviewed2.jsonl'
        self.assertEqual(import_review(self.data,review,output2),1)
        checked=load_dataset(output2)[0]
        self.assertEqual(checked['gold_score'],4.6)
        self.assertEqual(checked['provenance']['initial_proposal']['criteria']['testability'],5)
        self.assertEqual(checked['provenance']['reviewed_by'],'Test reviewer')
        with self.assertRaises(FileExistsError): import_review(self.data,review,output2)

    def test_review_rejects_stale_source(self):
        review=self.root/'review.csv';export_review(self.data,review)
        changed=item();changed['requirement']='Changed requirement.'
        self.data.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'Source changed'):
            import_review(self.data,review,self.root/'out.jsonl')

    @patch('harness.runner.grade_requirement')
    def test_unverified_test_is_blocked_before_model_call(self,model):
        self.data.write_text(json.dumps(item(split='test')))
        with self.assertRaisesRegex(ValueError,'blocked'):
            run(self.data,self.root,split='test')
        model.assert_not_called()

    @patch('harness.runner.grade_requirement')
    def test_dry_run_validates_all_without_calls(self,model):
        with redirect_stdout(io.StringIO()):
            run(results_dir=self.root,split='all',dry_run=True)
        model.assert_not_called()
        self.assertEqual(list(self.root.glob('pipeline*')),[])

    def test_freeze_detects_changed_dataset(self):
        with redirect_stdout(io.StringIO()):
            path=run(self.data,self.root,dry_run=True,freeze=True)
        changed=item();changed['requirement']='Changed requirement.';self.data.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'Frozen configuration'):
            run(self.data,self.root,dry_run=True,frozen_config=path)

    @patch('harness.runner.assess_requirement',side_effect=RuntimeError('Unavailable'))
    @patch('harness.runner.grade_requirement',return_value=(llm1_output(4),{}))
    def test_judge_failure_preserves_first_comparison_and_total(self,*_):
        with redirect_stdout(io.StringIO()): path=run(self.data,self.root)
        row=read_jsonl(path)[0]
        self.assertEqual(row['llm1_overall_score'],4)
        self.assertIsNotNone(row['comparison']['llm1_vs_reference'])
        self.assertIsNone(row['judge_overall_score'])
        self.assertEqual(row['error']['stage'],'second_assessor')


class MetricsTests(unittest.TestCase):
    def test_equal_overall_does_not_mean_equal_criteria(self):
        a={k:3 for k in CRITERIA}; b=dict(a,atomicity=2,testability=4)
        compared=compare_to_human(a,b)
        self.assertTrue(compared['overall_exact_match'])
        self.assertFalse(compared['all_five_match'])
        self.assertEqual(compared['mean_absolute_error'],0.4)

    def test_invalid_raw_candidate_is_rejected(self):
        with self.assertRaises(ValueError):overall_score({k:99 for k in CRITERIA})
        with self.assertRaises(ValueError):overall_score({'criteria':{**llm1_output().model_dump()['criteria'],'extra':{'grade':3}}})

    def test_provisional_and_verified_metrics_stay_separate(self):
        a=result(3,4);b=result(5,5);b['annotation_status']='verified';b['split']='test'
        summary=summarize([a,b])
        self.assertEqual(set(summary['groups']),{'dev/proposed','test/verified'})
        group=summary['groups']['dev/proposed']
        self.assertEqual(group['judge']['per_criterion']['atomicity']['mae'],1)
        self.assertEqual(group['judge']['per_criterion']['atomicity']['within_one']['percent'],100)
        self.assertEqual(group['corrections']['closer']['count'],5)
        self.assertEqual(group['corrections']['overall_error']['improved']['count'],1)

    def test_corrected_equal_error_excludes_retained(self):
        row=result(2,4);row['gold_criteria']={k:3 for k in CRITERIA}
        out=correction_metrics([row])
        self.assertEqual(out['equal_error_corrections']['count'],5)
        retained=correction_metrics([result()])
        self.assertEqual(retained['equal_error_corrections']['denominator'],0)
        self.assertIsNone(retained['equal_error_corrections']['percent'])

    def test_missing_output_denominators(self):
        row=result();row['second_assessor_output']=None;row['status']='error'
        out=summarize([row])['groups']['dev/proposed']
        self.assertEqual(out['llm1']['valid'],1); self.assertEqual(out['judge']['valid'],0)
        self.assertIsNone(out['judge']['overall']['mae'])
        self.assertEqual(out['failed']['percent'],100)

    def test_known_cost_projection(self):
        row=result()
        for field in ('llm1_meta','second_assessor_meta'):
            row[field]={'estimated_cost_usd':0.01,'latency_seconds':1,'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}
        out=summarize([row])
        self.assertEqual(out['usage']['total_tokens'],30)
        self.assertEqual(out['cost_projection']['per_1000_requirements_usd'],20)
        self.assertEqual(out['cost_projection']['at_100x_1000_requirements_usd'],2000)

    def test_historical_results_rejected(self):
        with self.assertRaises(ValueError):summarize([{'status':'ok'}])


class BiasTests(unittest.TestCase):
    def test_position_identity_mapping(self):
        self.assertEqual(identity('A',['first','second']),identity('B',['second','first']))
        self.assertEqual(identity('tie',['first','second']),'tie')

    @patch('harness.position_bias.compare')
    def test_position_swaps_content_and_maps_identity(self,call):
        call.side_effect=[(PairwiseOutput(winner='A',reason='Reason'),{}),(PairwiseOutput(winner='B',reason='Reason'),{})]
        row=result(3,4);record={'calls':{},'errors':[],'status':'ok','id':'CASE'}
        position_case(record,row,'model',0)
        first,second=[c.args for c in call.call_args_list]
        self.assertEqual(first[1],second[2]);self.assertEqual(first[2],second[1])
        self.assertNotIn('gold_criteria',json.dumps(first))
        out=position_summary([record])
        self.assertEqual(out['preference_reversal']['count'],0)
        self.assertEqual(out['first_position_preference']['percent'],50)

    def test_position_first_slot_bias_and_tie_changes(self):
        rows=[{'id':'x','status':'ok','preferences':{'AB':'initial','BA':'corrected'},
               'calls':{k:{'output':{'winner':'A'}} for k in ('AB','BA')}},
              {'id':'y','status':'ok','preferences':{'AB':'tie','BA':'initial'},
               'calls':{'AB':{'output':{'winner':'tie'}},'BA':{'output':{'winner':'B'}}}}]
        out=position_summary(rows)
        self.assertEqual(out['preference_reversal']['percent'],100)
        self.assertEqual(out['tie_change']['count'],1)

    def test_padding_is_only_repetition_and_does_not_mutate_input(self):
        original=llm1_output().model_dump();before=deepcopy(original)
        padded=pad_assessment(original)
        self.assertEqual(original,before)
        for key in CRITERIA:
            self.assertEqual(padded['criteria'][key]['grade'],original['criteria'][key]['grade'])
            self.assertEqual(padded['criteria'][key]['explanation'],' '.join([original['criteria'][key]['explanation']]*3))

    @patch('harness.verbosity_bias.assess_requirement')
    def test_verbosity_repeated_control_and_metrics(self,call):
        call.side_effect=[(second_output(3),{}),(second_output(4),{}),(second_output(3),{})]
        record={'calls':{},'errors':[],'status':'ok','id':'CASE'}
        verbosity_case(record,result(3,3),'model',0)
        self.assertEqual(call.call_args_list[0].args,call.call_args_list[2].args)
        out=verbosity_summary([record])
        self.assertEqual(out['padding_effect']['criterion_scores']['increased']['percent'],100)
        self.assertEqual(out['repeat_control']['criterion_scores']['unchanged']['percent'],100)

    @patch('harness.verbosity_bias.assess_requirement')
    def test_bias_failure_keeps_other_conditions(self,call):
        call.side_effect=[(second_output(3),{}),RuntimeError('offline'),(second_output(3),{})]
        record={'calls':{},'errors':[],'status':'ok','id':'CASE'}
        verbosity_case(record,result(),'model',0)
        out=verbosity_summary([record])
        self.assertEqual(out['padding_effect']['valid_pairs'],0)
        self.assertEqual(out['repeat_control']['valid_pairs'],1)


class ClientTests(unittest.TestCase):
    def response(self, content=None, finish='stop'):
        return SimpleNamespace(id='fixture',model='openai/gpt-4o-mini',
            choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=content or llm1_output().model_dump_json()))],
            usage=SimpleNamespace(prompt_tokens=100,completion_tokens=50,total_tokens=150))

    def test_budget_persists_and_stops_before_cap(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'budget.json';Budget(path).reserve(1.9,'x')
            with self.assertRaises(RuntimeError):Budget(path).reserve(.2,'x')
            Budget(path).settle(1.9,.1,'x')
            self.assertAlmostEqual(json.loads(path.read_text())['reserved_or_spent_usd'],.1)
        with self.assertRaises(ValueError):Budget(cap=3)

    def test_prices_and_strict_provider_schema(self):
        self.assertAlmostEqual(estimate_cost('openai/gpt-4o-mini',1000,1000),.00075)
        schema=output_schema(LLM1Output)['properties']['criteria']
        self.assertEqual(set(schema['required']),set(CRITERIA))
        self.assertFalse(schema['additionalProperties'])

    @patch('harness.llm_client.Budget')
    @patch('harness.llm_client.get_client')
    def test_client_validates_and_records_usage(self,client,budget):
        client.return_value.chat.completions.create.return_value=self.response()
        output,meta=call_structured('openai/gpt-4o-mini','system','requirement',LLM1Output,1024)
        self.assertEqual(output,llm1_output())
        self.assertEqual(meta['total_tokens'],150);self.assertGreaterEqual(meta['latency_seconds'],0)
        self.assertAlmostEqual(meta['estimated_cost_usd'],.000045)
        budget.return_value.reserve.assert_called_once();budget.return_value.settle.assert_called_once()
        request=client.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(request['temperature'],0)
        self.assertEqual(request['response_format']['type'],'json_schema')

    @patch('harness.llm_client.Budget')
    @patch('harness.llm_client.get_client')
    def test_invalid_and_truncated_output_preserve_usage(self,client,budget):
        for response in (self.response('{"bad":true}'),self.response(finish='length')):
            client.return_value.chat.completions.create.return_value=response
            with self.assertRaises(ModelCallError) as ctx:
                call_structured('openai/gpt-4o-mini','s','u',LLM1Output,1024)
            self.assertEqual(ctx.exception.metadata['total_tokens'],150)

    @patch('harness.llm_client.Budget')
    @patch('harness.llm_client.get_client')
    def test_transport_errors_never_log_provider_secret(self,client,budget):
        client.return_value.chat.completions.create.side_effect=RuntimeError('sensitive-key-placeholder')
        with self.assertRaises(ModelCallError) as ctx:
            call_structured('openai/gpt-4o-mini','s','u',LLM1Output,1024)
        self.assertNotIn('sensitive-key-placeholder',str(ctx.exception))
        self.assertEqual(ctx.exception.metadata['cost_status'],'unknown_reserved')
        budget.return_value.settle.assert_not_called()

    @patch('harness.judge.call_structured')
    def test_retained_is_derived_from_numeric_grades(self,call):
        from harness.judge import assess_requirement
        wrong=second_output(3)
        call.return_value=(wrong,{})
        out,_=assess_requirement('Original requirement',llm1_output(5))
        self.assertTrue(all(not v.retained for v in out.criteria.values()))
        call.return_value=(second_output(3),{})
        out,_=assess_requirement('Original requirement',llm1_output(3))
        self.assertTrue(all(v.retained for v in out.criteria.values()))


if __name__=='__main__': unittest.main()
