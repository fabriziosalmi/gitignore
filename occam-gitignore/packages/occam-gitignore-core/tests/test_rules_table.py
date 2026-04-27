from __future__ import annotations

import pytest

from occam_gitignore_core import (
    JsonRulesTable,
    RulesTableError,
)
from occam_gitignore_core.schema import Feature


def test_empty_table_returns_no_extras() -> None:
    table = JsonRulesTable.empty()
    assert table.extras_for(frozenset({Feature("python")})) == ()


def test_subset_match_only() -> None:
    table = JsonRulesTable(
        {
            "version": "1",
            "rules": [
                {"features": ["python", "docker"], "patterns": ["x"]},
                {"features": ["python"], "patterns": ["y"]},
            ],
        },
    )
    only_py = table.extras_for(frozenset({Feature("python")}))
    assert [r.pattern for r in only_py] == ["y"]
    both = table.extras_for(frozenset({Feature("python"), Feature("docker")}))
    assert [r.pattern for r in both] == ["x", "y"]


def test_malformed_payload_rejected() -> None:
    with pytest.raises(RulesTableError):
        JsonRulesTable("not an object")


def test_dedup_within_extras() -> None:
    table = JsonRulesTable(
        {
            "version": "1",
            "rules": [
                {"features": ["python"], "patterns": ["x", "x"]},
            ],
        },
    )
    assert [r.pattern for r in table.extras_for(frozenset({Feature("python")}))] == ["x"]
