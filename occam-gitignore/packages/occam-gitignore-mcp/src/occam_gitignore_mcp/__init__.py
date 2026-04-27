"""occam-gitignore-mcp: MCP server adapter over occam-gitignore-core."""

from .server import build_server
from .settings import Settings

__all__ = ["Settings", "build_server"]
