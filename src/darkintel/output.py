"""Shared result rendering for the CLI command and the interactive console."""

from __future__ import annotations

from typing import Any

from intelforge.console.theme import console, good, status


def print_result(result: dict[str, Any]) -> None:
    """Render a ``bridge.run()`` result the same way in both entry points."""
    console.print(f"\n[heading]Session:[/heading] {result['session_id']}")
    for path in result["report_paths"]:
        good(f"Report: {path}")

    attack_path = result["attack_path"]
    if attack_path.get("entry_point"):
        console.print(f"\n[accent]Entry point:[/accent] {attack_path['entry_point']}")
        console.print(attack_path["attack_narrative"])
        for step in attack_path.get("steps", []):
            command = step.get("command") or "(no command — inference only)"
            console.print(
                f"  {step.get('order', '?')}. {step.get('action', '')}\n"
                f"     $ {command}\n"
                f"     {step.get('why', '')}"
            )
        status(f"Confidence: {attack_path.get('confidence', 'Low')}")
    else:
        console.print(f"\n{attack_path.get('attack_narrative', 'No attack path.')}")
