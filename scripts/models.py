"""Domain models for the network monitoring toolkit.

This module defines the typed structures shared across the configuration
loader, the probe engine and the report generators. Models are intentionally
free of side effects: they only carry data and small derived computations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class HostRole(StrEnum):
    """Category assigned to a monitored host."""

    CONTAINER = "container"
    LOCAL = "local"
    PUBLIC = "public"


class OutputFormat(StrEnum):
    """Supported consolidated report formats."""

    JSON = "json"
    LOG = "log"
    MARKDOWN = "markdown"


@dataclass(frozen=True, slots=True)
class Host:
    """A monitored network endpoint."""

    name: str
    address: str
    role: HostRole


@dataclass(frozen=True, slots=True)
class MonitoringConfig:
    """Validated runtime configuration for a monitoring session."""

    interval_seconds: int
    iterations: int
    timeout_seconds: int
    hosts: tuple[Host, ...]
    reports_dir: str
    formats: tuple[OutputFormat, ...]


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Outcome of a single ICMP probe against a host."""

    host_name: str
    host_address: str
    iteration: int
    success: bool
    rtt_ms: float | None
    timestamp: datetime
    error: str | None = None


@dataclass
class HostStatistics:
    """Aggregated statistics for one host across all probe rounds."""

    host: Host
    total_probes: int = 0
    successful_probes: int = 0
    failed_probes: int = 0
    rtt_samples_ms: list[float] = field(default_factory=list)

    @property
    def availability_pct(self) -> float:
        """Percentage of successful probes (0.0 to 100.0)."""
        if self.total_probes == 0:
            return 0.0
        return self.successful_probes / self.total_probes * 100.0

    @property
    def avg_rtt_ms(self) -> float | None:
        if not self.rtt_samples_ms:
            return None
        return sum(self.rtt_samples_ms) / len(self.rtt_samples_ms)

    @property
    def min_rtt_ms(self) -> float | None:
        return min(self.rtt_samples_ms) if self.rtt_samples_ms else None

    @property
    def max_rtt_ms(self) -> float | None:
        return max(self.rtt_samples_ms) if self.rtt_samples_ms else None

    @property
    def jitter_ms(self) -> float | None:
        """Mean absolute difference between consecutive RTT samples.

        Returns None when fewer than two successful samples are available.
        """
        if len(self.rtt_samples_ms) < 2:
            return None
        diffs = [
            abs(self.rtt_samples_ms[i] - self.rtt_samples_ms[i - 1])
            for i in range(1, len(self.rtt_samples_ms))
        ]
        return sum(diffs) / len(diffs)

    def register(self, result: ProbeResult) -> None:
        """Update the aggregate with a new probe result."""
        self.total_probes += 1
        if result.success and result.rtt_ms is not None:
            self.successful_probes += 1
            self.rtt_samples_ms.append(result.rtt_ms)
        else:
            self.failed_probes += 1
