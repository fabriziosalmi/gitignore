"""Parse conversational Gemini-CLI logs into structured records.

Robust enough for the v0 corpus. Side-effect free (returns values; caller writes I/O).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["StructuredEntry", "parse_log"]


@dataclass(frozen=True, slots=True)
class StructuredEntry:
    """One repo's slice of the conversation."""

    repo: str
    had_gitignore: bool
    files_listed: tuple[str, ...]
    proposed_rules: tuple[str, ...]
    accepted: bool
    features: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        return asdict(self)


# Repo headers seen across both corpora (Italian Gemini-CLI sessions):
#   "Iniziamo con il primo della lista: <repo>."
#   "Passiamo al [secondo|prossimo]: <repo>."
#   "Procediamo con <repo>."
#   "Il prossimo repository da [verificare|analizzare] è <repo>."
#   "NEXT_REPO: <repo>"  (machine-readable marker)
#   Shell box: "repository '<repo>'"  (most reliable; appears once per repo)
_REPO_HEADER = re.compile(
    r"(?:"
    r"NEXT_REPO:\s*"
    r"|repository\s+['\"`]"
    r"|Iniziamo con [^:]+:\s*"
    r"|Passiamo al [^:]+:\s*"
    r"|Procediamo con\s+"
    r"|prossimo repository da \w+ \xe8\s+"
    r")([A-Za-z0-9][A-Za-z0-9._\-]*)['\"`]?\.?",
)

# Numbered .gitignore lines as rendered by the CLI:
#     "    1 # Byte-compiled..."
#     "   42 *.log"
_NUMBERED_RULE = re.compile(r"^\s*\d+\s+(.+?)\s*$")

_ACCEPT_MARKERS = (
    "Fatto!",
    "Fatto.",
    "Creo il file",
    "Creazione del file",
    "Aggiornamento del file",
    "è stato aggiunto",
    "creato con successo",
    "aggiornato con successo",
    "via API GitHub",
)
_FILE_BOX_LINE = re.compile(r"^[│|]\s*([^\s│|][^\n]*?)\s*[│|]?\s*$")


def parse_log(text: str) -> Iterator[StructuredEntry]:
    """Yield one `StructuredEntry` per repo found in `text`.

    The parser is intentionally tolerant: missing fields become empty/False.
    """
    segments = _split_by_repo(text)
    for repo, body in segments:
        yield _parse_segment(repo, body)


def _split_by_repo(text: str) -> list[tuple[str, str]]:
    """Split log into (repo, body) pairs.

    The same repo name often appears in multiple consecutive markers
    (analysis box + update box). Consecutive segments with the same repo
    are merged so that all evidence for that repo lives in one body.
    """
    matches = list(_REPO_HEADER.finditer(text))
    if not matches:
        return []
    raw: list[tuple[str, int, int]] = []
    for i, match in enumerate(matches):
        repo = match.group(1).rstrip(".")
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw.append((repo, start, end))
    merged: list[tuple[str, str]] = []
    for repo, start, end in raw:
        if merged and merged[-1][0] == repo:
            prev_repo, prev_body = merged[-1]
            merged[-1] = (prev_repo, prev_body + text[start:end])
        else:
            merged.append((repo, text[start:end]))
    return merged


def _parse_segment(repo: str, body: str) -> StructuredEntry:
    proposed: list[str] = []
    files: list[str] = []
    in_box = False
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if line.startswith(("╭", "┌")):
            in_box = True
            continue
        if line.startswith(("╰", "└")):
            in_box = False
            continue
        rule_match = _NUMBERED_RULE.match(line)
        if rule_match:
            candidate = rule_match.group(1).strip()
            if candidate and not candidate.startswith("#"):
                proposed.append(candidate)
            continue
        if in_box:
            box_match = _FILE_BOX_LINE.match(line)
            if box_match:
                token = box_match.group(1).strip()
                if (
                    token
                    and " " not in token
                    and not token.startswith(("✓", "Shell"))
                ):
                    files.append(token)

    accepted = any(marker in body for marker in _ACCEPT_MARKERS)
    return StructuredEntry(
        repo=repo,
        had_gitignore=False,  # set by caller based on which log file is parsed
        files_listed=tuple(dict.fromkeys(files)),
        proposed_rules=tuple(dict.fromkeys(proposed)),
        accepted=accepted,
    )
