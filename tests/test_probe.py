"""Tests for the ICMP probe engine."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest
from scripts.models import Host, HostRole
from scripts.probe import parse_rtt_ms, probe_host


@pytest.fixture
def host() -> Host:
    return Host(name="host-a", address="127.0.0.1", role=HostRole.LOCAL)


def _make_completed(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["ping"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


# ---------------------------------------------------------------------------
# parse_rtt_ms
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.042 ms", 0.042),
        ("64 bytes from 1.1.1.1: icmp_seq=1 ttl=49 time=25.7 ms", 25.7),
        ("time=123.456ms", 123.456),
    ],
)
def test_parse_rtt_ms_extracts_value(stdout: str, expected: float) -> None:
    assert parse_rtt_ms(stdout) == pytest.approx(expected)


def test_parse_rtt_ms_returns_none_when_missing() -> None:
    assert parse_rtt_ms("Destination Host Unreachable") is None


def test_parse_rtt_ms_returns_none_on_empty_stdout() -> None:
    assert parse_rtt_ms("") is None


# ---------------------------------------------------------------------------
# probe_host - success
# ---------------------------------------------------------------------------


def test_probe_host_success(mocker: Any, host: Host) -> None:
    stdout = "64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.123 ms"
    mocker.patch(
        "scripts.probe.subprocess.run",
        return_value=_make_completed(returncode=0, stdout=stdout),
    )

    result = probe_host(host, iteration=1, timeout_seconds=2)

    assert result.success is True
    assert result.rtt_ms == pytest.approx(0.123)
    assert result.error is None
    assert result.host_name == host.name
    assert result.host_address == host.address
    assert result.iteration == 1


# ---------------------------------------------------------------------------
# probe_host - failures
# ---------------------------------------------------------------------------


def test_probe_host_unreachable_host(mocker: Any, host: Host) -> None:
    mocker.patch(
        "scripts.probe.subprocess.run",
        return_value=_make_completed(returncode=1, stdout=""),
    )

    result = probe_host(host, iteration=2, timeout_seconds=1)

    assert result.success is False
    assert result.rtt_ms is None
    assert result.error is not None
    assert "code 1" in result.error


def test_probe_host_unparseable_output(mocker: Any, host: Host) -> None:
    mocker.patch(
        "scripts.probe.subprocess.run",
        return_value=_make_completed(returncode=0, stdout="garbage output"),
    )

    result = probe_host(host, iteration=3, timeout_seconds=1)

    assert result.success is False
    assert result.error == "could not parse RTT from ping output"


def test_probe_host_missing_binary(mocker: Any, host: Host) -> None:
    mocker.patch(
        "scripts.probe.subprocess.run",
        side_effect=FileNotFoundError,
    )

    result = probe_host(host, iteration=4, timeout_seconds=1)

    assert result.success is False
    assert result.error is not None
    assert "not found" in result.error


def test_probe_host_subprocess_timeout(mocker: Any, host: Host) -> None:
    mocker.patch(
        "scripts.probe.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ping", timeout=2),
    )

    result = probe_host(host, iteration=5, timeout_seconds=1)

    assert result.success is False
    assert result.error is not None
    assert "timeout" in result.error


def test_probe_host_command_construction(mocker: Any, host: Host) -> None:
    spy = mocker.patch(
        "scripts.probe.subprocess.run",
        return_value=_make_completed(returncode=0, stdout="time=1.0 ms"),
    )

    probe_host(host, iteration=1, timeout_seconds=3)

    called_args = spy.call_args
    command = called_args.args[0]
    assert command[:5] == ["ping", "-c", "1", "-W", "3"]
    assert "-n" in command
    assert host.address in command
