"""Create an empty labelling sheet for a new batch of gold cases.

Usage:
    python -m scripts.make_gold_template --start 31 --n 30 --out data/gold/heldout_labels.csv
Fill in verdict / types / photo_role / note for each row (in VS Code), exactly like week1_labels.csv.
Rows you leave without a verdict are ignored by the scoring scripts.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from looplens import config  # noqa: E402
from looplens.data import load_cases  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=31)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--out", type=Path, default=config.DATA / "gold" / "heldout_labels.csv")
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} already exists - not overwriting your labels.")
    cases = load_cases()[args.start - 1:][: args.n]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "verdict", "types", "photo_role", "note"])
        for c in cases:
            w.writerow([c.id, "", "", "", ""])
    print(f"Wrote {args.out} with {len(cases)} empty rows (cases {args.start}-{args.start + len(cases) - 1}).")


if __name__ == "__main__":
    main()
