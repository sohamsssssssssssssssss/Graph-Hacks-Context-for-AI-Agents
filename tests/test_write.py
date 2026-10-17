from types import SimpleNamespace

import pytest

from derive import write_results


class Graph:
    def __init__(self, rows):
        self.rows = rows
        self.writes = []
        self.cursors = []

    def query(self, query, params=None):
        if "WHERE id(e)>$cursor" in query:
            self.cursors.append(params["cursor"])
            return SimpleNamespace(result_set=[r for r in self.rows if r[0] > params["cursor"]][:params["limit"]])
        if query.startswith("UNWIND"):
            self.writes.extend(params["batch"])
            return SimpleNamespace(result_set=[])
        return SimpleNamespace(result_set=[["current", len(self.rows)]])


EDGES = [{"eid": "E1", "src": "a", "dst": "b", "type": "DEPENDS_ON"},
         {"eid": "E2", "src": "b", "dst": "c", "type": "DEPENDS_ON"}]
RESULTS = {e["eid"]: {"status": "current", "derived_reason": "D0b: test", "valid_to": None} for e in EDGES}


def test_write_paginates_internal_ids():
    graph = Graph([[4, "E1", "a", "b", "DEPENDS_ON"], [19, "E2", "b", "c", "DEPENDS_ON"]])
    assert write_results(graph, EDGES, RESULTS, batch_size=1) == [["current", 2]]
    assert graph.cursors == [-1, 4, 19]
    assert [r["id"] for r in graph.writes] == [4, 19]
    assert all(r["end"] is None for r in graph.writes)


def test_stale_endpoint_prevents_all_writes():
    graph = Graph([[4, "E1", "wrong-owner", "b", "DEPENDS_ON"], [19, "E2", "b", "c", "DEPENDS_ON"]])
    with pytest.raises(ValueError, match="endpoints/type"):
        write_results(graph, EDGES, RESULTS)
    assert not graph.writes


def test_missing_edge_prevents_all_writes():
    graph = Graph([[4, "E1", "a", "b", "DEPENDS_ON"]])
    with pytest.raises(ValueError, match="edge IDs"):
        write_results(graph, EDGES, RESULTS)
    assert not graph.writes
