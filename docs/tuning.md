# Development-only severity tuning

Chosen pagerank_severity_cutoff: **0.019535258803056135**.

Only four cases/dev_cases.jsonl inputs and their explicit synthetic severity rubric were used. No frozen answers/outcomes or evaluation failures were used to choose the cutoff. These primary input services are absent from the frozen primary inputs; they can still be dependency neighbors in the same synthetic graph.

| Dev service | Expected severity | PageRank |
| --- | --- | ---: |
| dns-resolver | elevated | 0.026454735301243371 |
| etl-coordinator | normal | 0.012615782304868898 |
| image-resizer | elevated | 0.030399790672599247 |
| ml-inference-runner | normal | 0.0096097378387881727 |

Cutoff is the midpoint of maximum normal 0.012615782304868898 and minimum elevated 0.026454735301243371, maximizing the separating margin for this dev rubric (4/4 dev severity classifications).

This separates DNS/image delivery infrastructure from ETL/ML batch work on the synthetic graph. It is not a production severity calibration. It does not change ACT/READ confidence thresholds or grant authorization. No LLM was needed to fit this one scalar.

Config frozen SHA-256: `7dcfd3b901e00e07e62f55c80dd5c74b8460fd154c99f8310577f274e55a4619`. The eval runner refuses config/dev changes and records case/prompt/model hashes before the one frozen evaluation. Timing measurements are independent of severity fitting.
