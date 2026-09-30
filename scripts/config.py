"""Configuration loader and validator.

Reads the monitoring configuration from a YAML file, validates every field
and returns a typed `MonitoringConfig` instance. All validation errors are
raised as `ConfigError` with a clear, human-readable message.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.models import Host, HostRole, MonitoringConfig, OutputFormat

_REQUIRED_TOP_LEVEL = ("monitoring", "hosts", "output")
_SUPPORTED_FORMATS = {fmt.value for fmt in OutputFormat}


class ConfigError(ValueError):
    """Raised when the configuration file is missing or invalid."""


def load_config(path: str | Path) -> MonitoringConfig:
    """Load and validate the monitoring configuration from `path`."""
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Top-level configuration must be a mapping")

    _require_keys(raw, _REQUIRED_TOP_LEVEL, context="top level")

    monitoring = _as_mapping(raw["monitoring"], "monitoring")
    output = _as_mapping(raw["output"], "output")

    interval = _positive_int(monitoring, "interval_seconds", "monitoring")
    iterations = _positive_int(monitoring, "iterations", "monitoring")
    timeout = _positive_int(monitoring, "timeout_seconds", "monitoring")

    hosts = _parse_hosts(raw["hosts"])
    reports_dir = _non_empty_str(output, "reports_dir", "output")
    formats = _parse_formats(output.get("formats"))

    return MonitoringConfig(
        interval_seconds=interval,
        iterations=iterations,
        timeout_seconds=timeout,
        hosts=hosts,
        reports_dir=reports_dir,
        formats=formats,
    )


def _require_keys(mapping: dict[str, Any], keys: tuple[str, ...], *, context: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(f"Missing required key(s) in {context}: {joined}")


def _as_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"'{context}' must be a mapping")
    return value


def _positive_int(mapping: dict[str, Any], key: str, context: str) -> int:
    if key not in mapping:
        raise ConfigError(f"Missing '{key}' in '{context}'")
    value = mapping[key]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"'{context}.{key}' must be a positive integer")
    return value


def _non_empty_str(mapping: dict[str, Any], key: str, context: str) -> str:
    if key not in mapping:
        raise ConfigError(f"Missing '{key}' in '{context}'")
    value = mapping[key]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{context}.{key}' must be a non-empty string")
    return value


def _parse_hosts(raw_hosts: Any) -> tuple[Host, ...]:
    if not isinstance(raw_hosts, list) or not raw_hosts:
        raise ConfigError("'hosts' must be a non-empty list")

    parsed: list[Host] = []
    seen_names: set[str] = set()

    for index, entry in enumerate(raw_hosts):
        ctx = f"hosts[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"'{ctx}' must be a mapping")

        _require_keys(entry, ("name", "address", "role"), context=ctx)

        name = _non_empty_str(entry, "name", ctx)
        address = _non_empty_str(entry, "address", ctx)

        if name in seen_names:
            raise ConfigError(f"Duplicate host name: '{name}'")
        seen_names.add(name)

        role_raw = entry["role"]
        try:
            role = HostRole(role_raw)
        except ValueError as exc:
            allowed = ", ".join(r.value for r in HostRole)
            raise ConfigError(
                f"'{ctx}.role' must be one of [{allowed}], got '{role_raw}'"
            ) from exc

        parsed.append(Host(name=name, address=address, role=role))

    return tuple(parsed)


def _parse_formats(raw_formats: Any) -> tuple[OutputFormat, ...]:
    if not isinstance(raw_formats, list) or not raw_formats:
        raise ConfigError("'output.formats' must be a non-empty list")

    parsed: list[OutputFormat] = []
    for entry in raw_formats:
        if not isinstance(entry, str) or entry not in _SUPPORTED_FORMATS:
            allowed = ", ".join(sorted(_SUPPORTED_FORMATS))
            raise ConfigError(f"Unsupported output format: '{entry}'. Allowed: {allowed}")
        fmt = OutputFormat(entry)
        if fmt not in parsed:
            parsed.append(fmt)

    return tuple(parsed)
