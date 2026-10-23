"""Setup 2: the agent pipeline (week 2).

Instead of one big model call, the work is split between small agents:

  Router (text only)   reads the listing and review, lists the customer's complaints and
                       gives a first verdict from the text alone.
  Photo inspector      looks at the listing photo and the customer photo and checks each
                       complaint: does the photo confirm it, contradict it, or not help?
  Judge                applies the taxonomy rules to everything found and gives the final
                       verdict, mismatch types, photo role and explanation.

Two modes (docs/DECISIONS.md #7):
  full   - always run the Photo inspector when there is a customer photo.
  smart  - skip the photos (and the Judge) when the Router is confident the review is a
           clear, complaint-free match. Cheaper; the experiment measures what it costs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from . import config
from .data import Case
from .model import ModelClient
from .single_model import FoundType, parse_check
from .taxonomy import Taxonomy

PHOTO_ROLES = ("decisive", "confirms", "contradicts", "no_help", "not_inspected")
SKIP_MIN_CONFIDENCE = 0.8
SKIP_MIN_WORDS = 8

# --------------------------------------------------------------------------- prompts
ROUTER_SYSTEM = (
    "[agent:router] You read product reviews for an online shop. You only see text, never images. "
    "Find what the customer complains about and judge from the text alone. Answer with JSON only."
)
ROUTER_USER = """{taxonomy}

PRODUCT LISTING
Title: {title}
Description: {description}

CUSTOMER REVIEW: ({rating} stars) {review_title}
{review_text}
END OF REVIEW

Tasks:
1. List every specific complaint the customer makes about the item they received, in a few words each
   (e.g. "lid missing", "rod ripped during use"). Use an empty list if there are none.
   Pure opinions ("not for me", "smells odd to me") are not complaints.
2. Give your verdict from the text alone, following the rules above.
3. Say how confident you are (0.0-1.0).

Return JSON exactly like:
{{"complaints": ["..."], "text_verdict": "match|mismatch|unclear", "confidence": 0.0-1.0,
  "reason": "<one sentence>"}}"""

INSPECTOR_SYSTEM = (
    "[agent:photo-inspector] You compare a seller's product photo with a photo taken by the customer. "
    "Report only what you can actually see. Answer with JSON only."
)
INSPECTOR_USER = """PRODUCT: {title}

Images: {images_note}

The customer complains about: {complaints}

Tasks:
1. Is the customer's photo showing the same product as the listing? Colour or size variants of the same
   product count as the same product.
2. For each complaint, say whether the customer photo confirms it, contradicts it, or cannot show it (no_help).
3. List any problem clearly visible in the customer photo (damage, missing parts, leaks) - even if not
   complained about. Do NOT list colour or size differences that could be a variant.

Return JSON exactly like:
{{"same_product": "yes|no|unsure",
  "complaints": [{{"complaint": "...", "photo": "confirms|contradicts|no_help", "note": "<what you see>"}}],
  "visible_problems": ["..."],
  "observations": "<one or two sentences>"}}"""

JUDGE_SYSTEM = (
    "[agent:judge] You make the final decision on whether what an online shopper received matches the "
    "product listing. Weigh the evidence your colleagues gathered and follow the rules exactly. "
    "Answer with JSON only."
)
JUDGE_USER = """{taxonomy}

PRODUCT LISTING
Title: {title}
Description: {description}

CUSTOMER REVIEW: ({rating} stars) {review_title}
{review_text}
END OF REVIEW

TEXT ANALYST (read the review):
{router}

PHOTO INSPECTOR (looked at the listing photo and customer photo):
{inspector}

Decide the final verdict and, for a mismatch, the types. Also say what role the customer photo played:
decisive (only the photo showed the problem), confirms (backs up the customer), contradicts (shows the
claim is false), no_help (could not show anything useful), not_inspected (no photo check was done).

Return JSON exactly like:
{{"verdict": "match|mismatch|unclear",
  "types": [{{"type": "<mismatch type id>", "evidence": "<short quote, or '(customer photo)'>"}}],
  "confidence": 0.0-1.0,
  "photo_role": "decisive|confirms|contradicts|no_help|not_inspected",
  "explanation": "<one or two sentences a seller would understand>"}}
Use an empty "types" list unless the verdict is mismatch."""


# --------------------------------------------------------------------------- results
class Step(BaseModel):
    agent: str
    output: dict = {}
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached: bool = False


class PipelineResult(BaseModel):
    case_id: str
    mode: str
    route: str                       # "text_only" or "with_photos" or "no_photo_available"
    verdict: str = "unclear"
    types: list[FoundType] = []
    confidence: float = Field(default=0.5, ge=0, le=1)
    photo_role: str = "not_inspected"
    explanation: str = ""
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    steps: list[Step] = []
    parse_error: bool = False


def _json(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    return d if isinstance(d, dict) else None


def _clamp(x, default=0.5) -> float:
    try:
        return min(1.0, max(0.0, float(x)))
    except (TypeError, ValueError):
        return default


def _photos(case: Case) -> tuple[list[Path], list[str]]:
    images, notes = [], []
    if case.listing.image_path and (config.ROOT / case.listing.image_path).exists():
        images.append(config.ROOT / case.listing.image_path)
        notes.append(f"image {len(images)} = listing photo")
    if case.review_image_path and (config.ROOT / case.review_image_path).exists():
        images.append(config.ROOT / case.review_image_path)
        notes.append(f"image {len(images)} = customer photo")
    return images, notes


def can_skip_photos(router: dict, case: Case) -> bool:
    """Smart-mode rule: skip photos only for a confident, complaint-free, non-trivial positive review."""
    return (router.get("text_verdict") == "match"
            and not router.get("complaints")
            and _clamp(router.get("confidence"), 0) >= SKIP_MIN_CONFIDENCE
            and len(f"{case.review_title} {case.review_text}".split()) >= SKIP_MIN_WORDS)


# --------------------------------------------------------------------------- run
def run_pipeline(case: Case, tax: Taxonomy, client: ModelClient | None = None,
                 mode: str = "smart") -> PipelineResult:
    if mode not in ("full", "smart"):
        raise ValueError("mode must be 'full' or 'smart'")
    client = client or ModelClient()
    steps: list[Step] = []
    fields = dict(taxonomy=tax.as_prompt(), title=case.listing.title or "(none)",
                  description=(case.listing.description or "(none)")[:1500],
                  rating=case.rating if case.rating is not None else "?",
                  review_title=case.review_title, review_text=case.review_text)

    def call(agent: str, system: str, user: str, images: list[Path]) -> dict | None:
        reply = client.complete(system, user, images)
        out = _json(reply.text)
        steps.append(Step(agent=agent, output=out or {"raw": reply.text[:500]},
                          prompt_tokens=reply.prompt_tokens, completion_tokens=reply.completion_tokens,
                          cached=reply.cached))
        return out

    # 1. Router -------------------------------------------------------------
    router = call("router", ROUTER_SYSTEM, ROUTER_USER.format(**fields), []) or {}
    complaints = [str(c) for c in router.get("complaints") or [] if str(c).strip()]
    router["complaints"] = complaints

    def finish(route: str, **kw) -> PipelineResult:
        return PipelineResult(case_id=case.id, mode=mode, route=route, steps=steps, calls=len(steps),
                              prompt_tokens=sum(s.prompt_tokens for s in steps),
                              completion_tokens=sum(s.completion_tokens for s in steps), **kw)

    if mode == "smart" and can_skip_photos(router, case):
        return finish("text_only", verdict="match", confidence=_clamp(router.get("confidence")),
                      photo_role="not_inspected",
                      explanation=str(router.get("reason", "Clear positive review; photos not needed."))[:500])

    # 2. Photo inspector ----------------------------------------------------
    images, notes = _photos(case)
    has_customer_photo = any("customer" in n for n in notes)
    if has_customer_photo:
        inspector = call("photo_inspector", INSPECTOR_SYSTEM, INSPECTOR_USER.format(
            title=fields["title"], images_note=", ".join(notes),
            complaints="; ".join(complaints) if complaints else "nothing (no complaints)"), images)
        inspector_text = json.dumps(inspector, ensure_ascii=False) if inspector else "(inspector reply unreadable)"
        route = "with_photos"
    else:
        inspector_text = "(no customer photo - not inspected)"
        route = "no_photo_available"

    # 3. Judge ---------------------------------------------------------------
    raw_router = json.dumps({k: router.get(k) for k in ("complaints", "text_verdict", "confidence", "reason")},
                            ensure_ascii=False)
    reply = client.complete(JUDGE_SYSTEM, JUDGE_USER.format(**fields, router=raw_router,
                                                            inspector=inspector_text), [])
    judge = parse_check(reply.text, tax)
    raw_judge = _json(reply.text) or {}
    steps.append(Step(agent="judge", output=raw_judge or {"raw": reply.text[:500]},
                      prompt_tokens=reply.prompt_tokens, completion_tokens=reply.completion_tokens,
                      cached=reply.cached))
    role = str(raw_judge.get("photo_role", "")).strip().lower()
    if route != "with_photos":
        role = "not_inspected"
    elif role not in PHOTO_ROLES:
        role = "no_help"
    return finish(route, verdict=judge["verdict"], types=judge.get("types", []),
                  confidence=judge.get("confidence", 0.5), photo_role=role,
                  explanation=judge.get("explanation", ""), parse_error=judge["parse_error"])
