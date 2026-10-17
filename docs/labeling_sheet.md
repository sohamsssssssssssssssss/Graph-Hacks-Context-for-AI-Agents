# Keystone scenario labeling sheet

Fill `LABEL` and `REASON` by hand for each entry. Source evidence is reproduced without a status assessment.

## Scenario authors

| Person | Team via MEMBER_OF | Role |
| --- | --- | --- |
| Alex Chen (`person-alex-chen`) | growth (`team-growth`) | engineer |
| Chloe Martin (`person-chloe-martin`) | commerce (`team-commerce`) | engineer |
| Dev Patel (`person-dev-patel`) | payments (`team-payments`) | lead |
| Elena Rostova (`person-platform-lead`) | platform (`team-platform`) | lead |
| Jitendra Rao (`person-j-rao`) | platform (`team-platform`) | engineer |
| Leo Vance (`person-leo-vance`) | commerce (`team-commerce`) | engineer |
| Marcus Vance (`person-marcus-vance`) | growth (`team-growth`) | engineer |
| Rachel Green (`person-rachel-green`) | commerce (`team-commerce`) | lead |
| Samira Khan (`person-samira-khan`) | platform (`team-platform`) | engineer |
| Sophia Taylor (`person-sophia-taylor`) | payments (`team-payments`) | engineer |

**Resolved Person authors missing MEMBER_OF:** none.

**Unresolved source authors (no Person/MEMBER_OF):** `ghost_coder_99` (`DOC-CHAT-S4`), `phantom_ops` (`DOC-TICKET-S5`), `shadow_actor` (`DOC-TICKET-S5B`), `system` (`DOC-CATALOG`).

## S1

### EID-S1-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-01` | `CONCERNS` | ADR-3: Use Redis for session cache (`DEC-ADR-3`) → session-cache (`service-session-cache`) | `2023-05-12T10:00:00Z` |

**Source docs**

- `DOC-ADR-3`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> We adopt Redis cluster as the primary storage engine for session-cache.

**Full source document text**

`DOC-ADR-3`:
> We adopt Redis cluster as the primary storage engine for session-cache. Redis provides sub-millisecond retrieval latency and native TTL support. All session state must be persisted in Redis.

LABEL:

REASON:


### EID-S1-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-02` | `DECIDED` | Elena Rostova (`person-platform-lead`) → ADR-3: Use Redis for session cache (`DEC-ADR-3`) | `2023-05-12T10:00:00Z` |

**Source docs**

- `DOC-ADR-3`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Span (verbatim)**

> We adopt Redis cluster as the primary storage engine for session-cache.

**Full source document text**

`DOC-ADR-3`:
> We adopt Redis cluster as the primary storage engine for session-cache. Redis provides sub-millisecond retrieval latency and native TTL support. All session state must be persisted in Redis.

LABEL:

REASON:


### EID-S1-08

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-08` | `CONCERNS` | ADR-5: Redis sliding window for rate-limiter (`DEC-ADR-5`) → rate-limiter (`service-rate-limiter`) | `2023-08-20T11:00:00Z` |

**Source docs**

- `DOC-ADR-5`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** payments (`team-payments`)

**Span (verbatim)**

> The rate-limiter service will use Redis sliding window counters for per-tenant traffic throttling.

**Full source document text**

`DOC-ADR-5`:
> The rate-limiter service will use Redis sliding window counters for per-tenant traffic throttling. This architecture provides high throughput counters independent of session storage.

LABEL:

REASON:


### EID-S1-09

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-09` | `DECIDED` | Elena Rostova (`person-platform-lead`) → ADR-5: Redis sliding window for rate-limiter (`DEC-ADR-5`) | `2023-08-20T11:00:00Z` |

**Source docs**

- `DOC-ADR-5`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Span (verbatim)**

> The rate-limiter service will use Redis sliding window counters for per-tenant traffic throttling.

**Full source document text**

`DOC-ADR-5`:
> The rate-limiter service will use Redis sliding window counters for per-tenant traffic throttling. This architecture provides high throughput counters independent of session storage.

LABEL:

REASON:


### EID-S1-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-03` | `CONCERNS` | ADR-7: Migrate session cache from Redis to Memcached (`DEC-ADR-7`) → session-cache (`service-session-cache`) | `2024-03-15T09:00:00Z` |

**Source docs**

- `DOC-ADR-7`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> We migrate session-cache storage to Memcached with active replication to avoid Redis cluster memory failure modes.

**Full source document text**

`DOC-ADR-7`:
> Following incident INC-2291, ADR-7 supersedes ADR-3. INC-2291 was a Redis cluster memory failure on session-cache. We migrate session-cache storage to Memcached with active replication to avoid Redis cluster memory failure modes.

LABEL:

REASON:


### EID-S1-04

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-04` | `DECIDED` | Elena Rostova (`person-platform-lead`) → ADR-7: Migrate session cache from Redis to Memcached (`DEC-ADR-7`) | `2024-03-15T09:00:00Z` |

**Source docs**

- `DOC-ADR-7`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Span (verbatim)**

> Following incident INC-2291, ADR-7 supersedes ADR-3.

**Full source document text**

`DOC-ADR-7`:
> Following incident INC-2291, ADR-7 supersedes ADR-3. INC-2291 was a Redis cluster memory failure on session-cache. We migrate session-cache storage to Memcached with active replication to avoid Redis cluster memory failure modes.

LABEL:

REASON:


### EID-S1-05

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-05` | `SUPERSEDES` | ADR-7: Migrate session cache from Redis to Memcached (`DEC-ADR-7`) → ADR-3: Use Redis for session cache (`DEC-ADR-3`) | `2024-03-15T09:00:00Z` |

**Source docs**

- `DOC-ADR-7`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Span (verbatim)**

> Following incident INC-2291, ADR-7 supersedes ADR-3.

**Full source document text**

`DOC-ADR-7`:
> Following incident INC-2291, ADR-7 supersedes ADR-3. INC-2291 was a Redis cluster memory failure on session-cache. We migrate session-cache storage to Memcached with active replication to avoid Redis cluster memory failure modes.

LABEL:

REASON:


### EID-S1-06

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-06` | `BECAUSE_OF` | ADR-7: Migrate session cache from Redis to Memcached (`DEC-ADR-7`) → Redis session cache cluster memory exhaustion outage (`INC-2291`) | `2024-03-15T09:00:00Z` |

**Source docs**

- `DOC-ADR-7`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Span (verbatim)**

> Following incident INC-2291, ADR-7 supersedes ADR-3.

**Full source document text**

`DOC-ADR-7`:
> Following incident INC-2291, ADR-7 supersedes ADR-3. INC-2291 was a Redis cluster memory failure on session-cache. We migrate session-cache storage to Memcached with active replication to avoid Redis cluster memory failure modes.

LABEL:

REASON:


### EID-S1-07

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S1-07` | `CAUSED_BY` | Redis session cache cluster memory exhaustion outage (`INC-2291`) → session-cache (`service-session-cache`) | `2024-03-15T09:00:00Z` |

**Source docs**

- `DOC-ADR-7`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> INC-2291 was a Redis cluster memory failure on session-cache.

**Full source document text**

`DOC-ADR-7`:
> Following incident INC-2291, ADR-7 supersedes ADR-3. INC-2291 was a Redis cluster memory failure on session-cache. We migrate session-cache storage to Memcached with active replication to avoid Redis cluster memory failure modes.

LABEL:

REASON:


## S2

### EID-S2-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S2-01` | `OWNS` | payments (`team-payments`) → checkout-api (`service-checkout-api`) | `2023-04-10T11:00:00Z` |

**Source docs**

- `DOC-ADR-CHECKOUT`; type `adr` (authority `3`); author_id=`person-dev-patel`, author_handle=`dpatel`, author_email=`dev.patel@company.internal` → Dev Patel (`person-dev-patel`), team payments (`team-payments`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Payments team owns checkout-api service and its transaction pipeline.

**Full source document text**

`DOC-ADR-CHECKOUT`:
> Payments team owns checkout-api service and its transaction pipeline. All architectural changes require payments sign-off.

LABEL:

REASON:


### EID-S2-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S2-02` | `OWNS` | commerce (`team-commerce`) → checkout-api (`service-checkout-api`) | `2024-02-01T14:00:00Z` |

**Source docs**

- `T-482`; type `ticket` (authority `2`); author_id=`person-chloe-martin`, author_handle=`cmartin`, author_email=`chloe.martin@company.internal` → Chloe Martin (`person-chloe-martin`), team commerce (`team-commerce`); src_conf=`0.85`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Commerce team claims ownership of checkout-api to streamline the storefront checkout funnel.

**Full source document text**

`T-482`:
> Commerce team claims ownership of checkout-api to streamline the storefront checkout funnel. We request transferring all service responsibilities from payments to commerce.

LABEL:

REASON:


### EID-S2-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S2-03` | `APPROVED` | Dev Patel (`person-dev-patel`) → checkout-api (`service-checkout-api`) | `2024-02-03T16:30:00Z` |

**Source docs**

- `T-482-C1`; type `ticket` (authority `2`); author_id=`person-dev-patel`, author_handle=`dpatel`, author_email=`dev.patel@company.internal` → Dev Patel (`person-dev-patel`), team payments (`team-payments`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Dev Patel approves ownership transfer of checkout-api to commerce team.

**Full source document text**

`T-482-C1`:
> Dev Patel approves ownership transfer of checkout-api to commerce team. Payments team has completed handoff verification.

LABEL:

REASON:


### EID-S2-04

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S2-04` | `DISPUTES` | Samira Khan (`person-samira-khan`) → checkout-api (`service-checkout-api`) | `2024-02-04T09:15:00Z` |

**Source docs**

- `C-901`; type `chat` (authority `1`); author_id=`person-samira-khan`, author_handle=`skhan`, author_email=`samira.khan@company.internal` → Samira Khan (`person-samira-khan`), team platform (`team-platform`); src_conf=`0.75`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Samira disputes the ownership transfer of checkout-api in ticket T-482.

**Full source document text**

`C-901`:
> Samira disputes the ownership transfer of checkout-api in ticket T-482. Platform team believes checkout-api must remain under payments due to PCI DSS compliance.

LABEL:

REASON:


## S3

### EID-S3-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S3-01` | `OWNS` | platform (`team-platform`) → search-index (`service-search-index`) | `2023-06-01T10:00:00Z` |

**Source docs**

- `DOC-ADR-SEARCH`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Platform team owns search-index infrastructure and cluster provisioning.

**Full source document text**

`DOC-ADR-SEARCH`:
> Platform team owns search-index infrastructure and cluster provisioning. Search indexing pipelines are maintained by platform core.

LABEL:

REASON:


### EID-S3-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S3-02` | `OWNS` | growth (`team-growth`) → search-index (`service-search-index`) | `2024-04-02T14:22:00Z` |

**Source docs**

- `DOC-CHAT-S3`; type `chat` (authority `1`); author_id=`person-marcus-vance`, author_handle=`mvance`, author_email=`marcus.vance@company.internal` → Marcus Vance (`person-marcus-vance`), team growth (`team-growth`); src_conf=`0.7`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Growth team now owns search-index for catalog experimentation.

**Full source document text**

`DOC-CHAT-S3`:
> Growth team now owns search-index for catalog experimentation. Growth has taken over day-to-day query ranking and indexing.

LABEL:

REASON:


## S4

### EID-S4-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S4-01` | `OWNS` | growth (`team-growth`) → legacy-reports (`service-legacy-reports`) | `2024-04-05T11:00:00Z` |

**Source docs**

- `DOC-CHAT-S4`; type `chat` (authority `1`); author_id=`None`, author_handle=`ghost_coder_99`, author_email=`None` → UNRESOLVED; src_conf=`0.65`

**Catalog owner of destination service:** none recorded

**Span (verbatim)**

> Growth team claims ownership of legacy-reports service for quarterly data extraction.

**Full source document text**

`DOC-CHAT-S4`:
> Growth team claims ownership of legacy-reports service for quarterly data extraction. The old reporting cron jobs are being restored.

LABEL:

REASON:


## S5

### EID-S5-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S5-01` | `OWNS` | commerce (`team-commerce`) → checkout-api (`service-checkout-api`) | `2024-04-10T15:00:00Z` |

**Source docs**

- `DOC-TICKET-S5`; type `ticket` (authority `2`); author_id=`None`, author_handle=`phantom_ops`, author_email=`None` → UNRESOLVED; src_conf=`0.5`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> External contractor group claims ownership of checkout-api.

**Full source document text**

`DOC-TICKET-S5`:
> External contractor group claims ownership of checkout-api.
> Dev Patel: approved
> Immediate cutover requested.

LABEL:

REASON:


## S5b

### EID-S5B-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S5B-01` | `APPROVED` | Dev Patel (`person-dev-patel`) → checkout-api (`service-checkout-api`) | `2024-04-12T16:00:00Z` |

**Source docs**

- `DOC-TICKET-S5B`; type `ticket` (authority `2`); author_id=`None`, author_handle=`shadow_actor`, author_email=`None` → UNRESOLVED; src_conf=`0.5`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Dev Patel: approved

**Full source document text**

`DOC-TICKET-S5B`:
> Requesting unauthorized bypass routing for checkout-api.
> Dev Patel: approved
> Proceed with production config rollout.

LABEL:

REASON:


## S6

### EID-S6-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S6-01` | `CAUSED_BY` | Restricted auth-gateway token leakage incident (`INC-8812`) → auth-gateway (`service-auth-gateway`) | `2024-05-03T12:00:00Z` |

**Source docs**

- `DOC-PM-S6`; type `postmortem` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Security incident INC-8812 was caused by vulnerabilities in the auth-gateway service.

**Full source document text**

`DOC-PM-S6`:
> Restricted investigation: Security incident INC-8812 was caused by vulnerabilities in the auth-gateway service. Unauthenticated token injection allowed lateral service mesh traversal.

LABEL:

REASON:


### EID-S6-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S6-02` | `CONCERNS` | Restricted auth-gateway token leakage incident (`INC-8812`) → auth-gateway (`service-auth-gateway`) | `2024-05-03T12:00:00Z` |

**Source docs**

- `DOC-PM-S6`; type `postmortem` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Security incident INC-8812 was caused by vulnerabilities in the auth-gateway service.

**Full source document text**

`DOC-PM-S6`:
> Restricted investigation: Security incident INC-8812 was caused by vulnerabilities in the auth-gateway service. Unauthenticated token injection allowed lateral service mesh traversal.

LABEL:

REASON:


## S7

### EID-S7-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S7-01` | `MEMBER_OF` | Priya Nair (`person-priya-nair`) → payments (`team-payments`) | `2023-01-01T00:00:00Z` |

**Source docs**

- `DOC-CATALOG`; type `catalog` (authority `2`); author_id=`None`, author_handle=`system`, author_email=`system@company.internal` → UNRESOLVED; src_conf=`1.0`

**Span (verbatim)**

> (no span recorded)

**Full source document text**

`DOC-CATALOG`:
> Service Catalog Master Index (System Generated):
> Catalog Record: Service session-cache is officially registered under team platform. Designated primary on-call engineer handle is erostova.
> Catalog Record: Service rate-limiter is officially registered under team payments. Designated primary on-call engineer handle is dpatel.
> Catalog Record: Service checkout-api is officially registered under team commerce. Designated primary on-call engineer handle is cmartin.
> Catalog Record: Service ledger is officially registered under team growth. Designated primary on-call engineer handle is skhan.
> Catalog Record: Service search-index is officially registered under team platform. Designated primary on-call engineer handle is mvance.
> Catalog Record: Service notifier is officially registered under team commerce. Designated primary on-call engineer handle is pnair.
> Catalog Record: Service auth-gateway is officially registered under team growth. Designated primary on-call engineer handle is pnayar.
> Catalog Record: Service telemetry-collector is officially registered under team platform. Designated primary on-call engineer handle is lvance.
> Catalog Record: Service billing-worker is officially registered under team payments. Designated primary on-call engineer handle is achen.
> Catalog Record: Service core-auth-service is officially registered under team commerce. Designated primary on-call engineer handle is staylor.
> Catalog Record: Service api-hub-service is officially registered under team growth. Designated primary on-call engineer handle is rgreen.
> Catalog Record: Service batch-exporter-service is officially registered under team platform. Designated primary on-call engineer handle is ksato.
> Catalog Record: Service web-frontend is officially registered under team payments. Designated primary on-call engineer handle is asterling.
> Catalog Record: Service api-gateway is officially registered under team commerce. Designated primary on-call engineer handle is doconnor.
> Catalog Record: Service redis-cluster is officially registered under team growth. Designated primary on-call engineer handle is mlin.
> Catalog Record: Service mobile-app-backend is officially registered under team platform. Designated primary on-call engineer handle is tmansoor.
> Catalog Record: Service order-service is officially registered under team payments. Designated primary on-call engineer handle is cgomez.
> Catalog Record: Service payment-vault is officially registered under team commerce. Designated primary on-call engineer handle is fzahra.
> Catalog Record: Service analytics-pipeline is officially registered under team growth. Designated primary on-call engineer handle is lmurphy.
> Catalog Record: Service event-stream is officially registered under team platform. Designated primary on-call engineer handle is ytanaka.
> Catalog Record: Service inventory-api is officially registered under team payments. Designated primary on-call engineer handle is zkravitz.
> Catalog Record: Service catalog-db is officially registered under team commerce. Designated primary on-call engineer handle is nmiller.
> Catalog Record: Service storage-cluster is officially registered under team growth. Designated primary on-call engineer handle is ewatson.
> Catalog Record: Service notification-dispatcher is officially registered under team platform. Designated primary on-call engineer handle is lsilva.
> Catalog Record: Service template-renderer is officially registered under team payments. Designated primary on-call engineer handle is asharma.
> Catalog Record: Service user-preferences is officially registered under team commerce. Designated primary on-call engineer handle is bbecker.
> Catalog Record: Service identity-provider is officially registered under team growth. Designated primary on-call engineer handle is ghopper.
> Catalog Record: Service ldap-directory is officially registered under team platform. Designated primary on-call engineer handle is aturing.
> Catalog Record: Service cart-service is officially registered under team payments. Designated primary on-call engineer handle is alovelace.
> Catalog Record: Service catalog-service is officially registered under team commerce. Designated primary on-call engineer handle is erostova.
> Catalog Record: Service pricing-engine is officially registered under team growth. Designated primary on-call engineer handle is dpatel.
> Catalog Record: Service shipping-calculator is officially registered under team platform. Designated primary on-call engineer handle is cmartin.
> Catalog Record: Service tax-calculator is officially registered under team payments. Designated primary on-call engineer handle is skhan.
> Catalog Record: Service fraud-detection is officially registered under team commerce. Designated primary on-call engineer handle is mvance.
> Catalog Record: Service audit-logger is officially registered under team growth. Designated primary on-call engineer handle is jrao.
> Catalog Record: Service metrics-collector is officially registered under team platform. Designated primary on-call engineer handle is pnair.
> Catalog Record: Service tracing-agent is officially registered under team payments. Designated primary on-call engineer handle is pnayar.
> Catalog Record: Service config-server is officially registered under team commerce. Designated primary on-call engineer handle is lvance.
> Catalog Record: Service secret-manager is officially registered under team growth. Designated primary on-call engineer handle is achen.
> Catalog Record: Service kms-vault is officially registered under team platform. Designated primary on-call engineer handle is staylor.
> Catalog Record: Service customer-portal is officially registered under team payments. Designated primary on-call engineer handle is rgreen.
> Catalog Record: Service merchant-dashboard is officially registered under team commerce. Designated primary on-call engineer handle is ksato.
> Catalog Record: Service recommendation-api is officially registered under team growth. Designated primary on-call engineer handle is asterling.
> Catalog Record: Service content-cdn is officially registered under team platform. Designated primary on-call engineer handle is doconnor.
> Catalog Record: Service image-resizer is officially registered under team payments. Designated primary on-call engineer handle is mlin.
> Catalog Record: Service video-streamer is officially registered under team commerce. Designated primary on-call engineer handle is tmansoor.
> Catalog Record: Service push-relay is officially registered under team growth. Designated primary on-call engineer handle is cgomez.
> Catalog Record: Service sms-gateway is officially registered under team platform. Designated primary on-call engineer handle is fzahra.
> Catalog Record: Service email-sender is officially registered under team payments. Designated primary on-call engineer handle is lmurphy.
> Catalog Record: Service etl-coordinator is officially registered under team commerce. Designated primary on-call engineer handle is ytanaka.
> Catalog Record: Service data-warehouse-sync is officially registered under team growth. Designated primary on-call engineer handle is zkravitz.
> Catalog Record: Service ml-inference-runner is officially registered under team platform. Designated primary on-call engineer handle is nmiller.
> Catalog Record: Service model-registry is officially registered under team payments. Designated primary on-call engineer handle is ewatson.
> Catalog Record: Service feature-store is officially registered under team commerce. Designated primary on-call engineer handle is lsilva.
> Catalog Record: Service graphql-federation is officially registered under team growth. Designated primary on-call engineer handle is asharma.
> Catalog Record: Service websocket-gateway is officially registered under team platform. Designated primary on-call engineer handle is bbecker.
> Catalog Record: Service webhook-dispatcher is officially registered under team payments. Designated primary on-call engineer handle is ghopper.
> Catalog Record: Service edge-router is officially registered under team commerce. Designated primary on-call engineer handle is aturing.
> Catalog Record: Service dns-resolver is officially registered under team growth. Designated primary on-call engineer handle is alovelace.

LABEL:

REASON:


### EID-S7-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S7-02` | `MEMBER_OF` | Priya Nayar (`person-priya-nayar`) → payments (`team-payments`) | `2023-01-01T00:00:00Z` |

**Source docs**

- `DOC-CATALOG`; type `catalog` (authority `2`); author_id=`None`, author_handle=`system`, author_email=`system@company.internal` → UNRESOLVED; src_conf=`1.0`

**Span (verbatim)**

> (no span recorded)

**Full source document text**

`DOC-CATALOG`:
> Service Catalog Master Index (System Generated):
> Catalog Record: Service session-cache is officially registered under team platform. Designated primary on-call engineer handle is erostova.
> Catalog Record: Service rate-limiter is officially registered under team payments. Designated primary on-call engineer handle is dpatel.
> Catalog Record: Service checkout-api is officially registered under team commerce. Designated primary on-call engineer handle is cmartin.
> Catalog Record: Service ledger is officially registered under team growth. Designated primary on-call engineer handle is skhan.
> Catalog Record: Service search-index is officially registered under team platform. Designated primary on-call engineer handle is mvance.
> Catalog Record: Service notifier is officially registered under team commerce. Designated primary on-call engineer handle is pnair.
> Catalog Record: Service auth-gateway is officially registered under team growth. Designated primary on-call engineer handle is pnayar.
> Catalog Record: Service telemetry-collector is officially registered under team platform. Designated primary on-call engineer handle is lvance.
> Catalog Record: Service billing-worker is officially registered under team payments. Designated primary on-call engineer handle is achen.
> Catalog Record: Service core-auth-service is officially registered under team commerce. Designated primary on-call engineer handle is staylor.
> Catalog Record: Service api-hub-service is officially registered under team growth. Designated primary on-call engineer handle is rgreen.
> Catalog Record: Service batch-exporter-service is officially registered under team platform. Designated primary on-call engineer handle is ksato.
> Catalog Record: Service web-frontend is officially registered under team payments. Designated primary on-call engineer handle is asterling.
> Catalog Record: Service api-gateway is officially registered under team commerce. Designated primary on-call engineer handle is doconnor.
> Catalog Record: Service redis-cluster is officially registered under team growth. Designated primary on-call engineer handle is mlin.
> Catalog Record: Service mobile-app-backend is officially registered under team platform. Designated primary on-call engineer handle is tmansoor.
> Catalog Record: Service order-service is officially registered under team payments. Designated primary on-call engineer handle is cgomez.
> Catalog Record: Service payment-vault is officially registered under team commerce. Designated primary on-call engineer handle is fzahra.
> Catalog Record: Service analytics-pipeline is officially registered under team growth. Designated primary on-call engineer handle is lmurphy.
> Catalog Record: Service event-stream is officially registered under team platform. Designated primary on-call engineer handle is ytanaka.
> Catalog Record: Service inventory-api is officially registered under team payments. Designated primary on-call engineer handle is zkravitz.
> Catalog Record: Service catalog-db is officially registered under team commerce. Designated primary on-call engineer handle is nmiller.
> Catalog Record: Service storage-cluster is officially registered under team growth. Designated primary on-call engineer handle is ewatson.
> Catalog Record: Service notification-dispatcher is officially registered under team platform. Designated primary on-call engineer handle is lsilva.
> Catalog Record: Service template-renderer is officially registered under team payments. Designated primary on-call engineer handle is asharma.
> Catalog Record: Service user-preferences is officially registered under team commerce. Designated primary on-call engineer handle is bbecker.
> Catalog Record: Service identity-provider is officially registered under team growth. Designated primary on-call engineer handle is ghopper.
> Catalog Record: Service ldap-directory is officially registered under team platform. Designated primary on-call engineer handle is aturing.
> Catalog Record: Service cart-service is officially registered under team payments. Designated primary on-call engineer handle is alovelace.
> Catalog Record: Service catalog-service is officially registered under team commerce. Designated primary on-call engineer handle is erostova.
> Catalog Record: Service pricing-engine is officially registered under team growth. Designated primary on-call engineer handle is dpatel.
> Catalog Record: Service shipping-calculator is officially registered under team platform. Designated primary on-call engineer handle is cmartin.
> Catalog Record: Service tax-calculator is officially registered under team payments. Designated primary on-call engineer handle is skhan.
> Catalog Record: Service fraud-detection is officially registered under team commerce. Designated primary on-call engineer handle is mvance.
> Catalog Record: Service audit-logger is officially registered under team growth. Designated primary on-call engineer handle is jrao.
> Catalog Record: Service metrics-collector is officially registered under team platform. Designated primary on-call engineer handle is pnair.
> Catalog Record: Service tracing-agent is officially registered under team payments. Designated primary on-call engineer handle is pnayar.
> Catalog Record: Service config-server is officially registered under team commerce. Designated primary on-call engineer handle is lvance.
> Catalog Record: Service secret-manager is officially registered under team growth. Designated primary on-call engineer handle is achen.
> Catalog Record: Service kms-vault is officially registered under team platform. Designated primary on-call engineer handle is staylor.
> Catalog Record: Service customer-portal is officially registered under team payments. Designated primary on-call engineer handle is rgreen.
> Catalog Record: Service merchant-dashboard is officially registered under team commerce. Designated primary on-call engineer handle is ksato.
> Catalog Record: Service recommendation-api is officially registered under team growth. Designated primary on-call engineer handle is asterling.
> Catalog Record: Service content-cdn is officially registered under team platform. Designated primary on-call engineer handle is doconnor.
> Catalog Record: Service image-resizer is officially registered under team payments. Designated primary on-call engineer handle is mlin.
> Catalog Record: Service video-streamer is officially registered under team commerce. Designated primary on-call engineer handle is tmansoor.
> Catalog Record: Service push-relay is officially registered under team growth. Designated primary on-call engineer handle is cgomez.
> Catalog Record: Service sms-gateway is officially registered under team platform. Designated primary on-call engineer handle is fzahra.
> Catalog Record: Service email-sender is officially registered under team payments. Designated primary on-call engineer handle is lmurphy.
> Catalog Record: Service etl-coordinator is officially registered under team commerce. Designated primary on-call engineer handle is ytanaka.
> Catalog Record: Service data-warehouse-sync is officially registered under team growth. Designated primary on-call engineer handle is zkravitz.
> Catalog Record: Service ml-inference-runner is officially registered under team platform. Designated primary on-call engineer handle is nmiller.
> Catalog Record: Service model-registry is officially registered under team payments. Designated primary on-call engineer handle is ewatson.
> Catalog Record: Service feature-store is officially registered under team commerce. Designated primary on-call engineer handle is lsilva.
> Catalog Record: Service graphql-federation is officially registered under team growth. Designated primary on-call engineer handle is asharma.
> Catalog Record: Service websocket-gateway is officially registered under team platform. Designated primary on-call engineer handle is bbecker.
> Catalog Record: Service webhook-dispatcher is officially registered under team payments. Designated primary on-call engineer handle is ghopper.
> Catalog Record: Service edge-router is officially registered under team commerce. Designated primary on-call engineer handle is aturing.
> Catalog Record: Service dns-resolver is officially registered under team growth. Designated primary on-call engineer handle is alovelace.

LABEL:

REASON:


### EID-S7-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S7-03` | `MEMBER_OF` | Jitendra Rao (`person-j-rao`) → platform (`team-platform`) | `2023-01-01T00:00:00Z` |

**Source docs**

- `DOC-CATALOG`; type `catalog` (authority `2`); author_id=`None`, author_handle=`system`, author_email=`system@company.internal` → UNRESOLVED; src_conf=`1.0`

**Span (verbatim)**

> (no span recorded)

**Full source document text**

`DOC-CATALOG`:
> Service Catalog Master Index (System Generated):
> Catalog Record: Service session-cache is officially registered under team platform. Designated primary on-call engineer handle is erostova.
> Catalog Record: Service rate-limiter is officially registered under team payments. Designated primary on-call engineer handle is dpatel.
> Catalog Record: Service checkout-api is officially registered under team commerce. Designated primary on-call engineer handle is cmartin.
> Catalog Record: Service ledger is officially registered under team growth. Designated primary on-call engineer handle is skhan.
> Catalog Record: Service search-index is officially registered under team platform. Designated primary on-call engineer handle is mvance.
> Catalog Record: Service notifier is officially registered under team commerce. Designated primary on-call engineer handle is pnair.
> Catalog Record: Service auth-gateway is officially registered under team growth. Designated primary on-call engineer handle is pnayar.
> Catalog Record: Service telemetry-collector is officially registered under team platform. Designated primary on-call engineer handle is lvance.
> Catalog Record: Service billing-worker is officially registered under team payments. Designated primary on-call engineer handle is achen.
> Catalog Record: Service core-auth-service is officially registered under team commerce. Designated primary on-call engineer handle is staylor.
> Catalog Record: Service api-hub-service is officially registered under team growth. Designated primary on-call engineer handle is rgreen.
> Catalog Record: Service batch-exporter-service is officially registered under team platform. Designated primary on-call engineer handle is ksato.
> Catalog Record: Service web-frontend is officially registered under team payments. Designated primary on-call engineer handle is asterling.
> Catalog Record: Service api-gateway is officially registered under team commerce. Designated primary on-call engineer handle is doconnor.
> Catalog Record: Service redis-cluster is officially registered under team growth. Designated primary on-call engineer handle is mlin.
> Catalog Record: Service mobile-app-backend is officially registered under team platform. Designated primary on-call engineer handle is tmansoor.
> Catalog Record: Service order-service is officially registered under team payments. Designated primary on-call engineer handle is cgomez.
> Catalog Record: Service payment-vault is officially registered under team commerce. Designated primary on-call engineer handle is fzahra.
> Catalog Record: Service analytics-pipeline is officially registered under team growth. Designated primary on-call engineer handle is lmurphy.
> Catalog Record: Service event-stream is officially registered under team platform. Designated primary on-call engineer handle is ytanaka.
> Catalog Record: Service inventory-api is officially registered under team payments. Designated primary on-call engineer handle is zkravitz.
> Catalog Record: Service catalog-db is officially registered under team commerce. Designated primary on-call engineer handle is nmiller.
> Catalog Record: Service storage-cluster is officially registered under team growth. Designated primary on-call engineer handle is ewatson.
> Catalog Record: Service notification-dispatcher is officially registered under team platform. Designated primary on-call engineer handle is lsilva.
> Catalog Record: Service template-renderer is officially registered under team payments. Designated primary on-call engineer handle is asharma.
> Catalog Record: Service user-preferences is officially registered under team commerce. Designated primary on-call engineer handle is bbecker.
> Catalog Record: Service identity-provider is officially registered under team growth. Designated primary on-call engineer handle is ghopper.
> Catalog Record: Service ldap-directory is officially registered under team platform. Designated primary on-call engineer handle is aturing.
> Catalog Record: Service cart-service is officially registered under team payments. Designated primary on-call engineer handle is alovelace.
> Catalog Record: Service catalog-service is officially registered under team commerce. Designated primary on-call engineer handle is erostova.
> Catalog Record: Service pricing-engine is officially registered under team growth. Designated primary on-call engineer handle is dpatel.
> Catalog Record: Service shipping-calculator is officially registered under team platform. Designated primary on-call engineer handle is cmartin.
> Catalog Record: Service tax-calculator is officially registered under team payments. Designated primary on-call engineer handle is skhan.
> Catalog Record: Service fraud-detection is officially registered under team commerce. Designated primary on-call engineer handle is mvance.
> Catalog Record: Service audit-logger is officially registered under team growth. Designated primary on-call engineer handle is jrao.
> Catalog Record: Service metrics-collector is officially registered under team platform. Designated primary on-call engineer handle is pnair.
> Catalog Record: Service tracing-agent is officially registered under team payments. Designated primary on-call engineer handle is pnayar.
> Catalog Record: Service config-server is officially registered under team commerce. Designated primary on-call engineer handle is lvance.
> Catalog Record: Service secret-manager is officially registered under team growth. Designated primary on-call engineer handle is achen.
> Catalog Record: Service kms-vault is officially registered under team platform. Designated primary on-call engineer handle is staylor.
> Catalog Record: Service customer-portal is officially registered under team payments. Designated primary on-call engineer handle is rgreen.
> Catalog Record: Service merchant-dashboard is officially registered under team commerce. Designated primary on-call engineer handle is ksato.
> Catalog Record: Service recommendation-api is officially registered under team growth. Designated primary on-call engineer handle is asterling.
> Catalog Record: Service content-cdn is officially registered under team platform. Designated primary on-call engineer handle is doconnor.
> Catalog Record: Service image-resizer is officially registered under team payments. Designated primary on-call engineer handle is mlin.
> Catalog Record: Service video-streamer is officially registered under team commerce. Designated primary on-call engineer handle is tmansoor.
> Catalog Record: Service push-relay is officially registered under team growth. Designated primary on-call engineer handle is cgomez.
> Catalog Record: Service sms-gateway is officially registered under team platform. Designated primary on-call engineer handle is fzahra.
> Catalog Record: Service email-sender is officially registered under team payments. Designated primary on-call engineer handle is lmurphy.
> Catalog Record: Service etl-coordinator is officially registered under team commerce. Designated primary on-call engineer handle is ytanaka.
> Catalog Record: Service data-warehouse-sync is officially registered under team growth. Designated primary on-call engineer handle is zkravitz.
> Catalog Record: Service ml-inference-runner is officially registered under team platform. Designated primary on-call engineer handle is nmiller.
> Catalog Record: Service model-registry is officially registered under team payments. Designated primary on-call engineer handle is ewatson.
> Catalog Record: Service feature-store is officially registered under team commerce. Designated primary on-call engineer handle is lsilva.
> Catalog Record: Service graphql-federation is officially registered under team growth. Designated primary on-call engineer handle is asharma.
> Catalog Record: Service websocket-gateway is officially registered under team platform. Designated primary on-call engineer handle is bbecker.
> Catalog Record: Service webhook-dispatcher is officially registered under team payments. Designated primary on-call engineer handle is ghopper.
> Catalog Record: Service edge-router is officially registered under team commerce. Designated primary on-call engineer handle is aturing.
> Catalog Record: Service dns-resolver is officially registered under team growth. Designated primary on-call engineer handle is alovelace.

LABEL:

REASON:


### EID-S7-04

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S7-04` | `ON_CALL` | Jitendra Rao (`person-j-rao`) → session-cache (`service-session-cache`) | `2023-09-01T10:00:00Z` |

**Source docs**

- `DOC-S7-1`; type `runbook` (authority `2`); author_id=`None`, author_handle=`None`, author_email=`j.rao@company.internal` → Jitendra Rao (`person-j-rao`), team platform (`team-platform`); src_conf=`0.95`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Maintenance managed by j.rao@company.internal.

**Full source document text**

`DOC-S7-1`:
> Execute the redis warmup cache script before traffic peaks. Maintenance managed by j.rao@company.internal.

LABEL:

REASON:


## S8

### EID-S8-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S8-01` | `OWNS` | payments (`team-payments`) → ledger (`service-ledger`) | `2023-03-01T10:00:00Z` |

**Source docs**

- `DOC-ADR-LEDGER`; type `adr` (authority `3`); author_id=`person-dev-patel`, author_handle=`dpatel`, author_email=`dev.patel@company.internal` → Dev Patel (`person-dev-patel`), team payments (`team-payments`); src_conf=`1.0`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Payments team owns ledger service and maintains the double-entry accounting records.

**Full source document text**

`DOC-ADR-LEDGER`:
> Payments team owns ledger service and maintains the double-entry accounting records. No other team may alter ledger schema.

LABEL:

REASON:


### EID-S8-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S8-02` | `OWNS` | commerce (`team-commerce`) → ledger (`service-ledger`) | `2024-03-20T10:00:00Z` |

**Source docs**

- `T-S8`; type `ticket` (authority `2`); author_id=`person-leo-vance`, author_handle=`lvance`, author_email=`leo.vance@company.internal` → Leo Vance (`person-leo-vance`), team commerce (`team-commerce`); src_conf=`0.75`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Commerce team claims ownership of ledger service to unify billing records.

**Full source document text**

`T-S8`:
> Commerce team claims ownership of ledger service to unify billing records.
> Approved by Leo Vance: self-approval for organizational transfer.

LABEL:

REASON:


### EID-S8-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S8-03` | `APPROVED` | Leo Vance (`person-leo-vance`) → ledger (`service-ledger`) | `2024-03-20T10:00:00Z` |

**Source docs**

- `T-S8`; type `ticket` (authority `2`); author_id=`person-leo-vance`, author_handle=`lvance`, author_email=`leo.vance@company.internal` → Leo Vance (`person-leo-vance`), team commerce (`team-commerce`); src_conf=`0.75`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Approved by Leo Vance: self-approval for organizational transfer.

**Full source document text**

`T-S8`:
> Commerce team claims ownership of ledger service to unify billing records.
> Approved by Leo Vance: self-approval for organizational transfer.

LABEL:

REASON:


## S9a

### EID-S9A-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S9A-01` | `OWNS` | growth (`team-growth`) → telemetry-collector (`service-telemetry-collector`) | `2024-01-10T10:00:00Z` |

**Source docs**

- `DOC-S9A-1`; type `chat` (authority `1`); author_id=`None`, author_handle=`achen`, author_email=`None` → Alex Chen (`person-alex-chen`), team growth (`team-growth`); src_conf=`0.6`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Growth team claims ownership of telemetry-collector for experiment metrics.

**Full source document text**

`DOC-S9A-1`:
> Growth team claims ownership of telemetry-collector for experiment metrics.

LABEL:

REASON:


### EID-S9A-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S9A-02` | `OWNS` | growth (`team-growth`) → telemetry-collector (`service-telemetry-collector`) | `2024-01-11T10:00:00Z` |

**Source docs**

- `DOC-S9A-2`; type `chat` (authority `1`); author_id=`None`, author_handle=`None`, author_email=`alex.chen@company.internal` → Alex Chen (`person-alex-chen`), team growth (`team-growth`); src_conf=`0.6`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Growth team claims ownership of telemetry-collector for experiment metrics.

**Full source document text**

`DOC-S9A-2`:
> Growth team claims ownership of telemetry-collector for experiment metrics.

LABEL:

REASON:


### EID-S9A-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S9A-03` | `OWNS` | growth (`team-growth`) → telemetry-collector (`service-telemetry-collector`) | `2024-01-12T10:00:00Z` |

**Source docs**

- `DOC-S9A-3`; type `chat` (authority `1`); author_id=`None`, author_handle=`Alex C.`, author_email=`None` → Alex Chen (`person-alex-chen`), team growth (`team-growth`); src_conf=`0.6`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Growth team claims ownership of telemetry-collector for experiment metrics.

**Full source document text**

`DOC-S9A-3`:
> Growth team claims ownership of telemetry-collector for experiment metrics.

LABEL:

REASON:


## S9b

### EID-S9B-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S9B-01` | `OWNS` | payments (`team-payments`) → billing-worker (`service-billing-worker`) | `2024-01-15T11:00:00Z` |

**Source docs**

- `DOC-S9B-1`; type `ticket` (authority `2`); author_id=`None`, author_handle=`staylor`, author_email=`None` → Sophia Taylor (`person-sophia-taylor`), team payments (`team-payments`); src_conf=`0.6`

**Catalog owner of destination service:** payments (`team-payments`)

**Span (verbatim)**

> Payments team claims ownership of billing-worker to manage automated invoicing cycles.

**Full source document text**

`DOC-S9B-1`:
> Payments team claims ownership of billing-worker to manage automated invoicing cycles.

LABEL:

REASON:


### EID-S9B-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S9B-02` | `OWNS` | payments (`team-payments`) → billing-worker (`service-billing-worker`) | `2024-01-16T11:00:00Z` |

**Source docs**

- `DOC-S9B-2`; type `ticket` (authority `2`); author_id=`None`, author_handle=`None`, author_email=`sophia.taylor@company.internal` → Sophia Taylor (`person-sophia-taylor`), team payments (`team-payments`); src_conf=`0.6`

**Catalog owner of destination service:** payments (`team-payments`)

**Span (verbatim)**

> Payments team claims ownership of billing-worker to manage automated invoicing cycles.

**Full source document text**

`DOC-S9B-2`:
> Payments team claims ownership of billing-worker to manage automated invoicing cycles.

LABEL:

REASON:


### EID-S9B-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S9B-03` | `OWNS` | payments (`team-payments`) → billing-worker (`service-billing-worker`) | `2024-01-17T11:00:00Z` |

**Source docs**

- `DOC-S9B-3`; type `ticket` (authority `2`); author_id=`None`, author_handle=`S. Taylor`, author_email=`None` → Sophia Taylor (`person-sophia-taylor`), team payments (`team-payments`); src_conf=`0.6`

**Catalog owner of destination service:** payments (`team-payments`)

**Span (verbatim)**

> Payments team claims ownership of billing-worker to manage automated invoicing cycles.

**Full source document text**

`DOC-S9B-3`:
> Payments team claims ownership of billing-worker to manage automated invoicing cycles.

LABEL:

REASON:


## S10

### EID-S10-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S10-01` | `OWNS` | commerce (`team-commerce`) → notifier (`service-notifier`) | `2024-02-10T10:00:00Z` |

**Source docs**

- `DOC-ADR-NOTIFIER-COMMERCE`; type `adr` (authority `3`); author_id=`person-rachel-green`, author_handle=`rgreen`, author_email=`rachel.green@company.internal` → Rachel Green (`person-rachel-green`), team commerce (`team-commerce`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Commerce team owns notifier service to manage promotional and transactional emails directly.

**Full source document text**

`DOC-ADR-NOTIFIER-COMMERCE`:
> Commerce team owns notifier service to manage promotional and transactional emails directly.

LABEL:

REASON:


### EID-S10-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-S10-02` | `OWNS` | platform (`team-platform`) → notifier (`service-notifier`) | `2024-02-12T10:00:00Z` |

**Source docs**

- `DOC-ADR-NOTIFIER-PLATFORM`; type `adr` (authority `3`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Platform team owns notifier service as shared enterprise notification infrastructure.

**Full source document text**

`DOC-ADR-NOTIFIER-PLATFORM`:
> Platform team owns notifier service as shared enterprise notification infrastructure.

LABEL:

REASON:


## M1

### EID-M1-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M1-01` | `DEPENDS_ON` | web-frontend (`service-web-frontend`) → api-gateway (`service-api-gateway`) | `2023-07-01T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M1`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Service web-frontend depends on api-gateway.

**Full source document text**

`DOC-RUNBOOK-M1`:
> Service web-frontend depends on api-gateway. Service api-gateway depends on session-cache. Service session-cache depends on redis-cluster.

LABEL:

REASON:


### EID-M1-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M1-02` | `DEPENDS_ON` | api-gateway (`service-api-gateway`) → session-cache (`service-session-cache`) | `2023-07-01T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M1`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Service api-gateway depends on session-cache.

**Full source document text**

`DOC-RUNBOOK-M1`:
> Service web-frontend depends on api-gateway. Service api-gateway depends on session-cache. Service session-cache depends on redis-cluster.

LABEL:

REASON:


### EID-M1-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M1-03` | `DEPENDS_ON` | session-cache (`service-session-cache`) → redis-cluster (`service-redis-cluster`) | `2023-07-01T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M1`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Service session-cache depends on redis-cluster.

**Full source document text**

`DOC-RUNBOOK-M1`:
> Service web-frontend depends on api-gateway. Service api-gateway depends on session-cache. Service session-cache depends on redis-cluster.

LABEL:

REASON:


## M2

### EID-M2-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M2-01` | `DEPENDS_ON` | mobile-app-backend (`service-mobile-app-backend`) → order-service (`service-order-service`) | `2023-07-02T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M2`; type `runbook` (authority `2`); author_id=`person-dev-patel`, author_handle=`dpatel`, author_email=`dev.patel@company.internal` → Dev Patel (`person-dev-patel`), team payments (`team-payments`); src_conf=`1.0`

**Catalog owner of destination service:** payments (`team-payments`)

**Span (verbatim)**

> Service mobile-app-backend depends on order-service.

**Full source document text**

`DOC-RUNBOOK-M2`:
> Service mobile-app-backend depends on order-service. Service order-service depends on checkout-api. Service checkout-api depends on ledger. Service ledger depends on payment-vault.

LABEL:

REASON:


### EID-M2-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M2-02` | `DEPENDS_ON` | order-service (`service-order-service`) → checkout-api (`service-checkout-api`) | `2023-07-02T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M2`; type `runbook` (authority `2`); author_id=`person-dev-patel`, author_handle=`dpatel`, author_email=`dev.patel@company.internal` → Dev Patel (`person-dev-patel`), team payments (`team-payments`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Service order-service depends on checkout-api.

**Full source document text**

`DOC-RUNBOOK-M2`:
> Service mobile-app-backend depends on order-service. Service order-service depends on checkout-api. Service checkout-api depends on ledger. Service ledger depends on payment-vault.

LABEL:

REASON:


### EID-M2-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M2-03` | `DEPENDS_ON` | checkout-api (`service-checkout-api`) → ledger (`service-ledger`) | `2023-07-02T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M2`; type `runbook` (authority `2`); author_id=`person-dev-patel`, author_handle=`dpatel`, author_email=`dev.patel@company.internal` → Dev Patel (`person-dev-patel`), team payments (`team-payments`); src_conf=`1.0`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Service checkout-api depends on ledger.

**Full source document text**

`DOC-RUNBOOK-M2`:
> Service mobile-app-backend depends on order-service. Service order-service depends on checkout-api. Service checkout-api depends on ledger. Service ledger depends on payment-vault.

LABEL:

REASON:


### EID-M2-04

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M2-04` | `DEPENDS_ON` | ledger (`service-ledger`) → payment-vault (`service-payment-vault`) | `2023-07-02T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M2`; type `runbook` (authority `2`); author_id=`person-dev-patel`, author_handle=`dpatel`, author_email=`dev.patel@company.internal` → Dev Patel (`person-dev-patel`), team payments (`team-payments`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Service ledger depends on payment-vault.

**Full source document text**

`DOC-RUNBOOK-M2`:
> Service mobile-app-backend depends on order-service. Service order-service depends on checkout-api. Service checkout-api depends on ledger. Service ledger depends on payment-vault.

LABEL:

REASON:


## M3

### EID-M3-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M3-01` | `DEPENDS_ON` | analytics-pipeline (`service-analytics-pipeline`) → event-stream (`service-event-stream`) | `2023-07-03T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M3`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Service analytics-pipeline depends on event-stream.

**Full source document text**

`DOC-RUNBOOK-M3`:
> Service analytics-pipeline depends on event-stream. Service event-stream depends on search-index. Service search-index depends on inventory-api. Service inventory-api depends on catalog-db. Service catalog-db depends on storage-cluster.

LABEL:

REASON:


### EID-M3-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M3-02` | `DEPENDS_ON` | event-stream (`service-event-stream`) → search-index (`service-search-index`) | `2023-07-03T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M3`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Service event-stream depends on search-index.

**Full source document text**

`DOC-RUNBOOK-M3`:
> Service analytics-pipeline depends on event-stream. Service event-stream depends on search-index. Service search-index depends on inventory-api. Service inventory-api depends on catalog-db. Service catalog-db depends on storage-cluster.

LABEL:

REASON:


### EID-M3-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M3-03` | `DEPENDS_ON` | search-index (`service-search-index`) → inventory-api (`service-inventory-api`) | `2023-07-03T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M3`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** payments (`team-payments`)

**Span (verbatim)**

> Service search-index depends on inventory-api.

**Full source document text**

`DOC-RUNBOOK-M3`:
> Service analytics-pipeline depends on event-stream. Service event-stream depends on search-index. Service search-index depends on inventory-api. Service inventory-api depends on catalog-db. Service catalog-db depends on storage-cluster.

LABEL:

REASON:


### EID-M3-04

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M3-04` | `DEPENDS_ON` | inventory-api (`service-inventory-api`) → catalog-db (`service-catalog-db`) | `2023-07-03T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M3`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Service inventory-api depends on catalog-db.

**Full source document text**

`DOC-RUNBOOK-M3`:
> Service analytics-pipeline depends on event-stream. Service event-stream depends on search-index. Service search-index depends on inventory-api. Service inventory-api depends on catalog-db. Service catalog-db depends on storage-cluster.

LABEL:

REASON:


### EID-M3-05

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M3-05` | `DEPENDS_ON` | catalog-db (`service-catalog-db`) → storage-cluster (`service-storage-cluster`) | `2023-07-03T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M3`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Service catalog-db depends on storage-cluster.

**Full source document text**

`DOC-RUNBOOK-M3`:
> Service analytics-pipeline depends on event-stream. Service event-stream depends on search-index. Service search-index depends on inventory-api. Service inventory-api depends on catalog-db. Service catalog-db depends on storage-cluster.

LABEL:

REASON:


## M4

### EID-M4-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M4-01` | `DEPENDS_ON` | notification-dispatcher (`service-notification-dispatcher`) → notifier (`service-notifier`) | `2023-07-04T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M4`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Service notification-dispatcher depends on notifier.

**Full source document text**

`DOC-RUNBOOK-M4`:
> Service notification-dispatcher depends on notifier. Service notifier depends on template-renderer. Service template-renderer depends on user-preferences. Service user-preferences depends on auth-gateway. Service auth-gateway depends on identity-provider. Service identity-provider depends on ldap-directory.

LABEL:

REASON:


### EID-M4-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M4-02` | `DEPENDS_ON` | notifier (`service-notifier`) → template-renderer (`service-template-renderer`) | `2023-07-04T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M4`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** payments (`team-payments`)

**Span (verbatim)**

> Service notifier depends on template-renderer.

**Full source document text**

`DOC-RUNBOOK-M4`:
> Service notification-dispatcher depends on notifier. Service notifier depends on template-renderer. Service template-renderer depends on user-preferences. Service user-preferences depends on auth-gateway. Service auth-gateway depends on identity-provider. Service identity-provider depends on ldap-directory.

LABEL:

REASON:


### EID-M4-03

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M4-03` | `DEPENDS_ON` | template-renderer (`service-template-renderer`) → user-preferences (`service-user-preferences`) | `2023-07-04T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M4`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Service template-renderer depends on user-preferences.

**Full source document text**

`DOC-RUNBOOK-M4`:
> Service notification-dispatcher depends on notifier. Service notifier depends on template-renderer. Service template-renderer depends on user-preferences. Service user-preferences depends on auth-gateway. Service auth-gateway depends on identity-provider. Service identity-provider depends on ldap-directory.

LABEL:

REASON:


### EID-M4-04

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M4-04` | `DEPENDS_ON` | user-preferences (`service-user-preferences`) → auth-gateway (`service-auth-gateway`) | `2023-07-04T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M4`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Service user-preferences depends on auth-gateway.

**Full source document text**

`DOC-RUNBOOK-M4`:
> Service notification-dispatcher depends on notifier. Service notifier depends on template-renderer. Service template-renderer depends on user-preferences. Service user-preferences depends on auth-gateway. Service auth-gateway depends on identity-provider. Service identity-provider depends on ldap-directory.

LABEL:

REASON:


### EID-M4-05

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M4-05` | `DEPENDS_ON` | auth-gateway (`service-auth-gateway`) → identity-provider (`service-identity-provider`) | `2023-07-04T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M4`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** growth (`team-growth`)

**Span (verbatim)**

> Service auth-gateway depends on identity-provider.

**Full source document text**

`DOC-RUNBOOK-M4`:
> Service notification-dispatcher depends on notifier. Service notifier depends on template-renderer. Service template-renderer depends on user-preferences. Service user-preferences depends on auth-gateway. Service auth-gateway depends on identity-provider. Service identity-provider depends on ldap-directory.

LABEL:

REASON:


### EID-M4-06

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-M4-06` | `DEPENDS_ON` | identity-provider (`service-identity-provider`) → ldap-directory (`service-ldap-directory`) | `2023-07-04T10:00:00Z` |

**Source docs**

- `DOC-RUNBOOK-M4`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** platform (`team-platform`)

**Span (verbatim)**

> Service identity-provider depends on ldap-directory.

**Full source document text**

`DOC-RUNBOOK-M4`:
> Service notification-dispatcher depends on notifier. Service notifier depends on template-renderer. Service template-renderer depends on user-preferences. Service user-preferences depends on auth-gateway. Service auth-gateway depends on identity-provider. Service identity-provider depends on ldap-directory.

LABEL:

REASON:


## P1

### EID-P1-01

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-P1-01` | `DEPENDS_ON` | api-hub-service (`service-api-hub`) → core-auth-service (`service-core-auth`) | `2023-08-01T10:00:00Z` |

**Source docs**

- `DOC-ARCH-P1`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Service api-hub-service depends on core-auth-service for gateway token verification.

**Full source document text**

`DOC-ARCH-P1`:
> Service api-hub-service depends on core-auth-service for gateway token verification. Service batch-exporter-service depends on core-auth-service for nocturnal batch sync.

LABEL:

REASON:


### EID-P1-02

| eid | type | src name → dst name | valid_from |
| --- | --- | --- | --- |
| `EID-P1-02` | `DEPENDS_ON` | batch-exporter-service (`service-batch-exporter`) → core-auth-service (`service-core-auth`) | `2023-08-01T10:00:00Z` |

**Source docs**

- `DOC-ARCH-P1`; type `runbook` (authority `2`); author_id=`person-platform-lead`, author_handle=`erostova`, author_email=`elena.rostova@company.internal` → Elena Rostova (`person-platform-lead`), team platform (`team-platform`); src_conf=`1.0`

**Catalog owner of destination service:** commerce (`team-commerce`)

**Span (verbatim)**

> Service batch-exporter-service depends on core-auth-service for nocturnal batch sync.

**Full source document text**

`DOC-ARCH-P1`:
> Service api-hub-service depends on core-auth-service for gateway token verification. Service batch-exporter-service depends on core-auth-service for nocturnal batch sync.

LABEL:

REASON:
