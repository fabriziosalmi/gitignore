"""Mine a deterministic rules table from structured JSONL records.

v0 strategy (transparent, reproducible):
  For each feature F observed across the corpus, collect proposed rules from
  records that fingerprint to F. Emit a rule for F when its support among
  F-bearing records is >= min_support AND it is not already covered by the
  bundled template for F.

Output format matches ``occam_gitignore_core.JsonRulesTable``.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from occam_gitignore_core import (
    DefaultFingerprinter,
    Rule,
    TemplateRepository,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__all__ = ["MineConfig", "MinedRule", "mine", "to_payload"]


@dataclass(frozen=True, slots=True)
class MineConfig:
    """Thresholds for mining. All defaults are conservative."""

    min_support: float = 0.5
    min_repos_per_feature: int = 2
    accepted_only: bool = False
    mine_pairs: bool = True
    min_pair_support: float = 0.6
    min_pair_lift: float = 1.5
    min_repos_per_pair: int = 2


@dataclass(frozen=True, slots=True, order=True)
class MinedRule:
    """One mined rule (pattern conditional on a feature set)."""

    features: tuple[str, ...]
    pattern: str
    support: float
    n_supporting: int
    n_total: int


_DEFAULT_CONFIG = MineConfig()


def _normalize_records(
    records: Iterable[Mapping[str, object]],
    config: MineConfig,
) -> list[tuple[frozenset[str], frozenset[str]]]:
    fingerprinter = DefaultFingerprinter()
    out: list[tuple[frozenset[str], frozenset[str]]] = []
    for record in records:
        if config.accepted_only and not record.get("accepted", False):
            continue
        files = tuple(_as_str_tuple(record.get("files_listed", ())))
        rules = frozenset(_as_str_tuple(record.get("proposed_rules", ())))
        declared = _as_str_tuple(record.get("features", ()))
        features = (
            frozenset(declared)
            if declared
            else frozenset(f.name for f in fingerprinter.fingerprint(files).features)
        )
        if not features or not rules:
            continue
        out.append((features, rules))
    return out


def _group_by_feature(
    enriched: list[tuple[frozenset[str], frozenset[str]]],
) -> dict[str, list[frozenset[str]]]:
    grouped: dict[str, list[frozenset[str]]] = defaultdict(list)
    for features, rules in enriched:
        for feature_name in features:
            if feature_name == "common":
                # `common` is implicit (always present); mining per-`common`
                # would emit spurious rules. Patterns shared across many
                # features will still surface as singleton rules per feature.
                continue
            grouped[feature_name].append(rules)
    return grouped


def mine(
    records: Iterable[Mapping[str, object]],
    *,
    templates: TemplateRepository,
    config: MineConfig | None = None,
) -> tuple[MinedRule, ...]:
    """Return mined rules sorted deterministically by (features, pattern)."""
    cfg = config or _DEFAULT_CONFIG
    enriched = _normalize_records(records, cfg)
    template_index = _index_templates(templates)
    feature_repos = _group_by_feature(enriched)

    mined: list[MinedRule] = []
    single_emitted: dict[str, set[str]] = defaultdict(set)
    for feature_name in sorted(feature_repos):
        repos = feature_repos[feature_name]
        n_total = len(repos)
        if n_total < cfg.min_repos_per_feature:
            continue
        already_covered = template_index.get(feature_name, frozenset())
        pattern_counts: dict[str, int] = defaultdict(int)
        for rules in repos:
            for pattern in rules:
                if pattern in already_covered:
                    continue
                pattern_counts[pattern] += 1
        for pattern, count in pattern_counts.items():
            support = count / n_total
            if support < cfg.min_support:
                continue
            single_emitted[feature_name].add(pattern)
            mined.append(
                MinedRule(
                    features=(feature_name,),
                    pattern=pattern,
                    support=support,
                    n_supporting=count,
                    n_total=n_total,
                ),
            )

    if cfg.mine_pairs:
        mined.extend(_mine_pairs(enriched, cfg, template_index, single_emitted))
    return tuple(sorted(mined))


def _mine_pairs(
    enriched: list[tuple[frozenset[str], frozenset[str]]],
    cfg: MineConfig,
    template_index: Mapping[str, frozenset[str]],
    single_emitted: Mapping[str, set[str]],
) -> list[MinedRule]:
    """Mine patterns whose support is concentrated in feature *pairs*.

    A pattern is emitted for pair (A,B) iff:
      - support among repos with {A,B} >= min_pair_support
      - support among {A,B} repos > min_pair_lift * max(support_A, support_B)
      - not already emitted as single-feature rule for A or B
      - not already in either feature's template
    """
    feature_to_repos: dict[str, list[int]] = defaultdict(list)
    for idx, (features, _) in enumerate(enriched):
        for feature_name in features:
            if feature_name == "common":
                continue
            feature_to_repos[feature_name].append(idx)

    out: list[MinedRule] = []
    sorted_features = sorted(feature_to_repos)
    for i, fa in enumerate(sorted_features):
        for fb in sorted_features[i + 1 :]:
            out.extend(
                _mine_one_pair(
                    enriched, cfg, template_index, single_emitted, feature_to_repos, fa, fb,
                ),
            )
    return out


def _mine_one_pair(
    enriched: list[tuple[frozenset[str], frozenset[str]]],
    cfg: MineConfig,
    template_index: Mapping[str, frozenset[str]],
    single_emitted: Mapping[str, set[str]],
    feature_to_repos: Mapping[str, list[int]],
    fa: str,
    fb: str,
) -> list[MinedRule]:
    both = [idx for idx in feature_to_repos[fa] if idx in feature_to_repos[fb]]
    n_both = len(both)
    if n_both < cfg.min_repos_per_pair:
        return []
    n_a = len(feature_to_repos[fa])
    n_b = len(feature_to_repos[fb])
    covered = (
        template_index.get(fa, frozenset())
        | template_index.get(fb, frozenset())
        | single_emitted.get(fa, set())
        | single_emitted.get(fb, set())
    )
    pattern_counts_both: dict[str, int] = defaultdict(int)
    for idx in both:
        for pattern in enriched[idx][1]:
            if pattern not in covered:
                pattern_counts_both[pattern] += 1

    rules: list[MinedRule] = []
    for pattern, count_both in pattern_counts_both.items():
        support_both = count_both / n_both
        if support_both < cfg.min_pair_support:
            continue
        count_a = sum(
            1 for idx in feature_to_repos[fa] if pattern in enriched[idx][1]
        )
        count_b = sum(
            1 for idx in feature_to_repos[fb] if pattern in enriched[idx][1]
        )
        baseline = max(
            count_a / n_a if n_a else 0.0,
            count_b / n_b if n_b else 0.0,
        )
        if baseline > 0 and support_both < cfg.min_pair_lift * baseline:
            continue
        rules.append(
            MinedRule(
                features=tuple(sorted((fa, fb))),
                pattern=pattern,
                support=support_both,
                n_supporting=count_both,
                n_total=n_both,
            ),
        )
    return rules


def _index_templates(templates: TemplateRepository) -> dict[str, frozenset[str]]:
    index: dict[str, frozenset[str]] = {}
    for feature in templates.features():
        rules: tuple[Rule, ...] = templates.get(feature)
        index[feature.name] = frozenset(r.pattern for r in rules)
    return index


def _as_str_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(v) for v in value if isinstance(v, str))


def to_payload(rules: tuple[MinedRule, ...], *, version: str | None = None) -> dict[str, object]:
    """Render mined rules as a stable ``rules_table.json`` payload.

    Rules sharing the same feature set are merged; patterns sorted alphabetically.
    Version is derived deterministically from content unless provided.
    """
    grouped: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for rule in rules:
        grouped[rule.features].append(rule.pattern)
    entries: list[dict[str, object]] = []
    for features in sorted(grouped):
        patterns = sorted(set(grouped[features]))
        entries.append({"features": list(features), "patterns": patterns})
    body = json.dumps(entries, sort_keys=True, ensure_ascii=False).encode("utf-8")
    resolved_version = version or f"sha256:{hashlib.sha256(body).hexdigest()[:12]}"
    return {"version": resolved_version, "rules": entries}
