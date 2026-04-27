# Schema

All value types are frozen dataclasses with `__slots__`. Equality is
structural, hashing is identity-free.

## `Feature`

```python
class Feature(str):
    """A feature name (e.g. 'python', 'node')."""
    name: str  # alias for str(self)
```

## `Rule`

```python
@dataclass(frozen=True, slots=True)
class Rule:
    pattern: str
    source: RuleSource
    feature: str | None = None
```

## `RuleSource`

```python
class RuleSource(StrEnum):
    TEMPLATE   = "template"
    MINED      = "mined"
    USER_EXTRA = "user_extra"
```

Section order in rendered output is `TEMPLATE → MINED → USER_EXTRA`. This
order is also used by stable dedupe (first occurrence wins, sorted by
source then pattern).

## `FingerprintResult`

```python
@dataclass(frozen=True, slots=True)
class FingerprintResult:
    features: tuple[Feature, ...]              # sorted, deduplicated
    evidence: tuple[tuple[str, str], ...]      # sorted (feature, witness_path)
```

## `GenerateOptions`

```python
@dataclass(frozen=True, slots=True)
class GenerateOptions:
    include_comments: bool = True
    include_provenance: bool = False
    extras: tuple[str, ...] = ()
```

## `GitignoreOutput`

See [Core API → `GitignoreOutput`](./core#gitignoreoutput).
