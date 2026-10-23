"""A tiny client for vision-language models, with a response cache.

Two providers:
  * "mock"   - no network, no cost; returns a deterministic, valid answer. Use it for tests and UI work.
  * "openai" - any OpenAI-compatible /chat/completions endpoint (OpenAI, Gemini's OpenAI endpoint,
               Ollama, LM Studio, vLLM ...). Set LOOPLENS_BASE_URL, LOOPLENS_MODEL, LOOPLENS_API_KEY.

Every real response is cached on disk by a hash of (model, prompt, image), so re-running an
experiment, or a public demo, costs nothing.
"""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path

import time

import requests

from . import config


@dataclass
class ModelReply:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached: bool = False


def _image_as_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _cache_key(model: str, system: str, user: str, images: list[Path]) -> str:
    h = hashlib.sha256()
    for part in (model, system, user):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    for image in images:
        h.update(image.read_bytes())
    return h.hexdigest()[:32]


class ModelClient:
    def __init__(self, provider: str | None = None, model: str | None = None,
                 base_url: str | None = None, api_key: str | None = None,
                 cache_dir: Path | None = None):
        self.provider = provider or config.PROVIDER
        self.model = model or config.MODEL
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else config.API_KEY
        self.cache_dir = cache_dir or config.CACHE_DIR

    # ---- public -------------------------------------------------------
    def complete(self, system: str, user: str, images: list[Path] | None = None) -> ModelReply:
        """Ask the model. `images` are sent in order after the text (e.g. listing photo, then customer photo)."""
        images = [p for p in (images or []) if p and p.exists()]
        if self.provider == "mock":
            return self._mock(user, images)
        key = _cache_key(self.model, system, user, images)
        hit = self.cache_dir / f"{key}.json"
        if hit.exists():
            d = json.loads(hit.read_text(encoding="utf-8"))
            return ModelReply(d["text"], d.get("prompt_tokens", 0), d.get("completion_tokens", 0), cached=True)
        reply = self._openai(system, user, images)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        hit.write_text(json.dumps(reply.__dict__), encoding="utf-8")
        return reply

    # ---- providers ----------------------------------------------------
    def _openai(self, system: str, user: str, images: list[Path]) -> ModelReply:
        content: list[dict] = [{"type": "text", "text": user}]
        for image in images:
            content.append({"type": "image_url", "image_url": {"url": _image_as_data_url(image)}})
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        }
        r = _post_with_retry(f"{self.base_url}/chat/completions", headers, body)
        d = r.json()
        usage = d.get("usage") or {}
        return ModelReply(
            text=d["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    @staticmethod
    def _mock(user: str, images: list[Path]) -> ModelReply:
        """Deterministic fake: judges from keywords in the customer review so the app can be built offline."""
        lower = user.lower()
        start, end = lower.find("customer review:"), lower.find("images attached:")
        text = lower[start:end] if start != -1 else lower
        rules = {
            "wrong_item": ("wrong item", "different product", "not the one", "sent me the wrong"),
            "colour_shade": ("wrong color", "wrong colour", "wrong shade", "different shade", "different color", "nothing like the", "darker than", "lighter than"),
            "size_quantity": ("smaller", "tiny", "travel size", "only got", "half the size"),
            "damaged_defective": ("broken", "leak", "crushed", "cracked", "doesn't work", "stopped working"),
            "counterfeit_suspected": ("fake", "counterfeit", "not genuine", "knock off", "knockoff"),
            "missing_parts": ("missing", "didn't include", "no brush", "no cap"),
        }
        found = [{"type": t, "evidence": next(k for k in kws if k in text)}
                 for t, kws in rules.items() if any(k in text for k in kws)]
        positive = any(k in text for k in ("as described", "as pictured", "exactly like", "matches", "as shown"))
        verdict = "mismatch" if found else ("match" if positive else "unclear")
        reply = {"verdict": verdict, "types": found, "confidence": 0.6 if found or positive else 0.3,
                 "explanation": "Mock model: keyword rules on the review text."}
        return ModelReply(text=json.dumps(reply), prompt_tokens=len(user) // 4 + 250 * len(images),
                          completion_tokens=60)


RETRY_STATUS = {429, 500, 502, 503, 504}


def _post_with_retry(url: str, headers: dict, body: dict, tries: int = 6,
                     sleep=time.sleep) -> requests.Response:
    """POST, waiting and retrying on rate limits (429) and temporary server errors.

    Free tiers allow only a few requests per minute; instead of crashing we wait
    (Retry-After header if given, else 5, 10, 20, 40, 60 s) and try again.
    """
    for attempt in range(tries):
        r = requests.post(url, headers=headers, json=body, timeout=180)
        if r.status_code not in RETRY_STATUS or attempt == tries - 1:
            r.raise_for_status()
            return r
        try:
            wait = float(r.headers.get("Retry-After", ""))
        except ValueError:
            wait = min(60, 5 * 2 ** attempt)
        print(f"   server said {r.status_code} (rate limit / busy) - waiting {wait:.0f}s, then retrying...")
        sleep(wait)
    raise RuntimeError("unreachable")

