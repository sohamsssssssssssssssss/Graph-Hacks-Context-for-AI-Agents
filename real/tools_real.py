"""Read-only deterministic tools. Print actual Cypher to stderr for the demo."""
import argparse
import json
import sys

from real.load_real import graph, matching_rules

OWNER_QUERY = '''MATCH (p:PathPattern)
OPTIONAL MATCH (p)-[e:OWNS]->(o:Owner)
RETURN properties(p), o.handle, e.owner_order ORDER BY p.order, e.owner_order'''
STATUS_QUERY = 'MATCH (d:ADR {id:$id}) RETURN properties(d)'
TRACE_QUERY = '''MATCH p=(newer:ADR)-[:SUPERSEDES*1..32]->(older:ADR)
WHERE (newer.id=$id OR older.id=$id)
  AND all(n IN nodes(p) WHERE n.planted=false OR n.id=$id)
RETURN [n IN nodes(p) | n.id], [e IN relationships(p) | properties(e)]'''


def query(cypher, params=None):
    print('Cypher [keystone_real]:\n' + cypher, file=sys.stderr)
    print('Parameters: ' + json.dumps(params or {}), file=sys.stderr)
    return graph().query(cypher, params or {}).result_set


def owners_of(path):
    rules = {}
    for props, owner, _ in query(OWNER_QUERY):
        props = dict(props)
        rule = rules.setdefault(props['id'], {**props, 'owners': []})
        if owner is not None:
            rule['owners'].append(owner)
    matches = matching_rules(path, list(rules.values()))
    if not matches:
        return {'path': path, 'owners': [], 'line': None, 'matched_rules': [],
                'reason': 'No CODEOWNERS pattern matches this path'}
    winner = matches[-1]
    return {'path': path, 'owners': winner['owners'], 'line': winner['line'],
            'pattern': winner['pattern'], 'source_path': winner['path'], 'span': winner['span'],
            'matched_rules': [{'pattern': r['pattern'], 'line': r['line'], 'owners': r['owners']} for r in matches],
            'reason': 'Last matching CODEOWNERS rule; empty owner list explicitly clears ownership'}


def doc_status(adr_id):
    rows = query(STATUS_QUERY, {'id': adr_id})
    if not rows:
        raise ValueError(f'Unknown ADR id: {adr_id}')
    doc = dict(rows[0][0])
    return {'adr_id': doc['id'], 'title': doc['title'], 'status': doc['status'],
            'date': doc.get('date'), 'planted': doc['planted'], 'path': doc['path'],
            'line': doc['status_line'] or 1,
            'end_line': doc['status_line'] or doc['metadata_end_line'],
            'span': doc['status_span'] or doc['metadata_span'],
            'derived_reason': doc['derived_reason']}


def trace_decision(adr_id):
    doc = doc_status(adr_id)
    evidence = {}
    for ids, props in query(TRACE_QUERY, {'id': adr_id}):
        for newer, older, edge in zip(ids, ids[1:], props):
            evidence[(newer, older)] = {'newer': newer, 'older': older, **dict(edge)}
    ordered = sorted(evidence)
    return {'adr_id': adr_id, 'status': doc['status'], 'document': doc,
            'links': [list(pair) for pair in ordered],
            'evidence': [evidence[pair] for pair in ordered],
            'reason': 'Metadata supersession only; body REFERENCES carry no authority'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool', choices=['owners_of', 'doc_status', 'trace_decision'])
    parser.add_argument('value', help='Repository-relative path or ADR id, e.g. ADR013')
    args = parser.parse_args()
    print(json.dumps(globals()[args.tool](args.value), indent=2, ensure_ascii=False))
