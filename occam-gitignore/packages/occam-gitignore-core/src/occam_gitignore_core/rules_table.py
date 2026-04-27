"""Adapter implementing `RulesTable` from a JSON payload."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, cast

from .errors import RulesTableError
from .schema import Feature, Rule, RuleSource

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["JsonRulesTable"]

_Entry = tuple[frozenset[Feature], tuple[Rule, ...]]


def _canonical_entries(entries: list[dict[str, object]]) -> bytes:
    """Stable bytes used to derive a content-addressed version."""
    normalized: list[dict[str, object]] = []
    for entry in entries:
        features = sorted(cast("list[str]", entry.get("features", [])))
        patterns = sorted(set(cast("list[str]", entry.get("patterns", []))))
        normalized.append({"features": features, "patterns": patterns})
    normalized.sort(key=lambda e: (e["features"], e["patterns"]))
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _coerce_payload(payload: object) -> tuple[str, tuple[_Entry, ...]]:
    if not isinstance(payload, dict):
        raise RulesTableError("rules table root must be an object")
    declared = payload.get("version", "0")
    if not isinstance(declared, str):
        raise RulesTableError("rules table 'version' must be a string")
    raw_rules = payload.get("rules", [])
    if not isinstance(raw_rules, list):
        raise RulesTableError("rules table 'rules' must be a list")

    # Verify content-addressed version: a `sha256:<hex>` declaration must
    # equal the recomputed hash of the canonical encoding. This makes the
    # rules table tamper-evident. Non-`sha256:` declarations are accepted
    # verbatim (legacy/dev tables) so callers can pin a human-readable tag.
    canonical = _canonical_entries(raw_rules)
    computed = f"sha256:{hashlib.sha256(canonical).hexdigest()[:12]}"
    if declared.startswith("sha256:") and declared != computed:
        raise RulesTableError(
            f"rules table version mismatch: declared {declared!r}, "
            f"computed {computed!r} (rules were edited without rehashing)",
        )
    version = computed if declared.startswith("sha256:") else declared

    entries: list[_Entry] = []
    for idx, item in enumerate(raw_rules):
        if not isinstance(item, dict):
            raise RulesTableError(f"rules[{idx}] must be an object")
        features_raw = item.get("features", [])
        patterns_raw = item.get("patterns", [])
        if not isinstance(features_raw, list) or not isinstance(patterns_raw, list):
            raise RulesTableError(f"rules[{idx}] features/patterns must be lists")
        features = frozenset(Feature(cast("str", f)) for f in features_raw)
        rules = tuple(
            Rule(pattern=cast("str", p), source=RuleSource.MINED) for p in patterns_raw
        )
        entries.append((features, rules))
    return version, tuple(entries)


class JsonRulesTable:
    """Mined rules table. Schema: `{"version": str, "rules": [{features, patterns}]}`."""

    __slots__ = ("_data", "_version")

    def __init__(self, payload: object) -> None:
        version, entries = _coerce_payload(payload)
        self._version = version
        self._data = entries

    @classmethod
    def from_file(cls, path: Path) -> JsonRulesTable:
        return cls(json.loads(path.read_text("utf-8")))

    @classmethod
    def empty(cls, version: str = "0") -> JsonRulesTable:
        return cls({"version": version, "rules": []})

    def extras_for(self, features: frozenset[Feature]) -> tuple[Rule, ...]:
        collected: list[Rule] = []
        for required, rules in self._data:
            if required.issubset(features):
                collected.extend(rules)
        seen: set[str] = set()
        deduped: list[Rule] = []
        for rule in collected:
            if rule.pattern not in seen:
                seen.add(rule.pattern)
                deduped.append(rule)
        return tuple(sorted(deduped, key=lambda r: r.pattern))

    def version(self) -> str:
        return self._version
