"""Read-only parameterized graph access. ACL metadata precedes content retrieval."""
import os


class GraphStore:
    def __init__(self, graph=None, clearance=False):
        if graph is None:
            from falkordb import FalkorDB
            graph = FalkorDB(host=os.getenv("FALKORDB_HOST", "localhost"),
                             port=int(os.getenv("FALKORDB_PORT", "6380")),
                             password=os.getenv("FALKORDB_PASSWORD") or None).select_graph(os.getenv("FALKORDB_GRAPH", "keystone"))
        self.graph = graph
        self.clearance = clearance

    def pages(self, query, params=None):
        rows, cursor = [], -1
        while True:
            page = self.graph.query(query, {**(params or {}), "cursor": cursor, "limit": 1000}).result_set
            if not page:
                return rows
            rows.extend(page)
            cursor = page[-1][0]

    def snapshot(self):
        metadata = self.pages("MATCH (n) WHERE NOT n:Commit AND id(n)>$cursor "
                              "RETURN id(n),n.id,labels(n)[0],n.restricted ORDER BY id(n) LIMIT $limit")
        allowed = {row[1]: row[0] for row in metadata if self.clearance or not row[3]}
        nodes = self.graph.query("MATCH (n) WHERE id(n) IN $ids RETURN properties(n),labels(n)[0]",
                                 {"ids": list(allowed.values())}).result_set
        # Content query above is restricted to IDs authorized by the metadata query.
        docs, entities = [], []
        for props, label in nodes:
            props = dict(props)
            if label == "Doc":
                docs.append(props)
            entities.append({**props, "label": label})
        doc_ids = {d["id"] for d in docs}
        rows = self.pages("MATCH (a)-[e]->(b) WHERE NOT a:Commit AND NOT b:Commit AND id(e)>$cursor "
                          "RETURN id(e),e.eid,type(e),a.id,b.id,e.src_ids,e.src_conf,e.src_auth,e.valid_from,e.valid_to,e.status "
                          "ORDER BY id(e) LIMIT $limit")
        visible, ids = [], []
        native_ok = self.clearance and all(self.clearance or not row[3] for row in metadata)
        for row in rows:
            internal, eid, kind, src, dst, sources, conf, auth, start, end, status = row
            sources = sources or []
            permitted = src in allowed and dst in allowed and (not sources or any(s in doc_ids for s in sources))
            if kind == "DEPENDS_ON" and (not permitted or status != "current"):
                native_ok = False
            if not permitted:
                continue
            indexes = [i for i, sid in enumerate(sources) if sid in doc_ids]
            visible.append({"eid": eid, "type": kind, "src": src, "dst": dst,
                "src_ids": [sources[i] for i in indexes], "src_conf": [(conf or [])[i] for i in indexes],
                "src_auth": [(auth or [])[i] for i in indexes], "valid_from": start, "valid_to": end,
                "status": status, "spans": []})
            ids.append(internal)
        # Never request spans for an unauthorized edge or source-only hidden claim.
        spans = self.graph.query("MATCH ()-[e]->() WHERE id(e) IN $ids RETURN e.eid,e.spans", {"ids": ids}).result_set
        by_eid = dict(spans)
        texts = {d["id"]: d.get("text", "") for d in docs}
        for edge in visible:
            original = by_eid.get(edge["eid"]) or []
            edge["spans"] = [span for span in original if any(span in texts[sid] for sid in edge["src_ids"])]
            edge["citation_invalid"] = len(original) != len(edge["spans"])
        return entities, visible, docs, native_ok

    def candidate_paths(self, start, target, allowed):
        # Server-owned literal bound; no client-provided Cypher or relationship types.
        rows = self.graph.query(
            "MATCH p=(a {id:$start})-[:OWNS|DEPENDS_ON|ON_CALL|CONCERNS*1..8]->(b {id:$target}) "
            "WHERE all(e IN relationships(p) WHERE e.status='current' AND e.eid IN $allowed) "
            "RETURN [e IN relationships(p) | e.eid] LIMIT 100", {"start": start, "target": target, "allowed": allowed}).result_set
        return [row[0] for row in rows]

    def pagerank(self):
        return self.graph.query("CALL algo.pageRank('Service','DEPENDS_ON') YIELD node,score RETURN node.id,score").result_set
