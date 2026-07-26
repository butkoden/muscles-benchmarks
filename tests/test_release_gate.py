from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_core_keeps_test_tools_out_of_runtime_dependencies():
    document = tomllib.loads((ROOT / "muscles" / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = document["tool"]["poetry"]["dependencies"]
    development = document["tool"]["poetry"]["dev-dependencies"]

    assert "pytest" not in runtime
    assert development["pytest"] == "==7.1.3"


def test_clean_install_gate_is_documented_and_executable():
    script = ROOT.parent / "scripts" / "clean-install-smoke.py"
    assert script.exists()
    assert "PYTHONPATH=" not in script.read_text(encoding="utf-8")


def test_p0_workflows_cover_ci_build_and_trusted_publishing():
    for package in ("muscles-ai", "muscles-documents", "muscles-data", "muscles-benchmarks"):
        ci = (ROOT / package / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        release = (ROOT / package / ".github/workflows/release.yml").read_text(encoding="utf-8")
        assert "pytest" in ci
        assert "python -m build" in ci
        assert "id-token: write" in release
        assert "gh-action-pypi-publish" in release


def test_every_rc_package_has_pr_ci_and_guarded_release_workflow():
    packages = (
        "muscles",
        "muscles-asgi",
        "muscles-wsgi",
        "muscles-cli",
        "muscles-jsonrpc",
        "muscles-sse",
        "muscles-mcp",
        "muscles-sql",
        "muscles-otel",
        "muscles-ai",
        "muscles-documents",
        "muscles-data",
        "muscles-data-elasticsearch",
        "muscles-data-opensearch",
        "muscles-data-qdrant",
        "muscles-data-redis",
        "muscles-data-mongodb",
        "muscles-data-s3",
        "muscles-data-sqlalchemy",
        "muscles-benchmarks",
    )

    for package in packages:
        ci = (ROOT / package / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        release = (ROOT / package / ".github/workflows/release.yml").read_text(encoding="utf-8")
        assert "pull_request" in ci
        assert "python -m pytest" in ci
        assert "python -m build" in ci
        assert "if: github.event_name == 'release' && github.event.action == 'published'" in release
        assert "id-token: write" in release
        assert "gh-action-pypi-publish" in release


def test_support_example_declares_explicit_setuptools_discovery():
    text = (ROOT / "muscular-example" / "pyproject.toml").read_text(encoding="utf-8")
    assert "setuptools.build_meta" in text
    assert "py-modules = []" in text


def test_cli_keeps_namespace_package_layout_for_clean_wheels():
    text = (ROOT / "muscles-cli" / "pyproject.toml").read_text(encoding="utf-8")

    assert 'packages = [{include = "muscles", from = "src"}]' in text
    assert 'to = "muscles.cli"' not in text
