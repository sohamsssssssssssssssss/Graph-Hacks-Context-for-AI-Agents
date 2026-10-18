"""Ollama DEV validation only: K/all, B1+B2/two smoke cases; resumable journal."""
import argparse
import json
import re
from pathlib import Path
import statistics
import time

from agent import ROOT, BaselineRuntime, run_agent
from app.tools import ToolRuntime
from derive import load_data
from eval.run_eval import grade, mechanical
from llm import CachedLLM, digest, failure_details


def load_dev():
    cases=[json.loads(line) for line in (ROOT/'cases/dev_cases.jsonl').read_text().splitlines() if line.strip()]
    if not cases or any(not c['id'].startswith('DEV') for c in cases):
        raise ValueError('Only DEV-prefixed cases are permitted')
    return cases


def summarize(rows):
    result={}
    for system in ['K','B1','B2']:
        selected=[r for r in rows if r['system']==system]
        if not selected:continue
        metrics=[r['metrics'] for r in selected]
        duration=sum(m['eval_seconds'] for m in metrics)
        result[system]={'runs':len(selected),'tokens_per_second':sum(m['eval_count'] for m in metrics)/duration if duration else None,
            'avg_wall_s':statistics.mean(m['wall_seconds'] for m in metrics),'max_wall_s':max(m['wall_seconds'] for m in metrics),
            'malformed_outputs':sum(m['malformed_output'] for m in metrics),
            'tool_call_failures':sum(m['tool_call_failures'] for m in metrics),
            'retries':sum(m['retries'] for m in metrics),'ctx_guard_triggers':sum(m['ctx_guard_triggers'] for m in metrics),
            'outcome_correct':sum(r.get('outcome_correct',False) for r in selected),
            'answer_correct':sum(r.get('answer_correct',False) for r in selected),
            'answer_scored':sum('answer_correct' in r for r in selected),
            'infra_failures':sum(bool(r.get('infra_failure') or r.get('grader_failure')) for r in selected),
            'prompt_tokens':sum(m['prompt_tokens'] for m in metrics),'completion_tokens':sum(m['completion_tokens'] for m in metrics)}
    if len(result)==3:
        result['estimated_72_run_wall_s']=24*sum(result[s]['avg_wall_s'] for s in ['K','B1','B2'])
        graded=[r for r in rows if 'grader_wall_s' in r]
        result['estimated_72_run_with_grading_s']=result['estimated_72_run_wall_s']+72*statistics.mean(r['grader_wall_s'] for r in graded) if graded else None
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--grade-only',action='store_true')
    parser.add_argument('--systems',nargs='+',choices=['K','B1','B2'],default=['K','B1','B2'])
    parser.add_argument('--run-name',default='',help='Separate DEV attempt suffix; prior results are preserved')
    args=parser.parse_args()
    cases=load_dev()
    agent=CachedLLM(role='agent')
    if agent.provider!='ollama':raise ValueError('DEV local validation requires Ollama')
    model_slug=re.sub(r'[^A-Za-z0-9._-]+','_',agent.model)
    run_suffix='_'+re.sub(r'[^A-Za-z0-9._-]+','_',args.run_name) if args.run_name else ''
    directory=ROOT/'eval'/('ollama_dev_'+model_slug+run_suffix);directory.mkdir(parents=True,exist_ok=True)
    journal=directory/'records.jsonl'
    if journal.exists() and not args.resume:raise RuntimeError('DEV journal exists; use --resume')
    records=[json.loads(line) for line in journal.read_text().splitlines() if line.strip()] if journal.exists() else []
    rows={(r['system'],r['case_id']):r for r in records}
    if any(r['model']!=agent.model for r in records):raise ValueError('Resume model differs from DEV journal')
    agents={'K':agent,**{s:CachedLLM(role='agent',cache_dir=ROOT/'cache/agent/ollama'/(model_slug+run_suffix)/s) for s in ['B1','B2']}}
    nodes,edges,docs=load_data(ROOT/'data')
    byedge={e['eid']:e for e in edges};bydoc={d['id']:d for d in docs}
    names={n['id']:n['name'] for n in nodes if n['label']=='Service'}
    # One ownership read and one catalog alert cover information and execution flows.
    questions=[c for c in cases if c['input']['type']=='question']
    alerts=[c for c in cases if c['input']['type']=='alert']
    smoke=[next((c for c in questions if c['id']=='DEV5'),questions[0]),
           next((c for c in alerts if c['id']=='DEV9'),alerts[0])]
    plan=[(s,c) for s in args.systems for c in (cases if s=='K' else smoke)]
    def save(row):
        rows[(row['system'],row['case_id'])]=row
        with journal.open('a') as stream:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
        (directory/'summary.json').write_text(json.dumps(summarize(list(rows.values())),indent=2))
    if not args.grade_only:
        for system,case in plan:
            agent=agents[system]
            key=(system,case['id']);previous=rows.get(key)
            if previous and not previous.get('infra_failure'):continue
            print(f'DEV only: {system}/{case["id"]}',flush=True)
            backend=None if system=='B2' else (BaselineRuntime if system=='B1' else ToolRuntime)(
                action_requested=case['input']['type']=='alert',audit_path=directory/'audit.jsonl')
            trace=run_agent(case['input'],case['id'],system,llm=agent,backend=backend,trace_dir=directory/'traces')
            row={'system':system,'case_id':case['id'],'model':agent.model,'input_sha256':digest(case),
                 'outcome':trace['final']['outcome'],'metrics':trace['metrics'],'infra_failure':trace.get('infra_failure'),
                 'errors':trace['errors'],'trace':str(directory/'traces'/f'{case["id"]}_{system}.json')}
            if not trace.get('infra_failure'):row.update(mechanical(case,trace,byedge,bydoc,names))
            save(row)
            print(json.dumps({k:row[k] for k in ['system','case_id','outcome','metrics','errors']},ensure_ascii=False),flush=True)
    grader=None
    for system,case in plan:
        row=rows.get((system,case['id']))
        if not row or row.get('infra_failure') or 'answer_correct' in row:continue
        if row['input_sha256']!=digest(case):raise ValueError('DEV case changed; refusing stale resume')
        if grader is None:grader=CachedLLM(role='grader')
        print(f'Groq grader, DEV only: {system}/{case["id"]}',flush=True)
        trace=json.loads(Path(row['trace']).read_text())
        started=time.perf_counter()
        try:
            row.update(grade(case,trace,grader));row.pop('grader_failure',None)
        except Exception as exc:
            row['grader_failure']=failure_details(exc)
            print('Grader failure: '+row['grader_failure']['message'],flush=True)
        row['grader_wall_s']=time.perf_counter()-started
        save(row)
    print(json.dumps(summarize(list(rows.values())),indent=2),flush=True)


if __name__=='__main__':main()
