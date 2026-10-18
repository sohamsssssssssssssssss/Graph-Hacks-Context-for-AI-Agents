"""Run only DEV-prefixed cases with 120b; no semantic grader or frozen-case runner."""
from pathlib import Path
import json

from agent import ROOT, run_agent
from app.tools import ToolRuntime
from derive import load_data
from eval.run_eval import mechanical, usage
from llm import CachedLLM, settings


def main():
    cases=[json.loads(line) for line in (ROOT/'cases/dev_cases.jsonl').read_text().splitlines() if line.strip()]
    if not cases or any(not c['id'].startswith('DEV') for c in cases):
        raise ValueError('Only DEV-prefixed development inputs are permitted')
    if settings()['LLM_MODEL']!='openai/gpt-oss-120b':
        raise ValueError('Dev check requires the requested openai/gpt-oss-120b model')
    directory=ROOT/'eval/dev_fix4_final';directory.mkdir(parents=True,exist_ok=True)
    journal=directory/'records.jsonl'
    rows=[json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    done={r['case_id'] for r in rows}
    nodes,edges,docs=load_data(ROOT/'data')
    byedge={e['eid']:e for e in edges};bydoc={d['id']:d for d in docs}
    names={n['id']:n['name'] for n in nodes if n['label']=='Service'}
    llm=CachedLLM()
    for case in cases:
        if case['id'] in done:continue
        print('Running dev only:',case['id'],flush=True)
        backend=ToolRuntime(action_requested=case['input']['type']=='alert',audit_path=directory/'audit.jsonl')
        trace=run_agent(case['input'],case['id'],'K',llm=llm,backend=backend,trace_dir=directory/'traces')
        row={'case_id':case['id'],'outcome':trace['final']['outcome'],
             'infra_failure':trace.get('infra_failure'),'errors':trace['errors'],
             'format_retries':trace['final_format_retries'],'target_retries':trace['target_retries'],
             'tools_called':[c['name'] for c in trace['tool_calls']],**usage(trace['llm_calls'])}
        if not row['infra_failure']:
            row['metrics']=mechanical(case,trace,byedge,bydoc,names)
            row['checks']={'expected_outcome':row['outcome']==case['gold_outcome'],
                           'citations_backed':row['metrics']['citation_correctness']==1,
                           'valid_final':not any(e in trace['errors'] for e in ['invalid_final_json','max_steps'])}
            if case['input']['type']=='alert':
                row['checks']['canonical_input']=trace['input']['service'].startswith('service-')
            if case['id'] in {'DEV5','DEV6','DEV8'}:
                histories=[c['result'] for c in trace['tool_calls'] if c['name']=='ownership_history']
                row['checks']['ownership_read']=bool(histories) and all(h.get('read_only') for h in histories)
                if case['id']=='DEV6':row['checks']['as_of_used']=any(h.get('as_of')=='2023-06-01T00:00:00Z' for h in histories)
            if case['id']=='DEV7':
                row['checks']['matched_decision']=any('DEC-ARCH-CORE-00' in (c['result'].get('matched_seed') or {}).get('ids',[]) for c in trace['tool_calls'])
            if case['input']['type']=='question':
                row['checks']['no_execution']=not any(c['name']=='propose_action' and c['result'].get('executed') for c in trace['tool_calls'])
        rows.append(row)
        with journal.open('a') as stream:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
    lines=['# Fix 4: dev-only 120b checks','',
           'Only cases/dev_cases.jsonl was run. No frozen eval, rubric grading call, or external action delivery. These are feature/outcome checks, not semantic answer-accuracy scores. Full evidence and final answers are in traces/.', '',
           '| Dev case | Outcome | Checks | Infrastructure failure | Tokens | Format / target retries |',
           '| --- | --- | --- | --- | ---: | ---: |']
    for r in rows:
        checks=r.get('checks',{})
        status='not scored' if r['infra_failure'] else 'pass' if all(checks.values()) else 'FAIL: '+', '.join(k for k,v in checks.items() if not v)
        lines.append(f'| {r["case_id"]} | {r["outcome"]} | {status} | {r["infra_failure"]["exception_type"] if r["infra_failure"] else "none"} | {r["total_tokens"]} | {r["format_retries"]} / {r["target_retries"]} |')
    lines+=['',f'Attempts: {len(rows)}. Passed feature checks: {sum(bool(r.get("checks")) and all(r["checks"].values()) for r in rows)}. Infrastructure failures: {sum(bool(r["infra_failure"]) for r in rows)}.',
            f'Recorded agent tokens: {sum(r["total_tokens"] for r in rows)}; uncached-request tokens: {sum(r["billed_tokens"] for r in rows)}. Failed/salvaged provider responses may not expose usage; no grader tokens were consumed.']
    (directory/'results.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines),flush=True)


if __name__=='__main__':main()
