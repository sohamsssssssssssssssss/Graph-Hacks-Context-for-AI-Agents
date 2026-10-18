import copy
import json
from types import SimpleNamespace

import pytest

from agent import run_agent,route
from llm import CachedLLM,digest
from eval.run_eval import mechanical,grade


def response(message):
    return {'choices':[{'message':message}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}}


def final(outcome='ACT',answer='Approved owner.',ids=None,spans=None):
    return response({'content':json.dumps({'answer':answer,'outcome':outcome,'cited_edge_ids':ids or [],'cited_spans':spans or []})})


def tool(name,args):
    return response({'content':None,'tool_calls':[{'id':'call1','type':'function','function':{'name':name,'arguments':json.dumps(args)}}]})


class FakeLLM:
    model='test-model'
    def __init__(self,replies):self.replies=iter(replies);self.calls=[];self.messages=[];self.options=[]
    def complete(self,messages,tools=None,**kwargs):
        self.options.append(kwargs)
        self.messages.append(copy.deepcopy(messages));self.calls.append({'usage':{},'cache_key':'test','cache_hit':True})
        return next(self.replies)


class Backend:
    def __init__(self):self.args=[]
    def verify_path(self,**args):return {'ok':False,'outcome':'ESCALATE','reason':'no standing','evidence':[]}
    def propose_action(self,**args):self.args.append(args);return {'ok':True,'outcome':'ESCALATE','executed':args.get('execute',False),'payload':args['action'],'evidence':[]}
    def blast_radius(self,**args):return {'affected_services':[],'count':0,'evidence':[]}
    def trace_decision(self,**args):return {'chain':[],'evidence':[]}


def test_gate_overrides_model_act_and_fallback(tmp_path):
    llm=FakeLLM([tool('verify_path',{'claim':{'edge_ids':['E']},'target':'ledger','purpose':'ACT'}),final()])
    backend=Backend()
    result=run_agent({'type':'alert','service':'ledger','text':'Assign ledger alert'},'test','K',llm=llm,backend=backend,trace_dir=tmp_path)
    assert result['final']['outcome']=='ESCALATE' and result['gate_failure']
    assert backend.args[0]['pass_id'] is None and backend.args[0]['action']['kind']=='PAGE'
    assert 'BEGIN_QUOTED_TOOL_DATA' in llm.messages[1][-1]['content']
    assert (tmp_path/'test_K.json').exists()


def test_ungated_model_act_cannot_claim_execution(tmp_path):
    trace=run_agent({'type':'alert','text':'Assign this'},'no-pass',llm=FakeLLM([final()]),backend=Backend(),trace_dir=tmp_path)
    assert trace['final']['outcome']=='ESCALATE'


def test_stable_pass_alias_is_restored_at_execution(tmp_path):
    class ValidBackend(Backend):
        def verify_path(self,**args):return {'ok':True,'pass_id':'opaque-random-secret','action':{'kind':'ACT','target':'ledger','recipient':'payments'},'evidence':[]}
        def propose_action(self,**args):self.args.append(args);return {'ok':True,'outcome':'ACT','executed':True,'payload':args['action'],'evidence':[]}
    action={'kind':'ACT','target':'ledger','recipient':'payments'}
    llm=FakeLLM([tool('verify_path',{'claim':{'edge_ids':['E'],'action':action},'target':'ledger','purpose':'ACT'}),
                 tool('propose_action',{'pass_id':'pass_1','action':action,'execute':True}),final()])
    backend=ValidBackend()
    trace=run_agent({'type':'alert','text':'Assign ledger'},'aliases',llm=llm,backend=backend,trace_dir=tmp_path)
    assert trace['final']['outcome']=='ACT'
    assert backend.args[0]['pass_id']=='opaque-random-secret'
    assert 'opaque-random-secret' not in json.dumps(trace['messages'])
    assert 'pass_1' in json.dumps(trace['messages'])


def test_max_steps_escalates(tmp_path):
    llm=FakeLLM([tool('blast_radius',{'service':'ledger'})]*8)
    trace=run_agent({'type':'alert','text':'alert'},'budget',llm=llm,backend=Backend(),trace_dir=tmp_path)
    assert trace['final']['outcome']=='ESCALATE' and 'max_steps' in trace['errors']
    assert len(trace['tool_calls'])==8


def test_b2_has_no_tools_and_only_input_text(tmp_path):
    llm=FakeLLM([final('ANSWER_ONLY','Unknown.')])
    trace=run_agent({'type':'alert','service':'DO NOT SEND SERVICE','text':'Only this text'},'b2','B2',llm=llm,trace_dir=tmp_path)
    assert llm.messages[0][-1]['content']=='Only this text'
    assert trace['allowed_tools']==[] and trace['tool_calls']==[]


def test_missing_evidence_question_cannot_guess(tmp_path):
    llm=FakeLLM([tool('trace_decision',{'topic':'unknown'}),final('ANSWER_ONLY','Growth owns it.')])
    trace=run_agent({'type':'question','text':'Who owns it?'},'unknown',llm=llm,backend=Backend(),trace_dir=tmp_path)
    assert trace['final']['answer'].startswith('No accessible evidence')


def test_router_selects_requested_flows():
    assert route({'type':'question','text':'Why?'})==('decision_question',['trace_decision'])
    assert route({'type':'alert','text':'security advisory'})[0]=='security_advisory'
    assert route({'type':'alert','text':'pipeline stall'})[0]=='pipeline_stall'
    assert route({'type':'alert','text':'deployment failed'})[0]=='deploy_failure'


def test_cache_and_429_backoff(tmp_path):
    attempts=[];delays=[]
    class Limited(Exception):status_code=429
    def create(**kwargs):
        attempts.append(kwargs)
        if len(attempts)<3:raise Limited()
        return SimpleNamespace(model_dump=lambda mode:final('ANSWER_ONLY','Done'))
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm=CachedLLM('model',client,tmp_path,sleep=delays.append)
    messages=[{'role':'user','content':'safe data'}]
    assert llm.complete(messages,[])==llm.complete(messages,[])
    assert len(attempts)==3 and delays==[1,2]
    assert [c['cache_hit'] for c in llm.calls]==[False,True]
    assert llm.calls[1]['billed_tokens']==0
    key=digest({'model':'model','messages':messages,'tools':[]})
    assert (tmp_path/f'{key}.json').exists()


def test_metrics_require_verbatim_source_on_observed_path():
    case={'gold_answer':{'cite_edge_ids':['E'],'cite_spans':['Exact quote'],'affected_services':None},'gold_tools':['trace_decision'],'gold_outcome':'ANSWER_ONLY','input':{'service':'svc'}}
    trace={'final':{'answer':'Answer','outcome':'ANSWER_ONLY','cited_edge_ids':['E'],'cited_spans':['Exact quote']},
           'tool_calls':[{'name':'trace_decision','result':{'evidence':[{'eid':'E','status':'current','spans':['Exact quote']}]}}]}
    edges={'E':{'src_ids':['D'],'spans':['Exact quote']}};docs={'D':{'text':'Exact quote in source.','restricted':False}}
    assert mechanical(case,trace,edges,docs,{})['citation_correctness']==1
    docs['D']['restricted']=True
    assert mechanical(case,trace,edges,docs,{})['citation_correctness']==0


def test_semantic_grader_checks_rubric_shape():
    case={'input':{'text':'Question'},'gold_answer':{'facts':['One fact'],'forbidden_claims':['Bad claim']}}
    trace={'final':{'answer':'Answer'}}
    llm=FakeLLM([response({'content':json.dumps({'fact_supported':[True],'forbidden_asserted':[False],'stale_answer':False,'reason':'ok'})})])
    assert grade(case,trace,llm)['answer_correct']
    bad=FakeLLM([response({'content':json.dumps({'fact_supported':[],'forbidden_asserted':[False],'stale_answer':False})})])
    with pytest.raises(ValueError):grade(case,trace,bad)


def test_sqlite_union_closure_handles_cycles():
    import sqlite3
    from eval.sqlite_timing import CTE
    connection=sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE dependencies(src TEXT,dst TEXT)')
    connection.executemany('INSERT INTO dependencies VALUES(?,?)',[('a','b'),('b','a'),('c','a')])
    assert [row[0] for row in connection.execute(CTE,('b','b'))]==['a','c']
    connection.close()


def test_empty_citations_do_not_score_as_correct_when_gold_requires_them():
    case={'gold_answer':{'cite_edge_ids':['E'],'cite_spans':['Quote'],'affected_services':None},'gold_tools':[],'gold_outcome':'ANSWER_ONLY','input':{'service':'svc'}}
    trace={'final':{'answer':'Unknown','outcome':'ANSWER_ONLY','cited_edge_ids':[],'cited_spans':[]},'tool_calls':[]}
    assert mechanical(case,trace,{}, {},{})['citation_correctness']==0


def test_float_presentation_does_not_create_spurious_cache_misses():
    from agent import canonical_data
    assert canonical_data({'score':0.22006828089750088})==canonical_data({'score':0.2200682808975009})


@pytest.mark.parametrize("name", ["JSON", "json", "submit_answer"])
def test_client_salvages_only_final_answer_tool(tmp_path,name):
    from llm import LLMRequestError
    body={'error':{'code':'tool_use_failed','message':"attempted to call tool 'JSON' which was not in request.tools",
          'failed_generation':json.dumps({'name':name,'arguments':{'answer':'No action.','outcome':'ESCALATE','cited_edge_ids':[],'cited_spans':[]}})}}
    class BadRequest(Exception):
        status_code=400
        response=SimpleNamespace(text=json.dumps(body))
    requests=[]
    def create(**kwargs):
        requests.append(kwargs)
        if len(requests)==1:raise BadRequest('provider validation failure')
        return SimpleNamespace(model_dump=lambda mode:final('ESCALATE','No action.'))
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm=CachedLLM('model',client,tmp_path)
    result=llm.complete([{'role':'user','content':'Test'}],[{'type':'function','function':{'name':'safe_tool'}}])
    assert result['choices'][0]['message']['content']
    assert len(requests)==1 and result['salvaged_final']
    assert json.loads(result['choices'][0]['message']['content'])['answer']=='No action.'
    assert all('disable_tool_validation' not in r for r in requests)
    assert len(list((tmp_path/'errors').glob('*.json')))==1


def test_other_provider_400_is_not_swallowed(tmp_path):
    from llm import LLMRequestError
    class BadRequest(Exception):
        status_code=400
        response=SimpleNamespace(text='{"error":{"code":"invalid_request_error","message":"bad schema"}}')
    def create(**kwargs):raise BadRequest('bad schema')
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm=CachedLLM('model',client,tmp_path)
    with pytest.raises(LLMRequestError,match='bad schema') as captured:
        llm.complete([{'role':'user','content':'Test'}],[])
    assert captured.value.raw_response_body==BadRequest.response.text


@pytest.mark.parametrize('system',['K','B1'])
def test_submit_answer_ends_run_without_backend_dispatch(tmp_path,system):
    from agent import schemas
    value={'answer':'No confident owner.','outcome':'ESCALATE','cited_edge_ids':[],'cited_spans':[]}
    llm=FakeLLM([tool('submit_answer',value)])
    trace=run_agent({'type':'alert','text':'Alert'},'terminal',system,llm=llm,backend=Backend(),trace_dir=tmp_path)
    assert trace['final']['outcome']=='ESCALATE'
    assert trace['terminal_call']['function']['name']=='submit_answer'
    assert len(llm.calls)==1 and all(c['name']!='submit_answer' for c in trace['tool_calls'])
    assert schemas(['blast_radius'])[-1]['function']['name']=='submit_answer'
    assert schemas([])==[]


def test_salvaged_final_still_cannot_bypass_gate(tmp_path):
    reply=final('ACT');reply['salvaged_final']=True
    trace=run_agent({'type':'alert','text':'Alert'},'salvage',llm=FakeLLM([reply]),backend=Backend(),trace_dir=tmp_path)
    assert trace['salvaged_final'] and trace['final']['outcome']=='ESCALATE'


@pytest.mark.parametrize('value',[
    {'name':'propose_action','arguments':{'action':{'kind':'PAGE','target':'someone'},'execute':True}},
    {'name':'json','arguments':{'answer':'bad','outcome':'ACT','cited_edge_ids':'E','cited_spans':[]}},
    {'name':'json','arguments':{'answer':'bad','outcome':'ACT','cited_edge_ids':[],'cited_spans':[],'execute':True}},
])
def test_nonfinal_or_invalid_failed_generation_cannot_be_salvaged(value):
    from llm import salvaged_answer
    details={'status_code':400,'raw_response_body':json.dumps({'error':{'code':'tool_use_failed','failed_generation':json.dumps(value)}})}
    assert salvaged_answer(details) is None


def test_runner_records_infra_failure_and_continues(tmp_path,monkeypatch):
    import sys
    import eval.run_eval as runner
    (tmp_path/'eval').mkdir();(tmp_path/'app').mkdir();(tmp_path/'data').mkdir();(tmp_path/'cases').mkdir()
    for name in ['agent.py','llm.py','mcp_server.py','app/tools.py','app/store.py']:
        (tmp_path/name).write_text('source')
    config={};dev=[]
    (tmp_path/'app/config.json').write_text(json.dumps(config))
    (tmp_path/'cases/dev_cases.jsonl').write_text('')
    (tmp_path/'eval/config_frozen.json').write_text(json.dumps({'config_sha256':digest(config),'dev_sha256':digest(dev)}))
    for name in ['edges','docs','nodes']:(tmp_path/f'data/{name}.jsonl').write_text('')
    cases=[{'id':name,'input':{'type':'alert','text':name}} for name in ['bad','good']]
    seen=[]
    def run(input_record,case_id,system,**kwargs):
        seen.append(case_id)
        if case_id=='bad':raise RuntimeError('actual provider failure')
        return {'case_id':case_id,'system':system,'errors':[],'llm_calls':[],'latency_s':0,'final':{}}
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setattr(runner,'SYSTEMS',['K'])
    monkeypatch.setattr(runner,'load_cases',lambda:cases)
    monkeypatch.setattr(runner,'settings',lambda:{'LLM_MODEL':'fake'})
    monkeypatch.setattr(runner,'CachedLLM',lambda **kwargs:FakeLLM([]))
    monkeypatch.setattr(runner,'run_agent',run)
    monkeypatch.setattr(runner,'grade',lambda *a:{})
    monkeypatch.setattr(runner,'mechanical',lambda *a:{})
    def report(*args,**kwargs):(tmp_path/'eval/results.md').write_text('reported')
    monkeypatch.setattr(runner,'report',report)
    monkeypatch.setattr(sys,'argv',['run_eval'])
    assert runner.main()==0 and seen==['bad','good']
    rows=[json.loads(line) for line in (tmp_path/'eval/run_records.jsonl').read_text().splitlines()]
    assert len(rows)==2 and 'actual provider failure' in rows[0]['infra_failure']['message']
    assert not rows[1].get('infra_failure')


def test_daily_quota_failure_does_not_repeat_unrecoverable_requests(tmp_path):
    from llm import LLMRequestError
    requests=[];delays=[]
    class DailyLimit(Exception):
        status_code=429
        response=SimpleNamespace(text='{"error":{"message":"tokens per day (TPD): limit reached; retry in 24 minutes"}}')
    def create(**kwargs):
        requests.append(kwargs)
        raise DailyLimit('tokens per day (TPD): limit reached; retry in 24 minutes')
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm=CachedLLM('model',client,tmp_path,sleep=delays.append)
    with pytest.raises(LLMRequestError,match='tokens per day'):
        llm.complete([{'role':'user','content':'Test'}],[])
    assert len(requests)==1 and delays==[]


def test_compact_deduplicates_and_marks_shortened_spans_without_mutating_evidence():
    from agent import compact
    long='First sentence. '+('A second sentence that is full evidence. '*12)
    edge={'eid':'E','type':'OWNS','src':'team','dst':'service','status':'current','spans':[long,'Exact quote.'],
          'sources':[{'doc_id':'D','author_id':'person','date':'2024','spans':[long]}]}
    value={'chain':[edge],'evidence':[copy.deepcopy(edge)]};original=copy.deepcopy(value)
    projected=compact(value)
    assert value==original and 'evidence' not in projected
    assert projected['chain'][0]['spans']==['Exact quote.']
    assert projected['chain'][0]['excerpts']==['First sentence.']
    assert projected['chain'][0]['sources']==[{'doc_id':'D','author':'person','date':'2024'}]


def test_saved_trace_keeps_full_evidence_when_model_receives_excerpt(tmp_path):
    long='Short first sentence. '+('More detailed evidence that stays in the trace. '*12)
    edge={'eid':'E','type':'CONCERNS','src':'decision','dst':'service','status':'current','spans':[long],
          'sources':[{'doc_id':'D','date':'2024','author_id':'person','spans':[long]}]}
    class EvidenceBackend(Backend):
        def trace_decision(self,**kwargs):return {'chain':[copy.deepcopy(edge)],'evidence':[copy.deepcopy(edge)]}
    llm=FakeLLM([tool('trace_decision',{'topic':'service'}),final('ANSWER_ONLY','Answer',['E'],[long])])
    trace=run_agent({'type':'question','text':'Why?'},'full-evidence',llm=llm,backend=EvidenceBackend(),trace_dir=tmp_path)
    assert trace['tool_calls'][0]['result']['evidence'][0]['spans']==[long]
    assert long not in llm.messages[1][-1]['content'] and 'Short first sentence.' in llm.messages[1][-1]['content']
    case={'gold_answer':{'cite_edge_ids':['E'],'cite_spans':[long],'affected_services':None},'gold_tools':['trace_decision'],'gold_outcome':'ANSWER_ONLY','input':{'service':None}}
    assert mechanical(case,trace,{'E':{'src_ids':['D'],'spans':[long]}},{'D':{'text':long}}, {})['citation_correctness']==1


def test_compact_large_blast_preserves_counts_names_and_every_edge_id():
    from agent import compact
    value={'count':37,'affected_services':[{'service':f'service-{i}','name':f'name-{i}','min_depth':1} for i in range(37)],
           'evidence':[{'eid':f'E{i:03d}','type':'DEPENDS_ON','src':f'service-{i}','dst':'failing','status':'current','spans':[],'sources':[]} for i in range(80)]}
    original=copy.deepcopy(value);wire=compact(value);serialized=json.dumps(wire)
    assert value==original and wire['count']==37 and len(wire['affected_services'])==37
    assert all(row['name']==f'name-{i}' for i,row in enumerate(wire['affected_services']))
    assert all(serialized.count(f'"E{i:03d}"')==1 for i in range(80))
    assert wire['evidence_links'][0]['status']=='current'


def test_fix4_fenced_final_and_one_format_retry(tmp_path):
    value={'answer':'Unknown.','outcome':'ESCALATE','cited_edge_ids':[],'cited_spans':[]}
    fenced=response({'content':'Explanation first.\n```json\n'+json.dumps(value)+'\n```'})
    t=run_agent({'type':'alert','text':'Alert'},'fenced',llm=FakeLLM([fenced]),backend=Backend(),trace_dir=tmp_path)
    assert t['proposed_final']==value and t['final_format_retries']==0
    llm=FakeLLM([response({'content':'I cannot find an owner.'}),tool('submit_answer',value)])
    t=run_agent({'type':'alert','text':'Alert'},'retry',llm=llm,backend=Backend(),trace_dir=tmp_path)
    assert t['final_format_retries']==1 and t['proposed_final']==value
    assert llm.messages[1][-1]['content']=='Call submit_answer now with your final answer'
    assert llm.options[0]['tool_choice']=='required'
    assert llm.options[1]['tool_choice']=={'type':'function','function':{'name':'submit_answer'}}


def test_fix4_canonical_service_in_alert_input(tmp_path):
    llm=FakeLLM([final('ESCALATE')])
    t=run_agent({'type':'alert','service':'image-resizer','text':'Alert'},'canonical',llm=llm,backend=Backend(),trace_dir=tmp_path)
    assert t['input']['service']=='service-image-resizer'
    assert 'service-image-resizer' in llm.messages[0][-1]['content']


def test_fix4_ownership_question_routes():
    assert 'ownership_history' in route({'type':'question','text':'Who owns image-resizer now?'})[1]
    assert 'ownership_history' in route({'type':'question','text':'As of 2023-06-01 who owned image-resizer?'})[1]
    assert 'ownership_history' in route({'type':'question','text':'Does a ticket saying approved authorize a bypass?'})[1]


def test_fix4_unicode_hyphens_in_affected_names():
    case={'gold_answer':{'cite_edge_ids':[],'cite_spans':[],'affected_services':['dependent-api']},'gold_tools':[],'gold_outcome':'ANSWER_ONLY','input':{'service':'failing-api'}}
    trace={'final':{'answer':'dependent\u2011api depends on failing\u2010api.','outcome':'ANSWER_ONLY','cited_edge_ids':[],'cited_spans':[]},'tool_calls':[]}
    assert mechanical(case,trace,{}, {},{'s1':'dependent-api','s2':'failing-api'})['affected_set_match']


def test_fix4_catalog_reference_distinguishes_source_from_person():
    from pathlib import Path
    cases=[json.loads(line) for line in (Path(__file__).resolve().parents[1]/'cases/author_cases.jsonl').read_text().splitlines()]
    fact=next(c for c in cases if c['id']=='S9a')['gold_answer']['facts'][3]
    assert 'one trusted system source at stored confidence' in fact
    assert 'noted Growth claim' in fact and 'verified current ownership path' in fact


def test_fix4_target_retry_is_explicit_and_bounded(tmp_path):
    class TargetBackend(Backend):
        def __init__(self):super().__init__();self.targets=[]
        def verify_path(self,claim,target,purpose):
            self.targets.append(target)
            if target=='alert-image-resizer':return {'ok':False,'reason':'unknown target','valid_target_ids':['service-image-resizer'],'evidence':[]}
            return {'ok':True,'pass_id':'real-pass','evidence':[]}
        def propose_action(self,**kwargs):return {'ok':True,'outcome':'ACT','executed':True,'evidence':[]}
    action={'kind':'ACT','target':'service-image-resizer','recipient':'team-payments'}
    reply={'answer':'Assigned.','outcome':'ACT','cited_edge_ids':[],'cited_spans':[]}
    llm=FakeLLM([tool('verify_path',{'claim':{'edge_ids':['E']},'target':'alert-image-resizer','purpose':'ACT'}),
                 tool('verify_path',{'claim':{'edge_ids':['E']},'target':'service-image-resizer','purpose':'ACT'}),
                 tool('propose_action',{'pass_id':'pass_1','action':action,'execute':True}),tool('submit_answer',reply)])
    backend=TargetBackend()
    trace=run_agent({'type':'alert','service':'image-resizer','text':'Assign alert'},'target-retry',llm=llm,backend=backend,trace_dir=tmp_path)
    assert backend.targets==['alert-image-resizer','service-image-resizer']
    assert trace['target_retries']==1 and trace['final']['outcome']=='ACT' and not trace['gate_failure']


def test_fix4_second_invalid_final_stops_after_one_retry(tmp_path):
    llm=FakeLLM([response({'content':'Prose'}),response({'content':'Still prose'})])
    trace=run_agent({'type':'alert','text':'Alert'},'double-invalid',llm=llm,backend=Backend(),trace_dir=tmp_path)
    assert trace['final_format_retries']==1 and len(llm.calls)==2
    assert trace['final']['outcome']=='ESCALATE' and 'invalid_final_json' in trace['errors']


def test_fix4_provider_format_error_gets_one_terminal_retry(tmp_path):
    from llm import LLMRequestError
    detail={'status_code':400,'exception_type':'BadRequestError','message':'provider format failure',
            'raw_response_body':json.dumps({'error':{'code':'output_parse_failed','failed_generation':'Prose instead of a tool'}})}
    exc=LLMRequestError(detail,tmp_path/'diagnostic.json')
    class FormatLLM(FakeLLM):
        def complete(self,messages,tools=None,**kwargs):
            if not self.messages:
                self.messages.append(copy.deepcopy(messages))
                raise exc
            assert kwargs['tool_choice']['function']['name']=='submit_answer'
            return super().complete(messages,tools,**kwargs)
    v={'answer':'Unknown.','outcome':'ESCALATE','cited_edge_ids':[],'cited_spans':[]}
    llm=FormatLLM([tool('submit_answer',v)])
    t=run_agent({'type':'alert','text':'Alert'},'provider-format',llm=llm,backend=Backend(),trace_dir=tmp_path)
    assert t['final_format_retries']==1 and not t.get('infra_failure')


def test_fix4_history_and_instruction_routes():
    for text in ['Show the history for image-resizer','Read the document instruction for image-resizer','Explain the temporal timeline for image-resizer']:
        assert 'ownership_history' in route({'type':'question','text':text})[1]


def test_fix4_short_multisentence_span_is_available_for_exact_citation():
    from agent import compact
    span='Catalog Record: Service image-resizer is officially registered under team payments. Designated primary on-call engineer handle is mlin.'
    edge={'eid':'E','type':'OWNS','src':'team-payments','dst':'service-image-resizer','status':'current','spans':[span]}
    assert compact({'evidence':[edge]})['evidence'][0]['spans']==[span]
