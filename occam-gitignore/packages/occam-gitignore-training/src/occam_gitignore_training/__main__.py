"""CLI: parse logs -> JSONL; mine JSONL -> rules_table.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from occam_gitignore_core import FileSystemTemplateRepository

from .mine_rules import MineConfig, mine, to_payload
from .raw_to_structured import parse_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="occam-gitignore-train")
    sub = parser.add_subparsers(dest="cmd", required=True)

    parse = sub.add_parser("parse", help="Parse a raw log into JSONL.")
    parse.add_argument("input", type=Path)
    parse.add_argument("--had-gitignore", action="store_true")
    parse.add_argument("-o", "--output", type=Path, default=None)

    mine_cmd = sub.add_parser("mine", help="Mine a rules table from JSONL records.")
    mine_cmd.add_argument("inputs", nargs="+", type=Path, help="JSONL files.")
    mine_cmd.add_argument("--templates", type=Path, required=True)
    mine_cmd.add_argument("--min-support", type=float, default=0.5)
    mine_cmd.add_argument("--min-repos", type=int, default=2)
    mine_cmd.add_argument("--accepted-only", action="store_true")
    mine_cmd.add_argument("--version", default=None, help="Override rules_table version.")
    mine_cmd.add_argument("-o", "--output", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.cmd == "parse":
        return _cmd_parse(args.input, args.had_gitignore, args.output)
    if args.cmd == "mine":
        return _cmd_mine(args)
    return 2  # unreachable


def _cmd_parse(input_path: Path, had_gitignore: bool, output: Path | None) -> int:
    text = input_path.read_text("utf-8")
    out_lines: list[str] = []
    for entry in parse_log(text):
        record = entry.to_json()
        record["had_gitignore"] = had_gitignore
        out_lines.append(json.dumps(record, sort_keys=True, ensure_ascii=False))
    payload = "\n".join(out_lines) + ("\n" if out_lines else "")
    if output is None:
        sys.stdout.write(payload)
    else:
        output.write_text(payload, "utf-8")
    return 0


def _cmd_mine(args: argparse.Namespace) -> int:
    records: list[dict[str, object]] = []
    for path in args.inputs:
        for line in path.read_text("utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            if not isinstance(obj, dict):
                continue
            records.append(obj)
    templates = FileSystemTemplateRepository(args.templates)
    config = MineConfig(
        min_support=args.min_support,
        min_repos_per_feature=args.min_repos,
        accepted_only=args.accepted_only,
    )
    mined = mine(records, templates=templates, config=config)
    payload = to_payload(mined, version=args.version)
    body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output is None:
        sys.stdout.write(body)
    else:
        args.output.write_text(body, "utf-8")
    sys.stderr.write(
        f"mined {len(mined)} rules across "
        f"{len(payload['rules']) if isinstance(payload['rules'], list) else 0} feature groups\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
