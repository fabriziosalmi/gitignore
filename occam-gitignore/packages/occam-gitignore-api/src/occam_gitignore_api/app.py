"""FastAPI app builder. Pure composition; no global state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from occam_gitignore_core import (
    CORE_VERSION,
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    OccamGitignoreError,
    generate,
)

if TYPE_CHECKING:
    from .settings import Settings

__all__ = ["build_app"]


class _FingerprintRequest(BaseModel):
    tree: list[str] = Field(..., description="Repository file paths (POSIX).")


class _FingerprintResponse(BaseModel):
    features: list[str]
    evidence: list[tuple[str, str]]


class _GenerateRequest(BaseModel):
    features: list[str] | None = None
    tree: list[str] | None = None
    extras: list[str] = []
    include_provenance: bool = False
    include_comments: bool = True


class _GenerateResponse(BaseModel):
    content: str
    content_hash: str
    provenance_hash: str
    output_hash: str  # alias of content_hash for backwards compat
    rules_table_version: str
    templates_version: str
    core_version: str


class _VersionResponse(BaseModel):
    core_version: str
    rules_table_version: str
    templates_version: str


def build_app(settings: Settings) -> FastAPI:
    """Construct a FastAPI app wired against the given settings."""
    templates = FileSystemTemplateRepository(settings.templates_dir)
    rules_table = JsonRulesTable.from_file(settings.rules_table_path)
    fingerprinter = DefaultFingerprinter()

    app = FastAPI(
        title="occam-gitignore",
        version=CORE_VERSION,
        description="Deterministic .gitignore generation. Zero latency. Reproducible.",
    )

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/occam-gitignore/version", response_model=_VersionResponse)
    def version() -> _VersionResponse:
        return _VersionResponse(
            core_version=CORE_VERSION,
            rules_table_version=rules_table.version(),
            templates_version=templates.version(),
        )

    @app.post("/v1/occam-gitignore/fingerprint", response_model=_FingerprintResponse)
    def fingerprint_endpoint(req: _FingerprintRequest) -> _FingerprintResponse:
        _validate_tree(req.tree, settings.max_tree_size)
        fp = fingerprinter.fingerprint(tuple(req.tree))
        return _FingerprintResponse(
            features=[f.name for f in fp.features],
            evidence=[(e[0], e[1]) for e in fp.evidence],
        )

    @app.post("/v1/occam-gitignore/generate", response_model=_GenerateResponse)
    def generate_endpoint(req: _GenerateRequest, response: Response) -> _GenerateResponse:
        if req.features is None and req.tree is None:
            raise HTTPException(status_code=400, detail="provide 'features' or 'tree'")
        if req.tree is not None:
            _validate_tree(req.tree, settings.max_tree_size)
            fp = fingerprinter.fingerprint(tuple(req.tree))
        else:
            assert req.features is not None  # noqa: S101 - narrowed above
            fp = fingerprinter.fingerprint(())
            from occam_gitignore_core import Feature, FingerprintResult  # noqa: PLC0415

            fp = FingerprintResult(
                features=tuple(sorted({Feature(name) for name in req.features})),
            )
        try:
            output = generate(
                fp,
                GenerateOptions(
                    extras=tuple(req.extras),
                    include_comments=req.include_comments,
                    include_provenance=req.include_provenance,
                ),
                templates=templates,
                rules_table=rules_table,
            )
        except OccamGitignoreError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response.headers["X-Occam-Gitignore-Hash"] = output.content_hash
        response.headers["X-Occam-Gitignore-Provenance"] = output.provenance_hash
        response.headers["X-Occam-Gitignore-Rules-Version"] = output.rules_table_version
        response.headers["X-Occam-Gitignore-Templates-Version"] = output.templates_version
        return _GenerateResponse(
            content=output.content,
            content_hash=output.content_hash,
            provenance_hash=output.provenance_hash,
            output_hash=output.content_hash,
            rules_table_version=output.rules_table_version,
            templates_version=output.templates_version,
            core_version=output.core_version,
        )

    return app


def _validate_tree(tree: list[str], limit: int) -> None:
    if len(tree) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"tree too large: {len(tree)} > {limit}",
        )
