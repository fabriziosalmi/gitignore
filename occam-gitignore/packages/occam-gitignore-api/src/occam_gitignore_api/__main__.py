"""CLI entry point: occam-gitignore-api."""

from __future__ import annotations

import argparse

import uvicorn

from .app import build_app
from .settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="occam-gitignore-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args(argv)

    if args.data_dir:
        import os  # noqa: PLC0415

        os.environ["OCCAM_GITIGNORE_DATA_DIR"] = args.data_dir
    settings = Settings.from_env()
    app = build_app(settings)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
