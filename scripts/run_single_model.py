"""Run the single-model baseline over all cases and save the results.

Usage:
    python -m scripts.run_single_model --limit 10    # try 10 cases first
    python -m scripts.run_single_model               # all cases
Output: data/results/single_model.jsonl  (+ a summary in the terminal)
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
from looplens.single_model import check_case  # noqa: E402
from looplens.taxonomy import load_taxonomy  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    tax, client = load_taxonomy(), ModelClient()
    cases = load_cases()[: args.limit]
    out = config.DATA / "results" / "single_model.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    verdicts, types, tokens, errors = Counter(), Counter(), 0, 0
    with out.open("w", encoding="utf-8") as f:
        for i, case in enumerate(cases, 1):
            res = check_case(case, tax, client)
            f.write(res.model_dump_json() + "\n")
            verdicts[res.verdict] += 1
            types.update(t.type for t in res.types)
            tokens += res.prompt_tokens + res.completion_tokens
            errors += res.parse_error
            tag = " (cached)" if res.cached else ""
            print(f"[{i}/{len(cases)}] {case.id}: {res.verdict} {[t.type for t in res.types]}{tag}")
    print(f"\nProvider: {client.provider}   Model: {client.model}")
    print(f"Cases: {len(cases)}   Tokens: {tokens:,} (~{tokens // max(1, len(cases))}/case)   Unparseable replies: {errors}")
    print("Verdicts:", dict(verdicts))
    print("Mismatch types:", dict(types.most_common()))
    print(f"Saved to {out.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
