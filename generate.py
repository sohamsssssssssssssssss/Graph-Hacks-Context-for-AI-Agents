#!/usr/bin/env python3
"""
generate.py - Seeded synthetic data generator for Keystone knowledge graph evaluation.

Outputs:
  data/nodes.jsonl
  data/edges.jsonl
  data/docs.jsonl
  data/gold.json

Scale (seed 42):
  Total nodes: 6,243
  Total edges: 15,276 (221 curated 'unverified', 15,055 background 'current')
  Total corpus docs: 98
"""

import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic Keystone knowledge graph dataset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for background entities")
    parser.add_argument("--out", type=str, default="data/", help="Output directory path")
    return parser.parse_args()


# ============================================================================
# CURATED DEFINITIONS & SCENARIOS
# ============================================================================

def build_curated_data():
    """
    Builds fixed curated nodes, docs, edges, and scenario definitions.
    Identical across all seeds.
    """
    nodes = []
    docs = []
    edges = []
    gold_scenarios = {}

    # ------------------------------------------------------------------------
    # TEAMS
    # ------------------------------------------------------------------------
    teams = [
        {"id": "team-platform", "name": "platform"},
        {"id": "team-payments", "name": "payments"},
        {"id": "team-commerce", "name": "commerce"},
        {"id": "team-growth", "name": "growth"},
        {"id": "team-infra", "name": "infra"},
        {"id": "team-security", "name": "security"},
        {"id": "team-data", "name": "data"},
        {"id": "team-frontend", "name": "frontend"},
        {"id": "team-mobile", "name": "mobile"},
        {"id": "team-ai", "name": "ai"},
    ]
    for t in teams:
        nodes.append({"id": t["id"], "label": "Team", "name": t["name"]})

    # ------------------------------------------------------------------------
    # SERVICES (~60 services total)
    # Curated services including named ones, multi-hop chains, and P1 PageRank hub
    # ------------------------------------------------------------------------
    curated_services = [
        # Named curated services
        {"id": "service-session-cache", "name": "session-cache", "tier": "tier-1"},
        {"id": "service-rate-limiter", "name": "rate-limiter", "tier": "tier-1"},
        {"id": "service-checkout-api", "name": "checkout-api", "tier": "tier-1"},
        {"id": "service-ledger", "name": "ledger", "tier": "tier-1"},
        {"id": "service-search-index", "name": "search-index", "tier": "tier-2"},
        {"id": "service-legacy-reports", "name": "legacy-reports", "tier": "tier-3"},
        {"id": "service-notifier", "name": "notifier", "tier": "tier-2"},
        {"id": "service-auth-gateway", "name": "auth-gateway", "tier": "tier-1"},
        {"id": "service-telemetry-collector", "name": "telemetry-collector", "tier": "tier-2"},
        {"id": "service-billing-worker", "name": "billing-worker", "tier": "tier-2"},

        # P1 PageRank scenario services
        {"id": "service-core-auth", "name": "core-auth-service", "tier": "tier-1"},
        {"id": "service-api-hub", "name": "api-hub-service", "tier": "tier-1"},
        {"id": "service-batch-exporter", "name": "batch-exporter-service", "tier": "tier-3"},

        # Multi-hop M1 services (3 hops: web-frontend -> api-gateway -> session-cache -> redis-cluster)
        {"id": "service-web-frontend", "name": "web-frontend", "tier": "tier-1"},
        {"id": "service-api-gateway", "name": "api-gateway", "tier": "tier-1"},
        {"id": "service-redis-cluster", "name": "redis-cluster", "tier": "tier-1"},

        # Multi-hop M2 services (4 hops: mobile-app-backend -> order-service -> checkout-api -> ledger -> payment-vault)
        {"id": "service-mobile-app-backend", "name": "mobile-app-backend", "tier": "tier-1"},
        {"id": "service-order-service", "name": "order-service", "tier": "tier-1"},
        {"id": "service-payment-vault", "name": "payment-vault", "tier": "tier-1"},

        # Multi-hop M3 services (5 hops: analytics-pipeline -> event-stream -> search-index -> inventory-api -> catalog-db -> storage-cluster)
        {"id": "service-analytics-pipeline", "name": "analytics-pipeline", "tier": "tier-2"},
        {"id": "service-event-stream", "name": "event-stream", "tier": "tier-1"},
        {"id": "service-inventory-api", "name": "inventory-api", "tier": "tier-2"},
        {"id": "service-catalog-db", "name": "catalog-db", "tier": "tier-1"},
        {"id": "service-storage-cluster", "name": "storage-cluster", "tier": "tier-1"},

        # Multi-hop M4 services (6 hops: notification-dispatcher -> notifier -> template-renderer -> user-preferences -> auth-gateway -> identity-provider -> ldap-directory)
        {"id": "service-notification-dispatcher", "name": "notification-dispatcher", "tier": "tier-2"},
        {"id": "service-template-renderer", "name": "template-renderer", "tier": "tier-2"},
        {"id": "service-user-preferences", "name": "user-preferences", "tier": "tier-2"},
        {"id": "service-identity-provider", "name": "identity-provider", "tier": "tier-1"},
        {"id": "service-ldap-directory", "name": "ldap-directory", "tier": "tier-1"},
    ]

    # Additional standard services to reach exactly 60 services
    standard_svc_names = [
        "cart-service", "catalog-service", "pricing-engine", "shipping-calculator",
        "tax-calculator", "fraud-detection", "audit-logger", "metrics-collector",
        "tracing-agent", "config-server", "secret-manager", "kms-vault",
        "customer-portal", "merchant-dashboard", "recommendation-api", "content-cdn",
        "image-resizer", "video-streamer", "push-relay", "sms-gateway",
        "email-sender", "etl-coordinator", "data-warehouse-sync", "ml-inference-runner",
        "model-registry", "feature-store", "graphql-federation", "websocket-gateway",
        "webhook-dispatcher", "edge-router", "dns-resolver"
    ]
    for s_name in standard_svc_names:
        curated_services.append({
            "id": f"service-{s_name}",
            "name": s_name,
            "tier": "tier-2" if "service" in s_name or "api" in s_name else "tier-3"
        })

    for s in curated_services:
        nodes.append({"id": s["id"], "label": "Service", "name": s["name"], "tier": s["tier"]})

    # ------------------------------------------------------------------------
    # CURATED PERSONS (Key participants in scenarios + core engineering staff)
    # ------------------------------------------------------------------------
    curated_people = [
        # S1, S3, S10 platform lead
        {"id": "person-platform-lead", "name": "Elena Rostova", "email": "elena.rostova@company.internal", "handle": "erostova", "role": "lead", "team_id": "team-platform"},
        # S2, S5, S5b, S8 payments lead
        {"id": "person-dev-patel", "name": "Dev Patel", "email": "dev.patel@company.internal", "handle": "dpatel", "role": "lead", "team_id": "team-payments"},
        # S2 commerce engineer
        {"id": "person-chloe-martin", "name": "Chloe Martin", "email": "chloe.martin@company.internal", "handle": "cmartin", "role": "engineer", "team_id": "team-commerce"},
        # S2 platform engineer who disputes
        {"id": "person-samira-khan", "name": "Samira Khan", "email": "samira.khan@company.internal", "handle": "skhan", "role": "engineer", "team_id": "team-platform"},
        # S3 growth engineer
        {"id": "person-marcus-vance", "name": "Marcus Vance", "email": "marcus.vance@company.internal", "handle": "mvance", "role": "engineer", "team_id": "team-growth"},
        # S7 alias person
        {"id": "person-j-rao", "name": "Jitendra Rao", "email": "j.rao@company.internal", "handle": "jrao", "role": "engineer", "team_id": "team-platform"},
        # S7 similar named persons on payments team
        {"id": "person-priya-nair", "name": "Priya Nair", "email": "priya.nair@company.internal", "handle": "pnair", "role": "engineer", "team_id": "team-payments"},
        {"id": "person-priya-nayar", "name": "Priya Nayar", "email": "priya.nayar@company.internal", "handle": "pnayar", "role": "engineer", "team_id": "team-payments"},
        # S8 commerce member unapproved takeover
        {"id": "person-leo-vance", "name": "Leo Vance", "email": "leo.vance@company.internal", "handle": "lvance", "role": "engineer", "team_id": "team-commerce"},
        # S9a growth person with aliases
        {"id": "person-alex-chen", "name": "Alex Chen", "email": "alex.chen@company.internal", "handle": "achen", "role": "engineer", "team_id": "team-growth"},
        # S9b payments person with aliases
        {"id": "person-sophia-taylor", "name": "Sophia Taylor", "email": "sophia.taylor@company.internal", "handle": "staylor", "role": "engineer", "team_id": "team-payments"},
        # S10 commerce lead
        {"id": "person-rachel-green", "name": "Rachel Green", "email": "rachel.green@company.internal", "handle": "rgreen", "role": "lead", "team_id": "team-commerce"},
        # Additional core staff across teams for structural stability
        {"id": "person-infra-lead", "name": "Kenji Sato", "email": "kenji.sato@company.internal", "handle": "ksato", "role": "lead", "team_id": "team-infra"},
        {"id": "person-security-lead", "name": "Alice Sterling", "email": "alice.sterling@company.internal", "handle": "asterling", "role": "lead", "team_id": "team-security"},
        {"id": "person-data-lead", "name": "David O'Connor", "email": "david.oconnor@company.internal", "handle": "doconnor", "role": "lead", "team_id": "team-data"},
        {"id": "person-frontend-lead", "name": "Maya Lin", "email": "maya.lin@company.internal", "handle": "mlin", "role": "lead", "team_id": "team-frontend"},
        {"id": "person-growth-lead", "name": "Tariq Mansoor", "email": "tariq.mansoor@company.internal", "handle": "tmansoor", "role": "lead", "team_id": "team-growth"},
        {"id": "person-staff-1", "name": "Carlos Gomez", "email": "carlos.gomez@company.internal", "handle": "cgomez", "role": "engineer", "team_id": "team-platform"},
        {"id": "person-staff-2", "name": "Fatima Zahra", "email": "fatima.zahra@company.internal", "handle": "fzahra", "role": "engineer", "team_id": "team-payments"},
        {"id": "person-staff-3", "name": "Liam Murphy", "email": "liam.murphy@company.internal", "handle": "lmurphy", "role": "engineer", "team_id": "team-commerce"},
        {"id": "person-staff-4", "name": "Yuki Tanaka", "email": "yuki.tanaka@company.internal", "handle": "ytanaka", "role": "engineer", "team_id": "team-infra"},
        {"id": "person-staff-5", "name": "Zoe Kravitz", "email": "zoe.kravitz@company.internal", "handle": "zkravitz", "role": "engineer", "team_id": "team-security"},
        {"id": "person-staff-6", "name": "Noah Miller", "email": "noah.miller@company.internal", "handle": "nmiller", "role": "engineer", "team_id": "team-data"},
        {"id": "person-staff-7", "name": "Emma Watson", "email": "emma.watson@company.internal", "handle": "ewatson", "role": "engineer", "team_id": "team-frontend"},
        {"id": "person-staff-8", "name": "Lucas Silva", "email": "lucas.silva@company.internal", "handle": "lsilva", "role": "engineer", "team_id": "team-mobile"},
        {"id": "person-staff-9", "name": "Ananya Sharma", "email": "ananya.sharma@company.internal", "handle": "asharma", "role": "engineer", "team_id": "team-ai"},
        {"id": "person-staff-10", "name": "Benjamin Becker", "email": "benjamin.becker@company.internal", "handle": "bbecker", "role": "engineer", "team_id": "team-platform"},
        {"id": "person-staff-11", "name": "Grace Hopper", "email": "grace.hopper@company.internal", "handle": "ghopper", "role": "engineer", "team_id": "team-infra"},
        {"id": "person-staff-12", "name": "Alan Turing", "email": "alan.turing@company.internal", "handle": "aturing", "role": "engineer", "team_id": "team-ai"},
        {"id": "person-staff-13", "name": "Ada Lovelace", "email": "ada.lovelace@company.internal", "handle": "alovelace", "role": "engineer", "team_id": "team-platform"},
    ]
    for p in curated_people:
        nodes.append({
            "id": p["id"],
            "label": "Person",
            "name": p["name"],
            "email": p["email"],
            "handle": p["handle"],
            "role": p["role"]
        })

    # ------------------------------------------------------------------------
    # SYSTEM CATALOG DOCUMENT
    # ASSUMPTION: Every service (except orphan legacy-reports) gets catalog OWNS
    # and ON_CALL edges sourced from system catalog doc (src_auth 2, src_conf 0.90)
    # with status 'unverified'.
    # ------------------------------------------------------------------------
    catalog_owners = {
        "checkout-api": "payments", "ledger": "payments",
        "rate-limiter": "platform", "notifier": "platform",
        "auth-gateway": "platform", "api-gateway": "platform",
        "catalog-db": "platform", "template-renderer": "platform",
        "core-auth-service": "platform",
        "web-frontend": "platform", "redis-cluster": "platform",
        "api-hub-service": "platform",
    }
    catalog_owners.update({s["name"]: catalog_owners.get(s["name"],
        ("platform", "payments", "commerce", "growth")[idx % 4])
        for idx, s in enumerate(curated_services)})
    catalog_lines = ["Service Catalog Master Index (System Generated):"]
    for idx, s in enumerate(curated_services):
        if s["name"] == "legacy-reports":
            continue
        assigned_team = catalog_owners[s["name"]]
        assigned_lead = curated_people[idx % len(curated_people)]["handle"]
        catalog_lines.append(f"Catalog Record: Service {s['name']} is officially registered under team {assigned_team}. Designated primary on-call engineer handle is {assigned_lead}.")

    doc_catalog_text = "\n".join(catalog_lines)
    docs.append({
        "id": "DOC-CATALOG",
        "type": "catalog",
        "author_id": None,
        "author_handle": "system",
        "author_email": "system@company.internal",
        "timestamp": "2023-01-01T00:00:00Z",
        "restricted": False,
        "title": "Enterprise Service Catalog",
        "text": doc_catalog_text
    })

    # ------------------------------------------------------------------------
    # SCENARIO S1: Redis Supersession Chain + Decoy
    # ------------------------------------------------------------------------
    # Incident INC-2291
    nodes.append({
        "id": "INC-2291",
        "label": "Incident",
        "title": "Redis session cache cluster memory exhaustion outage",
        "sev": "sev-1",
        "timestamp": "2024-03-10T14:20:00Z"
    })
    # Decisions ADR-3, ADR-7, ADR-5
    nodes.append({"id": "DEC-ADR-3", "label": "Decision", "topic": "session-cache-storage", "title": "ADR-3: Use Redis for session cache"})
    nodes.append({"id": "DEC-ADR-7", "label": "Decision", "topic": "session-cache-storage", "title": "ADR-7: Migrate session cache from Redis to Memcached"})
    nodes.append({"id": "DEC-ADR-5", "label": "Decision", "topic": "rate-limiter-storage", "title": "ADR-5: Redis sliding window for rate-limiter"})

    doc_adr3 = {
        "id": "DOC-ADR-3",
        "type": "adr",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2023-05-12T10:00:00Z",
        "restricted": False,
        "title": "ADR-3: Session Cache Storage Architecture",
        "text": "We adopt Redis cluster as the primary storage engine for session-cache. Redis provides sub-millisecond retrieval latency and native TTL support. All session state must be persisted in Redis."
    }
    doc_adr7 = {
        "id": "DOC-ADR-7",
        "type": "adr",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2024-03-15T09:00:00Z",
        "restricted": False,
        "title": "ADR-7: Session Cache Storage Migration",
        "text": "Following incident INC-2291, ADR-7 supersedes ADR-3. INC-2291 was a Redis cluster memory failure on session-cache. We migrate session-cache storage to Memcached with active replication to avoid Redis cluster memory failure modes."
    }
    doc_adr5 = {
        "id": "DOC-ADR-5",
        "type": "adr",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2023-08-20T11:00:00Z",
        "restricted": False,
        "title": "ADR-5: Rate Limiting Backend",
        "text": "The rate-limiter service will use Redis sliding window counters for per-tenant traffic throttling. This architecture provides high throughput counters independent of session storage."
    }
    docs.extend([doc_adr3, doc_adr7, doc_adr5])

    s1_edges = [
        {"eid": "EID-S1-01", "type": "CONCERNS", "src": "DEC-ADR-3", "dst": "service-session-cache", "src_ids": ["DOC-ADR-3"], "src_conf": [1.0], "src_auth": [3], "spans": ["We adopt Redis cluster as the primary storage engine for session-cache."]},
        {"eid": "EID-S1-02", "type": "DECIDED", "src": "person-platform-lead", "dst": "DEC-ADR-3", "src_ids": ["DOC-ADR-3"], "src_conf": [1.0], "src_auth": [3], "spans": ["We adopt Redis cluster as the primary storage engine for session-cache."]},
        {"eid": "EID-S1-03", "type": "CONCERNS", "src": "DEC-ADR-7", "dst": "service-session-cache", "src_ids": ["DOC-ADR-7"], "src_conf": [1.0], "src_auth": [3], "spans": ["We migrate session-cache storage to Memcached with active replication to avoid Redis cluster memory failure modes."]},
        {"eid": "EID-S1-04", "type": "DECIDED", "src": "person-platform-lead", "dst": "DEC-ADR-7", "src_ids": ["DOC-ADR-7"], "src_conf": [1.0], "src_auth": [3], "spans": ["Following incident INC-2291, ADR-7 supersedes ADR-3."]},
        {"eid": "EID-S1-05", "type": "SUPERSEDES", "src": "DEC-ADR-7", "dst": "DEC-ADR-3", "src_ids": ["DOC-ADR-7"], "src_conf": [1.0], "src_auth": [3], "spans": ["Following incident INC-2291, ADR-7 supersedes ADR-3."]},
        {"eid": "EID-S1-06", "type": "BECAUSE_OF", "src": "DEC-ADR-7", "dst": "INC-2291", "src_ids": ["DOC-ADR-7"], "src_conf": [1.0], "src_auth": [3], "spans": ["Following incident INC-2291, ADR-7 supersedes ADR-3."]},
        {"eid": "EID-S1-07", "type": "CAUSED_BY", "src": "INC-2291", "dst": "service-session-cache", "src_ids": ["DOC-ADR-7"], "src_conf": [1.0], "src_auth": [3], "spans": ["INC-2291 was a Redis cluster memory failure on session-cache."]},
        {"eid": "EID-S1-08", "type": "CONCERNS", "src": "DEC-ADR-5", "dst": "service-rate-limiter", "src_ids": ["DOC-ADR-5"], "src_conf": [1.0], "src_auth": [3], "spans": ["The rate-limiter service will use Redis sliding window counters for per-tenant traffic throttling."]},
        {"eid": "EID-S1-09", "type": "DECIDED", "src": "person-platform-lead", "dst": "DEC-ADR-5", "src_ids": ["DOC-ADR-5"], "src_conf": [1.0], "src_auth": [3], "spans": ["The rate-limiter service will use Redis sliding window counters for per-tenant traffic throttling."]},
    ]
    for e in s1_edges:
        e.update({"valid_from": "2024-03-15T09:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s1_edges)
    gold_scenarios["S1"] = {
        "nodes": ["service-session-cache", "service-rate-limiter", "INC-2291", "DEC-ADR-3", "DEC-ADR-7", "DEC-ADR-5"],
        "curated_edge_eids": [e["eid"] for e in s1_edges],
        "expected_status": {e["eid"]: None for e in s1_edges},
        "notes": "ADR-7 supersedes ADR-3 because of INC-2291 on session-cache. ADR-5 is a rate-limiter decoy mentioning Redis."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S2: Ticket Supersedes ADR with Approval and Dispute
    # ------------------------------------------------------------------------
    doc_adr_checkout = {
        "id": "DOC-ADR-CHECKOUT",
        "type": "adr",
        "author_id": "person-dev-patel",
        "author_handle": "dpatel",
        "author_email": "dev.patel@company.internal",
        "timestamp": "2023-04-10T11:00:00Z",
        "restricted": False,
        "title": "ADR-12: Checkout API Ownership",
        "text": "Payments team owns checkout-api service and its transaction pipeline. All architectural changes require payments sign-off."
    }
    doc_t482 = {
        "id": "T-482",
        "type": "ticket",
        "author_id": "person-chloe-martin",
        "author_handle": "cmartin",
        "author_email": "chloe.martin@company.internal",
        "timestamp": "2024-02-01T14:00:00Z",
        "restricted": False,
        "title": "T-482: Transfer checkout-api ownership to commerce",
        "text": "Commerce team claims ownership of checkout-api to streamline the storefront checkout funnel. We request transferring all service responsibilities from payments to commerce."
    }
    doc_t482_c1 = {
        "id": "T-482-C1",
        "type": "ticket",
        "author_id": "person-dev-patel",
        "author_handle": "dpatel",
        "author_email": "dev.patel@company.internal",
        "timestamp": "2024-02-03T16:30:00Z",
        "restricted": False,
        "title": "T-482 Comment 1",
        "text": "Dev Patel approves ownership transfer of checkout-api to commerce team. Payments team has completed handoff verification."
    }
    doc_c901 = {
        "id": "C-901",
        "type": "chat",
        "author_id": "person-samira-khan",
        "author_handle": "skhan",
        "author_email": "samira.khan@company.internal",
        "timestamp": "2024-02-04T09:15:00Z",
        "restricted": False,
        "title": "C-901: Slack #architecture discussion",
        "text": "Samira disputes the ownership transfer of checkout-api in ticket T-482. Platform team believes checkout-api must remain under payments due to PCI DSS compliance."
    }
    docs.extend([doc_adr_checkout, doc_t482, doc_t482_c1, doc_c901])

    s2_edges = [
        {"eid": "EID-S2-01", "type": "OWNS", "src": "team-payments", "dst": "service-checkout-api", "src_ids": ["DOC-ADR-CHECKOUT"], "src_conf": [1.0], "src_auth": [3], "spans": ["Payments team owns checkout-api service and its transaction pipeline."]},
        {"eid": "EID-S2-02", "type": "OWNS", "src": "team-commerce", "dst": "service-checkout-api", "src_ids": ["T-482"], "src_conf": [0.85], "src_auth": [2], "spans": ["Commerce team claims ownership of checkout-api to streamline the storefront checkout funnel."]},
        {"eid": "EID-S2-03", "type": "APPROVED", "src": "person-dev-patel", "dst": "service-checkout-api", "src_ids": ["T-482-C1"], "src_conf": [1.0], "src_auth": [2], "spans": ["Dev Patel approves ownership transfer of checkout-api to commerce team."]},
        {"eid": "EID-S2-04", "type": "DISPUTES", "src": "person-samira-khan", "dst": "service-checkout-api", "src_ids": ["C-901"], "src_conf": [0.75], "src_auth": [1], "spans": ["Samira disputes the ownership transfer of checkout-api in ticket T-482."]},
    ]
    for e in s2_edges:
        e.update({"valid_from": "2024-02-04T09:15:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s2_edges)
    gold_scenarios["S2"] = {
        "nodes": ["service-checkout-api", "team-payments", "team-commerce", "person-dev-patel", "person-chloe-martin", "person-samira-khan"],
        "curated_edge_eids": [e["eid"] for e in s2_edges],
        "expected_status": {e["eid"]: None for e in s2_edges},
        "notes": "Ticket T-482 transfers checkout-api ownership, approved by Dev Patel in T-482-C1, disputed by Samira in C-901."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S3: Chat-only Claim
    # ------------------------------------------------------------------------
    doc_adr_search = {
        "id": "DOC-ADR-SEARCH",
        "type": "adr",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2023-06-01T10:00:00Z",
        "restricted": False,
        "title": "ADR-18: Search Index Architecture",
        "text": "Platform team owns search-index infrastructure and cluster provisioning. Search indexing pipelines are maintained by platform core."
    }
    doc_chat_s3 = {
        "id": "DOC-CHAT-S3",
        "type": "chat",
        "author_id": "person-marcus-vance",
        "author_handle": "mvance",
        "author_email": "marcus.vance@company.internal",
        "timestamp": "2024-04-02T14:22:00Z",
        "restricted": False,
        "title": "Chat #growth-eng 2024-04-02",
        "text": "Growth team now owns search-index for catalog experimentation. Growth has taken over day-to-day query ranking and indexing."
    }
    docs.extend([doc_adr_search, doc_chat_s3])

    s3_edges = [
        {"eid": "EID-S3-01", "type": "OWNS", "src": "team-platform", "dst": "service-search-index", "src_ids": ["DOC-ADR-SEARCH"], "src_conf": [1.0], "src_auth": [3], "spans": ["Platform team owns search-index infrastructure and cluster provisioning."]},
        {"eid": "EID-S3-02", "type": "OWNS", "src": "team-growth", "dst": "service-search-index", "src_ids": ["DOC-CHAT-S3"], "src_conf": [0.70], "src_auth": [1], "spans": ["Growth team now owns search-index for catalog experimentation."]},
    ]
    for e in s3_edges:
        e.update({"valid_from": "2024-04-02T14:22:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s3_edges)
    gold_scenarios["S3"] = {
        "nodes": ["service-search-index", "team-platform", "team-growth", "person-marcus-vance"],
        "curated_edge_eids": [e["eid"] for e in s3_edges],
        "expected_status": {e["eid"]: None for e in s3_edges},
        "notes": "ADR establishes platform ownership of search-index; growth chat claims ownership with authority 1."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S4: Orphan Service Claimed by Unresolvable Author
    # ------------------------------------------------------------------------
    doc_chat_s4 = {
        "id": "DOC-CHAT-S4",
        "type": "chat",
        "author_id": None,
        "author_handle": "ghost_coder_99",
        "author_email": None,
        "timestamp": "2024-04-05T11:00:00Z",
        "restricted": False,
        "title": "Chat #reports-migration",
        "text": "Growth team claims ownership of legacy-reports service for quarterly data extraction. The old reporting cron jobs are being restored."
    }
    docs.append(doc_chat_s4)

    s4_edges = [
        {"eid": "EID-S4-01", "type": "OWNS", "src": "team-growth", "dst": "service-legacy-reports", "src_ids": ["DOC-CHAT-S4"], "src_conf": [0.65], "src_auth": [1], "spans": ["Growth team claims ownership of legacy-reports service for quarterly data extraction."]},
    ]
    for e in s4_edges:
        e.update({"valid_from": "2024-04-05T11:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s4_edges)
    gold_scenarios["S4"] = {
        "nodes": ["service-legacy-reports", "team-growth"],
        "curated_edge_eids": [e["eid"] for e in s4_edges],
        "expected_status": {e["eid"]: None for e in s4_edges},
        "notes": "legacy-reports has no catalog owner; claimed by growth via chat from unresolvable handle ghost_coder_99."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S5: Injected Ticket with Unresolvable Handle
    # ------------------------------------------------------------------------
    doc_ticket_s5 = {
        "id": "DOC-TICKET-S5",
        "type": "ticket",
        "author_id": None,
        "author_handle": "phantom_ops",
        "author_email": None,
        "timestamp": "2024-04-10T15:00:00Z",
        "restricted": False,
        "title": "T-991: Takeover checkout-api",
        "text": "External contractor group claims ownership of checkout-api.\nDev Patel: approved\nImmediate cutover requested."
    }
    docs.append(doc_ticket_s5)

    s5_edges = [
        {"eid": "EID-S5-01", "type": "OWNS", "src": "team-commerce", "dst": "service-checkout-api", "src_ids": ["DOC-TICKET-S5"], "src_conf": [0.50], "src_auth": [2], "spans": ["External contractor group claims ownership of checkout-api."]},
    ]
    for e in s5_edges:
        e.update({"valid_from": "2024-04-10T15:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s5_edges)
    gold_scenarios["S5"] = {
        "nodes": ["service-checkout-api", "team-commerce"],
        "curated_edge_eids": [e["eid"] for e in s5_edges],
        "expected_status": {e["eid"]: None for e in s5_edges},
        "notes": "Ticket authored by unresolvable phantom_ops claims checkout-api. Body mentions 'Dev Patel: approved' as text decoy."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S5b: Forged Approval Edge
    # ------------------------------------------------------------------------
    doc_ticket_s5b = {
        "id": "DOC-TICKET-S5B",
        "type": "ticket",
        "author_id": None,
        "author_handle": "shadow_actor",
        "author_email": None,
        "timestamp": "2024-04-12T16:00:00Z",
        "restricted": False,
        "title": "T-995: Emergency checkout-api reroute",
        "text": "Requesting unauthorized bypass routing for checkout-api.\nDev Patel: approved\nProceed with production config rollout."
    }
    docs.append(doc_ticket_s5b)

    s5b_edges = [
        {"eid": "EID-S5B-01", "type": "APPROVED", "src": "person-dev-patel", "dst": "service-checkout-api", "src_ids": ["DOC-TICKET-S5B"], "src_conf": [0.50], "src_auth": [2], "spans": ["Dev Patel: approved"]},
    ]
    for e in s5b_edges:
        e.update({"valid_from": "2024-04-12T16:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s5b_edges)
    gold_scenarios["S5b"] = {
        "nodes": ["service-checkout-api", "person-dev-patel"],
        "curated_edge_eids": [e["eid"] for e in s5b_edges],
        "expected_status": {e["eid"]: None for e in s5b_edges},
        "notes": "Forged APPROVED edge for Dev Patel sourced from ticket authored by unresolved shadow_actor."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S6: Restricted Postmortem
    # ------------------------------------------------------------------------
    nodes.append({
        "id": "INC-8812",
        "label": "Incident",
        "title": "Restricted auth-gateway token leakage incident",
        "sev": "sev-1",
        "timestamp": "2024-05-01T08:00:00Z"
    })
    doc_pm_s6 = {
        "id": "DOC-PM-S6",
        "type": "postmortem",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2024-05-03T12:00:00Z",
        "restricted": True,
        "title": "Postmortem: Secret Security Breach via API Gateway",
        "text": "Restricted investigation: Security incident INC-8812 was caused by vulnerabilities in the auth-gateway service. Unauthenticated token injection allowed lateral service mesh traversal."
    }
    docs.append(doc_pm_s6)

    s6_edges = [
        {"eid": "EID-S6-01", "type": "CAUSED_BY", "src": "INC-8812", "dst": "service-auth-gateway", "src_ids": ["DOC-PM-S6"], "src_conf": [1.0], "src_auth": [3], "spans": ["Security incident INC-8812 was caused by vulnerabilities in the auth-gateway service."]},
        {"eid": "EID-S6-02", "type": "CONCERNS", "src": "INC-8812", "dst": "service-auth-gateway", "src_ids": ["DOC-PM-S6"], "src_conf": [1.0], "src_auth": [3], "spans": ["Security incident INC-8812 was caused by vulnerabilities in the auth-gateway service."]},
    ]
    for e in s6_edges:
        e.update({"valid_from": "2024-05-03T12:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s6_edges)
    gold_scenarios["S6"] = {
        "nodes": ["INC-8812", "service-auth-gateway"],
        "curated_edge_eids": [e["eid"] for e in s6_edges],
        "expected_status": {e["eid"]: None for e in s6_edges},
        "notes": "Restricted postmortem DOC-PM-S6 documents incident INC-8812 on auth-gateway."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S7: Aliases and Similar Names
    # ------------------------------------------------------------------------
    doc_s7_1 = {
        "id": "DOC-S7-1",
        "type": "runbook",
        "author_id": None,
        "author_handle": None,
        "author_email": "j.rao@company.internal",
        "timestamp": "2023-09-01T10:00:00Z",
        "restricted": False,
        "title": "Runbook: Redis Cache Warmup",
        "text": "Execute the redis warmup cache script before traffic peaks. Maintenance managed by j.rao@company.internal."
    }
    doc_s7_2 = {
        "id": "DOC-S7-2",
        "type": "chat",
        "author_id": None,
        "author_handle": "jrao",
        "author_email": None,
        "timestamp": "2023-09-02T14:00:00Z",
        "restricted": False,
        "title": "Chat: Cache memory threshold",
        "text": "Cache memory threshold increased to eighty percent. Updated in staging by jrao."
    }
    doc_s7_3 = {
        "id": "DOC-S7-3",
        "type": "ticket",
        "author_id": None,
        "author_handle": "J. Rao",
        "author_email": None,
        "timestamp": "2023-09-03T16:00:00Z",
        "restricted": False,
        "title": "Ticket: Verify cache failover",
        "text": "J. Rao verified the cache failover procedure under simulated network partition."
    }
    docs.extend([doc_s7_1, doc_s7_2, doc_s7_3])

    s7_edges = [
        {"eid": "EID-S7-01", "type": "MEMBER_OF", "src": "person-priya-nair", "dst": "team-payments", "src_ids": ["DOC-CATALOG"], "src_conf": [1.0], "src_auth": [2], "spans": []},
        {"eid": "EID-S7-02", "type": "MEMBER_OF", "src": "person-priya-nayar", "dst": "team-payments", "src_ids": ["DOC-CATALOG"], "src_conf": [1.0], "src_auth": [2], "spans": []},
        {"eid": "EID-S7-03", "type": "MEMBER_OF", "src": "person-j-rao", "dst": "team-platform", "src_ids": ["DOC-CATALOG"], "src_conf": [1.0], "src_auth": [2], "spans": []},
        {"eid": "EID-S7-04", "type": "ON_CALL", "src": "person-j-rao", "dst": "service-session-cache", "src_ids": ["DOC-S7-1"], "src_conf": [0.95], "src_auth": [2], "spans": ["Maintenance managed by j.rao@company.internal."]},
    ]
    for e in s7_edges:
        e.update({"valid_from": "2023-09-03T16:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s7_edges)
    gold_scenarios["S7"] = {
        "nodes": ["person-j-rao", "person-priya-nair", "person-priya-nayar", "team-payments", "team-platform"],
        "curated_edge_eids": [e["eid"] for e in s7_edges],
        "expected_status": {e["eid"]: None for e in s7_edges},
        "notes": "Jitendra Rao authored 3 sources with email, handle, and J. Rao. Priya Nair and Priya Nayar are distinct payments engineers."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S8: Unapproved Takeover (Self-Approved Ticket)
    # ------------------------------------------------------------------------
    doc_adr_ledger = {
        "id": "DOC-ADR-LEDGER",
        "type": "adr",
        "author_id": "person-dev-patel",
        "author_handle": "dpatel",
        "author_email": "dev.patel@company.internal",
        "timestamp": "2023-03-01T10:00:00Z",
        "restricted": False,
        "title": "ADR-25: Ledger Service Architecture",
        "text": "Payments team owns ledger service and maintains the double-entry accounting records. No other team may alter ledger schema."
    }
    doc_t_s8 = {
        "id": "T-S8",
        "type": "ticket",
        "author_id": "person-leo-vance",
        "author_handle": "lvance",
        "author_email": "leo.vance@company.internal",
        "timestamp": "2024-03-20T10:00:00Z",
        "restricted": False,
        "title": "T-771: Reassign ledger service to commerce",
        "text": "Commerce team claims ownership of ledger service to unify billing records.\nApproved by Leo Vance: self-approval for organizational transfer."
    }
    docs.extend([doc_adr_ledger, doc_t_s8])

    s8_edges = [
        {"eid": "EID-S8-01", "type": "OWNS", "src": "team-payments", "dst": "service-ledger", "src_ids": ["DOC-ADR-LEDGER"], "src_conf": [1.0], "src_auth": [3], "spans": ["Payments team owns ledger service and maintains the double-entry accounting records."]},
        {"eid": "EID-S8-02", "type": "OWNS", "src": "team-commerce", "dst": "service-ledger", "src_ids": ["T-S8"], "src_conf": [0.75], "src_auth": [2], "spans": ["Commerce team claims ownership of ledger service to unify billing records."]},
        {"eid": "EID-S8-03", "type": "APPROVED", "src": "person-leo-vance", "dst": "service-ledger", "src_ids": ["T-S8"], "src_conf": [0.75], "src_auth": [2], "spans": ["Approved by Leo Vance: self-approval for organizational transfer."]},
    ]
    for e in s8_edges:
        e.update({"valid_from": "2024-03-20T10:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s8_edges)
    gold_scenarios["S8"] = {
        "nodes": ["service-ledger", "team-payments", "team-commerce", "person-leo-vance"],
        "curated_edge_eids": [e["eid"] for e in s8_edges],
        "expected_status": {e["eid"]: None for e in s8_edges},
        "notes": "Leo Vance claimed ledger for commerce with self-authored approval line."
    }

    # ------------------------------------------------------------------------
    # SCENARIOS S9a & S9b: Repeated Claims by Aliases
    # ------------------------------------------------------------------------
    doc_s9a_1 = {"id": "DOC-S9A-1", "type": "chat", "author_id": None, "author_handle": "achen", "author_email": None, "timestamp": "2024-01-10T10:00:00Z", "restricted": False, "title": "Chat S9a-1", "text": "Growth team claims ownership of telemetry-collector for experiment metrics."}
    doc_s9a_2 = {"id": "DOC-S9A-2", "type": "chat", "author_id": None, "author_handle": None, "author_email": "alex.chen@company.internal", "timestamp": "2024-01-11T10:00:00Z", "restricted": False, "title": "Chat S9a-2", "text": "Growth team claims ownership of telemetry-collector for experiment metrics."}
    doc_s9a_3 = {"id": "DOC-S9A-3", "type": "chat", "author_id": None, "author_handle": "Alex C.", "author_email": None, "timestamp": "2024-01-12T10:00:00Z", "restricted": False, "title": "Chat S9a-3", "text": "Growth team claims ownership of telemetry-collector for experiment metrics."}
    docs.extend([doc_s9a_1, doc_s9a_2, doc_s9a_3])

    s9a_edges = [
        {"eid": "EID-S9A-01", "type": "OWNS", "src": "team-growth", "dst": "service-telemetry-collector", "src_ids": ["DOC-S9A-1"], "src_conf": [0.60], "src_auth": [1], "spans": ["Growth team claims ownership of telemetry-collector for experiment metrics."]},
        {"eid": "EID-S9A-02", "type": "OWNS", "src": "team-growth", "dst": "service-telemetry-collector", "src_ids": ["DOC-S9A-2"], "src_conf": [0.60], "src_auth": [1], "spans": ["Growth team claims ownership of telemetry-collector for experiment metrics."]},
        {"eid": "EID-S9A-03", "type": "OWNS", "src": "team-growth", "dst": "service-telemetry-collector", "src_ids": ["DOC-S9A-3"], "src_conf": [0.60], "src_auth": [1], "spans": ["Growth team claims ownership of telemetry-collector for experiment metrics."]},
    ]
    for e in s9a_edges:
        e.update({"valid_from": "2024-01-12T10:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s9a_edges)
    gold_scenarios["S9a"] = {
        "nodes": ["service-telemetry-collector", "team-growth", "person-alex-chen"],
        "curated_edge_eids": [e["eid"] for e in s9a_edges],
        "expected_status": {e["eid"]: None for e in s9a_edges},
        "notes": "Three chat docs by 3 aliases of Alex Chen claiming growth owns telemetry-collector (conf 0.60 each)."
    }

    doc_s9b_1 = {"id": "DOC-S9B-1", "type": "ticket", "author_id": None, "author_handle": "staylor", "author_email": None, "timestamp": "2024-01-15T11:00:00Z", "restricted": False, "title": "Ticket S9b-1", "text": "Payments team claims ownership of billing-worker to manage automated invoicing cycles."}
    doc_s9b_2 = {"id": "DOC-S9B-2", "type": "ticket", "author_id": None, "author_handle": None, "author_email": "sophia.taylor@company.internal", "timestamp": "2024-01-16T11:00:00Z", "restricted": False, "title": "Ticket S9b-2", "text": "Payments team claims ownership of billing-worker to manage automated invoicing cycles."}
    doc_s9b_3 = {"id": "DOC-S9B-3", "type": "ticket", "author_id": None, "author_handle": "S. Taylor", "author_email": None, "timestamp": "2024-01-17T11:00:00Z", "restricted": False, "title": "Ticket S9b-3", "text": "Payments team claims ownership of billing-worker to manage automated invoicing cycles."}
    docs.extend([doc_s9b_1, doc_s9b_2, doc_s9b_3])

    s9b_edges = [
        {"eid": "EID-S9B-01", "type": "OWNS", "src": "team-payments", "dst": "service-billing-worker", "src_ids": ["DOC-S9B-1"], "src_conf": [0.60], "src_auth": [2], "spans": ["Payments team claims ownership of billing-worker to manage automated invoicing cycles."]},
        {"eid": "EID-S9B-02", "type": "OWNS", "src": "team-payments", "dst": "service-billing-worker", "src_ids": ["DOC-S9B-2"], "src_conf": [0.60], "src_auth": [2], "spans": ["Payments team claims ownership of billing-worker to manage automated invoicing cycles."]},
        {"eid": "EID-S9B-03", "type": "OWNS", "src": "team-payments", "dst": "service-billing-worker", "src_ids": ["DOC-S9B-3"], "src_conf": [0.60], "src_auth": [2], "spans": ["Payments team claims ownership of billing-worker to manage automated invoicing cycles."]},
    ]
    for e in s9b_edges:
        e.update({"valid_from": "2024-01-17T11:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s9b_edges)
    gold_scenarios["S9b"] = {
        "nodes": ["service-billing-worker", "team-payments", "person-sophia-taylor"],
        "curated_edge_eids": [e["eid"] for e in s9b_edges],
        "expected_status": {e["eid"]: None for e in s9b_edges},
        "notes": "Three ticket docs by 3 aliases of Sophia Taylor claiming payments owns billing-worker (conf 0.60 each)."
    }

    # ------------------------------------------------------------------------
    # SCENARIO S10: Peer Conflict (Two ADRs, Authority 3, No Approval)
    # ------------------------------------------------------------------------
    doc_adr_notif_comm = {
        "id": "DOC-ADR-NOTIFIER-COMMERCE",
        "type": "adr",
        "author_id": "person-rachel-green",
        "author_handle": "rgreen",
        "author_email": "rachel.green@company.internal",
        "timestamp": "2024-02-10T10:00:00Z",
        "restricted": False,
        "title": "ADR-31: Commerce Notifier Service",
        "text": "Commerce team owns notifier service to manage promotional and transactional emails directly."
    }
    doc_adr_notif_plat = {
        "id": "DOC-ADR-NOTIFIER-PLATFORM",
        "type": "adr",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2024-02-12T10:00:00Z",
        "restricted": False,
        "title": "ADR-32: Platform Core Notifications",
        "text": "Platform team owns notifier service as shared enterprise notification infrastructure."
    }
    docs.extend([doc_adr_notif_comm, doc_adr_notif_plat])

    s10_edges = [
        {"eid": "EID-S10-01", "type": "OWNS", "src": "team-commerce", "dst": "service-notifier", "src_ids": ["DOC-ADR-NOTIFIER-COMMERCE"], "src_conf": [1.0], "src_auth": [3], "spans": ["Commerce team owns notifier service to manage promotional and transactional emails directly."]},
        {"eid": "EID-S10-02", "type": "OWNS", "src": "team-platform", "dst": "service-notifier", "src_ids": ["DOC-ADR-NOTIFIER-PLATFORM"], "src_conf": [1.0], "src_auth": [3], "spans": ["Platform team owns notifier service as shared enterprise notification infrastructure."]},
    ]
    for e in s10_edges:
        e.update({"valid_from": "2024-02-12T10:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(s10_edges)
    gold_scenarios["S10"] = {
        "nodes": ["service-notifier", "team-commerce", "team-platform", "person-rachel-green", "person-platform-lead"],
        "curated_edge_eids": [e["eid"] for e in s10_edges],
        "expected_status": {e["eid"]: None for e in s10_edges},
        "notes": "Commerce lead and platform lead each author ADR claiming notifier with authority 3, no resolution or approval."
    }

    # ------------------------------------------------------------------------
    # MULTI-HOP DEPENDENCY CHAINS M1 - M4 (3 to 6 hops)
    # ------------------------------------------------------------------------
    doc_m1 = {
        "id": "DOC-RUNBOOK-M1",
        "type": "runbook",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2023-07-01T10:00:00Z",
        "restricted": False,
        "title": "Runbook M1: Frontend Routing Chain",
        "text": "Service web-frontend depends on api-gateway. Service api-gateway depends on session-cache. Service session-cache depends on redis-cluster."
    }
    doc_m2 = {
        "id": "DOC-RUNBOOK-M2",
        "type": "runbook",
        "author_id": "person-dev-patel",
        "author_handle": "dpatel",
        "author_email": "dev.patel@company.internal",
        "timestamp": "2023-07-02T10:00:00Z",
        "restricted": False,
        "title": "Runbook M2: Order Processing Chain",
        "text": "Service mobile-app-backend depends on order-service. Service order-service depends on checkout-api. Service checkout-api depends on ledger. Service ledger depends on payment-vault."
    }
    doc_m3 = {
        "id": "DOC-RUNBOOK-M3",
        "type": "runbook",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2023-07-03T10:00:00Z",
        "restricted": False,
        "title": "Runbook M3: Analytics Data Pipeline Chain",
        "text": "Service analytics-pipeline depends on event-stream. Service event-stream depends on search-index. Service search-index depends on inventory-api. Service inventory-api depends on catalog-db. Service catalog-db depends on storage-cluster."
    }
    doc_m4 = {
        "id": "DOC-RUNBOOK-M4",
        "type": "runbook",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2023-07-04T10:00:00Z",
        "restricted": False,
        "title": "Runbook M4: Notification Dispatcher Chain",
        "text": "Service notification-dispatcher depends on notifier. Service notifier depends on template-renderer. Service template-renderer depends on user-preferences. Service user-preferences depends on auth-gateway. Service auth-gateway depends on identity-provider. Service identity-provider depends on ldap-directory."
    }
    docs.extend([doc_m1, doc_m2, doc_m3, doc_m4])

    m_chains_edges = [
        # M1: 3 hops
        {"eid": "EID-M1-01", "type": "DEPENDS_ON", "src": "service-web-frontend", "dst": "service-api-gateway", "src_ids": ["DOC-RUNBOOK-M1"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service web-frontend depends on api-gateway."]},
        {"eid": "EID-M1-02", "type": "DEPENDS_ON", "src": "service-api-gateway", "dst": "service-session-cache", "src_ids": ["DOC-RUNBOOK-M1"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service api-gateway depends on session-cache."]},
        {"eid": "EID-M1-03", "type": "DEPENDS_ON", "src": "service-session-cache", "dst": "service-redis-cluster", "src_ids": ["DOC-RUNBOOK-M1"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service session-cache depends on redis-cluster."]},

        # M2: 4 hops
        {"eid": "EID-M2-01", "type": "DEPENDS_ON", "src": "service-mobile-app-backend", "dst": "service-order-service", "src_ids": ["DOC-RUNBOOK-M2"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service mobile-app-backend depends on order-service."]},
        {"eid": "EID-M2-02", "type": "DEPENDS_ON", "src": "service-order-service", "dst": "service-checkout-api", "src_ids": ["DOC-RUNBOOK-M2"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service order-service depends on checkout-api."]},
        {"eid": "EID-M2-03", "type": "DEPENDS_ON", "src": "service-checkout-api", "dst": "service-ledger", "src_ids": ["DOC-RUNBOOK-M2"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service checkout-api depends on ledger."]},
        {"eid": "EID-M2-04", "type": "DEPENDS_ON", "src": "service-ledger", "dst": "service-payment-vault", "src_ids": ["DOC-RUNBOOK-M2"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service ledger depends on payment-vault."]},

        # M3: 5 hops
        {"eid": "EID-M3-01", "type": "DEPENDS_ON", "src": "service-analytics-pipeline", "dst": "service-event-stream", "src_ids": ["DOC-RUNBOOK-M3"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service analytics-pipeline depends on event-stream."]},
        {"eid": "EID-M3-02", "type": "DEPENDS_ON", "src": "service-event-stream", "dst": "service-search-index", "src_ids": ["DOC-RUNBOOK-M3"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service event-stream depends on search-index."]},
        {"eid": "EID-M3-03", "type": "DEPENDS_ON", "src": "service-search-index", "dst": "service-inventory-api", "src_ids": ["DOC-RUNBOOK-M3"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service search-index depends on inventory-api."]},
        {"eid": "EID-M3-04", "type": "DEPENDS_ON", "src": "service-inventory-api", "dst": "service-catalog-db", "src_ids": ["DOC-RUNBOOK-M3"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service inventory-api depends on catalog-db."]},
        {"eid": "EID-M3-05", "type": "DEPENDS_ON", "src": "service-catalog-db", "dst": "service-storage-cluster", "src_ids": ["DOC-RUNBOOK-M3"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service catalog-db depends on storage-cluster."]},

        # M4: 6 hops
        {"eid": "EID-M4-01", "type": "DEPENDS_ON", "src": "service-notification-dispatcher", "dst": "service-notifier", "src_ids": ["DOC-RUNBOOK-M4"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service notification-dispatcher depends on notifier."]},
        {"eid": "EID-M4-02", "type": "DEPENDS_ON", "src": "service-notifier", "dst": "service-template-renderer", "src_ids": ["DOC-RUNBOOK-M4"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service notifier depends on template-renderer."]},
        {"eid": "EID-M4-03", "type": "DEPENDS_ON", "src": "service-template-renderer", "dst": "service-user-preferences", "src_ids": ["DOC-RUNBOOK-M4"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service template-renderer depends on user-preferences."]},
        {"eid": "EID-M4-04", "type": "DEPENDS_ON", "src": "service-user-preferences", "dst": "service-auth-gateway", "src_ids": ["DOC-RUNBOOK-M4"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service user-preferences depends on auth-gateway."]},
        {"eid": "EID-M4-05", "type": "DEPENDS_ON", "src": "service-auth-gateway", "dst": "service-identity-provider", "src_ids": ["DOC-RUNBOOK-M4"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service auth-gateway depends on identity-provider."]},
        {"eid": "EID-M4-06", "type": "DEPENDS_ON", "src": "service-identity-provider", "dst": "service-ldap-directory", "src_ids": ["DOC-RUNBOOK-M4"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service identity-provider depends on ldap-directory."]},
    ]
    for e in m_chains_edges:
        e.update({"valid_from": "2023-07-04T10:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(m_chains_edges)

    m1_chain = ["service-web-frontend", "service-api-gateway", "service-session-cache", "service-redis-cluster"]
    m2_chain = ["service-mobile-app-backend", "service-order-service", "service-checkout-api", "service-ledger", "service-payment-vault"]
    m3_chain = ["service-analytics-pipeline", "service-event-stream", "service-search-index", "service-inventory-api", "service-catalog-db", "service-storage-cluster"]
    m4_chain = ["service-notification-dispatcher", "service-notifier", "service-template-renderer", "service-user-preferences", "service-auth-gateway", "service-identity-provider", "service-ldap-directory"]

    gold_scenarios["M1"] = {"nodes": m1_chain, "curated_edge_eids": [e["eid"] for e in m_chains_edges[:3]], "expected_status": {e["eid"]: None for e in m_chains_edges[:3]}, "notes": "Multi-hop 3-hop dependency chain"}
    gold_scenarios["M2"] = {"nodes": m2_chain, "curated_edge_eids": [e["eid"] for e in m_chains_edges[3:7]], "expected_status": {e["eid"]: None for e in m_chains_edges[3:7]}, "notes": "Multi-hop 4-hop dependency chain"}
    gold_scenarios["M3"] = {"nodes": m3_chain, "curated_edge_eids": [e["eid"] for e in m_chains_edges[7:12]], "expected_status": {e["eid"]: None for e in m_chains_edges[7:12]}, "notes": "Multi-hop 5-hop dependency chain"}
    gold_scenarios["M4"] = {"nodes": m4_chain, "curated_edge_eids": [e["eid"] for e in m_chains_edges[12:]], "expected_status": {e["eid"]: None for e in m_chains_edges[12:]}, "notes": "Multi-hop 6-hop dependency chain"}

    # ------------------------------------------------------------------------
    # SCENARIO P1: PageRank Differential
    # ------------------------------------------------------------------------
    doc_p1 = {
        "id": "DOC-ARCH-P1",
        "type": "runbook",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2023-08-01T10:00:00Z",
        "restricted": False,
        "title": "Architecture P1: Core Auth Ingress Routing",
        "text": "Service api-hub-service depends on core-auth-service for gateway token verification. Service batch-exporter-service depends on core-auth-service for nocturnal batch sync."
    }
    docs.append(doc_p1)

    p1_edges = [
        {"eid": "EID-P1-01", "type": "DEPENDS_ON", "src": "service-api-hub", "dst": "service-core-auth", "src_ids": ["DOC-ARCH-P1"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service api-hub-service depends on core-auth-service for gateway token verification."]},
        {"eid": "EID-P1-02", "type": "DEPENDS_ON", "src": "service-batch-exporter", "dst": "service-core-auth", "src_ids": ["DOC-ARCH-P1"], "src_conf": [1.0], "src_auth": [2], "spans": ["Service batch-exporter-service depends on core-auth-service for nocturnal batch sync."]},
    ]
    for e in p1_edges:
        e.update({"valid_from": "2023-08-01T10:00:00Z", "valid_to": None, "status": "unverified", "derived_reason": None})
    edges.extend(p1_edges)
    gold_scenarios["P1"] = {
        "nodes": ["service-core-auth", "service-api-hub", "service-batch-exporter"],
        "curated_edge_eids": [e["eid"] for e in p1_edges],
        "expected_status": {e["eid"]: None for e in p1_edges},
        "notes": "Failing service core-auth-service has two dependents: api-hub-service (high PageRank hub) and batch-exporter-service (leaf)."
    }

    # ------------------------------------------------------------------------
    # CATALOG EDGES FOR ALL SERVICES (except orphan legacy-reports)
    # 59 services * 2 = 118 catalog edges
    # ------------------------------------------------------------------------
    catalog_edges = []
    # ASSUMPTION: Every service gets catalog OWNS + ON_CALL edges sourced from
    # one "system" catalog doc (src_auth 2, src_conf 0.90), status unverified.
    for idx, s in enumerate(curated_services):
        if s["name"] == "legacy-reports":
            continue
        assigned_team_id = f"team-{catalog_owners[s['name']]}"
        assigned_lead_p = curated_people[idx % len(curated_people)]
        span_owns = f"Catalog Record: Service {s['name']} is officially registered under team {assigned_team_id.replace('team-', '')}."
        span_oncall = f"Designated primary on-call engineer handle is {assigned_lead_p['handle']}."
        full_span = f"{span_owns} {span_oncall}"

        catalog_edges.append({
            "eid": f"EID-CATALOG-OWNS-{idx:02d}",
            "type": "OWNS",
            "src": assigned_team_id,
            "dst": s["id"],
            "src_ids": ["DOC-CATALOG"],
            "src_conf": [0.90],
            "src_auth": [2],
            "spans": [full_span],
            "valid_from": "2023-01-01T00:00:00Z",
            "valid_to": None,
            "status": "unverified",
            "derived_reason": None
        })
        catalog_edges.append({
            "eid": f"EID-CATALOG-ONCALL-{idx:02d}",
            "type": "ON_CALL",
            "src": assigned_lead_p["id"],
            "dst": s["id"],
            "src_ids": ["DOC-CATALOG"],
            "src_conf": [0.90],
            "src_auth": [2],
            "spans": [full_span],
            "valid_from": "2023-01-01T00:00:00Z",
            "valid_to": None,
            "status": "unverified",
            "derived_reason": None
        })
    edges.extend(catalog_edges)

    # ------------------------------------------------------------------------
    # FIXED CURATED STRUCTURAL EDGES (Team memberships & core decisions)
    # Bringing total curated edges to exactly 221
    # ------------------------------------------------------------------------
    # Curated MEMBER_OF edges for 30 core engineers
    member_edges = []
    for idx, p in enumerate(curated_people):
        member_edges.append({
            "eid": f"EID-CUR-MEMBER-{idx:02d}",
            "type": "MEMBER_OF",
            "src": p["id"],
            "dst": p["team_id"],
            "src_ids": ["DOC-CATALOG"],
            "src_conf": [1.0],
            "src_auth": [2],
            "spans": [],
            "valid_from": "2023-01-01T00:00:00Z",
            "valid_to": None,
            "status": "unverified",
            "derived_reason": None
        })
    edges.extend(member_edges)

    # Curated architectural DECIDED / CONCERNS edges for core decisions
    # We need exactly: 221 - len(edges) edges
    needed_curated = 221 - len(edges)
    arch_doc = {
        "id": "DOC-ARCH-CORE",
        "type": "adr",
        "author_id": "person-platform-lead",
        "author_handle": "erostova",
        "author_email": "elena.rostova@company.internal",
        "timestamp": "2023-01-15T00:00:00Z",
        "restricted": False,
        "title": "ADR-01: Core Architecture Standards",
        "text": "Core architectural standards dictate modular services, isolated datastores, and standardized API contracts across all engineering tiers."
    }
    docs.append(arch_doc)

    payments_arch_doc = dict(arch_doc, id="DOC-ARCH-CORE-PAYMENTS",
        author_id="person-dev-patel", author_handle="dpatel",
        author_email="dev.patel@company.internal")
    docs.append(payments_arch_doc)
    core_decision_edges = []
    for idx in range(needed_curated):
        dec_id = f"DEC-ARCH-CORE-{idx:02d}"
        target_svc = curated_services[idx % len(curated_services)]
        # Keep S4 ownerless; its unrelated filler baseline belongs on session-cache.
        if target_svc["name"] == "legacy-reports":
            target_svc = curated_services[0]
        baseline_doc = (payments_arch_doc if catalog_owners[target_svc["name"]] == "payments"
                        else arch_doc)
        nodes.append({
            "id": dec_id,
            "label": "Decision",
            "topic": f"core-architecture-{idx:02d}",
            "title": f"ADR-CORE-{idx:02d}: Architectural baseline for {target_svc['name']}"
        })
        core_decision_edges.append({
            "eid": f"EID-CUR-ARCH-{idx:02d}",
            "type": "CONCERNS",
            "src": dec_id,
            "dst": target_svc["id"],
            "src_ids": [baseline_doc["id"]],
            "src_conf": [1.0],
            "src_auth": [3],
            "spans": ["Core architectural standards dictate modular services, isolated datastores, and standardized API contracts across all engineering tiers."],
            "valid_from": "2023-01-15T00:00:00Z",
            "valid_to": None,
            "status": "unverified",
            "derived_reason": None
        })
    edges.extend(core_decision_edges)

    # Each curated claim begins when its first source document was published.
    docs_by_id = {doc["id"]: doc for doc in docs}
    for edge in edges:
        edge["valid_from"] = docs_by_id[edge["src_ids"][0]]["timestamp"]

    # Quick assert to ensure curated edge count is exactly 221
    assert len(edges) == 221, f"Expected 221 curated edges, got {len(edges)}"

    return {
        "nodes": nodes,
        "docs": docs,
        "edges": edges,
        "gold_scenarios": gold_scenarios,
        "m_chains": {"M1": m1_chain, "M2": m2_chain, "M3": m3_chain, "M4": m4_chain},
        "curated_services": curated_services,
        "curated_people": curated_people
    }


# ============================================================================
# BACKGROUND DATA GENERATION (Reseedable)
# ============================================================================

def generate_background_data(curated, seed=42):
    """
    Generates background nodes, filler docs, and background edges:
      Target Total Nodes: 6,243
      Target Corpus Docs: 98
    """
    rng = random.Random(seed)

    all_nodes = list(curated["nodes"])
    all_docs = list(curated["docs"])
    all_edges = list(curated["edges"])

    curated_services = curated["curated_services"]
    curated_people = curated["curated_people"]

    # 1. Fill random people (~80 total people)
    bg_people = []
    first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia",
                   "Mason", "Isabella", "Ethan", "Mia", "Alexander", "Charlotte", "Oliver",
                   "Amelia", "Daniel", "Harper", "Lucas", "Evelyn", "Matthew", "Abigail",
                   "Aiden", "Emily", "Jackson", "Elizabeth", "Logan", "Mila", "David", "Ella",
                   "Joseph", "Avery", "Samuel", "Sofia", "Henry", "Camila", "John", "Aria",
                   "Sebastian", "Scarlett", "Jack", "Victoria", "Owen", "Madison", "Theodore",
                   "Luna", "Ryan", "Grace", "Caleb", "Chloe", "Nathan", "Penelope", "Leo", "Layla"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
                  "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
                  "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez"]

    needed_people = 85 - len(curated_people)
    for i in range(needed_people):
        fn = rng.choice(first_names)
        ln = rng.choice(last_names)
        name = f"{fn} {ln}"
        handle = f"{fn[0].lower()}{ln.lower()}{rng.randint(10, 99)}"
        email = f"{fn.lower()}.{ln.lower()}{i}@company.internal"
        p_id = f"person-bg-{i:03d}"
        role = "lead" if i % 10 == 0 else "engineer"
        p = {
            "id": p_id,
            "label": "Person",
            "name": name,
            "email": email,
            "handle": handle,
            "role": role
        }
        bg_people.append(p)
        all_nodes.append(p)

    all_people = curated_people + bg_people

    # 2. Filler Incidents
    needed_incidents = 45 - sum(1 for n in all_nodes if n["label"] == "Incident")
    for i in range(needed_incidents):
        all_nodes.append({
            "id": f"INC-BG-{i:03d}",
            "label": "Incident",
            "title": f"Incident {i}: Elevated error rates on subsystem {i}",
            "sev": rng.choice(["sev-1", "sev-2", "sev-3"]),
            "timestamp": f"2023-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}T10:00:00Z"
        })

    # 3. Filler Decisions
    needed_decisions = 45 - sum(1 for n in all_nodes if n["label"] == "Decision")
    for i in range(needed_decisions):
        all_nodes.append({
            "id": f"DEC-BG-{i:03d}",
            "label": "Decision",
            "topic": f"infrastructure-topic-{i}",
            "title": f"Decision {i}: Adoption of background policy {i}"
        })

    # 4. Filler Corpus Docs to reach exactly 98 corpus docs
    needed_docs = 98 - len(all_docs)
    doc_types = ["runbook", "chat", "vcs", "ticket"]
    auth_map = {"adr": 3, "postmortem": 3, "ticket": 2, "runbook": 2, "vcs": 2, "chat": 1, "catalog": 2}

    filler_docs = []
    for i in range(needed_docs):
        dtype = rng.choice(doc_types)
        author = rng.choice(all_people)
        svc = rng.choice(curated_services)
        doc_id = f"DOC-FILLER-{i:03d}"
        quote_sentence = f"Service {svc['name']} maintains operational readiness through scheduled health checks."
        text = f"Routine {dtype} document for service maintenance.\n{quote_sentence}\nAll metrics remain nominal."
        doc = {
            "id": doc_id,
            "type": dtype,
            "author_id": author["id"],
            "author_handle": author["handle"],
            "author_email": author["email"],
            "timestamp": f"2023-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}T12:00:00Z",
            "restricted": False,
            "title": f"{dtype.capitalize()} Log {i}: Operational Overview",
            "text": text
        }
        filler_docs.append(doc)
        all_docs.append(doc)

    # Also add Doc nodes to all_nodes
    for d in all_docs:
        all_nodes.append({
            "id": d["id"],
            "label": "Doc",
            "type": d["type"],
            "author_id": d["author_id"],
            "author_handle": d["author_handle"],
            "author_email": d["author_email"],
            "timestamp": d["timestamp"],
            "restricted": d["restricted"],
            "title": d["title"],
            "text": d["text"]
        })

    # 5. Fill nodes to scale with filler Commits as specified:
    # "Fill nodes to scale with filler Persons/Services/Incidents/Commits as needed."
    # Target total nodes = 6,243
    needed_commits = 6243 - len(all_nodes)
    commit_nodes = []
    for i in range(needed_commits):
        sha = f"{rng.getrandbits(160):040x}"
        c = {
            "id": f"commit-{i:05d}",
            "label": "Commit",
            "hash": sha,
            "message": f"feat(core): periodic commit {i} update dependencies",
            "timestamp": f"2023-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00Z"
        }
        commit_nodes.append(c)
        all_nodes.append(c)

    # 6. Generate background edges.
    bg_edges = []

    # Priority A: sparse layered dependency DAG, including 25 inbound edges to the P1 hub.
    hub_svc_id = "service-api-hub"
    service_ids = [s["id"] for s in curated_services]
    curated_deps = [(e["src"], e["dst"]) for e in all_edges if e["type"] == "DEPENDS_ON"]
    connected = {service for pair in curated_deps for service in pair}
    layers = {service: 0 for service in service_ids}
    for i, service in enumerate(s for s in service_ids if s not in connected):
        layers[service] = i % 7
    layers[hub_svc_id] = 7
    layers["service-core-auth"] = 8
    for _ in service_ids:
        changed = False
        for src, dst in curated_deps:
            if layers[dst] <= layers[src]:
                layers[dst] = layers[src] + 1
                changed = True
        if not changed:
            break
    assert max(layers.values()) <= 8, "Curated dependency chain exceeds eight layers"

    hub_sources = sorted((s for s in service_ids if layers[s] < layers[hub_svc_id] and s != "service-batch-exporter"),
                         key=lambda s: (layers[s], s), reverse=True)[:25]
    dep_pairs = set(curated_deps)
    new_deps = [(src, hub_svc_id) for src in hub_sources]
    dep_pairs.update(new_deps)
    for src in service_ids:
        if src not in hub_sources and src not in (hub_svc_id, "service-core-auth", "service-batch-exporter"):
            targets = [dst for dst in hub_sources if layers[src] < layers[dst]]
            assert targets, f"No downstream hub path for {src}"
            pair = (src, rng.choice(targets))
            if pair not in dep_pairs:
                new_deps.append(pair)
                dep_pairs.add(pair)
    outdegree = {s: sum(src == s for src, _ in dep_pairs) for s in service_ids}
    candidates = [(src, dst) for src in service_ids for dst in service_ids
                  if layers[src] < layers[dst] and dst not in (hub_svc_id, "service-core-auth", "service-batch-exporter")
                  and (src, dst) not in dep_pairs]
    rng.shuffle(candidates)
    for src, dst in candidates:
        if len(dep_pairs) == 210:
            break
        if outdegree[src] < 5:
            new_deps.append((src, dst))
            dep_pairs.add((src, dst))
            outdegree[src] += 1
    assert len(dep_pairs) == 210, "Not enough layered service dependencies"
    for src_svc, dst_svc in new_deps:
        bg_edges.append({
            "eid": f"EID-BG-{len(bg_edges):05d}",
            "type": "DEPENDS_ON",
            "src": src_svc,
            "dst": dst_svc,
            "src_ids": [],
            "src_conf": [1.0],
            "src_auth": [2],
            "spans": [],
            "valid_from": "2023-01-01T00:00:00Z",
            "valid_to": None,
            "status": "current",
            "derived_reason": None
        })

    # Priority B: COMMITTED edges (Person -> Commit) and CONCERNS edges (Commit -> Service)
    # Distribute commits among engineers and services
    for i, c in enumerate(commit_nodes):
        p = rng.choice(all_people)
        bg_edges.append({
            "eid": f"EID-BG-{len(bg_edges):05d}",
            "type": "COMMITTED",
            "src": p["id"],
            "dst": c["id"],
            "src_ids": [],
            "src_conf": [1.0],
            "src_auth": [2],
            "spans": [],
            "valid_from": c["timestamp"],
            "valid_to": None,
            "status": "current",
            "derived_reason": None
        })

        svc = rng.choice(curated_services)
        bg_edges.append({
            "eid": f"EID-BG-{len(bg_edges):05d}",
            "type": "CONCERNS",
            "src": c["id"],
            "dst": svc["id"],
            "src_ids": [],
            "src_conf": [1.0],
            "src_auth": [2],
            "spans": [],
            "valid_from": c["timestamp"],
            "valid_to": None,
            "status": "current",
            "derived_reason": None
        })

    # Priority C: Sourced filler edges from filler docs (with verbatim spans)
    for i, doc in enumerate(filler_docs):
        # Extract verbatim span from doc text
        lines = [line.strip() for line in doc["text"].split("\n") if "maintains operational readiness" in line]
        span = lines[0] if lines else "Routine runbook document for service maintenance."
        svc = rng.choice(curated_services)
        bg_edges.append({
            "eid": f"EID-BG-{len(bg_edges):05d}",
            "type": "CONCERNS",
            "src": doc["id"],
            "dst": svc["id"],
            "src_ids": [doc["id"]],
            "src_conf": [0.95],
            "src_auth": [auth_map.get(doc["type"], 2)],
            "spans": [span],
            "valid_from": doc["timestamp"],
            "valid_to": None,
            "status": "current",
            "derived_reason": None
        })

    # Priority D: keep operational background relationships without adding dependency paths.
    for i in range(15055 - len(bg_edges)):
        if i % 2:
            p = rng.choice(all_people)
            s = rng.choice(service_ids)
            bg_edges.append({
                "eid": f"EID-BG-{len(bg_edges):05d}",
                "type": "ON_CALL",
                "src": p["id"],
                "dst": s,
                "src_ids": [],
                "src_conf": [0.90],
                "src_auth": [2],
                "spans": [],
                "valid_from": "2023-01-01T00:00:00Z",
                "valid_to": None,
                "status": "current",
                "derived_reason": None
            })
        else:
            p = rng.choice(all_people)
            s = rng.choice(service_ids)
            bg_edges.append({
                "eid": f"EID-BG-{len(bg_edges):05d}",
                "type": "COMMITTED",
                "src": p["id"],
                "dst": s,
                "src_ids": [],
                "src_conf": [1.0],
                "src_auth": [2],
                "spans": [],
                "valid_from": "2023-01-01T00:00:00Z",
                "valid_to": None,
                "status": "current",
                "derived_reason": None
            })

    all_edges.extend(bg_edges)

    return all_nodes, all_edges, all_docs


# ============================================================================
# MAIN
# ============================================================================

def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating Keystone synthetic data (seed={args.seed}) into {out_dir} ...")

    # Build fixed curated scenarios & data
    curated = build_curated_data()

    # Generate background data
    nodes, edges, docs = generate_background_data(curated, seed=args.seed)

    print(f"Nodes generated: {len(nodes):,}")
    print(f"Edges generated: {len(edges):,} ({len(curated['edges'])} curated unverified, {len(edges) - len(curated['edges']):,} background current)")
    print(f"Corpus Docs generated: {len(docs):,}")

    # Write data/nodes.jsonl
    nodes_file = out_dir / "nodes.jsonl"
    with open(nodes_file, "w", encoding="utf-8") as f:
        for node in nodes:
            f.write(json.dumps(node, ensure_ascii=False) + "\n")

    # Write data/edges.jsonl
    edges_file = out_dir / "edges.jsonl"
    with open(edges_file, "w", encoding="utf-8") as f:
        for edge in edges:
            f.write(json.dumps(edge, ensure_ascii=False) + "\n")

    # Write data/docs.jsonl
    docs_file = out_dir / "docs.jsonl"
    with open(docs_file, "w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # Build gold.json
    gold_data = dict(curated["gold_scenarios"])
    gold_data["multi_hop_chains"] = curated["m_chains"]
    gold_data["p1_pagerank"] = {
        "failing_service": "service-core-auth",
        "high_pagerank_hub": "service-api-hub",
        "low_pagerank_leaf": "service-batch-exporter"
    }
    gold_data["alias_groups"] = [
        {
            "person_id": "person-j-rao",
            "canonical_name": "Jitendra Rao",
            "aliases": ["j.rao@company.internal", "jrao", "J. Rao"]
        },
        {
            "person_id": "person-alex-chen",
            "canonical_name": "Alex Chen",
            "aliases": ["achen", "alex.chen@company.internal", "Alex C."]
        },
        {
            "person_id": "person-sophia-taylor",
            "canonical_name": "Sophia Taylor",
            "aliases": ["staylor", "sophia.taylor@company.internal", "S. Taylor"]
        }
    ]
    gold_data["restricted_doc_ids"] = ["DOC-PM-S6"]
    gold_data["unresolved_handles"] = ["ghost_coder_99", "phantom_ops", "shadow_actor"]
    gold_data["allowed_statuses"] = ["unverified", "current", "noted"]
    gold_data["status_notes"] = "Allowed status vocabulary includes unverified, current, and noted. expected_status values are left null for manual labeling."

    gold_file = out_dir / "gold.json"
    with open(gold_file, "w", encoding="utf-8") as f:
        json.dump(gold_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully wrote {nodes_file}, {edges_file}, {docs_file}, {gold_file}.")


if __name__ == "__main__":
    main()
