# CLI flags

See also [Guide → CLI](../guide/cli) for tutorial-style usage.

## `occam-gitignore generate`

```
Usage: occam-gitignore generate [OPTIONS] PATH

  Generate a deterministic .gitignore for the project at PATH.

Options:
  --templates DIR        Templates directory  [default: data/templates]
  --rules-table FILE     Rules table JSON     [default: data/rules_table.json]
  --no-comments          Suppress header and section comments
  --provenance           Append # <feature> to each rule
  --extra TEXT           User pattern (repeatable)
  --stdout               Print to stdout instead of writing a file
  --help                 Show this message and exit
```

## `occam-gitignore inspect`

```
Usage: occam-gitignore inspect [OPTIONS] PATH

  Print the FingerprintResult for the tree at PATH (no file is written).
```

## `occam-gitignore version`

```
Usage: occam-gitignore version

  Print core_version and rules_table_version.
```

## `occam-gitignore-bench run`

See [Benchmark methodology](../guide/benchmark) for full options.

```
Usage: occam-gitignore-bench run [OPTIONS] CORPUS_DIR

Options:
  --templates DIR        Templates directory
  --rules-table FILE     Rules table JSON
  --repeats INT          Repeat each case to measure stability + latency [default: 1]
  --diff                 Print false negatives / false positives per case
  --min-recall FLOAT     Fail with code 2 if macro recall is below this
  --min-f1 FLOAT         Fail with code 3 if macro F1 is below this
  --max-p99-ms FLOAT     Fail with code 4 if p99 latency exceeds this
  --json                 Emit JSON instead of text
```
