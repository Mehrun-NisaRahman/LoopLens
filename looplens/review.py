"""Human review: confirm or overrule the AI's verdict, and keep score.

Reviews are stored one per line in data/reviews/reviews.jsonl. The latest review of a case wins,
so changing your mind is just another click. Nothing here calls a model.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from . import config
from .taxonomy import Taxonomy


class ReviewIn(BaseModel):
    case_id: str
    setup: str
    decision: Literal["confirm", "overrule"]
    verdict: str | None = None      # only for overrule
    types: list[str] = []           # only for overrule with verdict "mismatch"
    reason: str = ""


class Review(BaseModel):
    case_id: str
    setup: str
    decision: str
    ai_verdict: str
    ai_types: list[str] = []
    final_verdict: str
    final_types: list[str] = []
    reason: str = ""
    at: str


# --------------------------------------------------------------------------- files
def results_dir() -> Path:
    return config.DATA / "results"


def reviews_path() -> Path:
    return config.DATA / "reviews" / "reviews.jsonl"


def list_setups() -> list[str]:
    """Saved AI runs, newest first (e.g. pipeline_smart_v2, single_model_v2 ...)."""
    files = sorted(results_dir().glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [f.stem for f in files]


def load_results(setup: str) -> dict[str, dict]:
    path = results_dir() / f"{setup}.jsonl"
    if not path.exists() or "/" in setup or "\\" in setup:
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["case_id"]] = d
    return out


def load_gold() -> dict[str, dict]:
    """All hand labels from data/gold/*.csv, keyed by case id."""
    out: dict[str, dict] = {}
    for path in sorted((config.DATA / "gold").glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if (r.get("verdict") or "").strip():
                    out[r["case_id"]] = {
                        "verdict": r["verdict"].strip().lower(),
                        "types": [t.strip() for t in (r.get("types") or "").split(";") if t.strip()],
                        "photo_role": (r.get("photo_role") or "").strip(),
                        "note": r.get("note", ""), "set": path.stem}
    return out


def load_reviews() -> dict[str, Review]:
    path = reviews_path()
    latest: dict[str, Review] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = Review(**json.loads(line))
                latest[r.case_id] = r
    return latest


# --------------------------------------------------------------------------- logic
class ReviewError(ValueError):
    pass


def make_review(inp: ReviewIn, ai: dict, tax: Taxonomy) -> Review:
    ai_verdict = ai.get("verdict", "unclear")
    ai_types = [t["type"] if isinstance(t, dict) else t for t in ai.get("types", [])]
    if inp.decision == "confirm":
        final_verdict, final_types = ai_verdict, ai_types
    else:
        if inp.verdict not in tax.verdict_ids:
            raise ReviewError("Pick a verdict: match, mismatch or unclear.")
        bad = [t for t in inp.types if t not in tax.type_ids]
        if bad:
            raise ReviewError(f"Unknown mismatch type(s): {', '.join(bad)}")
        final_verdict = inp.verdict
        final_types = list(dict.fromkeys(inp.types)) if final_verdict == "mismatch" else []
        if final_verdict == "mismatch" and not final_types:
            raise ReviewError("A mismatch needs at least one type.")
        if final_verdict == ai_verdict and sorted(final_types) == sorted(ai_types):
            raise ReviewError("That is the same as the AI's answer - use Confirm instead.")
    return Review(case_id=inp.case_id, setup=inp.setup, decision=inp.decision, ai_verdict=ai_verdict,
                  ai_types=ai_types, final_verdict=final_verdict, final_types=final_types,
                  reason=inp.reason.strip()[:300], at=datetime.now(timezone.utc).isoformat(timespec="seconds"))


def save_review(review: Review) -> None:
    path = reviews_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(review.model_dump_json() + "\n")


def stats(reviews: dict[str, Review]) -> dict:
    vals = list(reviews.values())
    confirmed = sum(r.decision == "confirm" for r in vals)
    overruled = [r for r in vals if r.decision == "overrule"]
    verdict_changed = sum(r.final_verdict != r.ai_verdict for r in overruled)
    reasons = Counter(r.reason.strip().lower() for r in overruled if r.reason.strip())
    return {
        "reviewed": len(vals),
        "confirmed": confirmed,
        "overruled": len(overruled),
        "verdict_changed": verdict_changed,
        "agreement": confirmed / len(vals) if vals else None,
        "top_reasons": reasons.most_common(5),
    }
