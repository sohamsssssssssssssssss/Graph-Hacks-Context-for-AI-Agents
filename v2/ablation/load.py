"""Build only keystone_noderive from unchanged seed-42 files; refuse overwrite."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from falkordb import FalkorDB

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
GRAPH = 'keystone_noderive'


def database():
    return FalkorDB(host='127.0.0.1', port=6380)


def source():
    nodes = [json.loads(s) for s in (ROOT / 'data/nodes.jsonl').read_text().splitlines()]
    edges = [json.loads(s) for s in (ROOT / 'data/edges.jsonl').read_text().splitlines()]
    for edge in edges:
        if not edge['eid'].startswith('EID-BG-'):
            edge.update(status='current', derived_reason='A1: status derivation not applied')
    return nodes, edges


def insert(g, nodes, edges, scope):
    labels = {n['label'] for n in nodes}
    kinds = {e['type'] for e in edges}
    if any(not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', v) for v in labels | kinds):
        raise ValueError('invalid graph schema identifier')
    for label in sorted(labels):
        rows = [{**n, '_scope': scope, '_uid': scope+':'+n['id']} for n in nodes if n['label'] == label]
        for offset in range(0, len(rows), 500):
            g.query(f'UNWIND $rows AS row CREATE (n:{label}) SET n = row', {'rows': rows[offset:offset+500]})
    for kind in sorted(kinds):
        rows = [{'src': scope+':'+e['src'], 'dst': scope+':'+e['dst'], 'props': {**e, '_scope': scope}}
                for e in edges if e['type'] == kind]
        for offset in range(0, len(rows), 500):
            g.query(f'UNWIND $rows AS row MATCH (a {{_uid:row.src}}), (b {{_uid:row.dst}}) '
                    f'CREATE (a)-[e:{kind}]->(b) SET e = row.props', {'rows': rows[offset:offset+500]})


def counts(g, scope=None):
    where = ' WHERE n._scope=$scope' if scope else ''
    nodes = g.query('MATCH (n)'+where+' RETURN labels(n)[0],count(n)', {'scope': scope}).result_set
    where = ' WHERE e._scope=$scope' if scope else ''
    edges = g.query('MATCH ()-[e]->()'+where+' RETURN type(e),count(e)', {'scope': scope}).result_set
    return {'nodes': dict(nodes), 'edges': dict(edges)}


def load_seed():
    db = database()
    if GRAPH in db.list_graphs():
        raise RuntimeError('keystone_noderive already exists; never overwrite a graph')
    if 'keystone' not in db.list_graphs():
        raise RuntimeError('normal keystone graph is unavailable for the required count check')
    nodes, edges = source()
    expected = {'nodes': dict(Counter(n['label'] for n in nodes)), 'edges': dict(Counter(e['type'] for e in edges))}
    normal = counts(db.select_graph('keystone'))
    if normal != expected:
        raise RuntimeError('seed-42 node/edge counts differ from the normal graph')
    g = db.select_graph(GRAPH)
    insert(g, nodes, edges, 'seed42')
    observed = counts(g, 'seed42')
    assert observed == expected
    status = g.query('MATCH ()-[e]->() WHERE e._scope="seed42" RETURN e.status,count(e)').result_set
    manifest = {'graph': GRAPH, 'normal_graph_counts': normal, 'seed42_counts': observed,
                'seed42_status_counts': dict(status),
                'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data').glob('*.jsonl')}}
    (HERE/'load_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    load_seed()
