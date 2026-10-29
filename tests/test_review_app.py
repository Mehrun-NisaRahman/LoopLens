import json

import pytest
from fastapi.testclient import TestClient

from app.main import _cases, app
from looplens import config

client = TestClient(app)


@pytest.fixture()
def data(tmp_path, monkeypatch):
    """A private data folder with one saved AI run and one gold label."""
    monkeypatch.setattr(config, "DATA", tmp_path)
    ids = list(_cases)[:3]
    (tmp_path / "results").mkdir()
    rows = [{"case_id": ids[0], "verdict": "mismatch", "types": [{"type": "missing_parts", "evidence": "x"}],
             "explanation": "Lid missing.", "confidence": 0.9},
            {"case_id": ids[1], "verdict": "match", "types": [], "explanation": "Fine."}]
    (tmp_path / "results" / "pipeline_smart_v2.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    (tmp_path / "gold").mkdir()
    (tmp_path / "gold" / "g.csv").write_text(
        f"case_id,verdict,types,photo_role,note\n{ids[0]},mismatch,missing_parts,confirms,lid\n", encoding="utf-8")
    return ids


def test_app_page_is_served():
    r = client.get("/")
    assert r.status_code == 200 and "LoopLens" in r.text


def test_overview_lists_cases_with_results(data):
    d = client.get("/api/overview").json()
    assert d["setup"] == "pipeline_smart_v2"
    assert [c["id"] for c in d["cases"]] == data[:2]
    assert d["cases"][0]["has_gold"] is True and d["stats"]["reviewed"] == 0


def test_detail_includes_result_and_gold(data):
    d = client.get(f"/api/cases/{data[0]}/detail?setup=pipeline_smart_v2").json()
    assert d["result"]["verdict"] == "mismatch" and d["gold"]["types"] == ["missing_parts"]


def test_confirm_then_overrule_latest_wins(data):
    r = client.post("/api/reviews", json={"case_id": data[1], "setup": "pipeline_smart_v2", "decision": "confirm"})
    assert r.status_code == 200 and r.json()["stats"]["agreement"] == 1.0
    r = client.post("/api/reviews", json={"case_id": data[1], "setup": "pipeline_smart_v2", "decision": "overrule",
                                          "verdict": "mismatch", "types": ["colour_shade"], "reason": "Wrong shade"})
    s = r.json()["stats"]
    assert s["reviewed"] == 1 and s["overruled"] == 1 and s["agreement"] == 0.0
    assert s["top_reasons"] == [["wrong shade", 1]]


@pytest.mark.parametrize("body, msg", [
    ({"decision": "overrule", "verdict": "maybe"}, "Pick a verdict"),
    ({"decision": "overrule", "verdict": "mismatch", "types": []}, "at least one type"),
    ({"decision": "overrule", "verdict": "mismatch", "types": ["missing_parts"]}, "Confirm instead"),
])
def test_bad_overrules_are_rejected(data, body, msg):
    r = client.post("/api/reviews", json={"case_id": data[0], "setup": "pipeline_smart_v2", **body})
    assert r.status_code == 400 and msg in r.json()["detail"]


def test_review_needs_an_ai_result(data):
    r = client.post("/api/reviews", json={"case_id": data[2], "setup": "pipeline_smart_v2", "decision": "confirm"})
    assert r.status_code == 404
