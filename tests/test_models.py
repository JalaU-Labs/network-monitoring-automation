"""Tests for the domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from scripts.models import Host, HostRole, HostStatistics, ProbeResult


def _make_result(*, success: bool, rtt_ms: float | None) -> ProbeResult:
    return ProbeResult(
        host_name="host-a",
        host_address="127.0.0.1",
        iteration=1,
        success=success,
        rtt_ms=rtt_ms,
        timestamp=datetime.now(UTC),
    )


def test_host_is_immutable() -> None:
    host = Host(name="h", address="127.0.0.1", role=HostRole.LOCAL)
    with pytest.raises(FrozenInstanceError):
        host.name = "other"  # type: ignore[misc]


def test_statistics_empty_returns_none_aggregates() -> None:
    stats = HostStatistics(host=Host("h", "127.0.0.1", HostRole.LOCAL))
    assert stats.availability_pct == 0.0
    assert stats.avg_rtt_ms is None
    assert stats.min_rtt_ms is None
    assert stats.max_rtt_ms is None
    assert stats.jitter_ms is None


def test_statistics_aggregates_only_successful_samples() -> None:
    stats = HostStatistics(host=Host("h", "127.0.0.1", HostRole.LOCAL))
    stats.register(_make_result(success=True, rtt_ms=10.0))
    stats.register(_make_result(success=True, rtt_ms=20.0))
    stats.register(_make_result(success=False, rtt_ms=None))
    stats.register(_make_result(success=True, rtt_ms=30.0))

    assert stats.total_probes == 4
    assert stats.successful_probes == 3
    assert stats.failed_probes == 1
    assert stats.availability_pct == pytest.approx(75.0)
    assert stats.avg_rtt_ms == pytest.approx(20.0)
    assert stats.min_rtt_ms == pytest.approx(10.0)
    assert stats.max_rtt_ms == pytest.approx(30.0)
    assert stats.jitter_ms == pytest.approx(10.0)


def test_jitter_requires_two_samples() -> None:
    stats = HostStatistics(host=Host("h", "127.0.0.1", HostRole.LOCAL))
    stats.register(_make_result(success=True, rtt_ms=10.0))
    assert stats.jitter_ms is None
