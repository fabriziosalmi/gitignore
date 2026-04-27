"""Metrics: precision/recall/F1, stability, latency."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from occam_gitignore_core import (
    DefaultFingerprinter,
    GenerateOptions,
    generate,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from occam_gitignore_core import RulesTable, TemplateRepository

    from .cases import BenchCase

__all__ = ["CaseResult", "ReportSummary", "evaluate", "summarize"]


@dataclass(frozen=True, slots=True)
class CaseResult:
    """Per-case metrics with diagnostics."""

    name: str
    precision: float
    recall: float
    f1: float
    n_predicted: int
    n_expected: int
    n_correct: int
    stable: bool
    false_negatives: tuple[str, ...] = ()
    false_positives: tuple[str, ...] = ()
    latency_ms: tuple[float, ...] = field(default_factory=tuple)

    @property
    def latency_p50(self) -> float:
        return _percentile(self.latency_ms, 50.0)

    @property
    def latency_p99(self) -> float:
        return _percentile(self.latency_ms, 99.0)


@dataclass(frozen=True, slots=True)
class ReportSummary:
    """Corpus-wide aggregates."""

    n_cases: int
    macro_precision: float
    macro_recall: float
    macro_f1: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    stability_rate: float
    latency_p50_ms: float
    latency_p99_ms: float


def evaluate(
    case: BenchCase,
    *,
    templates: TemplateRepository,
    rules_table: RulesTable,
    repeats: int = 5,
) -> CaseResult:
    """Run a case `repeats` times. Verify byte-stability and measure latency."""
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    fingerprinter = DefaultFingerprinter()
    fp = fingerprinter.fingerprint(case.tree)

    latencies: list[float] = []
    first_hash: str | None = None
    stable = True
    last_predicted: frozenset[str] = frozenset()

    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        out = generate(
            fp,
            GenerateOptions(include_comments=False),
            templates=templates,
            rules_table=rules_table,
        )
        latencies.append((time.perf_counter_ns() - t0) / 1_000_000.0)
        if first_hash is None:
            first_hash = out.content_hash
        elif out.content_hash != first_hash:
            stable = False
        last_predicted = frozenset(r.pattern for r in out.rules)

    correct = last_predicted & case.expected
    precision = len(correct) / len(last_predicted) if last_predicted else 0.0
    recall = len(correct) / len(case.expected) if case.expected else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return CaseResult(
        name=case.name,
        precision=precision,
        recall=recall,
        f1=f1,
        n_predicted=len(last_predicted),
        n_expected=len(case.expected),
        n_correct=len(correct),
        stable=stable,
        false_negatives=tuple(sorted(case.expected - last_predicted)),
        false_positives=tuple(sorted(last_predicted - case.expected)),
        latency_ms=tuple(latencies),
    )


def summarize(results: Iterable[CaseResult]) -> ReportSummary:
    """Aggregate per-case results into corpus metrics."""
    items = tuple(results)
    n = len(items)
    if n == 0:
        return ReportSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    macro_p = sum(r.precision for r in items) / n
    macro_r = sum(r.recall for r in items) / n
    macro_f = sum(r.f1 for r in items) / n
    tp = sum(r.n_correct for r in items)
    fp = sum(r.n_predicted - r.n_correct for r in items)
    fn = sum(r.n_expected - r.n_correct for r in items)
    micro_p = tp / (tp + fp) if (tp + fp) else 0.0
    micro_r = tp / (tp + fn) if (tp + fn) else 0.0
    micro_f = (
        2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0
    )
    stability = sum(1 for r in items if r.stable) / n
    all_lat = [v for r in items for v in r.latency_ms]
    return ReportSummary(
        n_cases=n,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f,
        micro_precision=micro_p,
        micro_recall=micro_r,
        micro_f1=micro_f,
        stability_rate=stability,
        latency_p50_ms=_percentile(tuple(all_lat), 50.0),
        latency_p99_ms=_percentile(tuple(all_lat), 99.0),
    )


def _percentile(values: tuple[float, ...], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (q / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac
