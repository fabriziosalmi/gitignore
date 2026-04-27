"""MCP server: tools + resources over occam-gitignore-core.

Tools (verbs):
  - occam_gitignore.fingerprint_repo : tree[] -> {features, evidence}
  - occam_gitignore.generate         : tree[] | features[] -> gitignore text + hash
  - occam_gitignore.diff_against     : existing + tree -> structured diff

Resources (nouns, content-addressed):
  - occam-gitignore://version
  - occam-gitignore://rules-table
  - occam-gitignore://templates/{feature}
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from occam_gitignore_core import (
    CORE_VERSION,
    DefaultFingerprinter,
    Feature,
    FileSystemTemplateRepository,
    FingerprintResult,
    GenerateOptions,
    JsonRulesTable,
    OccamGitignoreError,
    TemplateNotFoundError,
    generate,
)

if TYPE_CHECKING:
    from .settings import Settings

__all__ = ["build_server"]


def build_server(settings: Settings) -> FastMCP:
    """Construct an MCP server wired against the given settings."""
    templates = FileSystemTemplateRepository(settings.templates_dir)
    rules_table = JsonRulesTable.from_file(settings.rules_table_path)
    fingerprinter = DefaultFingerprinter()

    server = FastMCP(
        name="occam-gitignore",
        instructions=(
            "Deterministic .gitignore generation. "
            "Same inputs -> byte-identical output. "
            "Use fingerprint_repo to detect features, then generate."
        ),
    )

    @server.tool(
        name="occam_gitignore.fingerprint_repo",
        description="Detect features (python/node/...) from a list of repo paths.",
    )
    def fingerprint_repo(tree: list[str]) -> dict[str, object]:
        fp = fingerprinter.fingerprint(tuple(tree))
        return {
            "features": [f.name for f in fp.features],
            "evidence": [{"feature": e[0], "path": e[1]} for e in fp.evidence],
        }

    @server.tool(
        name="occam_gitignore.generate",
        description=(
            "Generate a .gitignore. Provide either 'tree' (paths) or 'features' "
            "(explicit list). Output is byte-deterministic; output_hash is sha256."
        ),
    )
    def generate_tool(
        tree: list[str] | None = None,
        features: list[str] | None = None,
        extras: list[str] | None = None,
        include_comments: bool = True,
        include_provenance: bool = False,
    ) -> dict[str, object]:
        fp = _resolve_fingerprint(fingerprinter, tree, features)
        try:
            output = generate(
                fp,
                GenerateOptions(
                    extras=tuple(extras or ()),
                    include_comments=include_comments,
                    include_provenance=include_provenance,
                ),
                templates=templates,
                rules_table=rules_table,
            )
        except OccamGitignoreError as exc:
            return {"error": str(exc), "kind": type(exc).__name__}
        return {
            "content": output.content,
            "content_hash": output.content_hash,
            "provenance_hash": output.provenance_hash,
            "output_hash": output.content_hash,
            "rules_table_version": output.rules_table_version,
            "templates_version": output.templates_version,
            "core_version": output.core_version,
            "rules": [
                {"pattern": r.pattern, "source": r.source.value, "feature": r.feature}
                for r in output.rules
            ],
        }

    @server.tool(
        name="occam_gitignore.diff_against",
        description=(
            "Compute a structured diff between an existing .gitignore (text) and "
            "the deterministic output for the given tree/features. "
            "Returns added/removed pattern sets."
        ),
    )
    def diff_against(
        existing: str,
        tree: list[str] | None = None,
        features: list[str] | None = None,
    ) -> dict[str, object]:
        fp = _resolve_fingerprint(fingerprinter, tree, features)
        try:
            output = generate(
                fp,
                GenerateOptions(include_comments=False),
                templates=templates,
                rules_table=rules_table,
            )
        except OccamGitignoreError as exc:
            return {"error": str(exc), "kind": type(exc).__name__}
        existing_set = _parse_patterns(existing)
        proposed_set = frozenset(r.pattern for r in output.rules)
        return {
            "added": sorted(proposed_set - existing_set),
            "removed": sorted(existing_set - proposed_set),
            "unchanged_count": len(existing_set & proposed_set),
            "content_hash": output.content_hash,
            "provenance_hash": output.provenance_hash,
            "output_hash": output.content_hash,
        }

    @server.resource(
        "occam-gitignore://version",
        name="occam-gitignore-version",
        description="Versions of core and rules table.",
        mime_type="application/json",
    )
    def res_version() -> str:
        return json.dumps(
            {
                "core_version": CORE_VERSION,
                "rules_table_version": rules_table.version(),
                "templates_version": templates.version(),
            },
            sort_keys=True,
        )

    @server.resource(
        "occam-gitignore://rules-table",
        name="occam-gitignore-rules-table",
        description="The mined rules table currently in use.",
        mime_type="application/json",
    )
    def res_rules_table() -> str:
        return settings.rules_table_path.read_text("utf-8")

    @server.resource(
        "occam-gitignore://templates/{feature}",
        name="occam-gitignore-template",
        description="Canonical template for a single feature (e.g. python, node).",
        mime_type="text/plain",
    )
    def res_template(feature: str) -> str:
        try:
            rules = templates.get(Feature(feature))
        except TemplateNotFoundError as exc:
            return f"# template not found: {exc}"
        return "\n".join(r.pattern for r in rules) + "\n"
    return server


def _resolve_fingerprint(
    fingerprinter: DefaultFingerprinter,
    tree: list[str] | None,
    features: list[str] | None,
) -> FingerprintResult:
    if tree is None and features is None:
        raise ValueError("provide 'tree' or 'features'")
    if features is not None:
        return FingerprintResult(
            features=tuple(sorted({Feature(name) for name in features})),
        )
    assert tree is not None  # noqa: S101
    return fingerprinter.fingerprint(tuple(tree))


def _parse_patterns(text: str) -> frozenset[str]:
    out: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return frozenset(out)
