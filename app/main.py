"""LoopLens API. Run:  uvicorn app.main:app --reload   then open http://127.0.0.1:8000/docs"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from looplens import __version__, config
from looplens.data import Case, load_cases
from looplens.model import ModelClient
from looplens.single_model import CheckResult, check_case
from looplens.taxonomy import Taxonomy, load_taxonomy

app = FastAPI(title="LoopLens API", version=__version__,
              description="Does what the buyer received match the listing? AI checks, a human decides.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

_tax: Taxonomy = load_taxonomy()
_cases: dict[str, Case] = {c.id: c for c in load_cases()}
_client = ModelClient()


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
