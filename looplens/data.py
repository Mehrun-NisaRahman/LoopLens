"""Cases: one product listing paired with one customer review (with a photo)."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from . import config


class Listing(BaseModel):
    parent_asin: str = ""
    title: str = ""
    description: str = ""          # description + feature bullets, joined
    image_url: str | None = None
    image_path: str | None = None  # local copy, relative to the repo root


class Case(BaseModel):
    id: str
    rating: float | None = None
    review_title: str = ""
    review_text: str
    review_image_url: str | None = None
    review_image_path: str | None = None
    listing: Listing


def load_cases(path: Path | None = None) -> list[Case]:
    """Load the sampled cases; fall back to the small synthetic demo set shipped in the repo."""
    path = path or (config.SAMPLE_PATH if config.SAMPLE_PATH.exists() else config.DEMO_PATH)
    with path.open(encoding="utf-8") as f:
        return [Case(**json.loads(line)) for line in f if line.strip()]
