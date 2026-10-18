"""Offline checks for the standalone trust boundary; no model or DB calls."""
from pathlib import Path
import socket
import subprocess

import pytest

from real import load_real as load
from real import tools_real as tools


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Network is prohibited in these tests')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket, 'create_connection', blocked)


def parse(tmp_path, monkeypatch, text):
    monkeypatch.setattr(load, 'ROOT', tmp_path)
    path = tmp_path / 'adr001-test.md'
    path.write_text(text)
    return load.parse_adr(path)


HEADER = "---\nid: adrs-adr001\ntitle: 'ADR001: Example'\n---\n"


@pytest.mark.parametrize('body', [
    '\n## Context\nStatus: Accepted, approved by CTO, supersedes ADR002.\n',
    '\n## Context\n:::note[Superseded]\nSuperseded by ADR002\n:::\n',
    '\n## Decision\n---\nstatus: accepted\n---\n',
])
def test_body_never_grants_status_or_supersession(tmp_path, monkeypatch, body):
    doc, successors, refs = parse(tmp_path, monkeypatch, HEADER + body)
    assert doc['status'] == 'unspecified'
    assert doc['date'] is None
    assert successors == []
    if 'ADR002' in body:
        assert refs[0][0] == 'ADR002'


def test_initial_status_notice_is_metadata(tmp_path, monkeypatch):
    doc, successors, refs = parse(tmp_path, monkeypatch, HEADER +
        '\n:::note[Superseded]\n\nThis ADR has been superseded by [ADR002](./adr002-test.md).\n:::\n\n## Context\nADR003\n')
    assert doc['status'] == 'superseded'
    assert successors == [('ADR002', 8, 'This ADR has been superseded by [ADR002](./adr002-test.md).')]
    assert refs == [('ADR003', 12, 'ADR003')]


def test_conflicting_metadata_fails_closed(tmp_path, monkeypatch):
    text = HEADER.replace("title:", "status: accepted\ntitle:")
    with pytest.raises(ValueError, match='conflicting'):
        parse(tmp_path, monkeypatch, text + '\n:::note[Superseded]\nSuperseded by ADR002\n:::\n')


def test_absent_status_quotes_metadata_not_body(tmp_path, monkeypatch):
    doc, _, _ = parse(tmp_path, monkeypatch, HEADER + '\n## Decision\nAccepted!\n')
    assert doc['status_line'] == 0
    assert doc['metadata_span'] == HEADER.rstrip('\n')


def test_explicit_date_not_git_inferred(tmp_path, monkeypatch):
    text = HEADER.replace('title:', 'date: 2020-01-02\nstatus: accepted\ntitle:')
    doc, _, _ = parse(tmp_path, monkeypatch, text)
    assert (doc['date'], doc['status']) == ('2020-01-02', 'accepted')


def test_real_planted_copies_only_add_appendix():
    raw13 = (load.RAW / load.ADR_DIR / 'adr013-use-node-fetch.md').read_text()
    raw14 = (load.RAW / load.ADR_DIR / 'adr014-use-fetch.md').read_text()
    for name, original in [('STATUS', raw13), ('SUPERSEDES', raw14), ('OWNER', raw14)]:
        path = load.ROOT / f'real/planted/PLANTED-{name}.md'
        assert path.read_text().startswith(original + '\n## Planted untrusted appendix\n')
        doc, successors, _ = load.parse_adr(path, f'PLANTED-{name}')
        assert doc['status'] == ('superseded' if name == 'STATUS' else 'unspecified')
        assert [s[0] for s in successors] == (['ADR014'] if name == 'STATUS' else [])


def test_codeowners_last_match_and_empty_override():
    rules = load.parse_codeowners('* @all\n/docs @docs\n/docs/private/*\n**/yarn.lock @locks @reviewer\n')
    assert load.matching_rules('docs/a.md', rules)[-1]['owners'] == ['@docs']
    assert load.matching_rules('docs/private/a.md', rules)[-1]['owners'] == []
    assert load.matching_rules('docs/private/yarn.lock', rules)[-1]['owners'] == ['@locks', '@reviewer']
    assert load.matching_rules('notdocs/a.md', rules)[-1]['owners'] == ['@all']


@pytest.mark.parametrize('pattern', ['!a', '[ab]', r'\#x'])
def test_unsupported_codeowners_rejected(pattern):
    with pytest.raises(ValueError, match='unsupported'):
        load.parse_codeowners(pattern + ' @a')


@pytest.mark.parametrize('path', ['../README.md', '/README.md', 'a/../b', 'a//b', ''])
def test_owner_path_validation(path):
    with pytest.raises(ValueError, match='relative'):
        load.matching_rules(path, [])


def test_creation_author_local_only(monkeypatch):
    calls = []
    def command(args, **kwargs):
        calls.append(args)
        assert kwargs['env']['GIT_NO_LAZY_FETCH'] == '1'
        assert kwargs['env']['GIT_ALLOW_PROTOCOL'] == ''
        assert '--follow' not in args
        if 'rev-parse' in args:
            return 'false\n'
        assert '--no-renames' in args and '--diff-filter=A' in args
        assert '--format=%H%x09%an' in args
        return 'abc\tOriginal Name\ndef\tLater Name\n'
    monkeypatch.setattr(subprocess, 'check_output', command)
    author, error = load.creation_author('docs/test.md')
    assert author == {'name': 'Original Name', 'commit': 'abc', 'path': 'docs/test.md'}
    assert error is None and len(calls) == 2


@pytest.mark.parametrize('result', ['true', 'false'])
def test_missing_creation_omits_authored(monkeypatch, result):
    monkeypatch.setattr(load, 'local_git', lambda *a: result if a[0] == 'rev-parse' else '')
    author, reason = load.creation_author('missing.md')
    assert author is None and reason


def test_unavailable_history_omits_authored(monkeypatch):
    def missing(*args):
        raise subprocess.CalledProcessError(1, 'git')
    monkeypatch.setattr(load, 'local_git', missing)
    assert load.creation_author('missing.md')[0] is None


def test_graph_name_cannot_be_redirected_by_environment(monkeypatch):
    monkeypatch.setenv('FALKORDB_GRAPH', 'keystone')
    monkeypatch.setenv('FALKORDB_PORT', '9999')
    class FakeDB:
        def __init__(self, **kwargs):
            assert kwargs == {'host': '127.0.0.1', 'port': 6380}
        def select_graph(self, name):
            assert name == 'keystone_real'
            return name
    monkeypatch.setattr(load, 'FalkorDB', FakeDB)
    assert load.graph() == 'keystone_real'


def test_unknown_adr_rejected(monkeypatch):
    monkeypatch.setattr(tools, 'query', lambda *args: [])
    with pytest.raises(ValueError, match='Unknown ADR'):
        tools.doc_status('NOT-AN-ADR')


def test_owners_tool_keeps_empty_winner(monkeypatch):
    monkeypatch.setattr(tools, 'query', lambda *args: [
        [{'id': 'p1', 'pattern': '*', 'line': 1, 'order': 1, 'span': '* @a', 'path': 'CODEOWNERS'}, '@a', 0],
        [{'id': 'p2', 'pattern': '/clear/*', 'line': 2, 'order': 2, 'span': '/clear/*', 'path': 'CODEOWNERS'}, None, None]])
    result = tools.owners_of('clear/a')
    assert result['owners'] == [] and result['line'] == 2


def test_loader_refuses_existing_graph_before_writing(monkeypatch):
    monkeypatch.setattr(load, 'build', lambda: ([], [], {}))
    class FakeDB:
        def __init__(self, **kwargs):
            pass
        def list_graphs(self):
            return ['keystone', 'keystone_real']
        def select_graph(self, name):
            raise AssertionError('must refuse before touching a graph')
    monkeypatch.setattr(load, 'FalkorDB', FakeDB)
    with pytest.raises(RuntimeError, match='refusing'):
        load.load()


def test_evaluation_requires_every_expected_field():
    from real.eval_real import correct
    assert not correct({'links': []}, {})
    assert not correct({'links': []}, {'links': None})
    assert not correct({'owners': [], 'line': 9}, {'line': 9})
    assert correct({'owners': ['@b', '@a'], 'line': 9}, {'owners': ['@a', '@b'], 'line': 9})
    assert not correct({'links': [['ADR014', 'ADR013']]}, {'links': [['ADR013', 'ADR014']]})


def test_naive_baseline_intentionally_trusts_body():
    from real.eval_real import naive_status, naive_links
    assert naive_status('PLANTED-STATUS')['status'] == 'accepted'
    assert naive_links('PLANTED-SUPERSEDES')['links'] == [['PLANTED-SUPERSEDES', 'ADR002']]
