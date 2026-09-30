"""Smoke tests to verify package wiring and CI pipeline."""

from __future__ import annotations

import pytest

from scripts import __version__, network_monitor


def test_version_is_defined() -> None:
    assert isinstance(__version__, str)
    assert __version__.count(".") == 2


def test_main_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = network_monitor.main()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "placeholder" in captured.out
