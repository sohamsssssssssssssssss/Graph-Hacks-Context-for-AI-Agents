import copy
import json
from types import SimpleNamespace

import pytest

from llm import CachedLLM, GraderLimiter, guard_context, grader_context, grader_format, settings


def native(content='',calls=None):
    return {'message':{'role':'assistant','content':content,'tool_calls':calls or []},
            'prompt_eval_count':100,'eval_count':20,'eval_duration':1000000000}


def test_ollama_native_options_terminal_and_metrics(tmp_path):
    requests=[]
    def client(payload):
        requests.append(payload)
        return native('<think>hidden</think>',[{'function':{'name':'submit_answer','arguments':{'answer':'ok','outcome':'ANSWER_ONLY','cited_edge_ids':[],'cited_spans':[]}}}])
    llm=CachedLLM('qwen3:8b',client,tmp_path,provider='ollama')
    response=llm.complete([{'role':'system','content':'Use tools'},{'role':'user','content':'Question'}],
                          [{'type':'function','function':{'name':'submit_answer'}}],{'type':'function','function':{'name':'submit_answer'}})
    payload=requests[0]
    assert payload['think'] is False and payload['keep_alive']=='30m'
    assert payload['options']=={'temperature':0,'num_ctx':16384,'num_predict':1600}
    assert 'Finish now by calling submit_answer' in payload['messages'][0]['content']
    message=response['choices'][0]['message']
    assert message['content']=='' and json.loads(message['tool_calls'][0]['function']['arguments'])['answer']=='ok'
    assert llm.calls[0]['usage']['total_tokens']==120
    assert llm.calls[0]['ollama_metrics']['eval_duration']==1000000000


def test_thinking_fallback_and_tool_conversion_do_not_mutate_input(tmp_path):
    requests=[]
    def client(payload):
        requests.append(payload)
        raw=native('ok');raw['message']['thinking']='unexpected';return raw
    llm=CachedLLM('qwen3:8b',client,tmp_path,provider='ollama')
    messages=[{'role':'system','content':'System'},{'role':'user','content':'Task'},
              {'role':'assistant','content':'','tool_calls':[{'id':'x','function':{'name':'rank_owners','arguments':'{"service":"s"}'}}]},
              {'role':'tool','tool_call_id':'x','content':'evidence'}]
    original=copy.deepcopy(messages)
    llm.complete(messages)
    messages[-1]['content']='different evidence'
    llm.complete(messages)
    assert '/no_think' in requests[1]['messages'][0]['content']
    assert requests[0]['messages'][-1]['tool_name']=='rank_owners'
    assert requests[0]['messages'][2]['tool_calls'][0]['function']['arguments']=={'service':'s'}
    original[-1]['content']='different evidence'
    assert messages==original


def test_context_guard_preserves_task_and_last_two_tools():
    messages=[{'role':'system','content':'system'},{'role':'user','content':'task'}]+[
        {'role':'tool','content':'x'*24000},{'role':'tool','content':'y'*24000},
        {'role':'tool','content':'recent1'},{'role':'tool','content':'recent2'}]
    original=copy.deepcopy(messages)
    guarded,event=guard_context(messages)
    assert event['triggered'] and event['after']<=14000
    assert guarded[:2]==original[:2] and guarded[-2:]==original[-2:] and messages==original


def test_context_guard_fails_if_protected_content_too_large():
    with pytest.raises(ValueError,match='preserving system'):
        guard_context([{'role':'system','content':'x'*43000}])


def test_grader_truncation_preserves_full_rubric():
    payload={'question':'why','reference_facts':['full fact'],'forbidden_claims':['wrong'],'answer':'x'*25000}
    messages=[{'role':'system','content':'rubric'},{'role':'user','content':json.dumps(payload)}]
    shortened,triggered=grader_context(messages)
    output=json.loads(shortened[-1]['content'])
    assert triggered and output['reference_facts']==payload['reference_facts']
    assert output['forbidden_claims']==payload['forbidden_claims'] and shortened[0]==messages[0]
    assert messages[-1]['content']==json.dumps(payload)
    shape=grader_format(messages)['json_schema']['schema']['properties']
    assert shape['fact_supported']['minItems']==shape['fact_supported']['maxItems']==1
    assert shape['forbidden_asserted']['minItems']==shape['forbidden_asserted']['maxItems']==1


def test_grader_limiter_enforces_minute_and_day():
    clock=[0];delays=[]
    def sleep(seconds):delays.append(seconds);clock[0]+=seconds
    limiter=GraderLimiter(sleep,lambda:clock[0])
    limiter.acquire(7000);limiter.acquire(2000)
    assert clock[0]>=60
    limiter.events=[[clock[0],199000]]
    limiter.acquire(2000)
    assert clock[0]>=86460 and max(delays)<=60
    limiter.events=[[clock[0]-100,199000]]
    with pytest.raises(RuntimeError,match='tokens per day'):
        limiter.acquire(2000,defer_daily=True)


def test_roles_have_separate_model_and_key_settings(monkeypatch):
    monkeypatch.setenv('AGENT_PROVIDER','ollama');monkeypatch.setenv('AGENT_MODEL','qwen3:8b')
    monkeypatch.setenv('GRADER_MODEL','openai/gpt-oss-120b');monkeypatch.setenv('GRADER_API_KEY','fake-key')
    assert settings('agent')['LLM_MODEL']=='qwen3:8b'
    assert settings('grader')['LLM_MODEL']=='openai/gpt-oss-120b'
    assert settings('grader')['provider']=='groq'


def test_grader_429_waits_and_retries_daily_quota(tmp_path,monkeypatch):
    import llm as module
    attempts=[];delays=[]
    class Limited(Exception):
        status_code=429
        response=SimpleNamespace(text='rate limited',headers={'retry-after':'2'})
    def create(**kwargs):
        attempts.append(kwargs)
        if len(attempts)==1:raise Limited('tokens per day (TPD): limit reached; try again in 2s')
        return SimpleNamespace(model_dump=lambda mode:{'choices':[{'message':{'content':'ok'}}],'usage':{'total_tokens':10}})
    monkeypatch.setattr(module,'GRADER_LIMITER',SimpleNamespace(acquire=lambda tokens:None))
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm=CachedLLM('grader',client,tmp_path,sleep=delays.append,role='grader')
    llm.complete([{'role':'user','content':'small'}])
    assert len(attempts)==2 and sum(delays)>=2 and llm.calls[0]['retries']==1
    assert attempts[-1]['response_format']['json_schema']['strict'] is True
    assert attempts[-1]['response_format']['json_schema']['schema']['properties']['forbidden_asserted']['type']=='array'


def test_run_trace_reports_native_metrics_without_network(tmp_path):
    from agent import run_agent
    value={'answer':'No evidence available.','outcome':'ANSWER_ONLY','cited_edge_ids':[],'cited_spans':[]}
    llm=CachedLLM('qwen3:8b',lambda payload:native(json.dumps(value)),tmp_path/'cache',provider='ollama')
    trace=run_agent({'type':'question','text':'Question'},'DEV-mocked','B2',llm=llm,trace_dir=tmp_path/'traces')
    assert trace['metrics']['tokens_per_second']==20
    assert trace['metrics']['prompt_tokens']==100 and trace['metrics']['completion_tokens']==20
    assert trace['metrics']['tool_calls']==0 and not trace['metrics']['malformed_output']
    assert trace['metrics']['wall_seconds']>=0 and trace['metrics']['retries']==0


def test_qwen25_omits_thinking_controls_and_still_strips_tags(tmp_path):
    requests=[]
    def client(payload):
        requests.append(payload)
        return native('<think>discard</think>usable')
    llm=CachedLLM('qwen2.5:7b-instruct',client,tmp_path,provider='ollama')
    for task in ['first','second']:
        result=llm.complete([{'role':'system','content':'System'},{'role':'user','content':task}])
        assert result['choices'][0]['message']['content']=='usable'
    assert all('think' not in r and '/no_think' not in r['messages'][0]['content'] for r in requests)


def test_alert_prompt_verification_example_matches_live_schema():
    from agent import SYSTEM_PROMPT
    from mcp_server import SPECS,validate
    example=json.JSONDecoder().raw_decode(SYSTEM_PROMPT.split('verify_path arguments: ',1)[1])[0]
    properties,required,_=SPECS['verify_path']
    validate(example,{'type':'object','properties':properties,'required':required,'additionalProperties':False})
    assert example['purpose']=='ACT'
    assert example['claim']['start']==example['claim']['action']['recipient']
    assert example['target']==example['claim']['action']['target']


@pytest.mark.parametrize('at_budget,model_outcome',[(True,'ACT'),(False,'ANSWER_ONLY')])
def test_executed_alert_keeps_terminal_turn_and_gate_outcome(tmp_path,at_budget,model_outcome):
    from agent import run_agent
    def reply(message):return {'choices':[{'message':message}]}
    def call(name,args):return reply({'role':'assistant','content':'','tool_calls':[{
        'id':'c','type':'function','function':{'name':name,'arguments':json.dumps(args)}}]})
    action={'kind':'ACT','target':'service-example','recipient':'team-example'}
    replies=([call('blast_radius',{'service':'service-example'})]*7 if at_budget else [])+[
        call('propose_action',{'pass_id':'verified-pass','action':action,'execute':True}),
        call('submit_answer',{'answer':'The verified action executed.','outcome':model_outcome,'cited_edge_ids':[],'cited_spans':[]})]
    class LLM:
        model='mock'
        def __init__(self):self.calls=[];self.replies=iter(replies)
        def complete(self,*args,**kwargs):self.calls.append({'usage':{}});return next(self.replies)
    class Backend:
        def blast_radius(self,**kwargs):return {'ok':True,'evidence':[]}
        def propose_action(self,**kwargs):return {'ok':True,'executed':True,'outcome':'ACT','evidence':[]}
    llm=LLM()
    trace=run_agent({'type':'alert','service':'service-example','text':'An alert'},'DEV-terminal','K',
                    llm=llm,backend=Backend(),trace_dir=tmp_path)
    assert trace['final']['outcome']=='ACT' and 'max_steps' not in trace['errors']
    assert 'terminal_call' in trace and len(llm.calls)==(9 if at_budget else 2)
    assert trace['proposed_final']['outcome']==model_outcome


def test_frozen_grader_defers_daily_quota_without_losing_output(tmp_path):
    from llm import GraderQuotaDeferred
    class Limit(Exception):
        status_code=429
        response=SimpleNamespace(text='quota')
    calls=[]
    def create(**kwargs):calls.append(kwargs);raise Limit('tokens per day (TPD): try again in 20m')
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm=CachedLLM('grader',client,tmp_path,role='grader',defer_daily_quota=True)
    with pytest.raises(GraderQuotaDeferred):llm.complete([{'role':'user','content':'small'}])
    assert len(calls)==1 and llm.calls[-1]['failed']


def test_grader_413_truncates_only_answer_and_retries(tmp_path,monkeypatch):
    import llm as module
    attempts=[]
    class TooLarge(Exception):
        status_code=413
        response=SimpleNamespace(text='request too large')
    def create(**kwargs):
        attempts.append(kwargs)
        if len(attempts)==1:raise TooLarge('request too large')
        return SimpleNamespace(model_dump=lambda mode:{'choices':[{'message':{'content':'ok'}}],'usage':{'total_tokens':10}})
    monkeypatch.setattr(module,'GRADER_LIMITER',SimpleNamespace(acquire=lambda tokens:None))
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm=CachedLLM('grader',client,tmp_path,role='grader')
    payload={'question':'question','reference_facts':['keep fact'],'forbidden_claims':['keep prohibition'],'answer':'x'*18000}
    llm.complete([{'role':'user','content':json.dumps(payload)}])
    before=json.loads(attempts[0]['messages'][-1]['content']);after=json.loads(attempts[1]['messages'][-1]['content'])
    assert len(after['answer'])<len(before['answer'])
    assert after['reference_facts']==before['reference_facts']==payload['reference_facts']
    assert after['forbidden_claims']==payload['forbidden_claims'] and len(llm.calls)==2
