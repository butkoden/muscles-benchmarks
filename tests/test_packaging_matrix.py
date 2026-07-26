from __future__ import annotations

import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PROJECTS_ROOT = Path(os.environ.get("MUSCLES_ECOSYSTEM_ROOT", ROOT))
CORE_RANGE = ">=1.0.0rc1,<2.0.0"

pytestmark = pytest.mark.skipif(
    not (PROJECTS_ROOT / "muscles").exists(),
    reason="packaging matrix requires the monorepo workspace",
)


def _project_text(name: str) -> str:
    return (PROJECTS_ROOT / name / "pyproject.toml").read_text(encoding="utf-8")


def test_rc_packages_use_published_core_range_without_git_dependencies():
    for name in (
        "muscles-ai",
        "muscles-asgi",
        "muscles-cli",
        "muscles-data",
        "muscles-documents",
        "muscles-jsonrpc",
        "muscles-mcp",
        "muscles-otel",
        "muscles-sql",
        "muscles-sse",
        "muscles-wsgi",
    ):
        text = _project_text(name)
        assert f"muscles{CORE_RANGE}" in text or f'muscles = "{CORE_RANGE}"' in text
        assert "git+https://" not in text


def test_data_adapters_use_bounded_data_core_dependency():
    for name in (
        "muscles-data-elasticsearch",
        "muscles-data-opensearch",
        "muscles-data-qdrant",
        "muscles-data-redis",
        "muscles-data-mongodb",
        "muscles-data-s3",
        "muscles-data-sqlalchemy",
    ):
        text = _project_text(name)
        assert "muscles-data>=0.1.0,<1.0.0" in text
        assert "git+https://" not in text


def test_benchmark_package_declares_core_dependency():
    text = _project_text("muscles-benchmarks")
    assert f"muscles{CORE_RANGE}" in text
