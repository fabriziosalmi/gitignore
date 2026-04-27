from __future__ import annotations

import json
import random

import pytest

from occam_gitignore_core import (
    Feature,
    InMemoryTemplateRepository,
    JsonRulesTable,
    Rule,
    RuleSource,
)
from occam_gitignore_training import MineConfig, mine, to_payload


@pytest.fixture
def templates() -> InMemoryTemplateRepository:
    return InMemoryTemplateRepository(
        {
            Feature("python"): (
                Rule("__pycache__/", RuleSource.TEMPLATE, "python"),
                Rule("*.pyc", RuleSource.TEMPLATE, "python"),
            ),
            Feature("node"): (Rule("node_modules/", RuleSource.TEMPLATE, "node"),),
        },
    )


def _rec(
    repo: str,
    files: list[str],
    rules: list[str],
    *,
    accepted: bool = True,
) -> dict[str, object]:
    return {
        "repo": repo,
        "had_gitignore": False,
        "files_listed": files,
        "proposed_rules": rules,
        "accepted": accepted,
    }


def test_mining_filters_template_patterns(templates: InMemoryTemplateRepository) -> None:
    records = [
        _rec("a", ["pyproject.toml"], ["__pycache__/", ".env", "coverage.xml"]),
        _rec("b", ["pyproject.toml"], ["__pycache__/", ".env", "coverage.xml"]),
    ]
    rules = mine(records, templates=templates, config=MineConfig(min_support=0.5))
    patterns = {r.pattern for r in rules}
    assert "__pycache__/" not in patterns  # already in template
    assert ".env" in patterns
    assert "coverage.xml" in patterns


def test_mining_respects_min_support(templates: InMemoryTemplateRepository) -> None:
    records = [
        _rec("a", ["pyproject.toml"], [".env"]),
        _rec("b", ["pyproject.toml"], ["coverage.xml"]),
        _rec("c", ["pyproject.toml"], [".env"]),
    ]
    high = mine(records, templates=templates, config=MineConfig(min_support=0.6))
    low = mine(records, templates=templates, config=MineConfig(min_support=0.3))
    assert {r.pattern for r in high} == {".env"}
    assert {".env", "coverage.xml"}.issubset({r.pattern for r in low})


def test_mining_respects_min_repos(templates: InMemoryTemplateRepository) -> None:
    records = [_rec("a", ["pyproject.toml"], [".env"])]
    rules = mine(records, templates=templates, config=MineConfig(min_repos_per_feature=2))
    assert rules == ()


def test_mining_is_input_order_invariant(templates: InMemoryTemplateRepository) -> None:
    records = [
        _rec("a", ["pyproject.toml"], [".env", "secrets/"]),
        _rec("b", ["pyproject.toml"], [".env", "secrets/"]),
        _rec("c", ["package.json"], ["dist/"]),
        _rec("d", ["package.json"], ["dist/"]),
    ]
    rng = random.Random(7)
    shuffled = records[:]
    rng.shuffle(shuffled)
    a = mine(records, templates=templates)
    b = mine(shuffled, templates=templates)
    assert a == b


def test_payload_is_deterministic_and_loadable(templates: InMemoryTemplateRepository) -> None:
    records = [
        _rec("a", ["pyproject.toml"], [".env"]),
        _rec("b", ["pyproject.toml"], [".env"]),
    ]
    rules = mine(records, templates=templates)
    p1 = to_payload(rules)
    p2 = to_payload(rules)
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    table = JsonRulesTable(p1)
    extras = table.extras_for(frozenset({Feature("python")}))
    assert ".env" in {r.pattern for r in extras}


def test_accepted_only_filter(templates: InMemoryTemplateRepository) -> None:
    records = [
        _rec("a", ["pyproject.toml"], [".env"], accepted=True),
        _rec("b", ["pyproject.toml"], [".env"], accepted=False),
    ]
    strict = mine(
        records,
        templates=templates,
        config=MineConfig(accepted_only=True, min_repos_per_feature=2),
    )
    assert strict == ()
    permissive = mine(records, templates=templates, config=MineConfig(accepted_only=False))
    assert any(r.pattern == ".env" for r in permissive)
