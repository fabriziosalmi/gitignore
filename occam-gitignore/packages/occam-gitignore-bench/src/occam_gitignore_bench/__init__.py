"""occam-gitignore-bench: reproducible benchmarks.

A "benchmark case" is a fixture: a tree of file paths + a ground-truth set
of patterns that should be produced. The bench runs the deterministic
pipeline on each case and reports precision/recall/F1, plus stability
(byte-identical output across N runs) and latency (p50/p99).
"""

from .cases import BenchCase, load_cases
from .metrics import CaseResult, ReportSummary, evaluate, summarize

__all__ = [
    "BenchCase",
    "CaseResult",
    "ReportSummary",
    "evaluate",
    "load_cases",
    "summarize",
]
