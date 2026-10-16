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


def _cache_key(model: str, system: str, user: str, image: Path | None) -> str:
    h = hashlib.sha256()
    for part in (model, system, user):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    if image and image.exists():
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
    def complete(self, system: str, user: str, image: Path | None = None) -> ModelReply:
        if self.provider == "mock":
            return self._mock(user, image)
        key = _cache_key(self.model, system, user, image)
        hit = self.cache_dir / f"{key}.json"
        if hit.exists():
            d = json.loads(hit.read_text(encoding="utf-8"))
            return ModelReply(d["text"], d.get("prompt_tokens", 0), d.get("completion_tokens", 0), cached=True)
        reply = self._openai(system, user, image)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        hit.write_text(json.dumps(reply.__dict__), encoding="utf-8")
        return reply

    # ---- providers ----------------------------------------------------
    def _openai(self, system: str, user: str, image: Path | None) -> ModelReply:
        content: list[dict] = [{"type": "text", "text": user}]
        if image and image.exists():
            content.append({"type": "image_url", "image_url": {"url": _image_as_data_url(image)}})
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        }
        r = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=body, timeout=180)
        r.raise_for_status()
        d = r.json()
        usage = d.get("usage") or {}
        return ModelReply(
            text=d["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    @staticmethod
    def _mock(user: str, image: Path | None) -> ModelReply:
        """Deterministic fake: picks codes from simple keywords so the pipeline can be built offline."""
        # look only at the review itself, not the codebook part of the prompt
        lower = user.lower()
        start = lower.find("review text:")
        end = lower.find("photo attached:")
        text = lower[start:end] if start != -1 else lower
        rules = {
            "quality_negative": ("broke", "cheap", "doesn't work", "stopped", "poor"),
            "quality_positive": ("love", "great", "works", "amazing", "perfect"),
            "price_value": ("price", "worth", "value", "expensive", "$"),
            "packaging": ("package", "box", "leak", "arrived", "shipping"),
            "not_as_described": ("smaller", "different", "not as", "wrong"),
            "would_repurchase": ("buy again", "recommend", "repurchase"),
        }
        codes = [
            {"code": cid, "evidence": next(k for k in kws if k in text), "confidence": 0.6}
            for cid, kws in rules.items() if any(k in text for k in kws)
        ]
        if image is not None:
            codes.append({"code": "photo_supports_text", "evidence": "(image)", "confidence": 0.4})
        return ModelReply(text=json.dumps({"codes": codes}), prompt_tokens=len(user) // 4, completion_tokens=40)
