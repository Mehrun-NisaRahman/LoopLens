"""Compare every setup you have run against the gold labels, side by side.

Usage:  python -m scripts.compare
Reads data/results/*.jsonl (single_model, pipeline_full, pipeline_smart ...).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from looplens import config  # noqa: E402
from looplens.evaluate import load_gold, load_preds, score  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", type=Path, default=config.DATA / "gold" / "week1_labels.csv")
    args = ap.parse_args()
    gold = load_gold(args.gold)
    files = sorted((config.DATA / "results").glob("*.jsonl"))
    if not files:
        print("No results yet. Run scripts.run_single_model or scripts.run_pipeline first.")
        return
    head = f"{'setup':<16}{'cases':>6}{'accuracy':>10}{'kappa':>7}{'mism. F1':>10}{'types F1':>10}" \
           f"{'tokens/case':>13}{'calls/case':>12}"
    print(head)
    print("-" * len(head))
    for f in files:
        rep = score(gold, load_preds(f))
        if rep.n == 0:
            continue
        print(f"{f.stem:<16}{rep.n:>6}{rep.accuracy:>10.0%}{rep.kappa:>7.2f}{rep.mismatch_prf[2]:>10.2f}"
              f"{rep.types_prf[2]:>10.2f}{rep.tokens_per_case:>13,.0f}{rep.calls_per_case:>12.1f}")


if __name__ == "__main__":
    main()
