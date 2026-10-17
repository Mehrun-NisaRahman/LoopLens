"""Build the LoopLens dataset: customer reviews with photos, paired with their product listings.

Source: Amazon Reviews 2023, McAuley Lab (UCSD)
  https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023
  https://amazon-reviews-2023.github.io/

Steps:
  1. Stream the category's review file; keep reviews that have a customer photo and enough text.
  2. Sample N of them with a fixed seed. Low-star reviews are over-sampled (--low-share) because
     that is where mismatches live; otherwise almost every case would be a "match".
  3. Stream the category's metadata file and pick up the listing (title, description, features,
     main photo) for each sampled product, joined on parent_asin.
  4. Download the customer photo and the listing photo for every case.

Usage:
    python -m scripts.sample_reviews                         # All_Beauty, 300 cases
    python -m scripts.sample_reviews --category Handmade_Products --n 300

Check the dataset's terms before publishing any of the sampled reviews or photos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from looplens import config  # noqa: E402

BASE = "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw"
REVIEWS_URL = BASE + "/review_categories/{category}.jsonl"
META_URL = BASE + "/meta_categories/meta_{category}.jsonl"


def _lines(url: str):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if line:
                yield json.loads(line)


def collect_reviews(category: str, pool: int, min_chars: int) -> list[dict]:
    found: list[dict] = []
    for i, row in enumerate(_lines(REVIEWS_URL.format(category=category)), 1):
        images, text = row.get("images") or [], (row.get("text") or "").strip()
        if not images or len(text) < min_chars or not row.get("parent_asin"):
            continue
        img = images[0]
        url = img.get("large_image_url") or img.get("medium_image_url") or img.get("small_image_url")
        if not url:
            continue
        key = f"{row.get('user_id')}-{row.get('asin')}-{row.get('timestamp')}"
        found.append({
            "id": hashlib.sha1(key.encode()).hexdigest()[:12],
            "parent_asin": row["parent_asin"],
            "rating": row.get("rating"),
            "review_title": (row.get("title") or "").strip(),
            "review_text": text,
            "review_image_url": url,
        })
        if i % 50000 == 0:
            print(f"  scanned {i:,} reviews, {len(found)} with photos", flush=True)
        if len(found) >= pool:
            break
    return found


def stratified_sample(pool: list[dict], n: int, low_share: float, seed: int) -> list[dict]:
    rng = random.Random(seed)
    low = [r for r in pool if (r["rating"] or 5) <= 2]
    rest = [r for r in pool if (r["rating"] or 5) > 2]
    rng.shuffle(low)
    rng.shuffle(rest)
    k_low = min(len(low), round(n * low_share))
    picked = low[:k_low] + rest[: n - k_low]
    rng.shuffle(picked)
    return picked


def fetch_listings(category: str, asins: set[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i, row in enumerate(_lines(META_URL.format(category=category)), 1):
        pa = row.get("parent_asin")
        if pa in asins and pa not in out:
            imgs = row.get("images") or []
            main = next((im for im in imgs if im.get("variant") == "MAIN"), imgs[0] if imgs else {})
            desc = " ".join(row.get("description") or [])
            feats = " ".join(f"• {f}" for f in (row.get("features") or []))
            out[pa] = {
                "parent_asin": pa,
                "title": (row.get("title") or "").strip(),
                "description": (desc + (" " + feats if feats else "")).strip(),
                "image_url": main.get("hi_res") or main.get("large") or main.get("thumb"),
            }
            if len(out) == len(asins):
                break
        if i % 50000 == 0:
            print(f"  scanned {i:,} listings, matched {len(out)}/{len(asins)}", flush=True)
    return out


def download(url: str | None, dest: Path) -> bool:
    if not url:
        return False
    if dest.exists():
        return True
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except requests.RequestException:
        return False


def rel(p: Path) -> str:
    return str(p.relative_to(config.ROOT)).replace("\\", "/")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="All_Beauty")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--pool", type=int, default=4000, help="reviews with photos to collect before sampling")
    ap.add_argument("--low-share", type=float, default=0.5, help="share of 1-2 star reviews in the sample")
    ap.add_argument("--min-chars", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"1/4 Streaming {args.category} reviews ...")
    pool = collect_reviews(args.category, args.pool, args.min_chars)
    print(f"    {len(pool)} reviews with photos")

    picked = stratified_sample(pool, int(args.n * 1.2), args.low_share, args.seed)  # 20% spare
    print(f"2/4 Sampled {len(picked)} (low-star share {args.low_share:.0%})")

    print("3/4 Finding their product listings ...")
    listings = fetch_listings(args.category, {r["parent_asin"] for r in picked})
    print(f"    matched {len(listings)} listings")

    print("4/4 Downloading photos ...")
    rev_dir, lst_dir = config.IMAGES_DIR / "reviews", config.IMAGES_DIR / "listings"
    rev_dir.mkdir(parents=True, exist_ok=True)
    lst_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    for r in picked:
        if len(cases) >= args.n:
            break
        lst = listings.get(r["parent_asin"])
        if not lst or not lst["image_url"]:
            continue
        rp, lp = rev_dir / f"{r['id']}.jpg", lst_dir / f"{r['parent_asin']}.jpg"
        if not (download(r["review_image_url"], rp) and download(lst["image_url"], lp)):
            continue
        r = {**r, "review_image_path": rel(rp), "listing": {**lst, "image_path": rel(lp)}}
        r.pop("parent_asin")
        cases.append(r)
        if len(cases) % 25 == 0:
            print(f"    {len(cases)}/{args.n} cases ready", flush=True)

    config.SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with config.SAMPLE_PATH.open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    low = sum(1 for c in cases if (c["rating"] or 5) <= 2)
    print(f"\nSaved {len(cases)} cases ({low} with 1-2 stars) to {rel(config.SAMPLE_PATH)}")
    print(f"Photos are in {rel(rev_dir)}/ and {rel(lst_dir)}/")


if __name__ == "__main__":
    main()
