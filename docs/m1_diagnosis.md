# M1 diagnosis

Diagnosis only; no gate, tool, data, case, or grading changes. The original K/M1 journal row and trace are retained.

The immediate failure is a wrong target argument. The claim edge ID is correct: EID-CATALOG-OWNS-15 is current and connects team-platform to service-redis-cluster. The agent supplied target `alert-redis-cluster`, which is neither a node ID nor a unique node name. `View.find` returns None, and `_verify` returns `no available evidence` before it examines the selected path. The target should have been `service-redis-cluster` or `redis-cluster`. The explicit edge_ids claim does not invoke the candidate-path query.

Read-only live checks confirm the direct current path `[EID-CATALOG-OWNS-15]` is returned by candidate_paths(team-platform, service-redis-cluster). Therefore the recorded error does not mean the current ownership path is absent.

There is a second, independent authorization limitation. Rechecking the same claim with target redis-cluster reaches the current ownership edge but returns `insufficient standing author authority or confidence`, confidence=0, eligible_confidence=0, authority=0, authors=[]. Its sole DOC-CATALOG source has author_id=null, author_handle=system, author_email=system@company.internal. The current measures code only counts resolved people with standing; this source contributes no eligible author. Correcting the model target alone would not make this catalog-only claim pass ACT. No fix is applied here.

The blind reference expects ACT, nearest owning team team-platform, and the catalog owner edge as evidence. This expectation differs from the present author-confidence check on catalog-only evidence. rank_owners also returns no on-call and an ESCALATE recommendation. criticality was not called. The subsequent fixed-contact page is the automatic fallback, not a verified assignment.

## Every tool call after blast_radius

### rank_owners

Arguments:

```json
{
  "service": "redis-cluster"
}
```

Result:

```json
{
  "owner_teams": [
    "team-platform"
  ],
  "contested": false,
  "on_call": [],
  "outcome": "ESCALATE",
  "escalation_path": [
    "keystone-fixed-contact"
  ],
  "evidence": [
    {
      "eid": "EID-CATALOG-OWNS-15",
      "type": "OWNS",
      "src": "team-platform",
      "dst": "service-redis-cluster",
      "status": "current",
      "valid_from": "2023-01-01T00:00:00Z",
      "valid_to": null,
      "spans": [
        "Catalog Record: Service redis-cluster is officially registered under team platform. Designated primary on-call engineer handle is mlin."
      ],
      "sources": [
        {
          "doc_id": "DOC-CATALOG",
          "author_id": null,
          "author_handle": "system",
          "author_email": "system@company.internal",
          "date": "2023-01-01T00:00:00Z",
          "spans": [
            "Catalog Record: Service redis-cluster is officially registered under team platform. Designated primary on-call engineer handle is mlin."
          ]
        }
      ]
    }
  ]
}
```

### verify_path

Arguments:

```json
{
  "claim": {
    "edge_ids": [
      "EID-CATALOG-OWNS-15"
    ]
  },
  "purpose": "ACT",
  "target": "alert-redis-cluster"
}
```

Result:

```json
{
  "ok": false,
  "outcome": "ESCALATE",
  "reason": "no available evidence",
  "failing_edge": null,
  "evidence": []
}
```

### propose_action

Arguments:

```json
{
  "pass_id": null,
  "action": {
    "kind": "PAGE",
    "target": "keystone-fixed-contact"
  },
  "execute": true
}
```

Result:

```json
{
  "ok": true,
  "outcome": "ESCALATE",
  "target": "keystone-fixed-contact",
  "dry_run": false,
  "payload": {
    "kind": "PAGE",
    "target": "keystone-fixed-contact",
    "evidence_edge_ids": [],
    "severity": "unconfigured"
  },
  "executed": true,
  "delivered": false,
  "execution_mode": "audit_only",
  "evidence": []
}
```

This call was the agent’s automatic fixed-contact fallback.

## Exact blind reference

```json
{
  "input": {
    "type": "alert",
    "service": "redis-cluster",
    "text": "Alert: redis-cluster is failing. Identify all transitively affected services and assign this alert to the nearest owning team."
  },
  "gold_answer": {
    "facts": [
      "The failing service is redis-cluster; its direct, nearest owner is team platform, documented by EID-CATALOG-OWNS-15 in DOC-CATALOG.",
      "Illustrative 3-hop dependency chain: web-frontend -> api-gateway -> session-cache -> redis-cluster.",
      "Exactly 9 other services can reach the failing service by one or more DEPENDS_ON edges; affected_services is the complete set across the supplied graph.",
      "Assign the alert to team platform; do not invent an individual paging recipient."
    ],
    "affected_services": [
      "api-gateway",
      "batch-exporter-service",
      "notification-dispatcher",
      "push-relay",
      "rate-limiter",
      "session-cache",
      "sms-gateway",
      "video-streamer",
      "web-frontend"
    ],
    "owner_team": "platform",
    "cite_edge_ids": [
      "EID-CATALOG-OWNS-15",
      "EID-BG-00060",
      "EID-BG-00087",
      "EID-BG-00099",
      "EID-BG-00115",
      "EID-BG-00135",
      "EID-BG-00146",
      "EID-BG-00160",
      "EID-M1-01",
      "EID-M1-02",
      "EID-M1-03"
    ],
    "cite_doc_ids": [
      "DOC-CATALOG",
      "DOC-RUNBOOK-M1"
    ],
    "cite_spans": [
      "Catalog Record: Service redis-cluster is officially registered under team platform. Designated primary on-call engineer handle is mlin.",
      "Service web-frontend depends on api-gateway.",
      "Service api-gateway depends on session-cache.",
      "Service session-cache depends on redis-cluster."
    ],
    "forbidden_claims": [
      "The failing service redis-cluster itself belongs in affected_services.",
      "Only the services in the illustrative curated chain are affected.",
      "Downstream dependencies of the failing service are affected merely because the failing service depends on them.",
      "All reachable services are confirmed to be down.",
      "The current individual on-call recipient has been verified from the catalog alone."
    ]
  },
  "gold_outcome": "ACT",
  "gold_tools": [
    "blast_radius",
    "criticality",
    "rank_owners",
    "verify_path",
    "propose_action"
  ]
}
```

Source locations: agent.py run_agent; app/tools.py View.find, View.measures and ToolRuntime._verify; app/store.py GraphStore.candidate_paths. The live checks used only snapshot/candidate_paths/_verify (no propose_action or audit writes).
