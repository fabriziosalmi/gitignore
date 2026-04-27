# occam-gitignore Conformance Suite v1

This directory is the **canonical conformance test bed** for any
implementation of the `occam-gitignore` algorithm.

It is intentionally **language-agnostic**: the cases are pure JSON +
text and the inputs (templates, rules table) are pinned by content hash.
The Python reference implementation in this repository is one consumer;
others (Rust, Go, JS/WASM) MUST pass byte-for-byte.

## Layout

```
conformance/
  README.md              this file
  SPEC.md                the v1 algorithm specification (informative)
  fixtures/
    templates/           pinned template tree (content-addressed)
    rules_table.json     pinned mined rules table
    fixtures_hash.json   sha256 of fixtures (declared expectation)
  cases/
    NNN-<label>/
      tree.json          input: list of POSIX paths
      options.json       input: GenerateOptions (extras, include_*)
      expected.gitignore byte-exact expected output
      expected_hashes.json    {content_hash, provenance_hash, ...}
  generate_cases.py      regenerator (must be deterministic)
  run_conformance.py     validator (Python reference)
```

## Running (Python reference)

```sh
uv run python conformance/run_conformance.py
```

Exit code 0 means all cases pass byte-for-byte and every declared hash
verifies. Any drift fails loudly.

## Running (other implementations)

For each case directory:

1. Load `fixtures/templates/` and `fixtures/rules_table.json`.
2. Build the fingerprint from `cases/<id>/tree.json`.
3. Generate with options from `cases/<id>/options.json`.
4. Assert: `output.content == cases/<id>/expected.gitignore` byte-for-byte.
5. Assert: every key in `expected_hashes.json` matches.

## Promise

A v1.x conformance case **never changes meaning**. If a case must change,
its directory name MUST change (e.g. `042-python-minimal-v2`). This is
the same SemVer guarantee the reference implementation makes for
`provenance_hash`.

## Adding cases

Edit `generate_cases.py` and re-run. A case set is committed iff:

- it adds coverage (a feature or feature combination not previously
  exercised), OR
- it locks a regression discovered in the wild.

Trivial cases are not added. The suite is small on purpose; coverage
comes from the cartesian product, not from quantity.
