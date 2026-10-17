"""Central settings, read from environment variables (or a .env file)."""
from __future__ import annotations

import os
from pathlib import Path

try:  # optional: load .env when python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TAXONOMY_PATH = DATA / "taxonomy" / "mismatch_types.yaml"
SAMPLE_PATH = DATA / "sample" / "cases.jsonl"
DEMO_PATH = DATA / "sample" / "demo_cases.jsonl"
IMAGES_DIR = DATA / "images"
CACHE_DIR = DATA / "cache"

PROVIDER = os.getenv("LOOPLENS_PROVIDER", "mock")
BASE_URL = os.getenv("LOOPLENS_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv("LOOPLENS_MODEL", "qwen2.5vl:7b")
API_KEY = os.getenv("LOOPLENS_API_KEY", "")
