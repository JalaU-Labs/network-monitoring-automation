# network-monitoring-automation

Week 05 Lab - Network monitoring, diagnostics and automation.

Jala University | CSNT-245 | Software Engineering

## Overview

This repository contains the deliverables for the Week 05 Lab of the
Computer Networks 2 course. It covers two activities:

- **Activity 1 - Network monitoring:** connectivity, latency and
  throughput analysis using `ping`, `traceroute`, `iperf3` and `mtr`.
- **Activity 2 - Automation and centralized management:** a Python-based
  monitoring service orchestrated with Docker and a dedicated Docker
  network, using ICMP probes to collect latency and availability metrics.

Detailed documentation:

- Activity 1: [`docs/activity-1-monitoring.md`](docs/activity-1-monitoring.md)
- Activity 2: documented in this `README.md` (below).

## Project structure

```text
network-monitoring-automation/
├── assets/evidence/          # Screenshots of test results
├── docker/                   # Dockerfiles for monitor and target hosts
├── docs/                     # Activity-specific documentation
├── scripts/                  # Python source code
├── tests/                    # Pytest test suite
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── uv.lock
└── README.md
```

## Requirements

- Python 3.14 (managed with `uv`)
- Docker Engine 24+
- GNU Make
- `iperf3` and `mtr` for Activity 1 (see `docs/activity-1-monitoring.md`)

## Quick start

```bash
make setup
make lint
make test
```

## Author

Diego Alejandro Botina

## License

MIT - see [`LICENSE`](LICENSE).
