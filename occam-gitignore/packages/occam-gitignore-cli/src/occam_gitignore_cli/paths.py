"""Resolution of bundled data assets (templates, rules table)."""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["data_root", "rules_table_path", "templates_root"]

_ENV_DATA_DIR = "OCCAM_GITIGNORE_DATA_DIR"


def data_root() -> Path:
    """Locate the data directory.

    Resolution order:
      1. `OCCAM_GITIGNORE_DATA_DIR` environment variable.
      2. `<repo-root>/data` walking up from this file (monorepo layout).
    """
    env = os.environ.get(_ENV_DATA_DIR)
    if env:
        path = Path(env)
        if not path.is_dir():
            raise FileNotFoundError(f"{_ENV_DATA_DIR}={env} is not a directory")
        return path
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data"
        if (candidate / "rules_table.json").is_file():
            return candidate
    raise FileNotFoundError("could not locate occam-gitignore data directory")


def templates_root() -> Path:
    return data_root() / "templates"


def rules_table_path() -> Path:
    return data_root() / "rules_table.json"
