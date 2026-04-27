"""Bench case loader. Cases live as JSON files in a corpus directory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["BenchCase", "load_cases"]


@dataclass(frozen=True, slots=True)
class BenchCase:
    """A single benchmark fixture.

    `tree`     : POSIX-style relative paths the repo would expose.
    `expected` : the ground-truth set of `.gitignore` patterns.
    `name`     : human-readable identifier (filename stem by default).
    """

    name: str
    tree: tuple[str, ...]
    expected: frozenset[str]


def load_cases(corpus: Path) -> tuple[BenchCase, ...]:
    """Load all `*.json` cases under `corpus`. Sorted by name."""
    if not corpus.is_dir():
        raise NotADirectoryError(str(corpus))
    return tuple(_load_one(path) for path in sorted(corpus.glob("*.json")))


def _load_one(path: Path) -> BenchCase:
    payload = json.loads(path.read_text("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path}: case must be a JSON object")
    name_raw = payload.get("name", path.stem)
    tree_raw = payload.get("tree", [])
    expected_raw = payload.get("expected", [])
    if not isinstance(tree_raw, list) or not isinstance(expected_raw, list):
        raise TypeError(f"{path}: tree/expected must be lists")
    return BenchCase(
        name=str(name_raw),
        tree=tuple(str(p) for p in tree_raw if isinstance(p, str)),
        expected=frozenset(str(p) for p in expected_raw if isinstance(p, str)),
    )
