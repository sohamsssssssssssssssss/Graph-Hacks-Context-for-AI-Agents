"""Role-separated cached Ollama agent / Groq grader clients."""
import copy
import math
import re
import urllib.request
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

# Transport shape only; the grader prompt and scoring criteria remain in run_eval.py.
GRADER_FORMAT={'type':'json_schema','json_schema':{'name':'grade','strict':True,'schema':{
    'type':'object','properties':{'fact_supported':{'type':'array','items':{'type':'boolean'}},
    'forbidden_asserted':{'type':'array','items':{'type':'boolean'}},'stale_answer':{'type':'boolean'},'reason':{'type':'string'}},
    'required':['fact_supported','forbidden_asserted','stale_answer','reason'],'additionalProperties':False}}}


def grader_format(messages):
    result=copy.deepcopy(GRADER_FORMAT)
    try:
        rubric=json.loads(messages[-1]['content'])
        for output,source in [('fact_supported','reference_facts'),('forbidden_asserted','forbidden_claims')]:
            count=len(rubric[source])
            result['json_schema']['schema']['properties'][output].update(minItems=count,maxItems=count)
    except (ValueError,KeyError,TypeError):pass
    return result


def settings(role='agent'):
    load_dotenv(ROOT / '.env')
    if role == 'agent':
        provider=os.getenv('AGENT_PROVIDER','ollama')
        if provider not in {'ollama','groq','openai'}:raise ValueError('Unknown agent provider: '+provider)
        local=provider=='ollama'
        model=os.getenv('AGENT_MODEL') or ('qwen2.5:7b-instruct' if local else os.getenv('LLM_MODEL','openai/gpt-oss-120b'))
        base=os.getenv('AGENT_BASE_URL') or ('http://127.0.0.1:11434' if local else os.getenv('LLM_BASE_URL','https://api.groq.com/openai/v1'))
        key=os.getenv('AGENT_API_KEY') or ('' if local else os.getenv('LLM_API_KEY',''))
    elif role == 'grader':
        provider='groq'
        model=os.getenv('GRADER_MODEL','openai/gpt-oss-120b')
        base=os.getenv('GRADER_BASE_URL','https://api.groq.com/openai/v1')
        key=os.getenv('GRADER_API_KEY') or os.getenv('LLM_API_KEY','')
        if not key:raise RuntimeError('Configure local .env: GRADER_API_KEY (or LLM_API_KEY)')
    else:raise ValueError('Unknown LLM role: '+role)
    return {'provider':provider,'LLM_MODEL':model,'LLM_BASE_URL':base,'LLM_API_KEY':key}


def estimate_tokens(messages,tools=None):
    # Conservative UTF-8 estimate; no tokenizer download or model-specific dependency.
    return math.ceil(len(json.dumps([messages,tools or []],ensure_ascii=False).encode())/3)+32


class ContextLimitError(ValueError):
    def __init__(self,event):
        self.event=event
        super().__init__('Agent context exceeds 14000 tokens after preserving system, task, and last two tool results')


def guard_context(messages,tools=None):
    messages=copy.deepcopy(messages)
    before=estimate_tokens(messages,tools)
    removed=[]
    if before>14000:
        old=[i for i,m in enumerate(messages) if m['role']=='tool'][:-2]
        for i in old:
            messages[i]['content']='[Older tool output truncated by context guard; full evidence retained in trace.]'
            removed.append(i)
            if estimate_tokens(messages,tools)<=14000:break
        after=estimate_tokens(messages,tools)
        print(f'Agent context guard: estimated tokens {before} -> {after}; truncated {len(removed)} old tool outputs.',file=sys.stderr,flush=True)
        if after>14000:raise ContextLimitError({'triggered':True,'before':before,'after':after,'truncated_outputs':len(removed)})
    return messages,{'triggered':before>14000,'before':before,'after':estimate_tokens(messages,tools),'truncated_outputs':len(removed)}


class GraderLimiter:
    def __init__(self,sleep=time.sleep,clock=time.time):
        self.sleep=sleep;self.clock=clock;self.events=[]

    def acquire(self,tokens,defer_daily=False):
        if tokens>8000:raise ValueError('Grader request exceeds 8000-token minute budget')
        while True:
            now=self.clock()
            self.events=[e for e in self.events if now-e[0]<86400]
            delays=[]
            for window,limit in [(60,8000),(86400,200000)]:
                recent=[e for e in self.events if now-e[0]<window]
                if sum(e[1] for e in recent)+tokens>limit:
                    if window==86400 and defer_daily:raise RuntimeError('tokens per day (TPD): local grader budget exhausted; resume later')
                    released=0
                    for stamp,count in recent:
                        released+=count
                        if sum(e[1] for e in recent)-released+tokens<=limit:
                            delays.append(stamp+window-now+0.1);break
            if not delays:
                event=[now,tokens];self.events.append(event);return event
            self.sleep(min(max(delays),60))


GRADER_LIMITER=GraderLimiter()


def grader_context(messages,limit=6000):
    messages=copy.deepcopy(messages)
    if estimate_tokens(messages)<=limit:return messages,False
    # Keep the complete rubric and reference facts; shorten only the submitted answer.
    payload=json.loads(messages[-1]['content'])
    answer=payload.get('answer','')
    while estimate_tokens(messages)>limit and len(answer)>64:
        answer=answer[:int(len(answer)*0.7)]
        payload['answer']=answer+' [answer truncated for grader input limit]'
        messages[-1]['content']=json.dumps(payload,ensure_ascii=False)
    if estimate_tokens(messages)>limit:raise ValueError('Grader rubric exceeds input budget; rubric was not truncated')
    print('Grader input truncated to respect request/token limits.',file=sys.stderr,flush=True)
    return messages,True


def ollama_chat(base,args):
    request=urllib.request.Request(base.rstrip('/')+'/api/chat',data=json.dumps(args).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=300) as response:return json.load(response)
    except urllib.error.HTTPError as exc:
        exc.status_code=exc.code
        exc.raw_response_body=exc.read().decode(errors='replace')
        raise


def normalize_ollama(raw):
    message=raw['message']
    content=re.sub(r'<think>.*?</think>','',message.get('content') or '',flags=re.S)
    content=re.sub(r'<think>.*$','',content,flags=re.S).strip()
    result={'role':'assistant','content':content}
    calls=message.get('tool_calls') or []
    if calls:
        result['tool_calls']=[{'id':f'ollama_{i}_{digest(c)[:12]}','type':'function','function':{
            'name':c['function']['name'],'arguments':c['function']['arguments'] if isinstance(c['function']['arguments'],str) else json.dumps(c['function']['arguments'])}} for i,c in enumerate(calls)]
    prompt=raw.get('prompt_eval_count',0);completion=raw.get('eval_count',0)
    return {'choices':[{'message':result}], 'done_reason':raw.get('done_reason'), 'usage':{'prompt_tokens':prompt,'completion_tokens':completion,'total_tokens':prompt+completion},
            'ollama_metrics':{k:raw.get(k,0) for k in ['eval_count','eval_duration','prompt_eval_count','prompt_eval_duration','total_duration','load_duration']},
            'thinking_ignored':bool(message.get('thinking') or '<think>' in (message.get('content') or ''))}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def failure_details(exc):
    secrets=[os.getenv(k) for k in ('LLM_API_KEY','GRADER_API_KEY','AGENT_API_KEY')]
    def redact(value):
        text=str(value)
        for secret in secrets:
            if secret:text=text.replace(secret,'[REDACTED]')
        return text
    body=getattr(exc,'raw_response_body',None)
    if body is None:
        body=getattr(getattr(exc,'response',None),'text',None)
    return {'exception_type':type(exc).__name__,'message':redact(exc),
            'status_code':getattr(exc,'status_code',None),
            'raw_response_body':redact(body) if body is not None else None,
            'traceback':redact(''.join(traceback.format_exception(type(exc),exc,exc.__traceback__)))}


class LLMRequestError(RuntimeError):
    def __init__(self,details,path):
        self.status_code=details['status_code']
        self.raw_response_body=details['raw_response_body']
        self.diagnostic_path=str(path)
        super().__init__(f"LLM request failed ({details['exception_type']}, status={self.status_code}): {details['message']}\nRaw provider response: {self.raw_response_body}\nDiagnostic: {path}")


class GraderQuotaDeferred(LLMRequestError):
    pass


def is_final_answer(value):
    return (isinstance(value,dict) and set(value)=={'answer','outcome','cited_edge_ids','cited_spans'} and
            isinstance(value['answer'],str) and isinstance(value['outcome'],str) and
            value['outcome'] in {'ACT','ANSWER_ONLY','ESCALATE'} and
            all(isinstance(value[k],list) and all(isinstance(x,str) for x in value[k])
                for k in ('cited_edge_ids','cited_spans')))


def salvaged_answer(details):
    if details['status_code'] != 400 or not details['raw_response_body']:
        return None
    try:
        error=json.loads(details['raw_response_body'])['error']
        generation=json.loads(error['failed_generation'])
        value=generation['arguments']
        if error.get('code')=='tool_use_failed' and isinstance(generation.get('name'),str) and is_final_answer(value):
            return value
    except (ValueError,KeyError,TypeError):
        pass
    return None


class CachedLLM:
    def __init__(self, model=None, client=None, cache_dir=None, sleep=time.sleep, role='agent', provider=None, defer_daily_quota=False):
        config=settings(role) if client is None else {}
        self.role=role
        self.defer_daily_quota=defer_daily_quota
        self.grader_input_limit=6000
        self.provider=provider or config.get('provider','openai')
        self.base_url=config.get('LLM_BASE_URL','http://127.0.0.1:11434')
        self.no_think=False
        self.limiter=GRADER_LIMITER if role=='grader' else None
        self.model=model or config.get('LLM_MODEL')
        if not self.model:
            raise ValueError('model is required')
        self.thinking_control=not self.model.lower().startswith('qwen2.5')
        if client is None and self.provider!='ollama':
            from openai import OpenAI
            client=OpenAI(api_key=config['LLM_API_KEY'],base_url=config['LLM_BASE_URL'],max_retries=0,timeout=60)
        self.client=client
        self.cache_dir=Path(cache_dir or ROOT/'cache'/role/self.provider)
        self.sleep=sleep
        self.calls=[]

    def complete(self,messages,tools=None,tool_choice=None):
        guard={'triggered':False};truncated=False
        if self.role=='agent':
            try:messages,guard=guard_context(messages,tools)
            except ContextLimitError as exc:
                self.calls.append({'usage':{},'cache_hit':False,'context_guard':exc.event,'retries':0,'failed':True})
                raise
        else:messages,truncated=grader_context(messages,self.grader_input_limit)
        key_data={'model':self.model,'messages':messages,'tools':tools or []}
        response_format=grader_format(messages) if self.role=='grader' else None
        if self.role=='grader':key_data.update(reasoning_effort='low',response_format=response_format)
        if self.provider=='ollama':
            key_data.update(provider='ollama',tool_choice=tool_choice,num_ctx=16384)
            if self.thinking_control:key_data['think']=False
            if self.thinking_control and self.no_think:key_data['no_think_fallback']=True
        key=digest(key_data)
        attempt=0
        path=self.cache_dir/f'{key}.json'
        started=time.perf_counter()
        if path.exists():
            record=json.loads(path.read_text())
            response=record['response']
            hit=True
        else:
            salvaged=False
            diagnostics=[]
            for attempt in range(7):
                try:
                    args={'model':self.model,'messages':messages,'temperature':0,'max_tokens':1600}
                    if self.role=='grader':args.update(reasoning_effort='low',response_format=response_format)
                    if tools:
                        args['tools']=tools
                        args['parallel_tool_calls']=False
                        if tool_choice is not None:args['tool_choice']=tool_choice
                    reservation=(self.limiter.acquire(estimate_tokens(messages,tools)+1600,defer_daily=True) if self.defer_daily_quota else self.limiter.acquire(estimate_tokens(messages,tools)+1600)) if self.limiter else None
                    if self.provider=='ollama':
                        native=copy.deepcopy(messages)
                        for m in native:
                            m.pop('reasoning',None);m.pop('reasoning_content',None)
                            if m.get('tool_calls'):
                                for call in m['tool_calls']:
                                    call['function']['arguments']=json.loads(call['function']['arguments']) if isinstance(call['function']['arguments'],str) else call['function']['arguments']
                            if m['role']=='tool':
                                call_id=m.pop('tool_call_id',None)
                                m['tool_name']=next((c['function']['name'] for previous in native for c in previous.get('tool_calls',[]) if c.get('id')==call_id),'')
                        if self.thinking_control and self.no_think:native[0]['content']+=' /no_think'
                        if isinstance(tool_choice,dict):native[0]['content']+=' Finish now by calling '+tool_choice['function']['name']+'; no other output.'
                        payload={'model':self.model,'messages':native,'stream':False,'keep_alive':'30m',
                                 'options':{'temperature':0,'num_ctx':16384,'num_predict':1600}}
                        if self.thinking_control:payload['think']=False
                        if tools:payload['tools']=tools
                        raw=self.client(payload) if self.client else ollama_chat(self.base_url,payload)
                        response=normalize_ollama(raw)
                        self.no_think=self.no_think or response['thinking_ignored']
                    else:response=self.client.chat.completions.create(**args).model_dump(mode='json')
                    if reservation:reservation[1]=(response.get('usage') or {}).get('total_tokens',reservation[1])

                    break
                except Exception as exc:
                    details=failure_details(exc)
                    directory=self.cache_dir/'errors';directory.mkdir(parents=True,exist_ok=True)
                    diagnostic=directory/f'{key}_{time.time_ns()}.json'
                    diagnostic.write_text(json.dumps({'cache_key':key,'attempt':attempt+1,
                        'model':self.model,'request_options':{k:v for k,v in args.items() if k not in {'messages','tools'}},
                        **details},indent=2,ensure_ascii=False))
                    diagnostics.append(str(diagnostic))
                    final=salvaged_answer(details) if tools else None
                    if final is not None:
                        salvaged=True
                        response={'choices':[{'message':{'role':'assistant','content':json.dumps(final)},'finish_reason':'stop'}],
                                  'salvaged_final':True,'error_diagnostic':str(diagnostic)}
                        print('Salvaged final-answer arguments from Groq tool_use_failed; authorization checks still apply.',file=sys.stderr,flush=True)
                        break
                    # Legacy clients fail fast on daily quota; the grader waits for its retry window.
                    daily_quota='tokens per day (TPD)' in details['message'] or 'requests per day (RPD)' in details['message']
                    if self.role=='grader' and ((daily_quota and self.defer_daily_quota) or (details['status_code']==413 and self.grader_input_limit>1500)):
                        self.calls.append({'provider':self.provider,'role':self.role,'cache_key':key,'cache_hit':False,'usage':{},'billed_tokens':0,
                            'latency_s':time.perf_counter()-started,'retries':attempt+1,'failed':True,'status_code':details['status_code']})
                        if daily_quota and self.defer_daily_quota:raise GraderQuotaDeferred(details,diagnostic) from exc
                        self.grader_input_limit//=2
                        print(f'Grader HTTP 413; retrying with input budget {self.grader_input_limit}.',file=sys.stderr,flush=True)
                        return self.complete(messages,tools,tool_choice)
                    if getattr(exc,'status_code',None)!=429 or (daily_quota and self.role!='grader') or attempt==6:
                        self.calls.append({'provider':self.provider,'role':self.role,'cache_key':key,'cache_hit':False,'usage':{},'billed_tokens':0,
                            'latency_s':time.perf_counter()-started,'retries':attempt,'context_guard':guard,'failed':True})
                        print(details['traceback'],file=sys.stderr,flush=True)
                        raise LLMRequestError(details,diagnostic) from exc
                    delay=min(2**attempt,45)
                    header=getattr(getattr(exc,'response',None),'headers',{}).get('retry-after')
                    if header:
                        try:delay=min(max(delay,float(header)),60)
                        except ValueError:pass
                    if self.role=='grader':
                        wait=re.search(r'(?:try again in|retry in)\s*(?:(\d+(?:\.\d+)?)h)?\s*(?:(\d+(?:\.\d+)?)m(?:inutes?)?)?\s*(?:(\d+(?:\.\d+)?)s)?',details['message'],re.I)
                        if wait:delay=max(delay,sum(float(v or 0)*unit for v,unit in zip(wait.groups(),[3600,60,1])))
                        if header:
                            try:delay=max(delay,float(header))
                            except ValueError:pass
                        print(f'Grader rate limited; retrying after {delay:.1f}s.',file=sys.stderr,flush=True)
                    while delay>0:
                        chunk=min(delay,60);self.sleep(chunk);delay-=chunk
            self.cache_dir.mkdir(parents=True,exist_ok=True)
            record={'cache_key':key,'model':self.model,'response':response,
                    'transport_fallback':'salvaged_final' if salvaged else None,'error_diagnostics':diagnostics,'retries':attempt}
            temporary=path.with_suffix('.tmp')
            temporary.write_text(json.dumps(record,ensure_ascii=False))
            temporary.replace(path)
            hit=False
        if self.provider=='ollama':self.no_think=self.no_think or response.get('thinking_ignored',False)
        self.calls.append({'provider':self.provider,'role':self.role,'context_guard':guard,'grader_input_truncated':truncated,'retries':0 if hit else attempt,
                           'ollama_metrics':response.get('ollama_metrics',{}),'cache_key':key,'cache_hit':hit,'latency_s':time.perf_counter()-started,
                           'usage':response.get('usage') or {},'billed_tokens':0 if hit else (response.get('usage') or {}).get('total_tokens',0)})
        return response
