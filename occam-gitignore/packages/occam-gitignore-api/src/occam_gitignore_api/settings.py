"""Server settings (composition root inputs)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Settings"]

_ENV_DATA_DIR = "OCCAM_GITIGNORE_DATA_DIR"
_ENV_MAX_TREE = "OCCAM_GITIGNORE_API_MAX_TREE"


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable runtime settings."""

    templates_dir: Path
    rules_table_path: Path
    max_tree_size: int = 10_000

    @classmethod
    def from_env(cls) -> Settings:
        data = os.environ.get(_ENV_DATA_DIR)
        if data is None:
            raise RuntimeError(
                f"Set {_ENV_DATA_DIR} to the directory containing rules_table.json + templates/",
            )
        root = Path(data)
        return cls(
            templates_dir=root / "templates",
            rules_table_path=root / "rules_table.json",
            max_tree_size=int(os.environ.get(_ENV_MAX_TREE, "10000")),
        )
