"""occam-gitignore-training: offline pipelines.

Two stages:
  1. raw_to_structured: parse conversational logs into JSONL records.
  2. mine_rules: aggregate JSONL into a deterministic rules table.
"""

from .mine_rules import MineConfig, MinedRule, mine, to_payload
from .raw_to_structured import StructuredEntry, parse_log

__all__ = [
    "MineConfig",
    "MinedRule",
    "StructuredEntry",
    "mine",
    "parse_log",
    "to_payload",
]
