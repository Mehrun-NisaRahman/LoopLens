"""Compare the model's results with your gold labels.

Usage:
    python -m scripts.evaluate
    python -m scripts.evaluate --results data/results/single_model.jsonl --gold data/gold/week1_labels.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from looplens import config  # noqa: E402
from looplens.evaluate import VERDICTS, load_gold, load_preds, score  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=config.DATA / "results" / "single_model.jsonl")
    ap.add_argument("--gold", type=Path, default=config.DATA / "gold" / "week1_labels.csv")
    args = ap.parse_args()

    rep = score(load_gold(args.gold), load_preds(args.results))
    if rep.n == 0:
        print("No overlapping cases between results and gold labels.")
        return

    print(f"Scored {rep.n} cases (gold labels without a result: {len(rep.missing)})\n")
    print(f"Verdict accuracy : {rep.accuracy:.0%}")
    print(f"Cohen's kappa    : {rep.kappa:.2f}   (agreement beyond chance; >0.6 good, >0.8 very good)")
    p, r, f = rep.mismatch_prf
    print(f"Mismatch finding : precision {p:.0%}  recall {r:.0%}  F1 {f:.2f}")
    p, r, f = rep.types_prf
    print(f"Mismatch types   : precision {p:.0%}  recall {r:.0%}  F1 {f:.2f}")

    print(f"Cost             : {rep.tokens_per_case:,.0f} tokens and {rep.calls_per_case:.1f} model calls per case")

    print("\nConfusion (rows = you, columns = AI)")
    print(" " * 10 + "".join(f"{v:>10}" for v in VERDICTS))
    for gv in VERDICTS:
        print(f"{gv:>10}" + "".join(f"{rep.confusion[gv][pv]:>10}" for pv in VERDICTS))

    if rep.disagreements:
        print("\nVerdict disagreements:")
        for g, pr in rep.disagreements:
            print(f"  {g.case_id}: you={g.verdict}  AI={pr.verdict}")
            print(f"     your note: {g.note}")
            print(f"     AI said  : {pr.explanation[:200]}")
    if rep.type_diffs:
        print("\nSame verdict, different types:")
        for g, pr in rep.type_diffs:
            print(f"  {g.case_id}: you={sorted(g.types)}  AI={sorted(pr.types)}")


if __name__ == "__main__":
    main()
