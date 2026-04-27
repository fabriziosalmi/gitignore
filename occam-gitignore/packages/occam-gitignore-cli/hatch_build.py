"""Hatch build hook: copy data/ assets into the package source tree.

Runs before wheel/sdist materialization. Resolves the data directory by
trying the monorepo layout first (`<workspace>/data/`) and then the sdist
layout (`<sdist-root>/data/`). The destination is always
`src/occam_gitignore_cli/_data/`, which is then picked up as part of the
package source.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):  # type: ignore[misc]
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version, build_data  # unused
        root = Path(self.root)
        candidates = (
            root.parent.parent / "data",  # monorepo: packages/<pkg>/ → ../../data
            root / "data",                # sdist root layout
        )
        src_data: Path | None = None
        for candidate in candidates:
            if (candidate / "rules_table.json").is_file():
                src_data = candidate
                break
        if src_data is None:
            msg = (
                "occam-gitignore: could not locate data/ directory. "
                f"Tried: {[str(c) for c in candidates]}"
            )
            raise FileNotFoundError(msg)

        dst = root / "src" / "occam_gitignore_cli" / "_data"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src_data, dst)
