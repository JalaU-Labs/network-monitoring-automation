"""Tests for the CLI orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts import network_monitor
from scripts.models import (
    Host,
    HostRole,
    MonitoringConfig,
    OutputFormat,
    ProbeResult,
)


@pytest.fixture
def config(tmp_path: Path) -> MonitoringConfig:
    return MonitoringConfig(
        interval_seconds=1,
        iterations=2,
        timeout_seconds=1,
        hosts=(
            Host("alpha", "172.28.0.10", HostRole.CONTAINER),
            Host("beta", "172.28.0.11", HostRole.CONTAINER),
        ),
        reports_dir=str(tmp_path / "reports"),
        formats=(OutputFormat.JSON, OutputFormat.LOG),
    )


def _fake_probe(success: bool = True):
    def _probe(host: Host, iteration: int, timeout_seconds: int) -> ProbeResult:
        from datetime import UTC, datetime

        return ProbeResult(
            host_name=host.name,
            host_address=host.address,
            iteration=iteration,
            success=success,
            rtt_ms=0.5 if success else None,
            timestamp=datetime.now(UTC),
            error=None if success else "synthetic failure",
        )

    return _probe


# ---------------------------------------------------------------------------
# run_session
# ---------------------------------------------------------------------------


def test_run_session_collects_all_probes(
    mocker,
    config: MonitoringConfig,
) -> None:
    mocker.patch("scripts.network_monitor.probe_host", side_effect=_fake_probe(True))
    sleeper = mocker.Mock()

    results, statistics, started_at, finished_at, paths = network_monitor.run_session(
        config, sleeper=sleeper
    )

    assert len(results) == 4  # 2 hosts x 2 iterations
    assert len(statistics) == 2
    assert finished_at >= started_at
    assert all(s.successful_probes == 2 for s in statistics)
    assert all(s.availability_pct == 100.0 for s in statistics)
    assert sleeper.call_count == 1  # only between iterations
    assert OutputFormat.JSON in paths
    assert OutputFormat.LOG in paths
    for path in paths.values():
        assert path.exists()


def test_run_session_registers_failures(
    mocker,
    config: MonitoringConfig,
) -> None:
    mocker.patch("scripts.network_monitor.probe_host", side_effect=_fake_probe(False))
    sleeper = mocker.Mock()

    results, statistics, *_ = network_monitor.run_session(config, sleeper=sleeper)

    assert all(not r.success for r in results)
    assert all(s.availability_pct == 0.0 for s in statistics)
    assert all(s.failed_probes == 2 for s in statistics)


def test_run_session_uses_run_id_in_filenames(
    mocker,
    config: MonitoringConfig,
) -> None:
    mocker.patch("scripts.network_monitor.probe_host", side_effect=_fake_probe(True))

    _, _, _, _, paths = network_monitor.run_session(
        config, run_id="custom-id", sleeper=lambda _: None
    )

    assert paths[OutputFormat.JSON].name == "monitoring-custom-id.json"
    assert paths[OutputFormat.LOG].name == "monitoring-custom-id.log"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def test_main_returns_config_error_for_missing_file(tmp_path: Path) -> None:
    exit_code = network_monitor.main(["--config", str(tmp_path / "missing.yaml")])
    assert exit_code == network_monitor.EXIT_CONFIG_ERROR


def test_main_returns_zero_on_success(
    mocker,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "monitoring:\n"
        "  interval_seconds: 1\n"
        "  iterations: 1\n"
        "  timeout_seconds: 1\n"
        "hosts:\n"
        "  - name: h\n"
        "    address: 127.0.0.1\n"
        "    role: local\n"
        "output:\n"
        f"  reports_dir: {tmp_path / 'reports'}\n"
        "  formats: [json]\n",
        encoding="utf-8",
    )
    mocker.patch("scripts.network_monitor.probe_host", side_effect=_fake_probe(True))
    mocker.patch("scripts.network_monitor.time.sleep")

    exit_code = network_monitor.main(["--config", str(config_file)])

    assert exit_code == network_monitor.EXIT_OK


def test_main_returns_interrupted_on_keyboard_interrupt(
    mocker,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "monitoring:\n"
        "  interval_seconds: 1\n"
        "  iterations: 1\n"
        "  timeout_seconds: 1\n"
        "hosts:\n"
        "  - name: h\n"
        "    address: 127.0.0.1\n"
        "    role: local\n"
        "output:\n"
        f"  reports_dir: {tmp_path / 'reports'}\n"
        "  formats: [json]\n",
        encoding="utf-8",
    )
    mocker.patch("scripts.network_monitor.probe_host", side_effect=KeyboardInterrupt)

    exit_code = network_monitor.main(["--config", str(config_file)])

    assert exit_code == network_monitor.EXIT_INTERRUPTED


def test_main_returns_runtime_error_on_unexpected_exception(
    mocker,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "monitoring:\n"
        "  interval_seconds: 1\n"
        "  iterations: 1\n"
        "  timeout_seconds: 1\n"
        "hosts:\n"
        "  - name: h\n"
        "    address: 127.0.0.1\n"
        "    role: local\n"
        "output:\n"
        f"  reports_dir: {tmp_path / 'reports'}\n"
        "  formats: [json]\n",
        encoding="utf-8",
    )
    mocker.patch(
        "scripts.network_monitor.probe_host",
        side_effect=RuntimeError("boom"),
    )

    exit_code = network_monitor.main(["--config", str(config_file)])

    assert exit_code == network_monitor.EXIT_RUNTIME_ERROR
