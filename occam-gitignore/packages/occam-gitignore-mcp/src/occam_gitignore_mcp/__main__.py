"""CLI entry point: occam-gitignore-mcp."""

from __future__ import annotations

import argparse
import os

from .server import build_server
from .settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="occam-gitignore-mcp")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default="stdio",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args(argv)

    if args.data_dir:
        os.environ["OCCAM_GITIGNORE_DATA_DIR"] = args.data_dir

    settings = Settings.from_env()
    server = build_server(settings)

    if args.transport == "stdio":
        server.run("stdio")
    elif args.transport == "streamable-http":
        # FastMCP host/port are set via settings on the instance.
        server.settings.host = args.host
        server.settings.port = args.port
        server.run("streamable-http")
    else:
        server.settings.host = args.host
        server.settings.port = args.port
        server.run("sse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
