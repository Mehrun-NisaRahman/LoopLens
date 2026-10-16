"""Run the single-model baseline over the sample and save the results.

Usage:
    python -m scripts.run_baseline --limit 10        # try 10 reviews first
    python -m scripts.run_baseline                    # all reviews
Output: data/results/baseline.jsonl  (+ a short summary in the terminal)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from looplens import config  # noqa: E402
from looplens.baseline import code_review  # noqa: E402
from looplens.codebook import load_codebook  # noqa: E402
from looplens.data import load_reviews  # noqa: E402
from looplens.model import ModelClient  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    book, client = load_codebook(), ModelClient()
    reviews = load_reviews()[: args.limit]
    out = config.DATA / "results" / "baseline.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    counts, tokens, dropped = Counter(), 0, 0
    with out.open("w", encoding="utf-8") as f:
        for i, rev in enumerate(reviews, 1):
            res = code_review(rev, book, client)
            f.write(res.model_dump_json() + "\n")
            counts.update(c.code for c in res.codes)
            tokens += res.prompt_tokens + res.completion_tokens
            dropped += len(res.dropped)
            print(f"[{i}/{len(reviews)}] {rev.id}: {[c.code for c in res.codes]}{' (cached)' if res.cached else ''}")
    print(f"\nProvider: {client.provider}  Model: {client.model}")
    print(f"Reviews: {len(reviews)}  Tokens: {tokens:,}  (~{tokens // max(1, len(reviews))}/review)  Invented codes dropped: {dropped}")
    print("Code counts:", json.dumps(counts.most_common(), indent=None))
    print(f"Saved to {out.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
