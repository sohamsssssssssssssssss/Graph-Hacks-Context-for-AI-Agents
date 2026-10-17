"""Live check after sparse-deps change. Run from repo folder: python3.11 block0_check.py"""
import time
from falkordb import FalkorDB

g = FalkorDB(host="localhost", port=6380).select_graph("keystone")

print("== counts ==")
print(g.query("MATCH (n) RETURN count(n)").result_set[0][0], "nodes")
print(g.query("MATCH ()-[e]->() RETURN count(e)").result_set[0][0], "edges")
print(g.query("MATCH ()-[e:DEPENDS_ON]->() RETURN count(e)").result_set[0][0], "DEPENDS_ON")

Q = ("MATCH p=(s:Service {name:$n})<-[:DEPENDS_ON*1..6]-(a:Service) "
     "RETURN a.name, min(length(p))")
print("\n== blast radius timing ==")
for n in ["core-auth-service", "api-hub-service"]:
    t = time.time()
    rows = g.query(Q, {"n": n}, timeout=60000).result_set
    print(f"{n}: {len(rows)} services, {time.time()-t:.2f}s")

print("\n== pageRank ==")
rows = g.query("CALL algo.pageRank('Service','DEPENDS_ON') YIELD node, score "
               "RETURN node.name, score ORDER BY score DESC").result_set
for r in rows[:5]:
    print(r)
sc = {r[0]: r[1] for r in rows}
a, b = sc.get("api-hub-service"), sc.get("batch-exporter-service")
print("api-hub:", a, "batch-exporter:", b, "ratio:", (a / b) if a and b else None)

print("\n== blast radius size across all services ==")
names = [r[0] for r in g.query("MATCH (s:Service) RETURN s.name").result_set]
sizes = []
for n in names:
    c = g.query("MATCH (s:Service {name:$n})<-[:DEPENDS_ON*1..6]-(a:Service) "
                "RETURN count(DISTINCT a)", {"n": n}, timeout=10000).result_set[0][0]
    sizes.append((c, n))
sizes.sort(reverse=True)
print("largest:", sizes[:5])
print("median:", sorted(c for c, _ in sizes)[len(sizes) // 2])
print("zero-dependents:", sum(1 for c, _ in sizes if c == 0))
