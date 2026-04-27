"""Conformance runner — Python reference implementation.

Replays every case under ``conformance/cases/`` against the pinned
fixtures and asserts byte-exact + hash-exact equality. Exits non-zero
on the first failure with a structured diff summary.

External implementations should mirror this logic in their own
language. The behavior asserted here is the contract.
"""

# ruff: noqa: INP001 - intentional script directory, not a package.

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "occam-gitignore-core" / "src"))

from occam_gitignore_core import (  # noqa: E402
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    generate,
)

SUITE = Path(__file__).resolve().parent
FIXTURES = SUITE / "fixtures"
CASES = SUITE / "cases"


class CaseFailureError(Exception):
    pass


def _verify_fixtures() -> tuple[FileSystemTemplateRepository, JsonRulesTable]:
    declared = json.loads((FIXTURES / "fixtures_hash.json").read_text("utf-8"))
    templates = FileSystemTemplateRepository(FIXTURES / "templates")
    rules = JsonRulesTable.from_file(FIXTURES / "rules_table.json")
    if templates.version() != declared["templates_version"]:
        raise CaseFailureError(
            f"fixtures drift: templates {templates.version()} != "
            f"{declared['templates_version']}",
        )
    if rules.version() != declared["rules_table_version"]:
        raise CaseFailureError(
            f"fixtures drift: rules_table {rules.version()} != "
            f"{declared['rules_table_version']}",
        )
    return templates, rules


def _run_case(
    case_dir: Path,
    templates: FileSystemTemplateRepository,
    rules: JsonRulesTable,
) -> None:
    tree = tuple(json.loads((case_dir / "tree.json").read_text("utf-8")))
    options_raw = json.loads((case_dir / "options.json").read_text("utf-8"))
    expected_content = (case_dir / "expected.gitignore").read_text("utf-8")
    expected_hashes = json.loads(
        (case_dir / "expected_hashes.json").read_text("utf-8"),
    )

    fp = DefaultFingerprinter().fingerprint(tree)
    out = generate(
        fp,
        GenerateOptions(
            extras=tuple(options_raw["extras"]),
            include_comments=options_raw["include_comments"],
            include_provenance=options_raw["include_provenance"],
        ),
        templates=templates,
        rules_table=rules,
    )

    if out.content != expected_content:
        # Surface a compact, character-level diff hint.
        for i, (a, b) in enumerate(zip(out.content, expected_content, strict=False)):
            if a != b:
                ctx_a = out.content[max(0, i - 20) : i + 20]
                ctx_b = expected_content[max(0, i - 20) : i + 20]
                raise CaseFailureError(
                    f"{case_dir.name}: content drift at byte {i}\n"
                    f"  actual..: {ctx_a!r}\n"
                    f"  expected: {ctx_b!r}",
                )
        raise CaseFailureError(
            f"{case_dir.name}: content length differs "
            f"(actual={len(out.content)}, expected={len(expected_content)})",
        )
    actual_hashes = {
        "content_hash": out.content_hash,
        "provenance_hash": out.provenance_hash,
        "core_version": out.core_version,
        "templates_version": out.templates_version,
        "rules_table_version": out.rules_table_version,
        "features": [f.name for f in fp.features],
    }
    for key, expected_value in expected_hashes.items():
        if actual_hashes[key] != expected_value:
            raise CaseFailureError(
                f"{case_dir.name}: {key} drift\n"
                f"  actual..: {actual_hashes[key]}\n"
                f"  expected: {expected_value}",
            )


def main() -> int:
    try:
        templates, rules = _verify_fixtures()
    except CaseFailureError as exc:
        sys.stderr.write(f"FIXTURE DRIFT: {exc}\n")
        return 2

    case_dirs = sorted(p for p in CASES.iterdir() if p.is_dir())
    if not case_dirs:
        sys.stderr.write("no cases found; run generate_cases.py first\n")
        return 2

    failures: list[str] = []
    for case_dir in case_dirs:
        try:
            _run_case(case_dir, templates, rules)
        except CaseFailureError as exc:
            failures.append(str(exc))

    if failures:
        sys.stderr.write(f"FAIL: {len(failures)}/{len(case_dirs)} cases\n")
        for f in failures:
            sys.stderr.write(f"  - {f}\n")
        return 1
    sys.stderr.write(f"OK: {len(case_dirs)}/{len(case_dirs)} cases\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
