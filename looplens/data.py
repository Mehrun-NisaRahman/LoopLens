"""Review records and loading helpers."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from . import config


class Review(BaseModel):
    id: str
    rating: float | None = None
    title: str = ""
    text: str
    image_url: str | None = None
    image_path: str | None = None  # local copy, relative to the repo root


def load_reviews(path: Path | None = None) -> list[Review]:
    """Load the sampled reviews; fall back to the small demo set shipped in the repo."""
    path = path or (config.SAMPLE_PATH if config.SAMPLE_PATH.exists() else config.DEMO_PATH)
    with path.open(encoding="utf-8") as f:
        return [Review(**json.loads(line)) for line in f if line.strip()]
