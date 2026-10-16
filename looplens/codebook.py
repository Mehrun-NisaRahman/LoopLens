"""Load and validate the codebook."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from . import config


class Code(BaseModel):
    id: str
    name: str
    definition: str
    needs_image: bool = False


class Codebook(BaseModel):
    codes: list[Code]

    @property
    def ids(self) -> set[str]:
        return {c.id for c in self.codes}

    def as_prompt(self) -> str:
        """The codebook as a compact list for the model prompt."""
        return "\n".join(f"- {c.id}: {c.definition}" for c in self.codes)


def load_codebook(path: Path | None = None) -> Codebook:
    path = path or config.CODEBOOK_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    book = Codebook(**data)
    if len(book.ids) != len(book.codes):
        raise ValueError("Duplicate code ids in codebook")
    return book
