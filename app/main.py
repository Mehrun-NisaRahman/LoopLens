"""LoopLens API and review app.

Run:  uvicorn app.main:app --reload
Then open http://127.0.0.1:8000        (the review app)
       or http://127.0.0.1:8000/docs   (the API documentation)
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from looplens import __version__, config
from looplens.data import Case, load_cases
from looplens.model import ModelClient
from looplens.pipeline import PipelineResult, run_pipeline
from looplens import review as rv
from looplens.single_model import CheckResult, check_case
from looplens.taxonomy import Taxonomy, load_taxonomy

app = FastAPI(title="LoopLens API", version=__version__,
              description="Does what the buyer received match the listing? AI checks, a human decides.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

_tax: Taxonomy = load_taxonomy()
_cases: dict[str, Case] = {c.id: c for c in load_cases()}
_client = ModelClient()
_order: dict[str, int] = {cid: i for i, cid in enumerate(_cases, 1)}  # case number, as in the viewer
STATIC = Path(__file__).parent / "static"
app.mount("/data/images", StaticFiles(directory=config.IMAGES_DIR, check_dir=False), name="images")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "provider": config.PROVIDER, "cases": len(_cases)}


@app.get("/taxonomy", response_model=Taxonomy)
def get_taxonomy() -> Taxonomy:
    return _tax


@app.get("/cases", response_model=list[Case])
def list_cases(limit: int = 20, offset: int = 0) -> list[Case]:
    return list(_cases.values())[offset: offset + limit]


@app.get("/cases/{case_id}", response_model=Case)
def get_case(case_id: str) -> Case:
    if case_id not in _cases:
        raise HTTPException(404, "Case not found")
    return _cases[case_id]


@app.post("/cases/{case_id}/single-model", response_model=CheckResult)
def run_single_model(case_id: str) -> CheckResult:
    """Check one case with the single-model baseline."""
    return check_case(get_case(case_id), _tax, _client)


@app.post("/cases/{case_id}/pipeline", response_model=PipelineResult)
def run_agent_pipeline(case_id: str, mode: str = "smart") -> PipelineResult:
    """Check one case with the agent pipeline (mode = smart or full)."""
    if mode not in ("smart", "full"):
        raise HTTPException(400, "mode must be 'smart' or 'full'")
    return run_pipeline(get_case(case_id), _tax, _client, mode=mode)


# --------------------------------------------------------------------------- review app
@app.get("/", include_in_schema=False)
def review_app() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/overview")
def overview(setup: str | None = None) -> dict:
    """Everything the case list needs: saved AI runs, one row per case, and review stats."""
    setups = rv.list_setups()
    if setup is None:
        preferred = ["pipeline_smart_v2", "pipeline_smart"]  # the setup kept in decision #12
        setup = next((p for p in preferred if p in setups),
                     next((s for s in setups if s.startswith("pipeline_smart")), setups[0] if setups else ""))
    results = rv.load_results(setup) if setup else {}
    reviews = rv.load_reviews()
    gold = rv.load_gold()
    rows = []
    for cid, res in results.items():
        case = _cases.get(cid)
        if case is None:
            continue
        rev = reviews.get(cid)
        rows.append({
            "id": cid, "n": _order.get(cid), "rating": case.rating,
            "title": case.listing.title[:90], "review_title": case.review_title[:90],
            "ai_verdict": res.get("verdict"), "ai_types": [t["type"] for t in res.get("types", [])],
            "decision": rev.decision if rev else None,
            "final_verdict": rev.final_verdict if rev else None,
            "has_gold": cid in gold,
        })
    rows.sort(key=lambda r: r["n"] or 0)
    return {"setups": setups, "setup": setup, "cases": rows, "stats": rv.stats(reviews),
            "taxonomy": _tax.model_dump()}


@app.get("/api/cases/{case_id}/detail")
def case_detail(case_id: str, setup: str) -> dict:
    """One case with the AI result for `setup`, your saved review and your gold label (if any)."""
    case = get_case(case_id)
    return {"case": case.model_dump(), "n": _order.get(case_id),
            "result": rv.load_results(setup).get(case_id),
            "review": (r.model_dump() if (r := rv.load_reviews().get(case_id)) else None),
            "gold": rv.load_gold().get(case_id)}


@app.post("/api/reviews")
def save_review(inp: rv.ReviewIn) -> dict:
    """Confirm or overrule the AI. The latest review of a case wins."""
    get_case(inp.case_id)
    ai = rv.load_results(inp.setup).get(inp.case_id)
    if ai is None:
        raise HTTPException(404, "No AI result for this case in that setup")
    try:
        review = rv.make_review(inp, ai, _tax)
    except rv.ReviewError as e:
        raise HTTPException(400, str(e)) from e
    rv.save_review(review)
    return {"review": review.model_dump(), "stats": rv.stats(rv.load_reviews())}


@app.post("/api/cases/{case_id}/run")
def run_live(case_id: str) -> dict:
    """Run the smart pipeline on a case right now (uses your API key) and save it to the 'live_app' setup."""
    res = run_pipeline(get_case(case_id), _tax, _client, mode="smart")
    path = rv.results_dir() / "live_app.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(res.model_dump_json() + "\n")
    return {"setup": "live_app", "result": res.model_dump()}

