"""Run the agent pipeline over the cases and save the results.

Usage:
    python -m scripts.run_pipeline --mode smart --limit 30
    python -m scripts.run_pipeline --mode full  --limit 30
Output: data/results/pipeline_<mode>.jsonl  (compare with: python -m scripts.compare)
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from looplens import config  # noqa: E402
from looplens.data import load_cases  # noqa: E402
from looplens.model import ModelClient  # noqa: E402
from looplens.pipeline import run_pipeline  # noqa: E402
from looplens.taxonomy import load_taxonomy  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "smart"], default="smart")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    tax, client = load_taxonomy(), ModelClient()
    cases = load_cases()[: args.limit]
    out = config.DATA / "results" / f"pipeline_{args.mode}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    verdicts, routes, tokens, calls = Counter(), Counter(), 0, 0
    with out.open("w", encoding="utf-8") as f:
        for i, case in enumerate(cases, 1):
            res = run_pipeline(case, tax, client, mode=args.mode)
            f.write(res.model_dump_json() + "\n")
            verdicts[res.verdict] += 1
            routes[res.route] += 1
            tokens += res.prompt_tokens + res.completion_tokens
            calls += res.calls
            print(f"[{i}/{len(cases)}] {case.id}: {res.verdict} {[t.type for t in res.types]}"
                  f"  route={res.route}  photo={res.photo_role}  calls={res.calls}")
    n = max(1, len(cases))
    print(f"\nMode: {args.mode}   Provider: {client.provider}   Model: {client.model}")
    print(f"Cases: {len(cases)}   Model calls: {calls} (~{calls / n:.1f}/case)   "
          f"Tokens: {tokens:,} (~{tokens // n}/case)")
    print("Routes:", dict(routes))
    print("Verdicts:", dict(verdicts))
    print(f"Saved to {out.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
