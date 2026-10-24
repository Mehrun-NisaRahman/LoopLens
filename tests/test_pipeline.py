from looplens.data import Case, Listing
from looplens.model import ModelClient
from looplens.pipeline import can_skip_photos, run_pipeline
from looplens.taxonomy import load_taxonomy

TAX = load_taxonomy()
MOCK = ModelClient(provider="mock")

HAPPY = "Exactly like the picture, works great and I love it so much."
ANGRY = "It arrived broken and the lid is missing, really disappointed."


def _case(text, tmp_path=None, rating=5):
    listing = Listing(title="Soap dish with lid", description="Ceramic dish and lid")
    photo = None
    if tmp_path is not None:
        for name in ("listing.jpg", "customer.jpg"):
            (tmp_path / name).write_bytes(b"\xff\xd8fake")
        listing.image_path = str(tmp_path / "listing.jpg")
        photo = str(tmp_path / "customer.jpg")
    return Case(id="c1", rating=rating, review_text=text, review_image_path=photo, listing=listing)


def test_smart_mode_skips_photos_for_clear_happy_review(tmp_path):
    res = run_pipeline(_case(HAPPY, tmp_path), TAX, MOCK, mode="smart")
    assert res.route == "text_only" and res.verdict == "match"
    assert res.calls == 1 and res.photo_role == "not_inspected"


def test_full_mode_always_inspects_photos(tmp_path):
    res = run_pipeline(_case(HAPPY, tmp_path), TAX, MOCK, mode="full")
    assert res.route == "with_photos"
    assert [s.agent for s in res.steps] == ["router", "photo_inspector", "judge"]


def test_complaint_goes_through_photos_and_judge(tmp_path):
    res = run_pipeline(_case(ANGRY, tmp_path, rating=1), TAX, MOCK, mode="smart")
    assert res.route == "with_photos" and res.verdict == "mismatch"
    assert {"damaged_defective", "missing_parts"} <= {t.type for t in res.types}
    assert res.prompt_tokens > 0 and res.calls == 3


def test_no_customer_photo_skips_inspector():
    res = run_pipeline(_case(ANGRY), TAX, MOCK, mode="full")
    assert res.route == "no_photo_available" and res.calls == 2
    assert res.photo_role == "not_inspected"


def test_skip_rule_is_conservative():
    case = _case(HAPPY)
    assert can_skip_photos({"text_verdict": "match", "complaints": [], "confidence": 0.9}, case)
    assert not can_skip_photos({"text_verdict": "match", "complaints": ["rod ripped"], "confidence": 0.9}, case)
    assert not can_skip_photos({"text_verdict": "match", "complaints": [], "confidence": 0.5}, case)
    assert not can_skip_photos({"text_verdict": "match", "complaints": [], "confidence": 0.9}, _case("Good."))


def test_judge_can_use_a_different_client(tmp_path):
    calls = []

    class Spy(ModelClient):
        def complete(self, system, user, images=None):
            calls.append(system[:20])
            return super().complete(system, user, images)

    res = run_pipeline(_case(ANGRY, tmp_path, rating=1), TAX, MOCK, mode="full",
                       judge_client=Spy(provider="mock"))
    assert res.verdict == "mismatch"
    assert calls == ["[agent:judge] You ma"]  # only the Judge went to the second client
