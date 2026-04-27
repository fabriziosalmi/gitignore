---
layout: home

hero:
  name: occam-gitignore
  text: Deterministic .gitignore generation
  tagline: Same input ⇒ byte-identical output. Pure core. Hash-verifiable. p99 < 200 µs.
  actions:
    - theme: brand
      text: Get started
      link: /guide/getting-started
    - theme: alt
      text: Architecture
      link: /guide/architecture
    - theme: alt
      text: View on GitHub
      link: https://github.com/fabriziosalmi/gitignore

features:
  - icon: 🧮
    title: Deterministic by contract
    details: Every output carries a sha256 hash, a core version, and a rules-table version. Two runs on the same tree are byte-identical — and tests enforce it.
  - icon: 🧱
    title: Hexagonal architecture
    details: The core is a pure function of (fingerprint, options, templates, rules). All I/O is in adapters — CLI, HTTP, MCP — that share the same generator.
  - icon: 🔍
    title: Explainable output
    details: Each rule carries provenance (template, mined, or user). Mined rules come from a transparent, lift-based association pipeline — no black box.
  - icon: ⚡
    title: Microsecond latency
    details: No filesystem walks, no LLMs at runtime. The benchmark corpus measures p50 ≈ 50 µs and p99 ≈ 120 µs end-to-end.
  - icon: 📐
    title: Honest measurement
    details: The benchmark exposes recall, precision, F1, stability, and latency p50/p99 — and CI fails if any threshold regresses.
  - icon: 🔌
    title: Multi-surface
    details: One core, four adapters — CLI, FastAPI HTTP, MCP server, training/bench harnesses. Add one without touching the others.
---
