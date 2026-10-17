import json

from looplens.data import Case, Listing
from looplens.model import ModelClient
from looplens.single_model import check_case, parse_check
from looplens.taxonomy import load_taxonomy

TAX = load_taxonomy()


def test_taxonomy_loads_and_ids_are_unique():
    assert TAX.verdict_ids == {"match", "mismatch", "unclear"}
    assert len(TAX.types) >= 5


def test_parse_keeps_only_taxonomy_ids():
    raw = 'Here you go: {"verdict": "mismatch", "types": [{"type": "size_quantity", "evidence": "tiny"},' \
          ' {"type": "made_up"}], "confidence": 0.8}'
    out = parse_check(raw, TAX)
    assert out["verdict"] == "mismatch"
    assert [t.type for t in out["types"]] == ["size_quantity"]
    assert out["dropped"] == ["made_up"]


def test_parse_handles_garbage_and_bad_verdicts():
    assert parse_check("no json here", TAX)["parse_error"] is True
    out = parse_check(json.dumps({"verdict": "maybe", "types": ["wrong_item"]}), TAX)
    assert out["verdict"] == "unclear" and out["types"] == []  # types are cleared unless mismatch
    assert "verdict:maybe" in out["dropped"]


def test_check_case_with_mock_model():
    case = Case(id="t1", rating=1, review_text="It arrived broken and leaking, and it is a fake.",
                listing=Listing(title="Lotion 400 ml", description="Pump bottle"))
    res = check_case(case, TAX, ModelClient(provider="mock"))
    assert res.verdict == "mismatch"
    assert {"damaged_defective", "counterfeit_suspected"} <= {t.type for t in res.types}
