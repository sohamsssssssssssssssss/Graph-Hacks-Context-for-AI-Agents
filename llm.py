"""OpenAI-compatible client with content-addressed disk cache and 429 backoff."""
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


def settings():
    load_dotenv(ROOT / '.env')
    missing=[key for key in ('LLM_BASE_URL','LLM_API_KEY','LLM_MODEL') if not os.getenv(key)]
    if missing:
        raise RuntimeError('Configure local .env: '+', '.join(missing))
    return {key:os.environ[key] for key in ('LLM_BASE_URL','LLM_API_KEY','LLM_MODEL')}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def failure_details(exc):
    secret=os.getenv('LLM_API_KEY')
    def redact(value):
        text=str(value)
        return text.replace(secret,'[REDACTED]') if secret else text
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
    def __init__(self, model=None, client=None, cache_dir=None, sleep=time.sleep):
        config=settings() if client is None else {}
        self.model=model or config.get('LLM_MODEL')
        if not self.model:
            raise ValueError('model is required')
        if client is None:
            from openai import OpenAI
            client=OpenAI(api_key=config['LLM_API_KEY'],base_url=config['LLM_BASE_URL'],max_retries=0,timeout=60)
        self.client=client
        self.cache_dir=Path(cache_dir or ROOT/'cache')
        self.sleep=sleep
        self.calls=[]

    def complete(self,messages,tools=None):
        # Temperature/output limit are fixed for this cache format.
        key=digest({'model':self.model,'messages':messages,'tools':tools or []})
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
                    if tools:
                        args['tools']=tools
                        args['parallel_tool_calls']=False
                    response=self.client.chat.completions.create(**args).model_dump(mode='json')
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
                    # Daily quota cannot recover within this client's bounded backoff.
                    daily_quota='tokens per day (TPD)' in details['message'] or 'requests per day (RPD)' in details['message']
                    if getattr(exc,'status_code',None)!=429 or daily_quota or attempt==6:
                        print(details['traceback'],file=sys.stderr,flush=True)
                        raise LLMRequestError(details,diagnostic) from exc
                    delay=min(2**attempt,45)
                    header=getattr(getattr(exc,'response',None),'headers',{}).get('retry-after')
                    if header:
                        try:delay=min(max(delay,float(header)),60)
                        except ValueError:pass
                    self.sleep(delay)
            self.cache_dir.mkdir(parents=True,exist_ok=True)
            record={'cache_key':key,'model':self.model,'response':response,
                    'transport_fallback':'salvaged_final' if salvaged else None,'error_diagnostics':diagnostics}
            temporary=path.with_suffix('.tmp')
            temporary.write_text(json.dumps(record,ensure_ascii=False))
            temporary.replace(path)
            hit=False
        self.calls.append({'cache_key':key,'cache_hit':hit,'latency_s':time.perf_counter()-started,
                           'usage':response.get('usage') or {},'billed_tokens':0 if hit else (response.get('usage') or {}).get('total_tokens',0)})
        return response
