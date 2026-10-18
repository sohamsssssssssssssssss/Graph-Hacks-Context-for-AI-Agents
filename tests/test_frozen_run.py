import json
from pathlib import Path
from types import SimpleNamespace

from eval import run_frozen as runner


def test_journal_keeps_ungraded_output_and_resume_uses_latest(tmp_path):
    journal=tmp_path/'journal.jsonl'
    row={'system':'K','case_id':'test','grading_state':'pending','trace':'kept.json'}
    runner.append(journal,'agent_started',system='K',case_id='test',attempt=1)
    runner.append(journal,'agent_result',row=row)
    assert runner.latest(journal)[('K','test')]['trace']=='kept.json'
    runner.append(journal,'graded',row={**row,'grading_state':'graded','answer_correct':False})
    assert runner.latest(journal)[('K','test')]['answer_correct'] is False
    assert len(journal.read_text().splitlines())==3


def test_frozen_resume_never_reruns_model_failure_and_defers_grader(tmp_path,monkeypatch):
    from llm import GraderQuotaDeferred
    (tmp_path/'data').mkdir();(tmp_path/'eval').mkdir()
    for name in ['edges','nodes','docs']:(tmp_path/'data'/f'{name}.jsonl').write_text('')
    case={'id':'test','input':{'type':'question','text':'Question'},'gold_outcome':'ANSWER_ONLY'}
    calls=[]
    class LLM:
        def __init__(self,**kwargs):self.calls=[]
    def run(input_record,case_id,system,**kwargs):
        calls.append(system)
        trace={'metrics':{'wall_seconds':1,'malformed_output':True,'retries':1,'tool_call_failures':0,'ctx_guard_triggers':0},
               'llm_calls':[],'final':{'outcome':'ESCALATE'},'tool_calls':[]}
        folder=kwargs['trace_dir'];folder.mkdir(parents=True,exist_ok=True)
        (folder/f'{case_id}_{system}.json').write_text(json.dumps(trace))
        return trace
    def quota(*args):raise GraderQuotaDeferred({'status_code':429,'raw_response_body':'quota','exception_type':'Limit','message':'daily quota'},'diagnostic')
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'identity',lambda:{'files':{},'data':{},'tag_commit':'tag'})
    monkeypatch.setattr(runner,'load_cases',lambda:[case])
    monkeypatch.setattr(runner,'CachedLLM',LLM)
    monkeypatch.setattr(runner,'run_agent',run)
    monkeypatch.setattr(runner,'ToolRuntime',lambda **kwargs:None)
    monkeypatch.setattr(runner,'BaselineRuntime',lambda **kwargs:None)
    monkeypatch.setattr(runner,'mechanical',lambda *args:{'outcome_correct':False,'unsafe_actions':0})
    monkeypatch.setattr(runner,'grade',quota)
    import sys
    monkeypatch.setattr(sys,'argv',['frozen','--resume','--results-dir',str(tmp_path/'eval/fresh')])
    assert runner.main()==2 and calls==['K','B2','B1']
    rows=runner.latest(tmp_path/'eval/fresh/journal.jsonl')
    assert len(rows)==3 and all(row['grading_state']=='pending' for row in rows.values())
    monkeypatch.setattr(runner,'grade',lambda *args:{'answer_correct':False,'judge_reason':'model omission'})
    assert runner.main()==2
    assert calls==['K','B2','B1']
    assert all(row['grading_state']=='graded' for row in runner.latest(tmp_path/'eval/fresh/journal.jsonl').values())
