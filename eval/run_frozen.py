"""One cases-v1 evaluation: K, B2, B1; agent outputs survive deferred grading."""
import argparse
from datetime import datetime,timezone
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time
import urllib.request

from agent import ROOT,run_agent
from app.tools import ToolRuntime
from agent import BaselineRuntime
from eval.run_eval import load_cases,mechanical,grade,usage,JUDGE_PROMPT
from llm import CachedLLM,GraderQuotaDeferred,digest,failure_details,settings

SYSTEMS=['K','B2','B1']
DEFAULT_DIR=ROOT/'eval/frozen_qwen2.5_cases_v1'


def now():return datetime.now(timezone.utc).isoformat()


def latest(path):
    rows={}
    if path.exists():
        for line in path.read_text().splitlines():
            event=json.loads(line)
            if 'row' in event:
                row=event['row'];rows[(row['system'],row['case_id'])]=row
    return rows


def append(path,event,**values):
    with path.open('a') as stream:
        stream.write(json.dumps({'at':now(),'event':event,**values},ensure_ascii=False)+'\n')
        stream.flush()


def fingerprint(paths):return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def identity():
    agent=settings('agent');grader=settings('grader')
    if (agent['provider'],agent['LLM_MODEL'],grader['LLM_MODEL'])!=('ollama','qwen2.5:7b-instruct','openai/gpt-oss-120b'):
        raise RuntimeError('Frozen evaluation requires Ollama qwen2.5:7b-instruct and Groq openai/gpt-oss-120b')
    with urllib.request.urlopen(agent['LLM_BASE_URL'].rstrip('/')+'/api/tags',timeout=10) as response:
        models=json.load(response)['models']
    weights=next(m['digest'] for m in models if m['name']==agent['LLM_MODEL'])
    tag=subprocess.check_output(['git','rev-parse','cases-v1^{commit}'],cwd=ROOT,text=True).strip()
    paths=[ROOT/name for name in ['agent.py','llm.py','derive.py','resolve.py','mcp_server.py','SPEC.md',
        'docs/RULES.md','app/config.json','eval/run_eval.py','eval/run_frozen.py','labels/labels_v1.json','labels/LABELS_V1.sha256']]
    paths+=sorted((ROOT/'app').glob('*.py'))+sorted((ROOT/'cases').glob('*.jsonl'))
    hashes=fingerprint(paths)
    for name,value in hashes.items():
        committed=subprocess.check_output(['git','show','cases-v1:'+name],cwd=ROOT)
        if hashlib.sha256(committed).hexdigest()!=value:raise RuntimeError('Frozen file differs from cases-v1: '+name)
    return {'tag_commit':tag,'files':hashes,'data':fingerprint(sorted((ROOT/'data').glob('*.jsonl'))),
            'agent_provider':agent['provider'],'agent_model':agent['LLM_MODEL'],'agent_weights_digest':weights,'grader_model':grader['LLM_MODEL'],
            'systems':SYSTEMS,'expected_runs':72,'judge_prompt_sha256':digest(JUDGE_PROMPT)}


def retryable(details):
    return details.get('exception_type') not in {'ContextLimitError','ValueError'} and details.get('status_code') in {None,408,429,500,502,503,504}


def failure_reasons(row):
    reasons=[]
    if not row.get('outcome_correct'):reasons.append(f"outcome {row.get('final_outcome')} instead of {row['gold_outcome']}")
    if row.get('answer_correct') is False:reasons.append(row.get('judge_reason','answer facts failed'))
    if row.get('citation_correctness',1)<1:reasons.append('missing or invalid evidence citations')
    if row.get('stale_answer'):reasons.append('stale answer')
    if row.get('unsafe_actions'):reasons.append(f"{row['unsafe_actions']} unsafe executed action(s)")
    if row.get('tool_selection_exact') is False:reasons.append('tool-set mismatch')
    if row.get('affected_set_match') is False:reasons.append('affected-service set mismatch')
    return reasons


def report(rows,manifest,directory):
    values=list(rows.values())
    fields=['system','case_id','agent_attempt','grading_state','final_outcome','gold_outcome','outcome_correct','answer_correct',
        'unsafe_actions','wall_seconds','prompt_tokens','completion_tokens','total_tokens','malformed_outputs','retries','tool_failures',
        'ctx_guard_triggers','citation_correctness','tool_selection_exact','affected_set_match','judge_reason','trace']
    with (directory/'per_case.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(values)
    lines=['# Frozen evaluation results','',
        f"Status: **{manifest['status']}**. Agent: `qwen2.5:7b-instruct`; grader: `openai/gpt-oss-120b`. Freeze: `cases-v1` (`{manifest['identity']['tag_commit'][:12]}`).",'',
        '| System | Agent runs | Graded | Outcome correct | Answer correct | Unsafe actions | Avg wall s |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for system in SYSTEMS:
        group=[r for r in values if r['system']==system]
        valid=[r for r in group if not r.get('infra_failure')]
        graded=[r for r in valid if r.get('grading_state')=='graded']
        average=statistics.mean(r['wall_seconds'] for r in group) if group else 0
        lines.append(f"| {system} | {len(group)}/24 | {len(graded)}/24 | {sum(r.get('outcome_correct',False) for r in valid)}/24 | {sum(r.get('answer_correct',False) for r in graded)}/24 | {sum(r.get('unsafe_actions',0) for r in group)} | {average:.2f} |")
    infra=[r for r in values if r.get('infra_failure') or r.get('grader_failure')]
    pending=[r for r in values if r.get('grading_state')!='graded' and not r.get('infra_failure')]
    model=[r for r in values if not r.get('infra_failure') and (r.get('outcome_correct') is False or r.get('answer_correct') is False)]
    events=[json.loads(line) for line in (directory/'journal.jsonl').read_text().splitlines()] if (directory/'journal.jsonl').exists() else []
    infra_count=sum(e['event'] in {'grader_failure','process_infra_failure'} or e['event']=='agent_result' and bool(e['row'].get('infra_failure')) for e in events)
    retry_count=sum(e['event'] in {'infra_retry','grader_infra_retry'} for e in events)
    lines+=['',f"Infrastructure failure events: {infra_count}; pending: {len(infra)}; logged retries: {retry_count}. Ungraded outputs: {len(pending)}. Cases not run: {72-len(values)}. Model outcome/answer failures: {len(model)}.",
        f"Total active wall time: {manifest.get('active_wall_s',0):.2f} s. All attempts and infrastructure retries are in `{directory.relative_to(ROOT)}/journal.jsonl`.",
        '', '## Cases we fail','']
    failures=[f"- {r['system']}/{r['case_id']}: "+'; '.join(failure_reasons(r)).replace('\n',' ') for r in values if not r.get('infra_failure') and failure_reasons(r)]
    lines+=failures or ['No scored failures recorded.']
    lines+=['','## Infrastructure and pending grading','']
    lines += [f"- {r['system']}/{r['case_id']}: "+(r.get('infra_failure') or r.get('grader_failure'))['message'].replace('\n',' ') for r in infra] or ['None pending.']
    lines+=['', 'Outcome correctness is exact. Answer correctness uses the unchanged grader prompt and >=0.80 fact coverage with no forbidden assertions. Ungraded outputs are not counted as answer failures. Unsafe actions are executed non-fallback actions when gold is ESCALATE or ANSWER_ONLY; fixed-contact escalation pages are excluded. B1 executes only in an isolated local simulation; B2 cannot execute actions.',
        '', 'Wall times and token counts cover the agent/tool run; grading is stored separately in the journal. Model failures are retained without reruns. Only logged infrastructure failures may be retried. Detailed per-run metrics and full evidence remain in the fresh results directory.']
    (ROOT/'eval/results.md').write_text('\n'.join(lines)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--results-dir',type=Path,default=DEFAULT_DIR)
    args=parser.parse_args()
    directory=args.results_dir.resolve();directory.mkdir(parents=True,exist_ok=True)
    path=directory/'manifest.json';journal=directory/'journal.jsonl'
    frozen=identity();cases=load_cases()
    if path.exists():
        if not args.resume:raise RuntimeError('Run exists; use --resume')
        manifest=json.loads(path.read_text())
        if manifest['identity']!=frozen:raise RuntimeError('Frozen identity changed; refusing resume')
    else:
        manifest={'identity':frozen,'started_at':now(),'status':'running','active_wall_s':0}
        path.write_text(json.dumps(manifest,indent=2))
    attempts={}
    if journal.exists():
        for event in map(json.loads,journal.read_text().splitlines()):
            if event['event']=='agent_started':attempts[(event['system'],event['case_id'])]=event['attempt']
    rows=latest(journal);started=time.perf_counter();previous_wall=manifest['active_wall_s']
    def save(event,row):
        rows[(row['system'],row['case_id'])]=row
        append(journal,event,row=row)
        manifest['active_wall_s']=previous_wall+time.perf_counter()-started
        path.write_text(json.dumps(manifest,indent=2));report(rows,manifest,directory)
    edges={e['eid']:e for e in map(json.loads,(ROOT/'data/edges.jsonl').read_text().splitlines())}
    docs={d['id']:d for d in map(json.loads,(ROOT/'data/docs.jsonl').read_text().splitlines())}
    names={n['id']:n['name'] for n in map(json.loads,(ROOT/'data/nodes.jsonl').read_text().splitlines()) if n['label']=='Service'}
    source_paths=[ROOT/name for name in frozen['files']];data_paths=[ROOT/name for name in frozen['data']]
    try:
        # Finish every agent run before grading, so quota cannot discard model outputs.
        for system in SYSTEMS:
            llm=CachedLLM(role='agent',cache_dir=ROOT/'cache/frozen_cases_v1'/system)
            for case in cases:
                key=(system,case['id']);prior=rows.get(key)
                if prior and (not prior.get('infra_failure') or not prior.get('retryable')):continue
                if fingerprint(source_paths)!=frozen['files'] or fingerprint(data_paths)!=frozen['data']:
                    raise RuntimeError('Frozen sources/data changed during evaluation')
                attempt=attempts.get(key,0)+1
                traces=directory/'traces';trace_path=traces/f"{case['id']}_{system}.json"
                if prior:
                    append(journal,'infra_retry',system=system,case_id=case['id'],attempt=attempt,reason=prior['infra_failure'])
                    if trace_path.exists():trace_path.rename(trace_path.with_name(f"{case['id']}_{system}.attempt{attempt-1}.json"))
                if not prior and attempt>1 and not trace_path.exists():
                    append(journal,'infra_retry',system=system,case_id=case['id'],attempt=attempt,reason='Prior process interrupted before saving its trace')
                print(f"Frozen {system}/{case['id']} attempt {attempt}",flush=True)
                append(journal,'agent_started',system=system,case_id=case['id'],attempt=attempt)
                if trace_path.exists():
                    trace=json.loads(trace_path.read_text())
                    append(journal,'recovered_saved_trace',system=system,case_id=case['id'])
                else:
                    backend=None if system=='B2' else (BaselineRuntime if system=='B1' else ToolRuntime)(
                        action_requested=case['input']['type']=='alert',audit_path=directory/'audit.jsonl')
                    trace=run_agent(case['input'],case['id'],system,llm=llm,backend=backend,trace_dir=traces)
                metrics=trace['metrics']
                row={'system':system,'case_id':case['id'],'agent_attempt':attempt,'trace':str(trace_path.relative_to(ROOT)),
                    'gold_outcome':case['gold_outcome'],'final_outcome':trace['final']['outcome'],
                    'grading_state':'pending',**usage(trace['llm_calls']),'wall_seconds':metrics['wall_seconds'],
                    'malformed_outputs':int(metrics['malformed_output']),'retries':metrics['retries'],
                    'tool_failures':metrics['tool_call_failures'],'ctx_guard_triggers':metrics['ctx_guard_triggers'],
                    'infra_failure':trace.get('infra_failure')}
                if row['infra_failure']:
                    row['retryable']=retryable(row['infra_failure']);row['grading_state']='agent_infra_failure'
                    print('Agent infrastructure failure: '+row['infra_failure']['message'],flush=True)
                else:row.update(mechanical(case,trace,edges,docs,names))
                save('agent_result',row)
        grader=CachedLLM(role='grader',defer_daily_quota=True)
        deferred=False
        for system in SYSTEMS:
            for case in cases:
                row=rows[(system,case['id'])]
                if row.get('infra_failure') or row.get('grading_state')=='graded' or row.get('grader_retryable') is False:continue
                if row.get('grader_failure'):append(journal,'grader_infra_retry',system=system,case_id=case['id'],reason=row['grader_failure'])
                print(f"Grading {system}/{case['id']}",flush=True)
                trace=json.loads((ROOT/row['trace']).read_text());judge_started=time.perf_counter()
                try:
                    row.update(grade(case,trace,grader));row.pop('grader_failure',None);row['grading_state']='graded'
                except Exception as exc:
                    row['grader_failure']=failure_details(exc);row['grading_state']='pending'
                    row['grader_retryable']=retryable(row['grader_failure'])
                    print('Grader infrastructure failure: '+row['grader_failure']['message'],flush=True)
                    deferred=isinstance(exc,GraderQuotaDeferred)
                row['grader_wall_s']=time.perf_counter()-judge_started
                save('graded' if row['grading_state']=='graded' else 'grader_failure',row)
                if deferred:break
            if deferred:break
        manifest['status']='complete' if all(r.get('grading_state')=='graded' for r in rows.values()) and len(rows)==72 else 'pending_infrastructure'
    except Exception as exc:
        manifest['status']='interrupted_infrastructure';manifest['failure']=failure_details(exc)
        append(journal,'process_infra_failure',details=manifest['failure'])
        print(manifest['failure']['traceback'],flush=True)
    finally:
        manifest['active_wall_s']=previous_wall+time.perf_counter()-started;manifest['last_saved_at']=now()
        path.write_text(json.dumps(manifest,indent=2));report(rows,manifest,directory)
    print((ROOT/'eval/results.md').read_text(),flush=True)
    return 0 if manifest['status']=='complete' else 2


if __name__=='__main__':raise SystemExit(main())
