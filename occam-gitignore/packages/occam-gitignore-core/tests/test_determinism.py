from __future__ import annotations

import random

import pytest

from occam_gitignore_core import (
    DefaultFingerprinter,
    Feature,
    GenerateOptions,
    InMemoryTemplateRepository,
    JsonRulesTable,
    Rule,
    RuleSource,
    generate,
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
            Feature("docker"): (
                Rule(".dockerignore.local", RuleSource.TEMPLATE, "docker"),
            ),
        },
        version="t1",
    )


@pytest.fixture
def rules_table() -> JsonRulesTable:
    return JsonRulesTable(
        {
            "version": "r1",
            "rules": [
                {"features": ["python", "docker"], "patterns": ["coverage.xml", "htmlcov/"]},
            ],
        },
    )


def test_generate_is_byte_identical_across_runs(
    templates: InMemoryTemplateRepository,
    rules_table: JsonRulesTable,
) -> None:
    fp = DefaultFingerprinter().fingerprint(("pyproject.toml", "Dockerfile"))
    a = generate(fp, GenerateOptions(), templates=templates, rules_table=rules_table)
    b = generate(fp, GenerateOptions(), templates=templates, rules_table=rules_table)
    assert a.content == b.content
    assert a.output_hash == b.output_hash


def test_generate_is_invariant_to_input_order(
    templates: InMemoryTemplateRepository,
    rules_table: JsonRulesTable,
) -> None:
    tree = ["pyproject.toml", "Dockerfile", "src/main.py", "tests/test_x.py"]
    rng = random.Random(42)
    shuffled = tree[:]
    rng.shuffle(shuffled)
    fp1 = DefaultFingerprinter().fingerprint(tuple(tree))
    fp2 = DefaultFingerprinter().fingerprint(tuple(shuffled))
    a = generate(fp1, GenerateOptions(), templates=templates, rules_table=rules_table)
    b = generate(fp2, GenerateOptions(), templates=templates, rules_table=rules_table)
    assert a.output_hash == b.output_hash


def test_generate_includes_mined_rules(
    templates: InMemoryTemplateRepository,
    rules_table: JsonRulesTable,
) -> None:
    fp = DefaultFingerprinter().fingerprint(("pyproject.toml", "Dockerfile"))
    out = generate(fp, GenerateOptions(), templates=templates, rules_table=rules_table)
    patterns = {r.pattern for r in out.rules}
    assert "coverage.xml" in patterns
    assert "htmlcov/" in patterns


def test_user_extras_appear_after_templates_and_mined(
    templates: InMemoryTemplateRepository,
    rules_table: JsonRulesTable,
) -> None:
    fp = DefaultFingerprinter().fingerprint(("pyproject.toml",))
    out = generate(
        fp,
        GenerateOptions(extras=("custom-secret.env",)),
        templates=templates,
        rules_table=rules_table,
    )
    sources = [r.source for r in out.rules]
    user_idx = sources.index(RuleSource.USER_EXTRA)
    assert all(s is not RuleSource.USER_EXTRA for s in sources[:user_idx])


def test_output_carries_versions(
    templates: InMemoryTemplateRepository,
    rules_table: JsonRulesTable,
) -> None:
    fp = DefaultFingerprinter().fingerprint(("pyproject.toml",))
    out = generate(fp, GenerateOptions(), templates=templates, rules_table=rules_table)
    assert out.rules_table_version == "r1"
    assert out.core_version
    assert out.output_hash.startswith("sha256:")
