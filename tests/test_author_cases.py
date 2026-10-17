import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_author_drafts_and_verbatim_citations():
    cases = [json.loads(line) for line in (ROOT / "cases/author_cases.jsonl").read_text().splitlines()]
    docs = {d["id"]: d for d in map(json.loads, (ROOT / "data/docs.jsonl").read_text().splitlines())}
    assert [case["id"] for case in cases] == ["ST3", "ST4", "S5", "S5b", "S8", "S9a", "S9b", "S10", "A1", "A2", "A3", "T2", "T3", "W2", "P1", "TS1"]
    for case in cases:
        assert case["draft_by_agent"] is True
        gold = case["gold_answer"]
        assert all(not docs[did]["restricted"] for did in gold["cite_doc_ids"])
        assert all(any(span in docs[did]["text"] for did in gold["cite_doc_ids"]) for span in gold["cite_spans"])
    restricted = next(case for case in cases if case["id"] == "W2")
    assert restricted["gold_answer"]["cite_edge_ids"] == []
    assert restricted["gold_answer"]["cite_doc_ids"] == []
    assert restricted["gold_answer"]["cite_spans"] == []
