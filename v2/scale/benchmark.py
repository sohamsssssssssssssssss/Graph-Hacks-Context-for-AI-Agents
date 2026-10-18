"""Frozen, isolated scale benchmark; no model imports/calls."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import signal
import sqlite3
import statistics
import subprocess
import time

from falkordb import FalkorDB
import redis

from generate import build_curated_data
from derive import derive
from v2.scale.queries import FALKOR, SQLITE

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
END = datetime(2026, 10, 18, 17, 0, tzinfo=timezone.utc).timestamp()
LOAD_100K_END = datetime(2026, 10, 18, 16, 45, tzinfo=timezone.utc).timestamp()
RESERVE = 120
SIZES = [('10k', 10000), ('100k', 100000)]


class Stop(BaseException):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def event(kind, **values):
    with (HERE/'journal.jsonl').open('a') as out:
        out.write(json.dumps({'at': now(), 'event': kind, **values})+'\n')


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


def check_registration():
    for name in ['SPEC.md','inputs.json','queries.py']:
        actual=(HERE/name).read_bytes()
        committed=subprocess.check_output(['git','show','scale-v1:v2/scale/'+name],cwd=ROOT)
        if actual!=committed:
            raise ValueError('Registration changed: '+name)


def scaled(target):
    tree=ast.parse((ROOT/'generate.py').read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='generate_background_data')
    replacements=Counter()
    class Scale(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is int and node.value in {6243,15055}:
                replacements[node.value]+=1
                node.value=target if node.value==6243 else round(15276*target/6243)-221
            return node
    function=Scale().visit(function)
    assert replacements=={6243:1,15055:1}
    module=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    namespace={'random':random}
    exec(compile(module,'<isolated scaled generator>','exec'),namespace)
    curated=build_curated_data()
    nodes,edges,docs=namespace['generate_background_data'](curated,seed=42)
    expected=curated['edges']
    assert edges[:len(expected)]==expected and len(expected)==221
    states=derive(nodes,expected,docs)
    for e in edges[:221]:
        e.update(states[e['eid']])
    assert len(nodes)==target and len(edges)==round(15276*target/6243)
    return nodes,edges,docs


def graph_counts(graph):
    return {'nodes':graph.query('MATCH (n) RETURN count(n)',timeout=5000).result_set[0][0],
            'edges':graph.query('MATCH ()-[e]->() RETURN count(e)',timeout=5000).result_set[0][0]}


def sql_connection(path):
    con=sqlite3.connect(path,timeout=5)
    con.execute('PRAGMA query_only=ON')
    return con


def build(size,target,manifest):
    name='keystone_scale_'+size
    db=FalkorDB(host='127.0.0.1',port=6380)
    sqlpath=HERE/(size+'.sqlite')
    if name in db.list_graphs() or sqlpath.exists():
        raise RuntimeError('Refusing to overwrite existing benchmark data: '+size)
    start=time.perf_counter()
    nodes,edges,docs=scaled(target)
    data=HERE/'data'/size;data.mkdir(parents=True,exist_ok=True)
    for filename,rows in [('nodes',nodes),('edges',edges),('docs',docs)]:
        with (data/(filename+'.jsonl')).open('w') as out:
            for row in rows:out.write(json.dumps(row,ensure_ascii=False)+'\n')
    item={'nodes':len(nodes),'edges':len(edges),'generation_seconds':time.perf_counter()-start,
          'node_types':dict(Counter(n['label'] for n in nodes)),
          'edge_types':dict(Counter(e['type'] for e in edges)),
          'status_counts':dict(Counter(e['status'] for e in edges)),
          'data_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.glob('*.jsonl')},'loads':{}}
    manifest['sizes'][size]=item;save(HERE/'manifest.json',manifest)
    # Load both fresh 100k stores before 22:15, including index construction.
    start=time.perf_counter();g=db.select_graph(name)
    for label in ['Entity','Service','Decision','Team']:
        g.query(f'CREATE INDEX FOR (n:{label}) ON (n.id)',timeout=5000)
    for label in sorted({n['label'] for n in nodes}):
        rows=[n for n in nodes if n['label']==label]
        for offset in range(0,len(rows),1000):
            g.query(f'UNWIND $rows AS row CREATE (n:Entity:{label}) SET n=row',{'rows':rows[offset:offset+1000]},timeout=5000)
    for kind in sorted({e['type'] for e in edges}):
        rows=[e for e in edges if e['type']==kind]
        for offset in range(0,len(rows),1000):
            g.query(f'UNWIND $rows AS row MATCH (a:Entity {{id:row.src}}),(b:Entity {{id:row.dst}}) '
                    f'CREATE (a)-[e:{kind}]->(b) SET e=row',{'rows':rows[offset:offset+1000]},timeout=5000)
    assert graph_counts(g)=={'nodes':len(nodes),'edges':len(edges)}
    item['loads']['falkordb_seconds']=time.perf_counter()-start
    item['falkordb_loaded_at']=now();save(HERE/'manifest.json',manifest)
    event('graph_loaded',size=size,**item['loads'])
    start=time.perf_counter();con=sqlite3.connect(sqlpath)
    con.executescript('CREATE TABLE nodes(id TEXT PRIMARY KEY,label TEXT,props TEXT);'
                      'CREATE TABLE edges(eid TEXT PRIMARY KEY,src TEXT,dst TEXT,type TEXT,status TEXT,props TEXT);')
    con.executemany('INSERT INTO nodes VALUES(?,?,?)',((n['id'],n['label'],json.dumps(n)) for n in nodes))
    con.executemany('INSERT INTO edges VALUES(?,?,?,?,?,?)',((e['eid'],e['src'],e['dst'],e['type'],e['status'],json.dumps(e)) for e in edges))
    con.executescript('CREATE INDEX node_label ON nodes(label,id);'
                      'CREATE INDEX edge_out ON edges(src,type,status,dst);'
                      'CREATE INDEX edge_in ON edges(dst,type,status,src);'
                      'CREATE INDEX edge_status ON edges(status,src);')
    con.commit()
    assert con.execute('SELECT count(*) FROM nodes').fetchone()[0]==len(nodes)
    assert con.execute('SELECT count(*) FROM edges').fetchone()[0]==len(edges)
    con.close();item['loads']['sqlite_seconds']=time.perf_counter()-start
    item['both_loaded_at']=now();save(HERE/'manifest.json',manifest)
    event('both_loaded',size=size,**item['loads'])
    print('Loaded',size,item['nodes'],item['edges'],item['loads'],flush=True)


def run_query(engine,connection,query,params):
    if engine=='sqlite':
        # Signal deadline also bounds recursive SQLite work.
        return [list(row) for row in connection.execute(SQLITE[query],params)]
    return [list(row) for row in connection.query(FALKOR[query],params,timeout=5000).result_set]


def correctness(size,inputs):
    g=FalkorDB(host='127.0.0.1',port=6380).select_graph('keystone_scale_'+size)
    con=sql_connection(HERE/(size+'.sqlite'))
    result=[]
    try:
        for query,values in inputs.items():
            for index,params in enumerate(values):
                a=run_query('sqlite',con,query,params);b=run_query('falkordb',g,query,params)
                result.append({'query':query,'input':index,'params':params,'sqlite':a,'falkordb':b,'match':a==b})
    finally:con.close()
    save(HERE/(size+'_correctness.json'),result)
    if not all(r['match'] for r in result):
        raise ValueError('Correctness mismatch: '+size)
    event('correctness_passed',size=size,inputs=len(result))
    print('Correctness',size,len(result),'/',len(result),flush=True)


def summary(samples):
    ordered=sorted(samples)
    return {'n':len(samples),'median_ms':statistics.median(samples),
            'p95_ms':ordered[math.ceil(0.95*len(ordered))-1]}


def timings(size,inputs):
    output=HERE/(size+'_timings.jsonl')
    if output.exists():
        raise RuntimeError('Timing file already exists; cannot silently repeat samples')
    g=FalkorDB(host='127.0.0.1',port=6380).select_graph('keystone_scale_'+size)
    con=sql_connection(HERE/(size+'.sqlite'))
    expected={(r['query'],r['input']):r['sqlite'] for r in json.loads((HERE/(size+'_correctness.json')).read_text())}
    try:
        for query,values in inputs.items():
            for index,params in enumerate(values):
                for repeat in range(20):
                    modes=['cold','warm'] if (index+repeat)%2==0 else ['warm','cold']
                    engines=['sqlite','falkordb'] if (index+repeat)%2==0 else ['falkordb','sqlite']
                    for mode in modes:
                        for engine in engines:
                            start=time.perf_counter()
                            connection=con if engine=='sqlite' else g
                            if mode=='cold':
                                connection=sql_connection(HERE/(size+'.sqlite')) if engine=='sqlite' else FalkorDB(host='127.0.0.1',port=6380).select_graph('keystone_scale_'+size)
                            try:actual=run_query(engine,connection,query,params)
                            finally:
                                if mode=='cold':
                                    if engine=='sqlite':connection.close()
                                    else:connection.client.close()
                            ms=(time.perf_counter()-start)*1000
                            assert actual==expected[(query,index)],(size,query,index,'timed result changed')
                            with output.open('a') as out:
                                out.write(json.dumps({'size':size,'query':query,'input':index,'repeat':repeat,'mode':mode,'engine':engine,'ms':ms,'rows':len(actual)})+'\n')
            event('query_timed',size=size,query=query,samples=1600)
            print('Timed',size,query,flush=True)
    finally:con.close()
    event('timings_complete',size=size)


def report(manifest):
    lines=['# Scale benchmark results','',f"Registration: scale-v1 (`{manifest['registration'][:12]}`). Status: {manifest['status']}. No LLM calls.",'',
           'Same data in both databases. Cold = first query on a new connection, including connection creation/close; server/OS caches were not flushed. Correctness ran before timings. SQLite is in-process; FalkorDB uses Docker and loopback networking. Each full table cell N=400 (20 input slots x 20 runs); per-input N=20. Q9 has one parameterless query repeated across all slots.','']
    for size,_ in SIZES:
        item=manifest['sizes'].get(size)
        if not item:lines += [f'## {size}','','Not loaded.',''];continue
        lines += [f'## {size}','',f"Nodes {item['nodes']:,}; edges {item['edges']:,}. Types: `{json.dumps(item['node_types'])}`; edge types: `{json.dumps(item['edge_types'])}`.",'',
                  f"Load + indexes: SQLite {item['loads'].get('sqlite_seconds','not finished')} s; FalkorDB {item['loads'].get('falkordb_seconds','not finished')} s. Generation/derivation excluded.",'']
        cp=HERE/(size+'_correctness.json')
        if cp.exists():
            checks=json.loads(cp.read_text());lines += [f"Correctness: {sum(c['match'] for c in checks)}/{len(checks)} exact-row checks matched.",'']
            for q in inputs_global:
                rs=[c for c in checks if c['query']==q]
                lines += [f"- {q}: {sum(bool(c['sqlite']) for c in rs)}/{len(rs)} input slots nonempty; result rows {sum(len(c['sqlite']) for c in rs)} across slots."]
            lines += ['']
        tp=HERE/(size+'_timings.jsonl');samples=[json.loads(l) for l in tp.read_text().splitlines()] if tp.exists() else []
        lines += ['| Query | Engine | Cold median ms | Cold p95 ms | Warm median ms | Warm p95 ms | N cold / warm |','| --- | --- | ---: | ---: | ---: | ---: | ---: |']
        details={}
        for q in inputs_global:
            for engine in ['sqlite','falkordb']:
                groups={mode:[r['ms'] for r in samples if r['query']==q and r['engine']==engine and r['mode']==mode] for mode in ['cold','warm']}
                values={m:summary(v) for m,v in groups.items() if v}
                details[q+'_'+engine]=values
                cells=[]
                for mode in ['cold','warm']:
                    cells.extend([f"{values[mode]['median_ms']:.4f}",f"{values[mode]['p95_ms']:.4f}"] if mode in values else ['—','—'])
                lines += ['| '+q+' | '+engine+' | '+' | '.join(cells)+f" | {len(groups['cold'])} / {len(groups['warm'])} |"]
            for mode in ['cold','warm']:
                a=details.get(q+'_sqlite',{}).get(mode);b=details.get(q+'_falkordb',{}).get(mode)
                if a and b:
                    winner='SQLite' if a['median_ms']<b['median_ms'] else 'FalkorDB' if b['median_ms']<a['median_ms'] else 'Neither (equal)'
                    lines += []
                    details[q+'_'+mode+'_faster']=winner
        lines += ['','Median comparison: '+ '; '.join(k.replace('_',' ')+': '+v for k,v in details.items() if isinstance(v,str))+'.','']
        per_input=[]
        for q in inputs_global:
            for index in range(20):
                for engine in ['sqlite','falkordb']:
                    for mode in ['cold','warm']:
                        v=[r['ms'] for r in samples if r['query']==q and r['input']==index and r['engine']==engine and r['mode']==mode]
                        if v:per_input.append({'query':q,'input':index,'engine':engine,'mode':mode,**summary(v)})
        save(HERE/(size+'_summary.json'),{'aggregate':details,'per_input':per_input,'observed_samples':len(samples),'planned_samples':6400})
        lines += [f'Timed samples: {len(samples)}/6400 planned. Raw timings, correctness rows, and per-input summaries are saved alongside this report.','']
        coverage=Counter((r['query'],r['input']) for r in samples)
        for q in inputs_global:
            full=sum(coverage[(q,i)]==80 for i in range(20))
            partial=sum(0<coverage[(q,i)]<80 for i in range(20))
            lines += [f'- {q} timing coverage: {full}/20 input slots complete, {partial}/20 partial, {20-full-partial}/20 unmeasured.']
        lines += ['']
    lines += ['## Limits and interpretation','',
              'The generator scales mostly filler commits and COMMITTED/CONCERNS noise; Service and Decision counts and the query-relevant curated topology stay fixed. Sparse decision queries and empty paths are retained. This is a background-noise benchmark, not 100k connected services. No ACL, standing, confidence, evidence verification or model cost is measured.',
              '', 'In Keystone, graph representation supports status-filtered path proof, connected decision chains, and PageRank severity. Those capabilities do not imply a raw traversal-speed advantage. Where SQLite has lower measured median traversal latency, SQLite is faster for this workload; graph value must be justified by the connected evidence model rather than these traversal timings.',
              '', f"Errors/missing work: {manifest.get('error','none')}. No score-improvement reruns. Infrastructure events/retries: journal.jsonl. Machine: `{json.dumps(manifest['machine'])}`.",'']
    lines += ['## Post-hoc configuration diagnosis','',
              'Saved SQLite EXPLAIN QUERY PLAN output in sqlite_plans.json shows Q1, Q3, and Q6 choosing edge_status(status) instead of the available adjacency indexes. ANALYZE was not run. The low-selectivity current-status scan is an important limitation: these timings compare the preregistered configuration, not a tuned SQLite baseline. Queries and indexes were not changed after observing this behavior.',
              '', 'The corpus has 60 Services, 45 Decisions, 210 DEPENDS_ON edges, one SUPERSEDES edge, and one BECAUSE_OF edge at both sizes. Q6 therefore does not test growing or long decision chains. Partial timing medians cover only the recorded input prefix and must not be used as complete size-to-size scaling estimates.',
              '', 'Extra generated commits consume random draws before background dependency wiring is generated. Seed 42 therefore keeps curated scenarios fixed but can produce different background dependency wiring between sizes; this further limits causal size-to-size comparisons. Engine correctness comparisons use identical data within each size.',
              '', 'Load-time durability is not normalized: SQLite uses its default DELETE journal/FULL synchronous mode; FalkorDB has appendonly disabled and periodic snapshots. See environment.json for versions, hardware, defaults, and generator/derivation hashes. No exclusive-machine or flushed-cache claim is made.']
    all_samples=[]
    for size,_ in SIZES:
        path=HERE/(size+'_timings.jsonl')
        if path.exists():all_samples.extend(json.loads(line) for line in path.read_text().splitlines())
    sql_samples=[r for r in all_samples if r['engine']=='sqlite']
    over_limit=sum(r['ms']>5000 for r in sql_samples)
    if over_limit:
        lines += ['',f'Protocol deviation: {over_limit}/{len(sql_samples)} SQLite samples exceeded 5 seconds. SQLite was protected by the global deadline but lacked the intended per-query timeout; FalkorDB had a 5-second query timeout. The slow SQLite samples are retained, not dropped or repeated.']
    (HERE/'results.md').write_text('\n'.join(lines))


inputs_global=json.loads((HERE/'inputs.json').read_text())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    check_registration()
    path=HERE/'manifest.json'
    if path.exists():
        if not args.resume:raise RuntimeError('Run exists; --resume required')
        manifest=json.loads(path.read_text())
        event('infrastructure_resume',reason='Continue completed load/size checkpoints; completed timings are never repeated')
    else:
        info=redis.Redis(host='127.0.0.1',port=6380).info('server')
        manifest={'registration':subprocess.check_output(['git','rev-parse','scale-v1'],cwd=ROOT,text=True).strip(),
                  'started_at':now(),'status':'running','sizes':{},'machine':{'platform':platform.platform(),'python':platform.python_version(),
                  'sqlite':sqlite3.sqlite_version,'cpu_count':os.cpu_count(),'redis':info.get('redis_version')}}
        save(path,manifest)
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(Stop('Hard deadline/reporting reserve')))
    signal.setitimer(signal.ITIMER_REAL,max(1,END-time.time()-RESERVE))
    try:
        # Load both sizes before measuring, so 100k's load deadline is respected.
        for size,target in SIZES:
            if manifest['sizes'].get(size,{}).get('both_loaded_at'):continue
            if size=='100k' and time.time()>=LOAD_100K_END:raise Stop('100k not loaded by 22:15 IST; omitted')
            signal.setitimer(signal.ITIMER_REAL,max(1,min(END-RESERVE,LOAD_100K_END if size=='100k' else END-RESERVE)-time.time()))
            build(size,target,manifest)
        signal.setitimer(signal.ITIMER_REAL,max(1,END-time.time()-RESERVE))
        for size,_ in SIZES:
            summary_path=HERE/(size+'_summary.json')
            if summary_path.exists() and json.loads(summary_path.read_text())['observed_samples']==6400:continue
            correctness(size,inputs_global)
            timings(size,inputs_global)
            report(manifest)
        manifest['status']='complete'
    except (Exception,Stop) as exc:
        manifest['status']='partial';manifest['error']=type(exc).__name__+': '+str(exc)
        event('infrastructure_failure' if isinstance(exc,Exception) else 'time_cap',message=manifest['error'])
        print(manifest['error'],flush=True)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        manifest['saved_at']=now();save(path,manifest);report(manifest)
    print((HERE/'results.md').read_text(),flush=True)


if __name__=='__main__':main()
