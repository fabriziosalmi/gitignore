"""Repository scanning utilities. Kept here, out of the pure core."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["scan_tree"]

_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn",
    "node_modules", ".venv", "venv", "env",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "target", "dist", "build",
})


def scan_tree(root: Path, *, max_entries: int = 50_000) -> tuple[str, ...]:
    """Return repo-relative POSIX paths. Bounded; skips common ignore dirs.

    Pure-ish: side effects limited to filesystem reads.
    """
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    entries: list[str] = []
    for path in _iter_files(root):
        rel = path.relative_to(root).as_posix()
        entries.append(rel)
        if len(entries) >= max_entries:
            break
    entries.sort()
    return tuple(entries)


def _iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name in _SKIP_DIRS:
                    continue
                stack.append(child)
            elif child.is_file():
                out.append(child)
    return out
