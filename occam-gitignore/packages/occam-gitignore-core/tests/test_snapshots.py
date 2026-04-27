"""Snapshot tests: lock canonical generator output.

If a snapshot fails, inspect the diff. To intentionally update, regenerate via:
    python -m occam_gitignore_core._snapshot_helper  (dev-only)
or manually replace the file contents and the matching hash.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from occam_gitignore_core import (
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    generate,
)

_DATA = Path(__file__).resolve().parents[3] / "data"
_SNAP = Path(__file__).resolve().parent / "snapshots"

_CASES = (
    (
        "python",
        ("pyproject.toml",),
        "sha256:f60d84f0ab1da237a8003acef70145e98a3d039bed9bc79c7f0a4c17cade4e90",
    ),
    (
        "node-ts",
        ("package.json", "tsconfig.json"),
        "sha256:f05907a1ec2d8189616ac950e537b24e5d2aa5a7be84ed7b525dacac03dcb664",
    ),
    (
        "python-docker",
        ("pyproject.toml", "Dockerfile", "docker-compose.yml"),
        "sha256:5e21738c00254f6a7b1bdeaf0abe5d0152d4ed870c102646c55997822dce900a",
    ),
    (
        "java",
        ("pom.xml", "src/main/java/A.java"),
        "sha256:160ee63c422320c0a096520510c0765ceb89272fe56dfa6a0eae39b2b9d3f014",
    ),
    (
        "rust",
        ("Cargo.toml", "src/main.rs"),
        "sha256:fb39ef6a7c20585ea58288bbf42004f9abaec3529715fa0f2d281c8bb473635b",
    ),
)


@pytest.fixture(scope="module")
def deps() -> tuple[FileSystemTemplateRepository, JsonRulesTable]:
    return (
        FileSystemTemplateRepository(_DATA / "templates"),
        JsonRulesTable.from_file(_DATA / "rules_table.json"),
    )


@pytest.mark.parametrize(("label", "tree", "expected_hash"), _CASES)
def test_snapshot_matches(
    deps: tuple[FileSystemTemplateRepository, JsonRulesTable],
    label: str,
    tree: tuple[str, ...],
    expected_hash: str,
) -> None:
    templates, rules = deps
    fp = DefaultFingerprinter().fingerprint(tree)
    out = generate(
        fp,
        GenerateOptions(include_comments=True),
        templates=templates,
        rules_table=rules,
    )
    snapshot_file = _SNAP / f"{label}.gitignore"
    assert snapshot_file.exists(), f"missing snapshot {snapshot_file}"
    assert out.content == snapshot_file.read_text("utf-8"), (
        f"snapshot drift for {label}: regenerate intentionally"
    )
    digest = "sha256:" + hashlib.sha256(out.content.encode("utf-8")).hexdigest()
    assert digest == expected_hash
    assert out.output_hash == expected_hash
