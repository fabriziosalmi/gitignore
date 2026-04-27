from __future__ import annotations

from occam_gitignore_training import parse_log

_SAMPLE = """\
Ottimo, procediamo in modo metodico. Iniziamo con il primo della lista: patterns.

╭───
│ ✓  Shell Analisi del contenuto del repository 'patterns'.
│ pyproject.toml
│ requirements.txt
│ src
╰───

Ecco la mia proposta:

    1 # Byte-compiled
    2 __pycache__/
    3 *.pyc

Procedo con la creazione?
> si
Fatto! Il file .gitignore è stato aggiunto a patterns.

Passiamo al secondo: gitoma-bench-quality.

    1 node_modules/
    2 dist/

Fatto!
"""


def test_parses_two_repos() -> None:
    entries = list(parse_log(_SAMPLE))
    repos = [e.repo for e in entries]
    assert "patterns" in repos
    assert "gitoma-bench-quality" in repos


def test_proposed_rules_are_extracted() -> None:
    entries = {e.repo: e for e in parse_log(_SAMPLE)}
    assert "__pycache__/" in entries["patterns"].proposed_rules
    assert "node_modules/" in entries["gitoma-bench-quality"].proposed_rules


def test_acceptance_detected() -> None:
    entries = {e.repo: e for e in parse_log(_SAMPLE)}
    assert entries["patterns"].accepted is True
