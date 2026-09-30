"""Tests for the configuration loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.config import ConfigError, load_config
from scripts.models import HostRole, OutputFormat

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_valid_config() -> None:
    config = load_config(FIXTURES / "valid_config.yaml")

    assert config.interval_seconds == 1
    assert config.iterations == 2
    assert config.timeout_seconds == 1
    assert len(config.hosts) == 2
    assert config.hosts[0].name == "host-a"
    assert config.hosts[0].role is HostRole.LOCAL
    assert config.hosts[1].role is HostRole.CONTAINER
    assert config.reports_dir == "reports"
    assert config.formats == (OutputFormat.JSON, OutputFormat.LOG)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "does-not-exist.yaml")


def test_missing_monitoring_section_raises() -> None:
    with pytest.raises(ConfigError, match="Missing required key"):
        load_config(FIXTURES / "invalid_missing_monitoring.yaml")


def test_invalid_role_raises() -> None:
    with pytest.raises(ConfigError, match="role"):
        load_config(FIXTURES / "invalid_role.yaml")


def test_invalid_format_raises() -> None:
    with pytest.raises(ConfigError, match="Unsupported output format"):
        load_config(FIXTURES / "invalid_format.yaml")


def test_duplicate_host_name_raises() -> None:
    with pytest.raises(ConfigError, match="Duplicate host name"):
        load_config(FIXTURES / "invalid_duplicate_host.yaml")


def test_non_mapping_yaml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "scalar.yaml"
    bad.write_text("just-a-string", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(bad)


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "broken.yaml"
    bad.write_text("monitoring: [unbalanced", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(bad)


def test_zero_interval_raises(tmp_path: Path) -> None:
    bad = tmp_path / "zero.yaml"
    bad.write_text(
        "monitoring:\n"
        "  interval_seconds: 0\n"
        "  iterations: 1\n"
        "  timeout_seconds: 1\n"
        "hosts:\n"
        "  - name: h\n"
        "    address: 127.0.0.1\n"
        "    role: local\n"
        "output:\n"
        "  reports_dir: reports\n"
        "  formats: [json]\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="positive integer"):
        load_config(bad)
