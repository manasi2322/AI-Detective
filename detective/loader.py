"""Load a case folder: case.json (cast + places), documents/*.txt (evidence), solution.json (answer key)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .models import Case, Document, Location, Person


def _parse_front_matter(raw: str, path: Path) -> tuple[dict[str, str], str]:
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: document must start with a '---' front-matter block")
    meta: dict[str, str] = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "".join(lines[i + 1 :])
            return meta, body
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"{path}: bad front-matter line {line!r}")
        meta[key.strip()] = value.strip()
    raise ValueError(f"{path}: front-matter block is never closed")


def load_document(path: Path) -> Document:
    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"), path)
    for required in ("id", "type", "title", "date"):
        if required not in meta:
            raise ValueError(f"{path}: missing front-matter field '{required}'")
    return Document(
        id=meta["id"],
        type=meta["type"],
        title=meta["title"],
        date=date.fromisoformat(meta["date"]),
        body=body,
        path=str(path),
        author=meta.get("author"),
    )


def load_case(case_dir: str | Path) -> Case:
    root = Path(case_dir)
    spec = json.loads((root / "case.json").read_text(encoding="utf-8"))
    documents: dict[str, Document] = {}
    for path in sorted((root / "documents").glob("*.txt")):
        doc = load_document(path)
        if doc.id in documents:
            raise ValueError(f"duplicate document id {doc.id!r}")
        documents[doc.id] = doc
    return Case(
        id=spec["id"],
        title=spec["title"],
        difficulty=spec.get("difficulty", "unknown"),
        incident_date=date.fromisoformat(spec["incident_date"]),
        summary=spec.get("summary", ""),
        people=[
            Person(p["name"], p.get("role", ""), bool(p.get("suspect")), tuple(p.get("aliases", ())), bool(p.get("outside")))
            for p in spec["people"]
        ],
        locations=[
            Location(l["name"], tuple(l.get("aliases", ())), bool(l.get("onsite", True)), bool(l.get("entrance", False)))
            for l in spec["locations"]
        ],
        documents=documents,
        root=str(root),
        scene=spec.get("scene"),
        window=spec.get("window"),
        item=tuple([spec["item"]["name"], *spec["item"].get("aliases", ())]) if "item" in spec else (),
    )


def load_solution(case_dir: str | Path) -> dict:
    """The answer key. Only tests/evaluation read this; the investigation pipeline never does."""
    return json.loads((Path(case_dir) / "solution.json").read_text(encoding="utf-8"))
