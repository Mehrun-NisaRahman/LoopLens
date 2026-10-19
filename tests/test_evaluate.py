from looplens.evaluate import Gold, Pred, cohen_kappa, score


def test_kappa_perfect_and_chance():
    assert cohen_kappa(["a", "b"], ["a", "b"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0


def test_score_counts():
    gold = {
        "1": Gold("1", "mismatch", {"missing_parts"}),
        "2": Gold("2", "match", set()),
        "3": Gold("3", "unclear", set()),
        "4": Gold("4", "mismatch", {"feature_claim_false"}),
    }
    preds = {
        "1": Pred("1", "mismatch", {"missing_parts"}),
        "2": Pred("2", "match", set()),
        "3": Pred("3", "match", set()),
        "4": Pred("4", "mismatch", {"quality_far_below"}),
    }
    rep = score(gold, preds)
    assert rep.n == 4 and rep.accuracy == 0.75
    assert rep.mismatch_prf == (1.0, 1.0, 1.0)
    assert rep.types_prf[0] == 0.5 and rep.types_prf[1] == 0.5
    assert [g.case_id for g, _ in rep.disagreements] == ["3"]
    assert [g.case_id for g, _ in rep.type_diffs] == ["4"]
    assert rep.confusion["unclear"]["match"] == 1
