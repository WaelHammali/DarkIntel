from __future__ import annotations

from typing import Any

import pytest

from darkintel import console


def test_burn_with_no_args_does_not_call_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(console, "run_bridge", fake_run)
    console._burn([])
    assert called is False


def test_burn_with_invalid_format_does_not_call_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(console, "run_bridge", fake_run)
    console._burn(["10.10.10.5", "csv"])
    assert called is False


def test_burn_passes_target_and_format(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_run(target: str, *, report_format: str) -> dict[str, Any]:
        seen["target"] = target
        seen["report_format"] = report_format
        return {
            "session_id": "s1",
            "report_paths": [],
            "attack_path": {"entry_point": "", "attack_narrative": "none", "steps": []},
        }

    monkeypatch.setattr(console, "run_bridge", fake_run)
    console._burn(["10.10.10.5", "html"])
    assert seen == {"target": "10.10.10.5", "report_format": "html"}


def test_burn_defaults_to_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_run(target: str, *, report_format: str) -> dict[str, Any]:
        seen["report_format"] = report_format
        return {
            "session_id": "s1",
            "report_paths": [],
            "attack_path": {"entry_point": "", "attack_narrative": "none", "steps": []},
        }

    monkeypatch.setattr(console, "run_bridge", fake_run)
    console._burn(["10.10.10.5"])
    assert seen["report_format"] == "pdf"


def test_burn_swallows_bridge_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise ValueError("invalid target")

    monkeypatch.setattr(console, "run_bridge", fake_run)
    console._burn(["not-a-target"])  # must not raise
