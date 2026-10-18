"""Queries frozen before scale generation or measurement."""
RELATIONS = ['OWNS', 'DEPENDS_ON', 'ON_CALL', 'CONCERNS']
FALKOR = {
 'Q1': "MATCH p=(a:Service)-[:DEPENDS_ON*1..6]->(b:Service {id:$service}) WHERE a.id<>b.id AND all(e IN relationships(p) WHERE e.status='current') RETURN a.id,min(length(p)) ORDER BY a.id",
 'Q3': "MATCH p=(a:Entity {id:$start})-[:OWNS|DEPENDS_ON|ON_CALL|CONCERNS*1..6]->(b:Entity {id:$target}) WHERE all(e IN relationships(p) WHERE e.status='current') RETURN DISTINCT b.id ORDER BY b.id",
 'Q6': "MATCH p=(a:Decision {id:$topic})-[:SUPERSEDES|BECAUSE_OF*1..8]->(b) WHERE all(e IN relationships(p) WHERE e.status='current') RETURN DISTINCT b.id ORDER BY b.id",
 'Q9': "MATCH (t:Team) OPTIONAL MATCH (t)-[e]->() WHERE e.status='contested' RETURN t.id,count(e) ORDER BY t.id",
}
SQLITE = {
 'Q1': "WITH RECURSIVE walk(id,depth) AS (SELECT :service,0 UNION SELECT e.src,w.depth+1 FROM edges e JOIN walk w ON e.dst=w.id WHERE e.type='DEPENDS_ON' AND e.status='current' AND w.depth<6) SELECT id,min(depth) FROM walk WHERE depth>0 AND id<>:service GROUP BY id ORDER BY id",
 'Q3': "WITH RECURSIVE walk(id,depth) AS (SELECT :start,0 UNION SELECT e.dst,w.depth+1 FROM edges e JOIN walk w ON e.src=w.id WHERE e.type IN ('OWNS','DEPENDS_ON','ON_CALL','CONCERNS') AND e.status='current' AND w.depth<6) SELECT DISTINCT id FROM walk WHERE depth>0 AND id=:target ORDER BY id",
 'Q6': "WITH RECURSIVE walk(id,depth) AS (SELECT :topic,0 UNION SELECT e.dst,w.depth+1 FROM edges e JOIN walk w ON e.src=w.id WHERE e.type IN ('SUPERSEDES','BECAUSE_OF') AND e.status='current' AND w.depth<8) SELECT DISTINCT id FROM walk WHERE depth>0 ORDER BY id",
 'Q9': "SELECT n.id,count(e.eid) FROM nodes n LEFT JOIN edges e ON e.src=n.id AND e.status='contested' WHERE n.label='Team' GROUP BY n.id ORDER BY n.id",
}
