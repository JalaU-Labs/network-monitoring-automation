"""Network monitoring CLI entry point.

Orchestrates a monitoring session: loads the YAML configuration, runs the
ICMP probes against every configured host, aggregates statistics and writes
reports in the requested formats.

Exit codes:
    0   Session completed successfully.
    1   Configuration error (file missing, invalid YAML, invalid values).
    2   Unexpected runtime error during the session.
    130 Session interrupted by the user (SIGINT / Ctrl+C).
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from scripts import __version__
from scripts.config import ConfigError, load_config
from scripts.models import HostStatistics, MonitoringConfig, OutputFormat, ProbeResult
from scripts.probe import probe_host
from scripts.report import write_reports

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_RUNTIME_ERROR = 2
EXIT_INTERRUPTED = 130

DEFAULT_CONFIG_PATH = Path("scripts/config.yaml")


# ---------------------------------------------------------------------------
# Session orchestration
# ---------------------------------------------------------------------------

def run_session(
    config: MonitoringConfig,
    *,
    run_id: str | None = None,
    sleeper: callable = time.sleep,
) -> tuple[
    list[ProbeResult],
    list[HostStatistics],
    datetime,
    datetime,
    dict[OutputFormat, Path],
]:
    """Execute a full monitoring session and return the collected data.

    The `sleeper` parameter allows tests to inject a no-op sleep function.
    """
    started_at = datetime.now(UTC)
    statistics = {host.name: HostStatistics(host=host) for host in config.hosts}
    results: list[ProbeResult] = []

    for iteration in range(1, config.iterations + 1):
        for host in config.hosts:
            result = probe_host(host, iteration=iteration, timeout_seconds=config.timeout_seconds)
            results.append(result)
            statistics[host.name].register(result)

            status = "OK" if result.success else "FAIL"
            rtt = f"{result.rtt_ms:.3f} ms" if result.rtt_ms is not None else "n/a"
            print(f"[iter {iteration:>3}/{config.iterations}] {host.name:<20} {status:<4} rtt={rtt}")

        if iteration < config.iterations:
            sleeper(config.interval_seconds)

    finished_at = datetime.now(UTC)

    paths = write_reports(
        results,
        list(statistics.values()),
        reports_dir=config.reports_dir,
        formats=config.formats,
        started_at=started_at,
        finished_at=finished_at,
        run_id=run_id,
    )

    return results, list(statistics.values()), started_at, finished_at, paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="network-monitor",
        description=(
            "Monitor a set of hosts via ICMP, aggregate latency and "
            "availability metrics and produce consolidated reports."
        ),
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to the YAML configuration file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional identifier for the session, used in report filenames.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"network-monitor {__version__}",
    )
    return parser


def _print_summary(statistics: list[HostStatistics], paths: dict[OutputFormat, Path]) -> None:
    print()
    print("Session summary")
    print("---------------")
    for stats in statistics:
        avg = f"{stats.avg_rtt_ms:.3f} ms" if stats.avg_rtt_ms is not None else "n/a"
        jitter = f"{stats.jitter_ms:.3f} ms" if stats.jitter_ms is not None else "n/a"
        print(
            f"  {stats.host.name:<20} "
            f"availability={stats.availability_pct:5.1f}%  "
            f"avg={avg:<12} "
            f"jitter={jitter}"
        )
    print()
    print("Reports written:")
    for fmt, path in paths.items():
        print(f"  {fmt.value:<10} {path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    try:
        _, statistics, _, _, paths = run_session(config, run_id=args.run_id)
    except KeyboardInterrupt:
        print("\ninterrupted by user", file=sys.stderr)
        return EXIT_INTERRUPTED
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print(f"unexpected error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    _print_summary(statistics, paths)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
