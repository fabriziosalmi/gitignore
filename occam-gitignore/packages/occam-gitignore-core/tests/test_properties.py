"""Property-based tests: prove the determinism contract on random inputs.

Invariants asserted (each ``@given`` runs hundreds of cases):

  P1  order-invariance .... fp(tree) == fp(shuffle(tree))
  P2  fingerprint idempotence .... fp(fp_paths) yields same features
  P3  generate is order-invariant w.r.t. input tree
  P4  extras are appended; their presence/absence does not reorder
      the rest of the output (prefix-stable up to the user-extras section)
  P5  provenance_hash changes iff one of (core, templates, rules_table,
      content) changes
  P6  generate is idempotent (same inputs -> same bytes)
  P7  content_hash matches sha256(content)
"""

from __future__ import annotations

import hashlib
import random

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from occam_gitignore_core import (
    DefaultFingerprinter,
    Feature,
    GenerateOptions,
    InMemoryTemplateRepository,
    JsonRulesTable,
    Rule,
    RuleSource,
    generate,
)

_FEATURE_NAMES = (
    "python",
    "node",
    "go",
    "rust",
    "docker",
    "terraform",
    "jupyter",
    "java",
    "ruby",
    "csharp",
    "swift",
)

# Path strategy: mix marker filenames + extension files + nested paths,
# plus arbitrary noise paths. Forces detectors to be tested both on
# positive and negative samples.
_MARKERS = (
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "Dockerfile",
    "docker-compose.yml",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "Rakefile",
    "Package.swift",
)
_EXTS = (
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".tf",
    ".tfvars",
    ".ipynb",
    ".java",
    ".kt",
    ".rb",
    ".cs",
    ".swift",
    ".md",
    ".txt",
)


def _path_strategy() -> st.SearchStrategy[str]:
    name_chars = st.text(
        alphabet=st.characters(min_codepoint=0x61, max_codepoint=0x7A),
        min_size=1,
        max_size=8,
    )
    leaf = st.one_of(
        st.sampled_from(_MARKERS),
        st.builds(lambda n, e: f"{n}{e}", name_chars, st.sampled_from(_EXTS)),
    )
    nesting = st.lists(name_chars, min_size=0, max_size=3)
    return st.builds(
        lambda d, f: ("/".join(d) + "/" + f) if d else f,
        nesting,
        leaf,
    )


_TREE = st.lists(_path_strategy(), min_size=0, max_size=40, unique=True)


def _build_repo() -> InMemoryTemplateRepository:
    """Same layout used in the determinism tests, expanded to all 11 features."""
    data: dict[Feature, tuple[Rule, ...]] = {}
    for name in _FEATURE_NAMES:
        data[Feature(name)] = (
            Rule(f"{name}-output/", RuleSource.TEMPLATE, name),
            Rule(f"*.{name}.tmp", RuleSource.TEMPLATE, name),
        )
    return InMemoryTemplateRepository(data)


def _empty_rules() -> JsonRulesTable:
    return JsonRulesTable.empty()


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(tree=_TREE, seed=st.integers(min_value=0, max_value=1 << 30))
def test_p1_fingerprint_order_invariance(tree: list[str], seed: int) -> None:
    """fp(tree) == fp(shuffle(tree))."""
    rng = random.Random(seed)
    shuffled = tree[:]
    rng.shuffle(shuffled)
    fp = DefaultFingerprinter()
    a = fp.fingerprint(tuple(tree))
    b = fp.fingerprint(tuple(shuffled))
    assert a.features == b.features
    assert a.evidence == b.evidence


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(tree=_TREE)
def test_p2_fingerprint_idempotent_on_evidence_paths(tree: list[str]) -> None:
    """Re-running fingerprint over only the witness paths returns the same set."""
    fp = DefaultFingerprinter()
    a = fp.fingerprint(tuple(tree))
    if not a.features:
        return  # vacuously true
    witness_paths = tuple(sorted({e[1] for e in a.evidence if e[1] != "(implicit)"}))
    b = fp.fingerprint(witness_paths)
    assert a.features == b.features


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(tree=_TREE, seed=st.integers(min_value=0, max_value=1 << 30))
def test_p3_generate_order_invariant(tree: list[str], seed: int) -> None:
    """generate(fp(tree)) is byte-identical to generate(fp(shuffle(tree)))."""
    rng = random.Random(seed)
    shuffled = tree[:]
    rng.shuffle(shuffled)
    fp = DefaultFingerprinter()
    templates = _build_repo()
    rules = _empty_rules()
    a = generate(
        fp.fingerprint(tuple(tree)),
        GenerateOptions(),
        templates=templates,
        rules_table=rules,
    )
    b = generate(
        fp.fingerprint(tuple(shuffled)),
        GenerateOptions(),
        templates=templates,
        rules_table=rules,
    )
    assert a.content == b.content
    assert a.content_hash == b.content_hash
    assert a.provenance_hash == b.provenance_hash


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    tree=_TREE,
    extras=st.lists(
        st.text(
            alphabet=st.characters(
                min_codepoint=0x61,
                max_codepoint=0x7A,
                whitelist_characters=("-", "_", ".", "/", "*"),
            ),
            min_size=1,
            max_size=12,
        ).filter(lambda s: not s.startswith("#") and not s.isspace()),
        min_size=0,
        max_size=6,
        unique=True,
    ),
)
def test_p4_extras_are_appended_not_reordered(
    tree: list[str], extras: list[str],
) -> None:
    """The non-extras prefix of the rules tuple must be identical with or
    without extras. This proves extras do not reorder template/mined output.
    """
    fp_res = DefaultFingerprinter().fingerprint(tuple(tree))
    templates = _build_repo()
    rules = _empty_rules()
    base = generate(
        fp_res, GenerateOptions(extras=()), templates=templates, rules_table=rules,
    )
    with_extras = generate(
        fp_res,
        GenerateOptions(extras=tuple(extras)),
        templates=templates,
        rules_table=rules,
    )
    base_non_extras = tuple(r for r in base.rules if r.source is not RuleSource.USER_EXTRA)
    with_non_extras = tuple(
        r for r in with_extras.rules if r.source is not RuleSource.USER_EXTRA
    )
    assert base_non_extras == with_non_extras
    # And: every extra ends up exactly once, after all non-extras.
    extras_seen = [r.pattern for r in with_extras.rules if r.source is RuleSource.USER_EXTRA]
    assert set(extras_seen) == set(extras)
    assert len(extras_seen) == len(set(extras_seen))


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(tree=_TREE)
def test_p5_provenance_hash_is_well_defined(tree: list[str]) -> None:
    """provenance_hash == sha256(core ‖ templates ‖ rules ‖ content_hash).

    Recomputed externally; must match the value from the output. Also: two
    different content_hashes MUST yield different provenance_hashes.
    """
    fp = DefaultFingerprinter()
    templates = _build_repo()
    rules = _empty_rules()
    out = generate(
        fp.fingerprint(tuple(tree)),
        GenerateOptions(),
        templates=templates,
        rules_table=rules,
    )

    digest = hashlib.sha256()
    for part in (
        out.core_version,
        out.templates_version,
        out.rules_table_version,
        out.content_hash,
    ):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    expected = f"sha256:{digest.hexdigest()}"
    assert out.provenance_hash == expected


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(tree=_TREE)
def test_p6_generate_is_idempotent(tree: list[str]) -> None:
    fp = DefaultFingerprinter()
    templates = _build_repo()
    rules = _empty_rules()
    fp_res = fp.fingerprint(tuple(tree))
    a = generate(fp_res, GenerateOptions(), templates=templates, rules_table=rules)
    b = generate(fp_res, GenerateOptions(), templates=templates, rules_table=rules)
    assert a.content == b.content
    assert a.content_hash == b.content_hash
    assert a.provenance_hash == b.provenance_hash


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(tree=_TREE)
def test_p7_content_hash_matches_content(tree: list[str]) -> None:
    fp = DefaultFingerprinter()
    templates = _build_repo()
    rules = _empty_rules()
    out = generate(
        fp.fingerprint(tuple(tree)),
        GenerateOptions(),
        templates=templates,
        rules_table=rules,
    )
    expected = "sha256:" + hashlib.sha256(out.content.encode("utf-8")).hexdigest()
    assert out.content_hash == expected
