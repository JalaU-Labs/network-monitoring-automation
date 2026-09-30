"""Report generation for monitoring sessions.

Consumes the raw probe results and per-host statistics, produces a single
structured payload and renders it to one or more formats (JSON, log,
Markdown). File writing is handled by `write_reports`, which is the only
entry point with side effects.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.models import HostStatistics, OutputFormat, ProbeResult


def session_id(moment: datetime | None = None) -> str:
    """Return a filesystem-safe identifier for a monitoring session."""
    return (moment or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")


def build_session_payload(
    results: list[ProbeResult],
    statistics: list[HostStatistics],
    *,
    started_at: datetime,
    finished_at: datetime,
) -> dict[str, Any]:
    """Build the structured payload shared by all report formats."""
    duration = (finished_at - started_at).total_seconds()
    return {
        "session": {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round(duration, 3),
            "total_probes": len(results),
            "hosts_monitored": len(statistics),
        },
        "hosts": [_host_summary(stats) for stats in statistics],
        "probes": [_probe_record(result) for result in results],
    }


def render_json(payload: dict[str, Any]) -> str:
    """Render the payload as a formatted JSON document."""
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_log(payload: dict[str, Any]) -> str:
    """Render the payload as a chronological log."""
    lines: list[str] = []
    session = payload["session"]

    lines.append(f"[{session['started_at']}] monitoring session started")
    lines.append(
        f"[{session['started_at']}] monitoring {session['hosts_monitored']} host(s), "
        f"{session['total_probes']} probe(s) total"
    )

    for probe in payload["probes"]:
        ts = probe["timestamp"]
        if probe["success"]:
            lines.append(
                f"[{ts}] {probe['host_name']} ({probe['host_address']}) "
                f"iter={probe['iteration']} success rtt={probe['rtt_ms']}ms"
            )
        else:
            lines.append(
                f"[{ts}] {probe['host_name']} ({probe['host_address']}) "
                f"iter={probe['iteration']} FAILED reason={probe['error']}"
            )

    lines.append(f"[{session['finished_at']}] probe phase finished")

    for host in payload["hosts"]:
        lines.append(
            f"[{session['finished_at']}] host={host['name']} "
            f"availability={host['availability_pct']}% "
            f"avg={host['avg_rtt_ms']}ms "
            f"min={host['min_rtt_ms']}ms "
            f"max={host['max_rtt_ms']}ms "
            f"jitter={host['jitter_ms']}ms"
        )

    lines.append(
        f"[{session['finished_at']}] session ended "
        f"(duration={session['duration_seconds']}s)"
    )
    return "\n".join(lines) + "\n"


def render_markdown(payload: dict[str, Any]) -> str:
    """Render the payload as a Markdown report."""
    session = payload["session"]
    lines: list[str] = []

    lines.append("# Monitoring Report")
    lines.append("")
    lines.append("## Session summary")
    lines.append("")
    lines.append(f"- Started at: `{session['started_at']}`")
    lines.append(f"- Finished at: `{session['finished_at']}`")
    lines.append(f"- Duration: `{session['duration_seconds']} s`")
    lines.append(f"- Hosts monitored: `{session['hosts_monitored']}`")
    lines.append(f"- Total probes executed: `{session['total_probes']}`")
    lines.append("")

    lines.append("## Per-host statistics")
    lines.append("")
    lines.append(
        "| Host | Address | Role | Availability | Avg RTT (ms) | "
        "Min (ms) | Max (ms) | Jitter (ms) | OK / Total |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for host in payload["hosts"]:
        lines.append(
            f"| {host['name']} "
            f"| {host['address']} "
            f"| {host['role']} "
            f"| {host['availability_pct']}% "
            f"| {_fmt(host['avg_rtt_ms'])} "
            f"| {_fmt(host['min_rtt_ms'])} "
            f"| {_fmt(host['max_rtt_ms'])} "
            f"| {_fmt(host['jitter_ms'])} "
            f"| {host['successful_probes']} / {host['total_probes']} |"
        )
    lines.append("")

    incidents = [p for p in payload["probes"] if not p["success"]]
    lines.append("## Incidents")
    lines.append("")
    if not incidents:
        lines.append("No connectivity failures detected during the session.")
    else:
        lines.append(
            "| Timestamp | Host | Address | Iteration | Reason |"
        )
        lines.append("|---|---|---|---|---|")
        for probe in incidents:
            lines.append(
                f"| {probe['timestamp']} "
                f"| {probe['host_name']} "
                f"| {probe['host_address']} "
                f"| {probe['iteration']} "
                f"| {probe['error']} |"
            )
    lines.append("")

    return "\n".join(lines) + "\n"


def write_reports(
    results: list[ProbeResult],
    statistics: list[HostStatistics],
    *,
    reports_dir: str | Path,
    formats: tuple[OutputFormat, ...],
    started_at: datetime,
    finished_at: datetime,
    run_id: str | None = None,
) -> dict[OutputFormat, Path]:
    """Write reports to disk in every requested format.

    Returns a mapping from format to the path of the written file.
    """
    directory = Path(reports_dir)
    directory.mkdir(parents=True, exist_ok=True)

    identifier = run_id or session_id(finished_at)
    payload = build_session_payload(
        results, statistics, started_at=started_at, finished_at=finished_at
    )

    renderers: dict[OutputFormat, tuple[str, callable]] = {
        OutputFormat.JSON: ("json", render_json),
        OutputFormat.LOG: ("log", render_log),
        OutputFormat.MARKDOWN: ("md", render_markdown),
    }

    written: dict[OutputFormat, Path] = {}
    for fmt in formats:
        extension, renderer = renderers[fmt]
        target = directory / f"monitoring-{identifier}.{extension}"
        target.write_text(renderer(payload), encoding="utf-8")
        written[fmt] = target

    return written


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _host_summary(stats: HostStatistics) -> dict[str, Any]:
    return {
        "name": stats.host.name,
        "address": stats.host.address,
        "role": stats.host.role.value,
        "total_probes": stats.total_probes,
        "successful_probes": stats.successful_probes,
        "failed_probes": stats.failed_probes,
        "availability_pct": round(stats.availability_pct, 2),
        "avg_rtt_ms": _round_or_none(stats.avg_rtt_ms, 3),
        "min_rtt_ms": _round_or_none(stats.min_rtt_ms, 3),
        "max_rtt_ms": _round_or_none(stats.max_rtt_ms, 3),
        "jitter_ms": _round_or_none(stats.jitter_ms, 3),
    }


def _probe_record(result: ProbeResult) -> dict[str, Any]:
    return {
        "host_name": result.host_name,
        "host_address": result.host_address,
        "iteration": result.iteration,
        "success": result.success,
        "rtt_ms": result.rtt_ms,
        "timestamp": result.timestamp.isoformat(),
        "error": result.error,
    }


def _round_or_none(value: float | None, digits: int) -> float | None:
    return round(value, digits) if value is not None else None


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value}"
