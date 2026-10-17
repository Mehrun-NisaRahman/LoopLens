"""Make a simple page to browse your cases side by side: listing on the left, what the buyer got on the right.

Usage:
    python -m scripts.make_viewer            # all cases
    python -m scripts.make_viewer --n 30     # first 30
Then open data/viewer.html in your browser (double-click it). It works offline and stays on your computer.
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from looplens import config  # noqa: E402
from looplens.data import load_cases  # noqa: E402

PAGE = """<!doctype html><meta charset="utf-8"><title>LoopLens cases</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;margin:0;background:#f4f2f7;color:#1e1b4b}}
header{{position:sticky;top:0;background:#1e1b4b;color:#fff;padding:12px 24px;z-index:1}}
header b{{font-size:18px}} header span{{opacity:.8;margin-left:12px}}
.case{{background:#fff;margin:18px auto;max-width:1100px;border-radius:14px;box-shadow:0 2px 10px #0001;overflow:hidden}}
.top{{display:flex;gap:12px;align-items:center;padding:10px 18px;border-bottom:1px solid #eee;font-size:13px}}
.id{{font-family:monospace;color:#666}} .stars{{color:#d97706;font-weight:700}}
.low{{background:#fde2ea;color:#9f1239;padding:2px 8px;border-radius:99px;font-weight:700}}
.cols{{display:grid;grid-template-columns:1fr 1fr}} .col{{padding:16px 18px}} .col+.col{{border-left:1px solid #eee}}
h3{{margin:0 0 8px;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#6b7280}}
img{{width:100%;max-height:320px;object-fit:contain;background:#fafafa;border-radius:8px;border:1px solid #eee}}
.title{{font-weight:700;margin:10px 0 4px}} .desc{{font-size:13px;color:#4b5563;max-height:140px;overflow:auto}}
.note{{padding:10px 18px;border-top:1px dashed #ddd;font-size:13px;color:#6b7280}}
</style>
<header><b>LoopLens cases</b><span>{n} cases · left = what the listing promised · right = what the buyer got</span></header>
{body}"""

CASE = """<section class="case" id="{id}">
<div class="top"><span class="id">#{i} · {id}</span><span class="stars">{stars}</span>{low}</div>
<div class="cols">
<div class="col"><h3>Listing</h3>{limg}<div class="title">{ltitle}</div><div class="desc">{ldesc}</div></div>
<div class="col"><h3>Customer</h3>{rimg}<div class="title">{rtitle}</div><div>{rtext}</div></div>
</div>
<div class="note">Your verdict: match / mismatch / unclear — and which type?</div>
</section>"""


def img(path: str | None) -> str:
    if not path:
        return "<p><i>(no photo)</i></p>"
    return f'<img loading="lazy" src="{html.escape("../" + path)}" alt="">'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None)
    args = ap.parse_args()
    cases = load_cases()[: args.n]
    parts = []
    for i, c in enumerate(cases, 1):
        stars = "★" * int(c.rating or 0) + "☆" * (5 - int(c.rating or 0))
        parts.append(CASE.format(
            i=i, id=html.escape(c.id), stars=stars,
            low='<span class="low">1–2 stars</span>' if (c.rating or 5) <= 2 else "",
            limg=img(c.listing.image_path), ltitle=html.escape(c.listing.title),
            ldesc=html.escape(c.listing.description[:1200]),
            rimg=img(c.review_image_path), rtitle=html.escape(c.review_title),
            rtext=html.escape(c.review_text),
        ))
    out = config.DATA / "viewer.html"
    out.write_text(PAGE.format(n=len(cases), body="\n".join(parts)), encoding="utf-8")
    print(f"Wrote {out.relative_to(config.ROOT)} with {len(cases)} cases. Double-click it to open in your browser.")


if __name__ == "__main__":
    main()
