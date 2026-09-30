"""Tests for the report generators."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from scripts.models import Host, HostRole, HostStatistics, OutputFormat, ProbeResult
from scripts.report import (
    build_session_payload,
    render_json,
    render_log,
    render_markdown,
    session_id,
    write_reports,
)

START = datetime(2026, 9, 30, 16, 0, 0, tzinfo=UTC)
END = START + timedelta(seconds=42)


def _host(name: str, address: str, role: HostRole) -> Host:
    return Host(name=name, address=address, role=role)


def _probe(
    *,
    host: Host,
    iteration: int,
    success: bool,
    rtt_ms: float | None,
    error: str | None = None,
    offset_seconds: int = 0,
) -> ProbeResult:
    return ProbeResult(
        host_name=host.name,
        host_address=host.address,
        iteration=iteration,
        success=success,
        rtt_ms=rtt_ms,
        timestamp=START + timedelta(seconds=offset_seconds),
        error=error,
    )


@pytest.fixture
def scenario() -> tuple[list[ProbeResult], list[HostStatistics]]:
    alpha = _host("alpha", "172.28.0.10", HostRole.CONTAINER)
    beta = _host("beta", "172.28.0.11", HostRole.CONTAINER)

    stats_alpha = HostStatistics(host=alpha)
    stats_beta = HostStatistics(host=beta)

    results = [
        _probe(host=alpha, iteration=1, success=True, rtt_ms=0.1, offset_seconds=0),
        _probe(host=alpha, iteration=2, success=True, rtt_ms=0.3, offset_seconds=5),
        _probe(host=beta, iteration=1, success=True, rtt_ms=1.0, offset_seconds=1),
        _probe(
            host=beta,
            iteration=2,
            success=False,
            rtt_ms=None,
            error="ping exited with code 1",
            offset_seconds=6,
        ),
    ]

    for result in results:
        (stats_alpha if result.host_name == "alpha" else stats_beta).register(result)

    return results, [stats_alpha, stats_beta]


# ---------------------------------------------------------------------------
# session_id
# ---------------------------------------------------------------------------


def test_session_id_uses_given_moment() -> None:
    assert session_id(START) == "20260930-160000"


# ---------------------------------------------------------------------------
# build_session_payload
# ---------------------------------------------------------------------------


def test_payload_shape(
    scenario: tuple[list[ProbeResult], list[HostStatistics]],
) -> None:
    results, statistics = scenario
    payload = build_session_payload(results, statistics, started_at=START, finished_at=END)

    assert payload["session"]["total_probes"] == 4
    assert payload["session"]["hosts_monitored"] == 2
    assert payload["session"]["duration_seconds"] == pytest.approx(42.0)
    assert len(payload["hosts"]) == 2
    assert len(payload["probes"]) == 4


def test_payload_host_fields(
    scenario: tuple[list[ProbeResult], list[HostStatistics]],
) -> None:
    results, statistics = scenario
    payload = build_session_payload(results, statistics, started_at=START, finished_at=END)
    by_name = {host["name"]: host for host in payload["hosts"]}

    alpha = by_name["alpha"]
    assert alpha["availability_pct"] == pytest.approx(100.0)
    assert alpha["avg_rtt_ms"] == pytest.approx(0.2)
    assert alpha["min_rtt_ms"] == pytest.approx(0.1)
    assert alpha["max_rtt_ms"] == pytest.approx(0.3)
    assert alpha["role"] == "container"

    beta = by_name["beta"]
    assert beta["availability_pct"] == pytest.approx(50.0)
    assert beta["failed_probes"] == 1
    assert beta["avg_rtt_ms"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# render_json
# ---------------------------------------------------------------------------


def test_render_json_is_parseable(
    scenario: tuple[list[ProbeResult], list[HostStatistics]],
) -> None:
    results, statistics = scenario
    payload = build_session_payload(results, statistics, started_at=START, finished_at=END)
    rendered = render_json(payload)
    parsed = json.loads(rendered)
    assert parsed["session"]["total_probes"] == 4


# ---------------------------------------------------------------------------
# render_log
# ---------------------------------------------------------------------------


def test_render_log_contains_key_markers(
    scenario: tuple[list[ProbeResult], list[HostStatistics]],
) -> None:
    results, statistics = scenario
    payload = build_session_payload(results, statistics, started_at=START, finished_at=END)
    log = render_log(payload)

    assert "monitoring session started" in log
    assert "monitoring 2 host(s), 4 probe(s) total" in log
    assert "iter=1 success rtt=0.1ms" in log
    assert "iter=2 FAILED reason=ping exited with code 1" in log
    assert "availability=100.0%" in log
    assert "availability=50.0%" in log
    assert "session ended" in log


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------


def test_render_markdown_contains_table_and_incidents(
    scenario: tuple[list[ProbeResult], list[HostStatistics]],
) -> None:
    results, statistics = scenario
    payload = build_session_payload(results, statistics, started_at=START, finished_at=END)
    md = render_markdown(payload)

    assert "# Monitoring Report" in md
    assert "## Session summary" in md
    assert "## Per-host statistics" in md
    assert "## Incidents" in md
    assert "| alpha " in md
    assert "| beta " in md
    assert "ping exited with code 1" in md


def test_render_markdown_without_incidents() -> None:
    host = _host("solo", "127.0.0.1", HostRole.LOCAL)
    stats = HostStatistics(host=host)
    result = _probe(host=host, iteration=1, success=True, rtt_ms=0.1)
    stats.register(result)

    payload = build_session_payload([result], [stats], started_at=START, finished_at=END)
    md = render_markdown(payload)

    assert "No connectivity failures detected" in md


# ---------------------------------------------------------------------------
# write_reports
# ---------------------------------------------------------------------------


def test_write_reports_creates_all_requested_files(
    tmp_path: Path,
    scenario: tuple[list[ProbeResult], list[HostStatistics]],
) -> None:
    results, statistics = scenario
    written = write_reports(
        results,
        statistics,
        reports_dir=tmp_path,
        formats=(OutputFormat.JSON, OutputFormat.LOG, OutputFormat.MARKDOWN),
        started_at=START,
        finished_at=END,
        run_id="20260930-160000",
    )

    assert set(written.keys()) == {OutputFormat.JSON, OutputFormat.LOG, OutputFormat.MARKDOWN}
    for fmt, path in written.items():
        assert path.exists(), f"{fmt} not written"
        assert path.name == f"monitoring-20260930-160000.{_ext(fmt)}"
        assert path.stat().st_size > 0


def test_write_reports_creates_directory(
    tmp_path: Path,
    scenario: tuple[list[ProbeResult], list[HostStatistics]],
) -> None:
    results, statistics = scenario
    target = tmp_path / "nested" / "reports"
    write_reports(
        results,
        statistics,
        reports_dir=target,
        formats=(OutputFormat.JSON,),
        started_at=START,
        finished_at=END,
    )
    assert target.is_dir()
    assert any(target.iterdir())


def _ext(fmt: OutputFormat) -> str:
    return {
        OutputFormat.JSON: "json",
        OutputFormat.LOG: "log",
        OutputFormat.MARKDOWN: "md",
    }[fmt]
