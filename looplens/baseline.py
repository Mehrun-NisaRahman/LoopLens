"""Setup 1 of 3: the single-model baseline.

One vision-language model call per review: it gets the codebook, the review text and the photo,
and must answer with JSON. The agent pipeline (week 2) will be compared against this.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from . import config
from .codebook import Codebook
from .data import Review
from .model import ModelClient

SYSTEM = (
    "You are a careful qualitative researcher. You apply a fixed codebook to customer reviews "
    "that may include a photo. Only use codes from the codebook. Answer with JSON only."
)

USER_TEMPLATE = """Codebook (id: definition):
{codebook}

Review title: {title}
Review text: {text}
Photo attached: {has_photo}

Return JSON exactly like:
{{"codes": [{{"code": "<id>", "evidence": "<short quote from the text, or '(image)' if from the photo>", "confidence": 0.0-1.0}}]}}
Use an empty list if no code applies."""


class AppliedCode(BaseModel):
    code: str
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)


class CodingResult(BaseModel):
    review_id: str
    codes: list[AppliedCode]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached: bool = False
    dropped: list[str] = []  # codes the model invented that are not in the codebook


def parse_codes(raw: str, allowed: set[str]) -> tuple[list[AppliedCode], list[str]]:
    """Pull the JSON object out of a model reply and keep only codebook codes."""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return [], []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [], []
    kept, dropped = [], []
    for item in data.get("codes", []):
        if not isinstance(item, dict) or "code" not in item:
            continue
        try:
            conf = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        item = {**item, "confidence": min(1.0, max(0.0, conf))}
        (kept if item["code"] in allowed else dropped).append(item)
    seen, unique = set(), []
    for item in kept:  # one entry per code
        if item["code"] not in seen:
            seen.add(item["code"])
            unique.append(AppliedCode(**item))
    return unique, [d["code"] for d in dropped]


def code_review(review: Review, book: Codebook, client: ModelClient | None = None) -> CodingResult:
    client = client or ModelClient()
    image = (config.ROOT / review.image_path) if review.image_path else None
    if image is not None and not image.exists():
        image = None
    user = USER_TEMPLATE.format(
        codebook=book.as_prompt(), title=review.title or "(none)", text=review.text,
        has_photo="yes" if image else "no",
    )
    reply = client.complete(SYSTEM, user, image)
    codes, dropped = parse_codes(reply.text, book.ids)
    return CodingResult(review_id=review.id, codes=codes, prompt_tokens=reply.prompt_tokens,
                        completion_tokens=reply.completion_tokens, cached=reply.cached, dropped=dropped)
