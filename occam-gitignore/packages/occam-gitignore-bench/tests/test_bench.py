from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - used at runtime by pytest fixture

import pytest

from occam_gitignore_bench import (
    BenchCase,
    evaluate,
    load_cases,
    summarize,
)
from occam_gitignore_core import (
    Feature,
    InMemoryTemplateRepository,
    JsonRulesTable,
    Rule,
    RuleSource,
)


@pytest.fixture
def templates() -> InMemoryTemplateRepository:
    return InMemoryTemplateRepository(
        {
            Feature("python"): (
                Rule("__pycache__/", RuleSource.TEMPLATE, "python"),
                Rule("*.pyc", RuleSource.TEMPLATE, "python"),
                Rule(".venv/", RuleSource.TEMPLATE, "python"),
            ),
        },
    )


@pytest.fixture
def empty_table() -> JsonRulesTable:
    return JsonRulesTable.empty()


def test_perfect_case_yields_recall_1(
    templates: InMemoryTemplateRepository,
    empty_table: JsonRulesTable,
) -> None:
    case = BenchCase(
        name="py",
        tree=("pyproject.toml", "src/main.py"),
        expected=frozenset({"__pycache__/", "*.pyc", ".venv/"}),
    )
    result = evaluate(case, templates=templates, rules_table=empty_table, repeats=3)
    assert result.recall == 1.0
    assert result.precision == 1.0
    assert result.f1 == 1.0
    assert result.stable is True
    assert len(result.latency_ms) == 3


def test_extra_predictions_drop_precision(
    templates: InMemoryTemplateRepository,
    empty_table: JsonRulesTable,
) -> None:
    case = BenchCase(
        name="py-narrow",
        tree=("pyproject.toml",),
        expected=frozenset({"__pycache__/"}),
    )
    result = evaluate(case, templates=templates, rules_table=empty_table)
    assert result.recall == 1.0
    assert result.precision < 1.0


def test_summarize_aggregates_correctly(
    templates: InMemoryTemplateRepository,
    empty_table: JsonRulesTable,
) -> None:
    cases = (
        BenchCase("a", ("pyproject.toml",), frozenset({"__pycache__/", "*.pyc", ".venv/"})),
        BenchCase("b", ("pyproject.toml",), frozenset({"__pycache__/"})),
    )
    results = tuple(
        evaluate(c, templates=templates, rules_table=empty_table, repeats=2)
        for c in cases
    )
    summary = summarize(results)
    assert summary.n_cases == 2
    assert summary.stability_rate == 1.0
    assert 0.0 < summary.macro_f1 <= 1.0


def test_load_cases_from_disk(tmp_path: Path) -> None:
    payload = {
        "name": "demo",
        "tree": ["pyproject.toml"],
        "expected": ["__pycache__/", "*.pyc"],
    }
    (tmp_path / "demo.json").write_text(json.dumps(payload), "utf-8")
    cases = load_cases(tmp_path)
    assert len(cases) == 1
    assert cases[0].name == "demo"
    assert "*.pyc" in cases[0].expected
