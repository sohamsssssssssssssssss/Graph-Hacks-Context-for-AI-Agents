import json
from pathlib import Path

import pytest

from derive import derive, load_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def results():
    nodes, edges, docs = load_data(ROOT / "data")
    return derive(nodes, edges, docs)


@pytest.fixture(scope="module")
def labels():
    return json.loads((ROOT / "labels/labels_v1.json").read_text())


@pytest.mark.parametrize("scenario", ["S1", "S2", "S3", "S4", "S5", "S5B", "S6", "S7", "S8", "S9A", "S9B", "S10"])
def test_scenario(scenario, results, labels):
    expected = {eid: label for eid, label in labels.items() if eid.startswith(f"EID-{scenario}-")}
    assert expected
    for eid, label in expected.items():
        assert results[eid]["status"] == label["status"], (eid, results[eid], label)
        assert results[eid]["derived_reason"]


def test_all_curated(results, labels):
    mismatches = {eid: {"derived": results[eid], "frozen": label}
                  for eid, label in labels.items() if results[eid]["status"] != label["status"]}
    assert len(labels) == 221
    assert not mismatches, mismatches


def test_background_remains_current(results):
    assert all(result["status"] == "current" for eid, result in results.items() if eid.startswith("EID-BG-"))


def test_retirement_times(results):
    assert results["EID-S1-01"]["valid_to"] == "2024-03-15T09:00:00Z"
    assert results["EID-S2-01"]["valid_to"] == "2024-02-03T16:30:00Z"
    assert results["EID-CATALOG-OWNS-02"]["valid_to"] == "2024-02-03T16:30:00Z"
    assert results["EID-S1-02"]["valid_to"] is None
