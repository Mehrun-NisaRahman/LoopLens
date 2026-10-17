"""Load and validate the mismatch taxonomy (verdicts + mismatch types)."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from . import config


class Verdict(BaseModel):
    id: str
    definition: str


class MismatchType(BaseModel):
    id: str
    name: str
    definition: str
    needs_image: bool = False


class Taxonomy(BaseModel):
    verdicts: list[Verdict]
    types: list[MismatchType]

    @property
    def verdict_ids(self) -> set[str]:
        return {v.id for v in self.verdicts}

    @property
    def type_ids(self) -> set[str]:
        return {t.id for t in self.types}

    def as_prompt(self) -> str:
        v = "\n".join(f"- {x.id}: {x.definition}" for x in self.verdicts)
        t = "\n".join(f"- {x.id}: {x.definition}" for x in self.types)
        return f"Verdicts:\n{v}\n\nMismatch types (only if verdict is mismatch):\n{t}"


def load_taxonomy(path: Path | None = None) -> Taxonomy:
    path = path or config.TAXONOMY_PATH
    tax = Taxonomy(**yaml.safe_load(path.read_text(encoding="utf-8")))
    if len(tax.type_ids) != len(tax.types) or len(tax.verdict_ids) != len(tax.verdicts):
        raise ValueError("Duplicate ids in taxonomy")
    return tax
