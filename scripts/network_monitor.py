"""Network monitoring entry point.

This module will be fully implemented in Activity 2 of the Week 05 Lab:
periodic ICMP probing of a configurable set of hosts, latency/availability
collection and consolidated reporting.
"""

from __future__ import annotations

from scripts import __version__


def main() -> int:
    """CLI entry point (placeholder)."""
    print(f"network-monitor v{__version__} - placeholder entry point")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
