"""One-off: apply the week-1 adjudication decisions to data/gold/week1_labels.csv.

Decisions (see docs/DECISIONS.md #5 and #6):
  71f8ac7c7002 -> match            (satisfied customer; listing photo is a sold-out banner)
  6d3b945d2609 -> mismatch / quality_far_below (melted during normal use)
  5b30f040c437 -> decided by the star rule for mixed reviews:
                  4-5 stars -> match, 1-3 stars -> mismatch / quality_far_below

Safe to run more than once.  Usage:  python -m scripts.fix_gold_week1
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from looplens import config  # noqa: E402
from looplens.data import load_cases  # noqa: E402

GOLD = config.DATA / "gold" / "week1_labels.csv"

FIXED = {
    "71f8ac7c7002": ("match", "", "confirms",
                     "Listing photo is a sold-out banner; customer satisfied and photo shows the lashes (reviewed)"),
    "6d3b945d2609": ("mismatch", "quality_far_below", "no_help",
                     "Melted and broke down during normal use (reviewed)"),
}


def main() -> None:
    with GOLD.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0].keys())

    cases = {c.id: c for c in load_cases()}
    curl = cases.get("5b30f040c437")
    if curl is None or curl.rating is None:
        sys.exit("Could not find case 5b30f040c437 or its star rating in data/sample/cases.jsonl")
    stars = int(curl.rating)
    print(f"Case 5b30f040c437 has {stars} stars. Review:\n  {curl.review_title} - {curl.review_text}\n")
    if stars >= 4:
        FIXED["5b30f040c437"] = ("match", "", "no_help",
                                 f"Happy with results; minor complaint accepted at {stars} stars (reviewed)")
    else:
        FIXED["5b30f040c437"] = ("mismatch", "quality_far_below", "no_help",
                                 f"Happy with results but a rod ripped; only {stars} stars (reviewed)")

    for r in rows:
        if r["case_id"] in FIXED:
            old = (r["verdict"], r["types"])
            r["verdict"], r["types"], r["photo_role"], r["note"] = FIXED[r["case_id"]]
            print(f"{r['case_id']}: {old[0]} {old[1] or ''} -> {r['verdict']} {r['types']}")

    with GOLD.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved {GOLD.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
