"""Download a sample of Amazon reviews that have customer photos.

Source: Amazon Reviews 2023, McAuley Lab (UCSD)
  https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023
  https://amazon-reviews-2023.github.io/

It streams one category file line by line (no need to download the whole file), keeps reviews
that have at least one photo and enough text, then randomly samples N of them with a fixed seed
and downloads the first photo of each.

Usage:
    python -m scripts.sample_reviews                       # All_Beauty, 300 reviews
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

URL = ("https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/"
       "raw/review_categories/{category}.jsonl")


def stream_candidates(category: str, pool: int, min_chars: int):
    """Yield reviews with a photo and enough text, until `pool` candidates were found."""
    found = 0
    with requests.get(URL.format(category=category), stream=True, timeout=60) as r:
        r.raise_for_status()
        for i, line in enumerate(r.iter_lines(decode_unicode=True)):
            if not line:
                continue
            row = json.loads(line)
            images = row.get("images") or []
            text = (row.get("text") or "").strip()
            if not images or len(text) < min_chars:
                continue
            img = images[0]
            url = img.get("large_image_url") or img.get("medium_image_url") or img.get("small_image_url")
            if not url:
                continue
            found += 1
            yield {
                "id": hashlib.sha1(f"{row.get('user_id')}-{row.get('asin')}-{row.get('timestamp')}".encode()).hexdigest()[:12],
                "rating": row.get("rating"),
                "title": (row.get("title") or "").strip(),
                "text": text,
                "image_url": url,
            }
            if i and i % 50000 == 0:
                print(f"  scanned {i:,} lines, {found} candidates", flush=True)
            if found >= pool:
                return


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except requests.RequestException:
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="All_Beauty")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--pool", type=int, default=3000, help="candidates to collect before sampling")
    ap.add_argument("--min-chars", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"Streaming {args.category} ...")
    pool = list(stream_candidates(args.category, args.pool, args.min_chars))
    print(f"Collected {len(pool)} candidates with photos")
    random.Random(args.seed).shuffle(pool)

    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    config.SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    kept = []
    for rev in pool:
        if len(kept) >= args.n:
            break
        dest = config.IMAGES_DIR / f"{rev['id']}.jpg"
        if dest.exists() or download_image(rev["image_url"], dest):
            rev["image_path"] = str(dest.relative_to(config.ROOT)).replace("\\", "/")
            kept.append(rev)
    with config.SAMPLE_PATH.open("w", encoding="utf-8") as f:
        for rev in kept:
            f.write(json.dumps(rev, ensure_ascii=False) + "\n")
    print(f"Saved {len(kept)} reviews to {config.SAMPLE_PATH.relative_to(config.ROOT)} "
          f"and their photos to {config.IMAGES_DIR.relative_to(config.ROOT)}/")


if __name__ == "__main__":
    main()
