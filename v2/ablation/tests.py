"""Offline loader invariants; no LLM/database/network calls."""
from copy import deepcopy

from v2.ablation.load import source


def test_seed_only_curated_status_changes():
    import json
    from pathlib import Path
    raw = list(map(json.loads, Path('data/edges.jsonl').read_text().splitlines()))
    _, result = source()
    assert len(raw) == len(result) == 15276
    for original, current in zip(raw, result):
        if original['eid'].startswith('EID-BG-'):
            assert current == original
        else:
            assert current['status'] == 'current'
            assert {k:v for k,v in current.items() if k not in {'status','derived_reason'}} == {
                k:v for k,v in original.items() if k not in {'status','derived_reason'}}
