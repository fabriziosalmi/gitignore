"""Ports (interfaces). Adapters live elsewhere; core depends only on these."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .schema import Feature, FingerprintResult, Rule


@runtime_checkable
class TemplateRepository(Protocol):
    """Provides canonical rules per feature. Implementations: FS, in-memory."""

    def get(self, feature: Feature) -> tuple[Rule, ...]: ...
    def features(self) -> tuple[Feature, ...]: ...
    def version(self) -> str: ...


@runtime_checkable
class RulesTable(Protocol):
    """Provides mined extra rules conditional on feature sets."""

    def extras_for(self, features: frozenset[Feature]) -> tuple[Rule, ...]: ...
    def version(self) -> str: ...


@runtime_checkable
class Fingerprinter(Protocol):
    """Maps a repository tree (list of paths) to a feature set."""

    def fingerprint(self, tree: tuple[str, ...]) -> FingerprintResult: ...
