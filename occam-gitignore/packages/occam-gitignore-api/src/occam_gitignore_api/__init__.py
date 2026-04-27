"""occam-gitignore-api: thin FastAPI adapter over occam-gitignore-core."""

from .app import build_app
from .settings import Settings

__all__ = ["Settings", "build_app"]
