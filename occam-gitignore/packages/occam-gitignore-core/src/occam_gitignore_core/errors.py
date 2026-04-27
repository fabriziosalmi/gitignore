"""Typed exception hierarchy. No bare excepts allowed downstream."""

from __future__ import annotations


class OccamGitignoreError(Exception):
    """Base class for all errors raised by occam-gitignore."""


class FingerprintError(OccamGitignoreError):
    """Raised when fingerprinting fails on malformed input."""


class TemplateNotFoundError(OccamGitignoreError):
    """Raised when a requested template is missing from the repository."""


class RulesTableError(OccamGitignoreError):
    """Raised when the rules table payload is malformed."""


class DeterminismError(OccamGitignoreError):
    """Raised when a determinism invariant is violated at runtime."""
