import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.store import GraphStore
from app.tools import CONFIG, ToolRuntime, View
from derive import derive, load_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def graph_data():
    nodes, edges, docs = load_data(ROOT / "data")
    statuses = derive(nodes, edges, docs)
    for e in edges:
        e.update(statuses[e["eid"]])
    return nodes, edges, docs


class MemoryStore:
    def __init__(self, data):
        self.nodes, self.edges, self.docs = copy.deepcopy(data)
        self.available = True

    def snapshot(self):
        if not self.available:
            raise ConnectionError("database unavailable")
        docs = [d for d in self.docs if not d.get("restricted")]
        docids = {d["id"] for d in docs}
        nodes = [n for n in self.nodes if n["label"]!="Commit" and not n.get("restricted")]
        ids = {n["id"] for n in nodes}
        edges = [e for e in self.edges if e["src"] in ids and e["dst"] in ids and all(s in docids for s in e["src_ids"])]
        return nodes,edges,docs,False

    def candidate_paths(self, start, target, allowed):
        return [[e["eid"]] for e in self.edges if e["src"]==start and e["dst"]==target and e["status"]=="current"]

    def pagerank(self):
        raise AssertionError("unfiltered native ranking must not run on a filtered projection")


@pytest.fixture
def runtime(graph_data,tmp_path):
    return ToolRuntime(MemoryStore(graph_data),audit_path=tmp_path/'audit.jsonl',action_requested=True)


def claim(edge, recipient='team-payments', target='service-ledger'):
    return {'edge_ids':[edge],'action':{'kind':'ACT','target':target,'recipient':recipient}}


@pytest.mark.parametrize('edge,target,recipient',[
    ('EID-S5-01','service-checkout-api','team-commerce'),
    ('EID-S5B-01','service-checkout-api','team-commerce'),
    ('EID-S8-02','service-ledger','team-commerce'),
    ('EID-S10-01','service-notifier','team-commerce'),
    ('EID-S9A-01','service-telemetry-collector','team-growth'),
])
def test_five_handwritten_attacks(runtime,edge,target,recipient):
    result=runtime.verify_path(claim(edge,recipient,target),target,'ACT')
    assert not result['ok'] and result['outcome']=='ESCALATE' and result['reason']
    assert 'pass_id' not in result
    assert not runtime.propose_action(None,{'kind':'ACT','target':target,'recipient':recipient},True)['ok']


def test_aliases_are_one_person_not_three(runtime):
    result=runtime.verify_path(claim('EID-S9A-01','team-growth','service-telemetry-collector'),'service-telemetry-collector','ACT')
    assert result['confidence']==pytest.approx(0.60)
    assert result['authors']==['person-alex-chen']
    assert result['eligible_confidence']==0  # All three sources are below ACT authority 2.
    assert not result['ok']


def test_current_aliases_still_below_act(runtime):
    result=runtime.verify_path(claim('EID-S9B-01','team-payments','service-billing-worker'),'service-billing-worker','ACT')
    assert result['confidence']==pytest.approx(0.60)
    assert not result['ok']


def test_contested_sides_are_visible_but_not_actionable(runtime):
    result=runtime.rank_owners('notifier')
    assert result['contested'] and result['outcome']=='ESCALATE'
    assert result['owner_teams']==['team-commerce','team-platform']
    assert {e['status'] for e in result['evidence']}=={'contested'}


def test_w2_restricted_evidence_invisible(runtime):
    trace=runtime.trace_decision('INC-8812')
    assert trace['chain']==[] and trace['evidence']==[]
    result=runtime.verify_path({'edge_ids':['EID-S6-01']},'auth-gateway','READ')
    serialized=json.dumps(result)
    assert not result['ok'] and result['failing_edge'] is None
    for forbidden in ('EID-S6','DOC-PM-S6','token leakage','restricted'):
        assert forbidden not in serialized
    missing=runtime.verify_path({'edge_ids':['not-an-edge']},'auth-gateway','READ')
    assert missing==result


def test_pass_dry_run_execute_replay_and_audit(runtime):
    action={'kind':'ACT','target':'service-ledger','recipient':'team-payments'}
    passed=runtime.verify_path(claim('EID-S8-01'),'service-ledger','ACT')
    assert passed['ok']
    dry=runtime.propose_action(passed['pass_id'],action)
    assert dry['dry_run'] and not dry['executed'] and not runtime.audit_path.exists()
    executed=runtime.propose_action(passed['pass_id'],action,True)
    assert executed['executed'] and not executed['delivered']
    replay=runtime.propose_action(passed['pass_id'],action,True)
    assert not replay['ok'] and 'used' in replay['reason']
    rows=[json.loads(l) for l in runtime.audit_path.read_text().splitlines()]
    assert len(rows)==1 and set(rows[0])=={'ts','kind','target','pass_id','dry_run','payload','executed'}


def test_pass_bound_to_target_and_recipient(runtime):
    passed=runtime.verify_path(claim('EID-S8-01'),'ledger','ACT')
    for action in [{'kind':'ACT','target':'service-checkout-api','recipient':'team-payments'},
                   {'kind':'ACT','target':'service-ledger','recipient':'team-commerce'}]:
        result=runtime.propose_action(passed['pass_id'],action,True)
        assert not result['ok'] and 'mismatch' in result['reason']


def test_expiry(runtime):
    clock=[0.0];runtime.clock=lambda:clock[0]
    passed=runtime.verify_path(claim('EID-S8-01'),'ledger','ACT')
    clock[0]=301
    assert runtime.propose_action(passed['pass_id'],passed['action'],True)['reason']=='pass expired'


def test_read_pass_cannot_execute(runtime):
    result=runtime.verify_path({'edge_ids':['EID-S8-01']},'ledger','READ')
    assert result['ok'] and result['outcome']=='ANSWER_ONLY'
    action={'kind':'ACT','target':'service-ledger','recipient':'team-payments'}
    assert not runtime.propose_action(result['pass_id'],action,True)['ok']


def test_execute_without_pass_rejected(runtime):
    assert not runtime.propose_action(None,{'kind':'ACT','target':'service-ledger','recipient':'team-payments'},True)['ok']


def test_only_fixed_contact_can_page_without_pass(runtime):
    assert not runtime.propose_action(None,{'kind':'PAGE','target':'some-other-contact'},True)['ok']
    result=runtime.propose_action(None,{'kind':'PAGE','target':CONFIG['fixed_contact']},True)
    assert result['ok'] and result['outcome']=='ESCALATE'
    assert json.loads(runtime.audit_path.read_text())['kind']=='PAGE'


def test_backend_rechecks_after_pass(runtime):
    passed=runtime.verify_path(claim('EID-S8-01'),'ledger','ACT')
    next(e for e in runtime.store.edges if e['eid']=='EID-S8-01')['status']='unverified'
    assert not runtime.propose_action(passed['pass_id'],passed['action'],True)['ok']
    assert not runtime.audit_path.exists()


def test_backend_does_not_trust_spoofed_current_status(runtime):
    next(e for e in runtime.store.edges if e['eid']=='EID-S5-01')['status']='current'
    result=runtime.verify_path(claim('EID-S5-01','team-commerce','service-checkout-api'),'checkout-api','ACT')
    assert not result['ok']


def test_no_database_no_authorization(runtime):
    runtime.store.available=False
    with pytest.raises(ConnectionError):
        runtime.verify_path(claim('EID-S8-01'),'ledger','ACT')


def test_source_text_or_model_claim_cannot_authorize(runtime):
    forged=claim('EID-S5B-01','team-commerce','service-checkout-api')
    forged['approved']=True
    result=runtime.verify_path(forged,'checkout-api','ACT')
    assert not result['ok'] and result['reason']=='invalid claim or purpose'
    assert not runtime.propose_action('model-says-approved',forged['action'],True)['ok']


def test_citation_must_be_verbatim(runtime):
    next(e for e in runtime.store.edges if e['eid']=='EID-S8-01')['spans']=['NOT A SOURCE QUOTE']
    result=runtime.verify_path(claim('EID-S8-01'),'ledger','ACT')
    assert not result['ok'] and 'verbatim' in result['reason']


def test_connected_path_and_bound_budget(runtime):
    c={'edge_ids':['EID-S8-01','EID-S2-02']}
    assert 'connected' in runtime.verify_path(c,'checkout-api','READ')['reason']
    assert not runtime.verify_path({'edge_ids':['EID-S8-01']*9},'ledger','ACT')['ok']


def test_page_rank_projection_and_order(runtime):
    result=runtime.criticality(['api-hub-service','batch-exporter-service'])
    assert result['algorithm']=='authorized_current_projection'
    assert result['escalation_order']==['service-api-hub','service-batch-exporter']
    assert all(r['severity']=='unconfigured' for r in result['services'])


def test_minimum_depth_no_duplicate_services(runtime):
    result=runtime.blast_radius('redis-cluster')
    ids=[r['service'] for r in result['affected_services']]
    assert len(ids)==len(set(ids))==result['count']
    assert 'service-redis-cluster' not in ids
    assert next(r for r in result['affected_services'] if r['service']=='service-session-cache')['min_depth']==1
    assert all(e['status']=='current' for e in result['evidence'])


def test_parameterized_query_no_agent_cypher():
    calls=[]
    class Graph:
        def query(self,q,p):
            calls.append((q,p));return SimpleNamespace(result_set=[])
    malicious="x'}) MATCH (n) DETACH DELETE n //"
    GraphStore(Graph()).candidate_paths(malicious,'safe',[])
    assert malicious not in calls[0][0] and calls[0][1]['start']==malicious
    assert 'SET ' not in calls[0][0] and 'DELETE' not in calls[0][0]


def test_acl_metadata_precedes_content_and_span_queries():
    calls=[]
    class Graph:
        def query(self,q,p):
            calls.append((q,p))
            if 'n.restricted' in q:
                rows=[[1,'s','Service',False],[2,'i','Incident',False],[3,'secret','Doc',True]] if p['cursor']==-1 else []
            elif 'properties(n)' in q:
                assert 3 not in p['ids']
                rows=[[{'id':'s','name':'s'},'Service'],[{'id':'i'},'Incident']]
            elif 'e.src_ids' in q:
                rows=[[4,'hidden-edge','CAUSED_BY','i','s',['secret'],[1.0],[3],'2024-01-01',None,'current']] if p['cursor']==-1 else []
            else:
                assert p['ids']==[];rows=[]
            return SimpleNamespace(result_set=rows)
    nodes,edges,docs,_=GraphStore(Graph()).snapshot()
    assert not edges and not docs
    assert 'n.restricted' in calls[0][0]


def test_step_budget_is_backend_enforced(runtime):
    for _ in range(CONFIG['max_steps']):
        assert runtime.propose_action(None,{'kind':'PAGE','target':CONFIG['fixed_contact']})['ok']
    with pytest.raises(ValueError,match='max_steps'):
        runtime.propose_action(None,{'kind':'PAGE','target':CONFIG['fixed_contact']})


def test_query_path_uses_authorized_edge_allowlist(runtime):
    captured=[]
    original=runtime.store.candidate_paths
    def spy(start,target,allowed):
        captured.extend(allowed)
        return original(start,target,allowed)
    runtime.store.candidate_paths=spy
    result=runtime.verify_path({'start':'team-payments'},'ledger','ACT')
    assert result['ok']
    assert 'EID-S6-01' not in captured and 'EID-S5-01' not in captured


def test_model_cannot_create_trusted_action_context(runtime):
    runtime.action_requested=False
    result=runtime.verify_path(claim('EID-S8-01'),'ledger','ACT')
    assert not result['ok'] and 'trusted user' in result['reason']
    assert 'pass_id' not in result


def test_path_confidence_is_product(runtime):
    next(e for e in runtime.store.edges if e['eid']=='EID-S8-01')['src_conf']=[0.8]
    next(e for e in runtime.store.edges if e['eid']=='EID-M2-04')['src_conf']=[0.8]
    result=runtime.verify_path({'edge_ids':['EID-S8-01','EID-M2-04']},'payment-vault','READ')
    assert result['ok'] and result['confidence']==pytest.approx(0.64)
    assert result['authority']==2


def test_distinct_people_noisy_or(runtime):
    original=next(d for d in runtime.store.docs if d['id']=='DOC-ADR-LEDGER')
    extra={**original,'id':'DOC-SECOND-PAYMENTS','author_id':'person-staff-2','author_email':'fatima.zahra@company.internal','author_handle':'fzahra'}
    runtime.store.docs.append(extra)
    edge=next(e for e in runtime.store.edges if e['eid']=='EID-S8-01')
    edge['src_conf']=[0.6,0.6]
    edge['src_auth']=[3,3]
    edge['src_ids'].append(extra['id'])
    result=runtime.verify_path(claim('EID-S8-01'),'ledger','ACT')
    assert result['ok'] and result['confidence']==pytest.approx(0.84)
    assert result['authors']==['person-dev-patel','person-staff-2']


def test_plain_functions_return_json_and_mask_driver_details(runtime,monkeypatch):
    import app.tools as tools
    runtime.store.available=False
    monkeypatch.setattr(tools,'_runtime',runtime)
    result=tools.blast_radius('ledger')
    assert result['ok'] is False and result['outcome']=='ESCALATE'
    assert result['reason']=='tool unavailable or request rejected'


def test_severity_uses_configured_pagerank_cutoff(runtime):
    runtime.config['pagerank_severity_cutoff']=0.01
    result=runtime.criticality(['api-hub-service','batch-exporter-service'])
    severity={row['service']:row['severity'] for row in result['services']}
    assert severity=={'service-api-hub':'elevated','service-batch-exporter':'normal'}


def test_unverified_approval_cannot_support_current_transfer(runtime):
    next(e for e in runtime.store.edges if e['eid']=='EID-S2-03')['status']='unverified'
    result=runtime.verify_path(claim('EID-S2-02','team-commerce','service-checkout-api'),'checkout-api','ACT')
    assert not result['ok'] and 'pass_id' not in result
