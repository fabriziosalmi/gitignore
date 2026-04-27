"""Adapters implementing `TemplateRepository`."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from .errors import TemplateNotFoundError
from .schema import Feature, Rule, RuleSource

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["FileSystemTemplateRepository", "InMemoryTemplateRepository"]


def _parse(content: str, feature: Feature) -> tuple[Rule, ...]:
    rules: list[Rule] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rules.append(Rule(pattern=line, source=RuleSource.TEMPLATE, feature=feature.name))
    return tuple(rules)


class FileSystemTemplateRepository:
    """Loads `<feature>.gitignore` files from a directory. Caches per-feature.

    The repository version is **content-addressed**: it is the prefix of
    ``sha256(name1\\0content1\\0name2\\0content2...)`` over all template
    files sorted by name. Two repositories are version-equal iff every
    template file has identical bytes. The version cannot drift from the
    contents.

    A user-supplied ``version`` overrides this only for testing; it is
    rejected unless it equals the computed one.
    """

    __slots__ = ("_cache", "_root", "_version")

    def __init__(self, root: Path, version: str | None = None) -> None:
        self._root = root
        self._cache: dict[Feature, tuple[Rule, ...]] = {}
        computed = self._compute_version()
        if version is None:
            self._version = computed
        elif version.startswith("sha256:") and version != computed:
            from .errors import RulesTableError  # noqa: PLC0415
            raise RulesTableError(
                f"templates version mismatch: caller said {version!r} "
                f"but contents hash to {computed!r}",
            )
        else:
            self._version = version if not version.startswith("sha256:") else computed

    def _compute_version(self) -> str:
        digest = hashlib.sha256()
        for path in sorted(self._root.glob("*.gitignore")):
            digest.update(path.name.encode("utf-8"))
            digest.update(b"\x00")
            digest.update(path.read_bytes())
            digest.update(b"\x00")
        return f"sha256:{digest.hexdigest()[:12]}"

    def get(self, feature: Feature) -> tuple[Rule, ...]:
        cached = self._cache.get(feature)
        if cached is not None:
            return cached
        path = self._root / f"{feature.name}.gitignore"
        if not path.is_file():
            raise TemplateNotFoundError(feature.name)
        rules = _parse(path.read_text("utf-8"), feature)
        self._cache[feature] = rules
        return rules

    def features(self) -> tuple[Feature, ...]:
        names = sorted(p.stem for p in self._root.glob("*.gitignore"))
        return tuple(Feature(n) for n in names)

    def version(self) -> str:
        return self._version


class InMemoryTemplateRepository:
    """Test-friendly in-memory implementation.

    Version is **content-addressed** by default, just like the FS adapter.
    """

    __slots__ = ("_data", "_version")

    def __init__(
        self,
        data: dict[Feature, tuple[Rule, ...]],
        version: str | None = None,
    ) -> None:
        self._data = dict(data)
        computed = self._compute_version()
        if version is None:
            self._version = computed
        elif version.startswith("sha256:") and version != computed:
            from .errors import RulesTableError  # noqa: PLC0415
            raise RulesTableError(
                f"templates version mismatch: caller said {version!r} "
                f"but contents hash to {computed!r}",
            )
        else:
            self._version = version if not version.startswith("sha256:") else computed

    def _compute_version(self) -> str:
        digest = hashlib.sha256()
        for feature in sorted(self._data):
            digest.update(feature.name.encode("utf-8"))
            digest.update(b"\x00")
            for rule in self._data[feature]:
                digest.update(rule.pattern.encode("utf-8"))
                digest.update(b"\n")
            digest.update(b"\x00")
        return f"sha256:{digest.hexdigest()[:12]}"

    def get(self, feature: Feature) -> tuple[Rule, ...]:
        if feature not in self._data:
            raise TemplateNotFoundError(feature.name)
        return self._data[feature]

    def features(self) -> tuple[Feature, ...]:
        return tuple(sorted(self._data.keys()))

    def version(self) -> str:
        return self._version
