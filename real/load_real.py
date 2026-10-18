"""Isolated metadata-only Backstage import. No dotenv, credentials, or LLM imports."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from falkordb import FalkorDB
from pathspec import GitIgnoreSpec

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'real/raw/backstage'
PIN = '8747376ceeb8c46d34549c53cdf6b81bb5de70f9'
GRAPH = 'keystone_real'
ADR_DIR = 'docs/architecture-decisions'
CODEOWNERS = '.github/CODEOWNERS'
ADR_REF = re.compile(r'\bADR[- ]?(\d+)\b', re.I)


def local_git(*args):
    # No lazy blob fetch, transport, --follow, or email formatting.
    env = {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': ''}
    return subprocess.check_output(['git', '-C', str(RAW), *args], env=env,
                                   text=True, stderr=subprocess.PIPE, timeout=60).strip()


def graph():
    return FalkorDB(host='127.0.0.1', port=6380).select_graph(GRAPH)


def source_path(path):
    return str(path.relative_to(ROOT))


def adr_refs(text):
    return list(dict.fromkeys(f'ADR{int(n):03d}' for n in ADR_REF.findall(text)))


def parse_adr(path, planted_id=None):
    """Only frontmatter and the first explicit status notice have authority."""
    lines = path.read_text().splitlines()
    if not lines or lines[0] != '---':
        raise ValueError(f'{path}: missing frontmatter')
    end = lines.index('---', 1)
    fields, field_lines = {}, {}
    for i, line in enumerate(lines[1:end], 2):
        match = re.fullmatch(r'(id|title|status|date):\s*(.*)', line)
        if match:
            key, value = match.groups()
            if key in fields or value in {'|', '>'}:
                raise ValueError(f'{path}:{i}: duplicate or multiline metadata')
            fields[key] = value.strip().strip("\"'")
            field_lines[key] = i
    if not {'id', 'title'} <= fields.keys():
        raise ValueError(f'{path}: missing id/title')
    ids = adr_refs(fields['id'])
    if len(ids) != 1:
        raise ValueError(f'{path}: expected one ADR id')
    doc_id = planted_id or ids[0]
    status, evidence_line = 'unspecified', 0
    candidates = []
    if 'status' in fields:
        candidates.append((field_lines['status'], fields['status']))
    title_status = re.search(r'\[(accepted|proposed|superseded|deprecated|rejected)\]', fields['title'], re.I)
    if title_status:
        candidates.append((field_lines['title'], title_status[1]))
    i = end + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    metadata_end = end + 1
    # shortcut: this source uses a Docusaurus initial status notice; add another
    # format only when importing a repository whose documented metadata uses it.
    if i < len(lines) and re.fullmatch(r':::note\[(Superseded|Deprecated)\]', lines[i], re.I):
        close = next((j for j in range(i + 1, len(lines)) if lines[j] == ':::'), None)
        if close is None:
            raise ValueError(f'{path}: unterminated status notice')
        candidates.append((i + 1, re.search(r'\[(.*)\]', lines[i])[1]))
        metadata_end = close + 1
        for j in range(i + 1, close):
            if re.search(r'\bsuperseded by\b', lines[j], re.I):
                candidates.append((j + 1, lines[j]))
    successors = []
    for line_no, value in candidates:
        match = re.search(r'\b(accepted|proposed|superseded|deprecated|rejected)\b', value, re.I)
        if not match:
            raise ValueError(f'{path}:{line_no}: unrecognized status')
        candidate = match[1].lower()
        if status != 'unspecified' and status != candidate:
            raise ValueError(f'{path}:{line_no}: conflicting metadata statuses')
        status, evidence_line = candidate, line_no
        if re.search(r'\bsuperseded by\b', value, re.I):
            successors.extend((ref, line_no, lines[line_no - 1]) for ref in adr_refs(value))
    props = {
        'id': doc_id, 'metadata_id': fields['id'], 'title': fields['title'],
        'status': status, 'date': fields.get('date'), 'path': source_path(path),
        'planted': planted_id is not None, 'source_commit': PIN,
        'status_line': evidence_line,
        'status_span': lines[evidence_line - 1] if evidence_line else '',
        'metadata_span': '\n'.join(lines[:metadata_end]), 'metadata_end_line': metadata_end,
        'derived_reason': ('metadata: explicit status' if evidence_line else
                           'metadata: no explicit status; no acceptance inferred'),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    references = [(ref, j + 1, line) for j, line in enumerate(lines)
                  if j >= metadata_end for ref in adr_refs(line) if ref != ids[0]]
    return props, successors, references


def parse_codeowners(text, path=CODEOWNERS):
    rules = []
    for number, line in enumerate(text.splitlines(), 1):
        content = line.split('#', 1)[0].strip()
        if not content:
            continue
        parts = content.split()
        pattern, owners = parts[0], parts[1:]
        if pattern.startswith('!') or any(c in pattern for c in '[]\\'):
            raise ValueError(f'{path}:{number}: unsupported CODEOWNERS syntax')
        if any(not owner.startswith('@') for owner in owners):
            raise ValueError(f'{path}:{number}: expected CODEOWNERS handles')
        # Compile before import, never discard a malformed rule silently.
        GitIgnoreSpec.from_lines([pattern])
        rules.append({'id': f'pattern:{number}', 'pattern': pattern, 'owners': owners,
                      'line': number, 'order': number, 'path': path, 'span': line})
    return rules


def matching_rules(path, rules):
    if not path or path.startswith('/') or '\\' in path or any(p in {'.', '..', ''} for p in path.split('/')):
        raise ValueError('path must be a repository-relative file path without traversal')
    return [r for r in sorted(rules, key=lambda r: r['order'])
            if GitIgnoreSpec.from_lines([r['pattern']]).match_file(path)]


def creation_author(path):
    try:
        if local_git('rev-parse', '--is-shallow-repository') != 'false':
            return None, 'shallow history: creation not verifiable'
        entries = local_git('log', '--reverse', '--no-renames', '--diff-filter=A',
                            '--format=%H%x09%an', '--', path).splitlines()
        if not entries:
            return None, 'no creation commit for current path'
        commit, name = entries[0].split('\t', 1)
        if not name.strip():
            return None, 'creation commit has no author name'
        return {'name': name, 'commit': commit, 'path': path}, None
    except (subprocess.SubprocessError, ValueError) as exc:
        return None, f'local history unavailable: {type(exc).__name__}'


def build():
    if local_git('rev-parse', 'HEAD') != PIN:
        raise ValueError('clone HEAD differs from pinned source commit')
    if local_git('status', '--porcelain', '--untracked-files=no', '--', ADR_DIR, CODEOWNERS):
        raise ValueError('raw ADRs/CODEOWNERS differ from the pinned checkout')
    files = sorted((RAW / ADR_DIR).glob('adr[0-9][0-9][0-9]-*.md'))
    files = [p for p in files if not p.name.startswith('adr000-')]
    originals = [parse_adr(p) for p in files]
    plants = [parse_adr(p, p.stem) for p in sorted((ROOT / 'real/planted').glob('PLANTED-*.md'))]
    docs = originals + plants
    ids = {doc['id'] for doc, _, _ in docs}
    if len(ids) != len(docs):
        raise ValueError('duplicate ADR ids')
    nodes = [('ADR', doc) for doc, _, _ in docs]
    edges, authors, omitted, unresolved = [], [], [], []
    people = {}
    for p, (doc, _, _) in zip(files, originals):
        author, reason = creation_author(str(p.relative_to(RAW)))
        if author:
            person_id = 'person:' + hashlib.sha256(author['name'].encode()).hexdigest()[:20]
            people[person_id] = {'id': person_id, 'name': author['name']}
            authors.append({'adr_id': doc['id'], **author})
            edges.append(('AUTHORED', person_id, doc['id'], {'creation_commit': author['commit'],
                           'path': doc['path'], 'method': 'current-path creation; no renames'}))
        else:
            omitted.append({'adr_id': doc['id'], 'reason': reason})
    nodes.extend(('Person', person) for person in people.values())
    for doc, successors, references in docs:
        for successor, line, span in successors:
            if successor not in ids:
                unresolved.append({'doc': doc['id'], 'target': successor, 'line': line})
                continue
            if successor == doc['id']:
                raise ValueError('self-supersession in metadata')
            edges.append(('SUPERSEDES', successor, doc['id'], {'path': doc['path'], 'line': line,
                          'span': span, 'authority': 'metadata', 'planted': doc['planted']}))
        for target, line, span in references:
            if target in ids:
                edges.append(('REFERENCES', doc['id'], target, {'path': doc['path'], 'line': line,
                              'span': span, 'authority': 0, 'planted': doc['planted']}))
    rules = parse_codeowners((RAW / CODEOWNERS).read_text(), source_path(RAW / CODEOWNERS))
    owners = {}
    for rule in rules:
        props = {k: v for k, v in rule.items() if k != 'owners'}
        nodes.append(('PathPattern', props))
        for index, handle in enumerate(rule['owners']):
            owner_id = 'owner:' + handle
            owners[owner_id] = {'id': owner_id, 'handle': handle}
            edges.append(('OWNS', rule['id'], owner_id, {'line': rule['line'], 'order': rule['order'],
                          'owner_order': index, 'path': rule['path'], 'span': rule['span']}))
    nodes.extend(('Owner', owner) for owner in owners.values())
    # A supersession cycle must not become a fabricated linear history.
    successors = {}
    for kind, newer, older, _ in edges:
        if kind == 'SUPERSEDES':
            successors.setdefault(older, []).append(newer)
    def visit(node, path):
        if node in path:
            raise ValueError('cyclic metadata supersession')
        for successor in successors.get(node, []):
            visit(successor, path | {node})
    for node in successors:
        visit(node, set())
    manifest = {'source_commit': PIN, 'graph': GRAPH, 'nodes': dict(Counter(t for t, _ in nodes)),
                'edges': dict(Counter(t for t, *_ in edges)), 'authorship': authors,
                'omitted_authorship': omitted, 'unresolved_metadata_targets': unresolved,
                'planted_authorship': 'omitted: synthetic copies have no upstream creation commit',
                'source_files': {d['path']: d['sha256'] for d, _, _ in docs}}
    return nodes, edges, manifest


def load():
    nodes, edges, manifest = build()
    db = FalkorDB(host='127.0.0.1', port=6380)
    # Never clear or reuse an existing graph, including this one.
    if GRAPH in db.list_graphs():
        raise RuntimeError('keystone_real already exists; refusing to overwrite any graph')
    g = db.select_graph(GRAPH)
    for label in sorted({label for label, _ in nodes}):
        rows = [props for kind, props in nodes if kind == label]
        g.query(f'UNWIND $rows AS row CREATE (n:{label}) SET n = row', {'rows': rows})
    for kind in sorted({kind for kind, *_ in edges}):
        rows = [{'src': a, 'dst': b, 'props': props} for t, a, b, props in edges if t == kind]
        g.query(f'UNWIND $rows AS row MATCH (a {{id:row.src}}), (b {{id:row.dst}}) '
                f'CREATE (a)-[e:{kind}]->(b) SET e = row.props', {'rows': rows})
    manifest['database_nodes'] = g.query('MATCH (n) RETURN count(n)').result_set[0][0]
    manifest['database_edges'] = g.query('MATCH ()-[e]->() RETURN count(e)').result_set[0][0]
    assert manifest['database_nodes'] == len(nodes)
    assert manifest['database_edges'] == len(edges)
    (ROOT / 'real/results_load.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(load(), indent=2, ensure_ascii=False))
