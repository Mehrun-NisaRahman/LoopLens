"""Setup 1 of 3: the single-model baseline.

One vision-language model call per case. The model sees the listing (title, description,
listing photo) and the customer review (text, customer photo), and must answer with JSON:
a verdict (match / mismatch / unclear) and, for a mismatch, which types apply.
The agent pipeline (week 2) will be compared against this.
"""
from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from . import config
from .data import Case
from .model import ModelClient
from .taxonomy import Taxonomy

SYSTEM = (
    "You check whether what an online shopper received matches the product listing. "
    "Compare the listing with the customer's review and photo. Be strict about evidence: "
    "only call a mismatch when the review or the customer photo shows one. Answer with JSON only."
)

USER_TEMPLATE = """{taxonomy}

PRODUCT LISTING
Title: {listing_title}
Description: {listing_description}

CUSTOMER REVIEW: ({rating} stars) {review_title}
{review_text}

Images attached: {images_note}

Return JSON exactly like:
{{"verdict": "match|mismatch|unclear",
  "types": [{{"type": "<mismatch type id>", "evidence": "<short quote, or '(customer photo)' / '(listing photo)'>"}}],
  "confidence": 0.0-1.0,
  "explanation": "<one sentence>"}}
Use an empty "types" list unless the verdict is mismatch."""


class FoundType(BaseModel):
    type: str
    evidence: str = ""


class CheckResult(BaseModel):
    case_id: str
    verdict: str = "unclear"
    types: list[FoundType] = []
    confidence: float = Field(default=0.5, ge=0, le=1)
    explanation: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached: bool = False
    dropped: list[str] = []  # anything the model invented that is not in the taxonomy
    parse_error: bool = False


def parse_check(raw: str, tax: Taxonomy) -> dict:
    """Pull the JSON object out of a model reply and keep only taxonomy ids."""
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        return {"verdict": "unclear", "types": [], "dropped": [], "parse_error": True}
    verdict = str(data.get("verdict", "unclear")).strip().lower()
    dropped: list[str] = []
    if verdict not in tax.verdict_ids:
        dropped.append(f"verdict:{verdict}")
        verdict = "unclear"
    kept, seen = [], set()
    for item in data.get("types") or []:
        if isinstance(item, str):
            item = {"type": item}
        if not isinstance(item, dict) or "type" not in item:
            continue
        if item["type"] not in tax.type_ids:
            dropped.append(str(item["type"]))
        elif item["type"] not in seen:
            seen.add(item["type"])
            kept.append(FoundType(type=item["type"], evidence=str(item.get("evidence", ""))))
    if verdict != "mismatch":
        kept = []  # types only make sense for a mismatch
    try:
        conf = min(1.0, max(0.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    return {"verdict": verdict, "types": kept, "confidence": conf,
            "explanation": str(data.get("explanation", ""))[:500], "dropped": dropped, "parse_error": False}


def check_case(case: Case, tax: Taxonomy, client: ModelClient | None = None) -> CheckResult:
    client = client or ModelClient()
    images, notes = [], []
    if case.listing.image_path and (config.ROOT / case.listing.image_path).exists():
        images.append(config.ROOT / case.listing.image_path)
        notes.append(f"image {len(images)} = listing photo")
    if case.review_image_path and (config.ROOT / case.review_image_path).exists():
        images.append(config.ROOT / case.review_image_path)
        notes.append(f"image {len(images)} = customer photo")
    user = USER_TEMPLATE.format(
        taxonomy=tax.as_prompt(),
        listing_title=case.listing.title or "(none)",
        listing_description=(case.listing.description or "(none)")[:1500],
        rating=case.rating if case.rating is not None else "?",
        review_title=case.review_title,
        review_text=case.review_text,
        images_note=", ".join(notes) if notes else "none",
    )
    reply = client.complete(SYSTEM, user, images)
    parsed = parse_check(reply.text, tax)
    return CheckResult(case_id=case.id, prompt_tokens=reply.prompt_tokens,
                       completion_tokens=reply.completion_tokens, cached=reply.cached, **parsed)
