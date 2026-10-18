"""Tool-level preregistered evaluation; intentionally text-trusting naive baseline."""
from contextlib import redirect_stderr
from datetime import datetime, timezone
import hashlib
import io
import json
import re
import subprocess

from real import tools_real
from real.load_real import ADR_DIR, RAW, ROOT, PIN, CODEOWNERS, adr_refs, local_git, matching_rules, parse_codeowners


def file_for(adr_id):
    if re.fullmatch(r'PLANTED-(STATUS|SUPERSEDES|OWNER)', adr_id):
        return ROOT / f'real/planted/{adr_id}.md'
    if not re.fullmatch(r'ADR\d{3}', adr_id):
        raise ValueError('invalid ADR id')
    paths = list((RAW / ADR_DIR).glob(adr_id.lower() + '-*.md'))
    if len(paths) != 1:
        raise ValueError('unknown ADR')
    return paths[0]


def naive_status(adr_id):
    status = 'unspecified'
    for line in file_for(adr_id).read_text().splitlines():
        match = re.search(r'(?i)(?:^Status:\s*|\[)(accepted|proposed|superseded|deprecated|rejected)\b', line)
        if match:
            status = match[1].lower()
    return {'status': status}


def naive_links(adr_id):
    files = [(f'ADR{n:03d}', file_for(f'ADR{n:03d}')) for n in range(1, 16)]
    if adr_id.startswith('PLANTED-'):
        files.append((adr_id, file_for(adr_id)))
    edges = set()
    for current, path in files:
        for line in path.read_text().splitlines():
            newer = re.search(r'\bsuperseded by\s+\[?(ADR[- ]?\d+)', line, re.I)
            older = re.search(r'\bsupersedes\s+\[?(ADR[- ]?\d+)', line, re.I)
            if newer:
                edges.add((adr_refs(newer[1])[0], current))
            if older:
                edges.add((current, adr_refs(older[1])[0]))
    selected, frontier = set(), {adr_id}
    while frontier:
        following = set()
        for a, b in edges - selected:
            if a in frontier or b in frontier:
                selected.add((a, b))
                following.update((a, b))
        frontier = following
    return {'links': [list(pair) for pair in sorted(selected)]}


def naive(case):
    if case['tool'] == 'doc_status':
        return naive_status(case['args']['adr_id'])
    if case['tool'] == 'trace_decision':
        return naive_links(case['args']['adr_id'])
    rules = parse_codeowners((RAW / CODEOWNERS).read_text())
    if case.get('context_adr'):
        for number, line in enumerate(file_for(case['context_adr']).read_text().splitlines(), 1):
            if re.fullmatch(r'\S+\s+(?:@[\w/-]+\s*)+', line):
                added = parse_codeowners(line)[0]
                rules.append({**added, 'order': 10000 + number, 'line': number})
    matches = matching_rules(case['args']['path'], rules)
    winner = matches[-1] if matches else {'owners': [], 'line': None}
    return {key: winner[key] for key in ['owners', 'line']}


def correct(expected, actual):
    for key, value in expected.items():
        if key not in actual:
            return False
        observed = actual.get(key)
        if key in {'owners', 'links'}:
            if not isinstance(observed, list) or sorted(value) != sorted(observed):
                return False
        elif value != observed:
            return False
    return True


def check_spans(result):
    citations = result.get('evidence', [])[:]
    if 'span' in result:
        citations.append(result)
    if 'document' in result:
        citations.append(result['document'])
    for item in citations:
        path = ROOT / item.get('source_path', item.get('path', ''))
        lines = path.read_text().splitlines()
        start, end = item['line'], item.get('end_line', item['line'])
        if '\n'.join(lines[start - 1:end]) != item['span']:
            raise AssertionError(f'non-verbatim or mislocated citation: {path}:{start}')


def main():
    cases_path = ROOT / 'real/cases_real.jsonl'
    if local_git('rev-parse', 'HEAD') != PIN or local_git(
            'status', '--porcelain', '--untracked-files=no', '--', ADR_DIR, CODEOWNERS):
        raise ValueError('source checkout differs from the pinned ADRs/CODEOWNERS')
    # Prove gold was committed, rather than trusting a report timestamp.
    tag = subprocess.check_output(['git', 'rev-parse', 'real-v1'], cwd=ROOT, text=True).strip()
    for path in ['real/cases_real.jsonl', 'real/SOURCE.md', 'real/CHECK.md',
                 'real/planted/PLANTED-STATUS.md', 'real/planted/PLANTED-SUPERSEDES.md',
                 'real/planted/PLANTED-OWNER.md']:
        committed = subprocess.check_output(['git', 'show', f'real-v1:{path}'], cwd=ROOT)
        if committed != (ROOT / path).read_bytes():
            raise ValueError(f'pre-run gold/protocol changed after real-v1: {path}')
    load_result = json.loads((ROOT / 'real/results_load.json').read_text())
    for path, digest in load_result['source_files'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('source changed since import: ' + path)
    cases = [json.loads(line) for line in cases_path.read_text().splitlines()]
    assert len(cases) == len({c['id'] for c in cases}) == 10
    started = datetime.now(timezone.utc).isoformat()
    rows, cypher_log = [], io.StringIO()
    for system in ['metadata_tools', 'naive_text']:
        for case in cases:
            try:
                with redirect_stderr(cypher_log):
                    actual = (getattr(tools_real, case['tool'])(**case['args'])
                              if system == 'metadata_tools' else naive(case))
                if system == 'metadata_tools':
                    check_spans(actual)
                passed, error = correct(case['expected'], actual), None
            except Exception as exc:
                actual, passed, error = None, False, f'{type(exc).__name__}: {exc}'
            rows.append({'system': system, 'case': case['id'], 'type': case['type'],
                         'planted': case['planted'], 'expected': case['expected'],
                         'actual': actual, 'correct': passed, 'error': error})
    counts = []
    for system in ['metadata_tools', 'naive_text']:
        for kind in ['owner', 'decision', 'planted', 'all']:
            selected = [r for r in rows if r['system'] == system and (kind == 'all' or r['type'] == kind)]
            counts.append({'system': system, 'type': kind, 'correct': sum(r['correct'] for r in selected),
                           'n': len(selected), 'errors': sum(bool(r['error']) for r in selected)})
    result = {'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
              'source_commit': PIN, 'gold_tag': 'real-v1', 'gold_commit': tag,
              'gold_sha256': hashlib.sha256(cases_path.read_bytes()).hexdigest(),
              'counts': counts, 'runs': rows, 'load': load_result}
    (ROOT / 'real/results.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (ROOT / 'real/results_cypher.log').write_text(cypher_log.getvalue())
    report = '# Real-data proof of concept results\n\n'
    report += f'Source: Backstage `{PIN}`; pre-run gold: `real-v1` (`{tag}`).\n\n'
    report += '| System | Owner | Decision | Planted | Total | Tool errors |\n| --- | --- | --- | --- | --- | --- |\n'
    for system in ['metadata_tools', 'naive_text']:
        subset = [c for c in counts if c['system'] == system]
        report += '| ' + system + ' | ' + ' | '.join(f"{c['correct']}/{c['n']}" for c in subset) + f" | {subset[-1]['errors']} |\n"
    report += '\n## Case results\n\n| Case | Type | Metadata tools | Naive text |\n| --- | --- | --- | --- |\n'
    for case in cases:
        cells = [('correct' if r['correct'] else r['error'] or 'wrong') for r in rows if r['case'] == case['id']]
        report += f"| {case['id']} | {case['type']} | {' | '.join(cells)} |\n"
    report += '''
## Scope and limitations

This is additional post-freeze **tool-level** evidence, not the Keystone LLM agent loop or the frozen evaluation. Gold was hand-labeled by an AI agent from raw files; the author still needs to spot-check [CHECK.md](CHECK.md). N=10 is small, only one real supersession pair is present, and all three planted attacks are synthetic by construction. The intentionally vulnerable naive comparator trusts text anywhere; it is not B1/B2 and does not isolate graph storage as the cause of a result. This test checks a metadata boundary, not whether upstream claims or human identities are true.

The metadata boundary includes the initial explicit Backstage status notice. No explicit Accepted status or date exists for the other ADRs; unspecified/null is retained. Person nodes contain creation-commit names for current paths only, with no emails, rename following, identity verification, or authenticated approval. CODEOWNERS handles and actual team permissions are not remotely validated. No external calls other than git clone, no LLM, no API keys, and no changes to existing graphs or frozen assets. The raw clone is ignored. [SOURCE.md](SOURCE.md) fixes the protocol; [results.json](results.json) contains complete tool outputs and import provenance; [results_cypher.log](results_cypher.log) contains the executed queries.
'''
    report += '\n## Graph and provenance\n\n'
    report += f"Nodes: {load_result['database_nodes']}; edges: {load_result['database_edges']}.\n\n"
    report += f"Node types: `{json.dumps(load_result['nodes'], sort_keys=True)}`. Edge types: `{json.dumps(load_result['edges'], sort_keys=True)}`.\n\n"
    report += f"Unverifiable original AUTHORED records omitted: {len(load_result['omitted_authorship'])}/15. Synthetic copies have no AUTHORED edges. Unresolved metadata targets: {len(load_result['unresolved_metadata_targets'])}.\n"
    (ROOT / 'real/results.md').write_text(report)
    print(json.dumps(counts, indent=2))
    if any(r['error'] for r in rows):
        raise SystemExit('Tool errors recorded; see real/results.json')


if __name__ == '__main__':
    main()
