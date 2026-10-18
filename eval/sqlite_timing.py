"""Compare exact distinct reverse reachability, including connection-cold and warm runs."""
import argparse
import json
from pathlib import Path
import sqlite3
import statistics
import time

import sys
if __package__ in {None, ''}:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from app.store import GraphStore
from app.tools import View

ROOT=Path(__file__).resolve().parents[1]
CTE='''WITH RECURSIVE affected(id) AS (
SELECT ? UNION SELECT d.src FROM dependencies d JOIN affected a ON d.dst=a.id
) SELECT id FROM affected WHERE id != ? ORDER BY id'''
Q1="MATCH (a:Service)-[e:DEPENDS_ON]->(b:Service) WHERE b.id IN $frontier AND e.status='current' AND e.eid IN $allowed RETURN a.id"


def falkor_blast(graph,service,allowed):
    seen={service};frontier={service}
    while frontier:
        rows=graph.query(Q1,{'frontier':sorted(frontier),'allowed':allowed}).result_set
        frontier={row[0] for row in rows}-seen
        seen.update(frontier)
    return sorted(seen-{service})


def benchmark(repeats=20):
    store=GraphStore();view=View(store)
    links=[e for e in view.es.values() if e['type']=='DEPENDS_ON' and view.current(e)]
    allowed=[e['eid'] for e in links]
    directory=ROOT/'eval';directory.mkdir(exist_ok=True)
    path=directory/'timing.sqlite'
    connection=sqlite3.connect(path)
    connection.execute('DROP TABLE IF EXISTS dependencies')
    connection.execute('CREATE TABLE dependencies(src TEXT NOT NULL,dst TEXT NOT NULL,PRIMARY KEY(src,dst))')
    connection.executemany('INSERT OR IGNORE INTO dependencies VALUES(?,?)',[(e['src'],e['dst']) for e in links])
    connection.execute('CREATE INDEX dependencies_dst ON dependencies(dst)');connection.commit()
    service='service-core-auth'  # Largest P1 reverse closure; identical inputs to both engines.
    expected=[r[0] for r in connection.execute(CTE,(service,service))]
    assert expected==falkor_blast(store.graph,service,allowed)
    samples={key:[] for key in ['sqlite_connection_cold','falkor_connection_cold','sqlite_warm','falkor_warm']}
    for i in range(repeats):
        # Alternate order to reduce monotonic load drift. No cache flushing/restarts.
        for engine in (['sqlite','falkor'] if i%2==0 else ['falkor','sqlite']):
            start=time.perf_counter()
            if engine=='sqlite':
                cold=sqlite3.connect(path)
                actual=[r[0] for r in cold.execute(CTE,(service,service))];cold.close()
            else:
                cold=GraphStore()
                actual=falkor_blast(cold.graph,service,allowed)
                cold.graph.client.close()
            samples[engine+'_connection_cold'].append((time.perf_counter()-start)*1000)
            assert actual==expected
        for engine in (['falkor','sqlite'] if i%2==0 else ['sqlite','falkor']):
            start=time.perf_counter()
            actual=([r[0] for r in connection.execute(CTE,(service,service))] if engine=='sqlite' else falkor_blast(store.graph,service,allowed))
            samples[engine+'_warm'].append((time.perf_counter()-start)*1000)
            assert actual==expected
    connection.close()
    result={'repeats':repeats,'service':service,'dependency_edges':len(links),'affected_count':len(expected),
            'median_ms':{k:statistics.median(v) for k,v in samples.items()},'samples_ms':samples,
            'cold_definition':'new client/connection including connection establishment; server and OS caches not flushed',
            'scope':'query-only comparison after common ACL/time/current projection; ingestion and ACL snapshot excluded for both',
            'sqlite_query':CTE,'falkor_query':Q1}
    (directory/'timing.json').write_text(json.dumps(result,indent=2))
    lines=['# SQLite versus FalkorDB timing','','Exact identical reverse closure; recursive SQLite UNION prevents repeated vertices. FalkorDB uses bounded-frontier Q1 with a visited set.','',
           '| Mode | SQLite median ms | FalkorDB median ms | Faster |','| --- | ---: | ---: | --- |']
    for mode in ['connection_cold','warm']:
        sql=result['median_ms']['sqlite_'+mode];falk=result['median_ms']['falkor_'+mode]
        lines.append(f'| {mode} | {sql:.4f} | {falk:.4f} | {"SQLite" if sql<falk else "FalkorDB"} |')
    lines+=['',f'n={repeats} per engine/mode, {len(links)} dependencies, {len(expected)} exact affected services. Every timed result matched.',
            '',result['cold_definition']+'. This is connection-cold, not a hardware/server-cache cold benchmark. SQLite runs in-process; FalkorDB includes local network round trips. No DB restart or global cache-flushing was performed. Common ACL projection/ingestion is excluded from both query timings. SQLite CTE is unbounded UNION closure; Q1 expands until no unseen nodes, and the actual DAG converges within the eight-hop tool bound.']
    (directory/'timing.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'samples_ms','sqlite_query','falkor_query'}}))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repeats',type=int,default=20)
    benchmark(parser.parse_args().repeats)
