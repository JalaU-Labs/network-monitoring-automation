"""ICMP probe engine.

Executes a single ping per call using the system `ping` binary and converts
the raw output into a typed `ProbeResult`. The module is split into two
layers:

- `parse_rtt_ms`: pure parsing of `ping` stdout (unit-testable without network).
- `probe_host`: subprocess orchestration and error handling.

The implementation targets the Linux iputils `ping` output format.
"""

from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime

from scripts.models import Host, ProbeResult

_RTT_PATTERN = re.compile(r"time=([\d.]+)\s*ms")

# The subprocess timeout is slightly larger than the ping-level timeout
# to avoid killing the process while it is still shutting down gracefully.
_SUBPROCESS_GRACE_SECONDS = 1


def parse_rtt_ms(ping_stdout: str) -> float | None:
    """Extract the first RTT in milliseconds from `ping` stdout.

    Returns None when no `time=<value> ms` token is present, which indicates
    either a failed probe or an unexpected output format.
    """
    match = _RTT_PATTERN.search(ping_stdout)
    if match is None:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _build_command(address: str, timeout_seconds: int) -> list[str]:
    """Build the ping command line for a single ICMP echo request."""
    return [
        "ping",
        "-c",
        "1",
        "-W",
        str(timeout_seconds),
        "-n",
        address,
    ]


def probe_host(host: Host, iteration: int, timeout_seconds: int) -> ProbeResult:
    """Perform one ICMP probe against `host` and return a `ProbeResult`.

    This function never raises on network errors: unreachable hosts, missing
    binaries or subprocess timeouts are all reported through `ProbeResult`.
    """
    timestamp = datetime.now(UTC)
    command = _build_command(host.address, timeout_seconds)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + _SUBPROCESS_GRACE_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return ProbeResult(
            host_name=host.name,
            host_address=host.address,
            iteration=iteration,
            success=False,
            rtt_ms=None,
            timestamp=timestamp,
            error="ping binary not found in PATH",
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(
            host_name=host.name,
            host_address=host.address,
            iteration=iteration,
            success=False,
            rtt_ms=None,
            timestamp=timestamp,
            error=f"ping subprocess exceeded {timeout_seconds}s timeout",
        )

    if completed.returncode != 0:
        return ProbeResult(
            host_name=host.name,
            host_address=host.address,
            iteration=iteration,
            success=False,
            rtt_ms=None,
            timestamp=timestamp,
            error=f"ping exited with code {completed.returncode}",
        )

    rtt_ms = parse_rtt_ms(completed.stdout)
    if rtt_ms is None:
        return ProbeResult(
            host_name=host.name,
            host_address=host.address,
            iteration=iteration,
            success=False,
            rtt_ms=None,
            timestamp=timestamp,
            error="could not parse RTT from ping output",
        )

    return ProbeResult(
        host_name=host.name,
        host_address=host.address,
        iteration=iteration,
        success=True,
        rtt_ms=rtt_ms,
        timestamp=timestamp,
        error=None,
    )
