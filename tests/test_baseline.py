import json

from looplens.baseline import code_review, parse_codes
from looplens.codebook import load_codebook
from looplens.data import Review
from looplens.model import ModelClient

BOOK = load_codebook()


def test_codebook_loads_and_ids_are_unique():
    assert len(BOOK.codes) >= 5
    assert len(BOOK.ids) == len(BOOK.codes)


def test_parse_keeps_only_codebook_codes():
    raw = 'Sure! {"codes": [{"code": "packaging", "evidence": "box", "confidence": 0.9},' \
          ' {"code": "made_up", "evidence": "x"}]}'
    codes, dropped = parse_codes(raw, BOOK.ids)
    assert [c.code for c in codes] == ["packaging"]
    assert dropped == ["made_up"]


def test_parse_handles_garbage_and_duplicates():
    assert parse_codes("no json here", BOOK.ids) == ([], [])
    raw = json.dumps({"codes": [{"code": "price_value", "confidence": "high"}, {"code": "price_value"}]})
    codes, _ = parse_codes(raw, BOOK.ids)
    assert len(codes) == 1 and codes[0].confidence == 0.5


def test_code_review_with_mock_model():
    review = Review(id="t1", text="The box arrived crushed and it leaked. Not worth the price.")
    res = code_review(review, BOOK, ModelClient(provider="mock"))
    got = {c.code for c in res.codes}
    assert {"packaging", "price_value"} <= got
