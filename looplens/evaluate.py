"""Score model results against hand-made gold labels.

Pure functions (no I/O) so they are easy to test. Metrics:
  - verdict accuracy and Cohen's kappa (agreement beyond chance)
  - confusion matrix (gold verdict x predicted verdict)
  - mismatch detection: precision / recall / F1, treating "mismatch" as the positive class
  - mismatch types: micro precision / recall / F1 over (case, type) pairs
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

VERDICTS = ["match", "mismatch", "unclear"]


@dataclass
class Gold:
    case_id: str
    verdict: str
    types: set[str]
    photo_role: str = ""
    note: str = ""


@dataclass
class Pred:
    case_id: str
    verdict: str
    types: set[str]
    explanation: str = ""
    tokens: int = 0
    calls: int = 1
    photo_role: str = ""


@dataclass
class Report:
    n: int
    accuracy: float
    kappa: float
    confusion: dict[str, dict[str, int]]
    mismatch_prf: tuple[float, float, float]
    types_prf: tuple[float, float, float]
    disagreements: list[tuple[Gold, Pred]] = field(default_factory=list)
    type_diffs: list[tuple[Gold, Pred]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    tokens_per_case: float = 0.0
    calls_per_case: float = 0.0


def load_gold(path: Path) -> dict[str, Gold]:
    with path.open(encoding="utf-8", newline="") as f:
        return {r["case_id"]: Gold(r["case_id"], r["verdict"].strip().lower(),
                                   {t.strip().lower() for t in r["types"].split(";") if t.strip()},
                                   r.get("photo_role", ""), r.get("note", ""))
                for r in csv.DictReader(f)}


def load_preds(path: Path) -> dict[str, Pred]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["case_id"]] = Pred(d["case_id"], d["verdict"],
                                     {t["type"] for t in d.get("types", [])}, d.get("explanation", ""),
                                     d.get("prompt_tokens", 0) + d.get("completion_tokens", 0),
                                     d.get("calls", 1), d.get("photo_role", ""))
    return out


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def score(gold: dict[str, Gold], preds: dict[str, Pred]) -> Report:
    ids = [i for i in gold if i in preds]
    g = [gold[i].verdict for i in ids]
    p = [preds[i].verdict for i in ids]
    conf = {gv: {pv: 0 for pv in VERDICTS} for gv in VERDICTS}
    for gv, pv in zip(g, p):
        conf.setdefault(gv, {}).setdefault(pv, 0)
        conf[gv][pv] += 1

    tp = sum(gv == pv == "mismatch" for gv, pv in zip(g, p))
    fp = sum(pv == "mismatch" and gv != "mismatch" for gv, pv in zip(g, p))
    fn = sum(gv == "mismatch" and pv != "mismatch" for gv, pv in zip(g, p))

    ttp = tfp = tfn = 0
    for i in ids:
        gt, pt = gold[i].types, preds[i].types
        ttp += len(gt & pt)
        tfp += len(pt - gt)
        tfn += len(gt - pt)

    return Report(
        n=len(ids),
        accuracy=sum(x == y for x, y in zip(g, p)) / len(ids) if ids else 0.0,
        kappa=cohen_kappa(g, p),
        confusion=conf,
        mismatch_prf=_prf(tp, fp, fn),
        types_prf=_prf(ttp, tfp, tfn),
        disagreements=[(gold[i], preds[i]) for i in ids if gold[i].verdict != preds[i].verdict],
        type_diffs=[(gold[i], preds[i]) for i in ids
                    if gold[i].verdict == preds[i].verdict == "mismatch" and gold[i].types != preds[i].types],
        missing=[i for i in gold if i not in preds],
        tokens_per_case=sum(preds[i].tokens for i in ids) / len(ids) if ids else 0.0,
        calls_per_case=sum(preds[i].calls for i in ids) / len(ids) if ids else 0.0,
    )
