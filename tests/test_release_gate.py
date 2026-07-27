from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PROJECTS_ROOT = Path(os.environ.get("MUSCLES_ECOSYSTEM_ROOT", ROOT))


def _clean_install_script() -> Path | None:
    for candidate in (
        PROJECTS_ROOT / "scripts" / "clean-install-smoke.py",
        PROJECTS_ROOT.parent / "scripts" / "clean-install-smoke.py",
    ):
        if candidate.exists():
            return candidate
    return None


def _ecosystem_test_script() -> Path | None:
    for candidate in (
        PROJECTS_ROOT / "scripts" / "ecosystem-test.sh",
        PROJECTS_ROOT.parent / "scripts" / "ecosystem-test.sh",
    ):
        if candidate.exists():
            return candidate
    return None


def _typecheck_script() -> Path | None:
    for candidate in (
        PROJECTS_ROOT / "scripts" / "typecheck.sh",
        PROJECTS_ROOT.parent / "scripts" / "typecheck.sh",
    ):
        if candidate.exists():
            return candidate
    return None


def _root_makefile() -> Path:
    return PROJECTS_ROOT.parent / "Makefile"

pytestmark = pytest.mark.skipif(
    not (PROJECTS_ROOT / "muscles").exists(),
    reason="release gate requires the monorepo workspace",
)


def test_core_keeps_test_tools_out_of_runtime_dependencies():
    document = tomllib.loads((ROOT / "muscles" / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = document["tool"]["poetry"]["dependencies"]
    development = document["tool"]["poetry"]["dev-dependencies"]

    assert "pytest" not in runtime
    assert development["pytest"] == "==7.1.3"


def test_clean_install_gate_is_documented_and_executable():
    script = _clean_install_script()
    if script is None:
        pytest.skip("clean-install gate is provided by the parent workspace")
    assert script.exists()
    assert "PYTHONPATH=" not in script.read_text(encoding="utf-8")


def test_ecosystem_gate_runs_benchmark_suite():
    script = _ecosystem_test_script()
    if script is None:
        pytest.skip("ecosystem gate is provided by the parent workspace")
    assert 'run_package "muscles-benchmarks"' in script.read_text(encoding="utf-8")


def test_common_typecheck_gate_covers_benchmark_source():
    script = _typecheck_script()
    if script is None:
        pytest.fail("common typecheck gate must be provided by the workspace")
    text = script.read_text(encoding="utf-8")
    assert "muscles-benchmarks/src" in text
    assert "pyright" in text
    assert (PROJECTS_ROOT / "muscles-benchmarks" / "pyrightconfig.json").exists()


def test_quality_target_runs_tests_and_typecheck():
    text = _root_makefile().read_text(encoding="utf-8")
    assert "quality-check: ecosystem-test typecheck" in text
    assert "typecheck:" in text


def test_p0_workflows_cover_ci_build_and_trusted_publishing():
    for package in ("muscles-ai", "muscles-documents", "muscles-data", "muscles-benchmarks"):
        ci = (PROJECTS_ROOT / package / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        release = (PROJECTS_ROOT / package / ".github/workflows/release.yml").read_text(encoding="utf-8")
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


def test_data_adapter_rc_assets_are_present():
    examples = {
        "muscles-data-elasticsearch": "example_data_elasticsearch_1",
        "muscles-data-opensearch": "example_data_opensearch_1",
        "muscles-data-qdrant": "example_data_qdrant_1",
        "muscles-data-redis": "example_data_redis_1",
        "muscles-data-mongodb": "example_data_mongodb_1",
        "muscles-data-s3": "example_data_s3_1",
        "muscles-data-sqlalchemy": "example_data_sqlalchemy_1",
    }

    for package, example in examples.items():
        package_root = PROJECTS_ROOT / package
        document = tomllib.loads((package_root / "pyproject.toml").read_text(encoding="utf-8"))
        dependencies = document["project"]["dependencies"]
        assert any(dependency.startswith("muscles-data>=0.1.0,<1.0.0") for dependency in dependencies)
        assert (package_root / "docs/release-candidate.md").exists()
        assert (package_root / "CHANGELOG.md").exists()
        ci = (package_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert 'python -m pip install --pre "muscles>=1.0.0rc1,<2.0.0" "muscles-data>=0.1.0,<1.0.0"' in ci
        assert "repository: butkoden/muscles-data" not in ci
        release = (package_root / ".github/workflows/release.yml").read_text(encoding="utf-8")
        assert 'python -m pip install --pre "muscles-data>=0.1.0,<1.0.0"' in release
        assert "repository: butkoden/muscles-data" not in release
        assert "workflow_dispatch" not in release
        example_root = PROJECTS_ROOT / "muscular-example" / example
        assert (example_root / "data_ports.py").exists()
        readme = (package_root / "README.md").read_text(encoding="utf-8")
        assert example in readme


def test_protocol_and_runtime_workflows_use_versioned_core_artifacts():
    packages = (
        "muscles-asgi",
        "muscles-wsgi",
        "muscles-cli",
        "muscles-sql",
        "muscles-jsonrpc",
        "muscles-sse",
        "muscles-mcp",
        "muscles-otel",
    )

    for package in packages:
        for workflow_name in ("ci.yml", "release.yml"):
            workflow = (ROOT / package / ".github/workflows" / workflow_name).read_text(encoding="utf-8")
            assert "feature/task-57" not in workflow
            assert "--pre \"muscles>=1.0.0rc1,<2.0.0\"" in workflow
            assert "../muscles" not in workflow


def test_support_example_declares_explicit_setuptools_discovery():
    text = (PROJECTS_ROOT / "muscular-example" / "pyproject.toml").read_text(encoding="utf-8")
    assert "setuptools.build_meta" in text
    assert "py-modules = []" in text


def test_cli_keeps_namespace_package_layout_for_clean_wheels():
    text = (PROJECTS_ROOT / "muscles-cli" / "pyproject.toml").read_text(encoding="utf-8")

    assert 'packages = [{include = "muscles", from = "src"}]' in text
    assert 'to = "muscles.cli"' not in text
