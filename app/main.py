"""LoopLens API (week 1 skeleton). Run:  uvicorn app.main:app --reload"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from looplens import __version__, config
from looplens.baseline import CodingResult, code_review
from looplens.codebook import Codebook, load_codebook
from looplens.data import Review, load_reviews
from looplens.model import ModelClient

app = FastAPI(title="LoopLens API", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

_book: Codebook = load_codebook()
_reviews: dict[str, Review] = {r.id: r for r in load_reviews()}
_client = ModelClient()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "provider": config.PROVIDER, "reviews": len(_reviews)}


@app.get("/codebook", response_model=Codebook)
def get_codebook() -> Codebook:
    return _book


@app.get("/reviews", response_model=list[Review])
def list_reviews(limit: int = 20, offset: int = 0) -> list[Review]:
    items = list(_reviews.values())
    return items[offset: offset + limit]


@app.get("/reviews/{review_id}", response_model=Review)
def get_review(review_id: str) -> Review:
    if review_id not in _reviews:
        raise HTTPException(404, "Review not found")
    return _reviews[review_id]


@app.post("/reviews/{review_id}/baseline", response_model=CodingResult)
def run_baseline(review_id: str) -> CodingResult:
    """Code one review with the single-model baseline."""
    review = get_review(review_id)
    return code_review(review, _book, _client)
