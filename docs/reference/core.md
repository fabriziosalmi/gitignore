# Core API

The `occam_gitignore_core` package is the only mandatory dependency for
adapters. It exports:

```python
from occam_gitignore_core import (
    # generation
    generate, GenerateOptions, GitignoreOutput,
    # fingerprinting
    DefaultFingerprinter, Detector, Feature, FingerprintResult,
    # rules
    Rule, RuleSource,
    # ports
    TemplateRepository, RulesTable,
    # adapters
    FileSystemTemplateRepository, InMemoryTemplateRepository,
    JsonRulesTable, InMemoryRulesTable,
    # errors
    TemplateNotFoundError,
)
```

## `generate`

```python
def generate(
    fingerprint: FingerprintResult,
    options: GenerateOptions,
    *,
    templates: TemplateRepository,
    rules_table: RulesTable,
) -> GitignoreOutput:
    ...
```

The single entry point. Pure: same arguments ⇒ byte-identical output.

## `GenerateOptions`

```python
@dataclass(frozen=True, slots=True)
class GenerateOptions:
    include_comments: bool = True
    include_provenance: bool = False
    extras: tuple[str, ...] = ()
```

User-facing knobs. All boolean defaults are conservative. `extras` are
emitted in their original order, sorted last.

## `GitignoreOutput`

```python
@dataclass(frozen=True, slots=True)
class GitignoreOutput:
    content: str
    rules: tuple[Rule, ...]
    output_hash: str            # "sha256:<hex>"
    rules_table_version: str
    core_version: str
```

`output_hash == "sha256:" + sha256(content.encode("utf-8")).hexdigest()`.
This identity is asserted by `test_determinism` and `test_snapshots`.

## Example

```python
from pathlib import Path
from occam_gitignore_core import (
    DefaultFingerprinter, FileSystemTemplateRepository, GenerateOptions,
    JsonRulesTable, generate,
)

fp = DefaultFingerprinter().fingerprint(("pyproject.toml", "Dockerfile"))
templates = FileSystemTemplateRepository(Path("data/templates"), version="snap")
rules = JsonRulesTable.from_file(Path("data/rules_table.json"))

out = generate(fp, GenerateOptions(include_comments=True), templates=templates, rules_table=rules)

print(out.output_hash)
print(out.content)
```
