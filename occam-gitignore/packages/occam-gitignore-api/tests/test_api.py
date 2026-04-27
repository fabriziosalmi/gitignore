from __future__ import annotations

from pathlib import Path  # noqa: TC003 - runtime fixtures

import pytest
from fastapi.testclient import TestClient

from occam_gitignore_api import Settings, build_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "python.gitignore").write_text("__pycache__/\n*.pyc\n", "utf-8")
    rules_path = tmp_path / "rules_table.json"
    rules_path.write_text('{"version":"t","rules":[]}', "utf-8")
    settings = Settings(
        templates_dir=templates,
        rules_table_path=rules_path,
    )
    return TestClient(build_app(settings))


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_version(client: TestClient) -> None:
    body = client.get("/v1/occam-gitignore/version").json()
    assert body["core_version"]
    assert body["rules_table_version"]
    assert body["templates_version"].startswith("sha256:")


def test_fingerprint(client: TestClient) -> None:
    resp = client.post(
        "/v1/occam-gitignore/fingerprint",
        json={"tree": ["pyproject.toml", "src/main.py"]},
    )
    assert resp.status_code == 200
    assert "python" in resp.json()["features"]


def test_generate_from_tree_returns_hash_header(client: TestClient) -> None:
    resp = client.post(
        "/v1/occam-gitignore/generate",
        json={"tree": ["pyproject.toml"], "include_comments": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["output_hash"].startswith("sha256:")
    assert "__pycache__/" in body["content"]
    assert resp.headers["X-Occam-Gitignore-Hash"] == body["output_hash"]


def test_generate_is_deterministic(client: TestClient) -> None:
    payload = {"tree": ["pyproject.toml"], "include_comments": False}
    a = client.post("/v1/occam-gitignore/generate", json=payload).json()
    b = client.post("/v1/occam-gitignore/generate", json=payload).json()
    assert a["output_hash"] == b["output_hash"]
    assert a["content"] == b["content"]


def test_generate_requires_features_or_tree(client: TestClient) -> None:
    resp = client.post("/v1/occam-gitignore/generate", json={})
    assert resp.status_code == 400


def test_generate_rejects_oversized_tree(tmp_path: Path) -> None:
    templates = tmp_path / "templates"
    templates.mkdir()
    rules_path = tmp_path / "rules_table.json"
    rules_path.write_text('{"version":"t","rules":[]}', "utf-8")
    settings = Settings(
        templates_dir=templates,
        rules_table_path=rules_path,
        max_tree_size=2,
    )
    c = TestClient(build_app(settings))
    resp = c.post(
        "/v1/occam-gitignore/generate",
        json={"tree": ["a", "b", "c"]},
    )
    assert resp.status_code == 413
