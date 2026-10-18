# SQLite versus FalkorDB timing

Exact identical reverse closure; recursive SQLite UNION prevents repeated vertices. FalkorDB uses bounded-frontier Q1 with a visited set.

| Mode | SQLite median ms | FalkorDB median ms | Faster |
| --- | ---: | ---: | --- |
| connection_cold | 0.1854 | 3.3018 | SQLite |
| warm | 0.0870 | 1.8568 | SQLite |

n=20 per engine/mode, 210 dependencies, 59 exact affected services. Every timed result matched.

new client/connection including connection establishment; server and OS caches not flushed. This is connection-cold, not a hardware/server-cache cold benchmark. SQLite runs in-process; FalkorDB includes local network round trips. No DB restart or global cache-flushing was performed. Common ACL projection/ingestion is excluded from both query timings. SQLite CTE is unbounded UNION closure; Q1 expands until no unseen nodes, and the actual DAG converges within the eight-hop tool bound.
