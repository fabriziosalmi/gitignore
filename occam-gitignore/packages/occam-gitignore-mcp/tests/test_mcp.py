from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - runtime fixture
from typing import cast

import pytest

from occam_gitignore_mcp import Settings, build_server


@pytest.fixture
def server_setup(tmp_path: Path) -> Settings:
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "python.gitignore").write_text("__pycache__/\n*.pyc\n", "utf-8")
    rules_path = tmp_path / "rules_table.json"
    rules_path.write_text('{"version":"t","rules":[]}', "utf-8")
    return Settings(templates_dir=templates, rules_table_path=rules_path)


@pytest.mark.anyio
async def test_lists_tools_and_resources(server_setup: Settings) -> None:
    server = build_server(server_setup)
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert "occam_gitignore.fingerprint_repo" in names
    assert "occam_gitignore.generate" in names
    assert "occam_gitignore.diff_against" in names
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "occam-gitignore://version" in uris
    assert "occam-gitignore://rules-table" in uris


@pytest.mark.anyio
async def test_fingerprint_tool(server_setup: Settings) -> None:
    server = build_server(server_setup)
    result = await server.call_tool(
        "occam_gitignore.fingerprint_repo",
        {"tree": ["pyproject.toml", "src/main.py"]},
    )
    payload = _structured(result)
    assert "python" in cast("list[str]", payload["features"])


@pytest.mark.anyio
async def test_generate_tool_is_deterministic(server_setup: Settings) -> None:
    server = build_server(server_setup)
    args = {"tree": ["pyproject.toml"], "include_comments": False}
    a = _structured(await server.call_tool("occam_gitignore.generate", args))
    b = _structured(await server.call_tool("occam_gitignore.generate", args))
    assert a["output_hash"] == b["output_hash"]
    assert a["content"] == b["content"]
    assert "__pycache__/" in cast("str", a["content"])


@pytest.mark.anyio
async def test_diff_against_tool(server_setup: Settings) -> None:
    server = build_server(server_setup)
    result = await server.call_tool(
        "occam_gitignore.diff_against",
        {"existing": "*.pyc\nnode_modules/\n", "tree": ["pyproject.toml"]},
    )
    payload = _structured(result)
    assert "__pycache__/" in cast("list[str]", payload["added"])
    assert "node_modules/" in cast("list[str]", payload["removed"])


@pytest.mark.anyio
async def test_version_resource(server_setup: Settings) -> None:
    server = build_server(server_setup)
    contents = await server.read_resource("occam-gitignore://version")
    text = next(iter(contents)).content
    payload = json.loads(text)
    assert payload["rules_table_version"]
    assert payload["templates_version"].startswith("sha256:")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _structured(call_result: object) -> dict[str, object]:
    # FastMCP.call_tool returns (content_blocks, structured_output)
    if isinstance(call_result, tuple) and len(call_result) == 2:
        structured = call_result[1]
        if isinstance(structured, dict):
            return structured
    raise AssertionError(f"unexpected call_tool return: {call_result!r}")
