"""Dragon — synthesizes the exploitation path from VoidHawk's confirmed findings.

Reasons only over what VoidHawk's own Validator already confirmed and the
commands actually run by IntelForge + VoidHawk this session — it does not
execute anything itself and never re-implements VoidHawk's own validation.
See ``prompts/dragon.txt`` for the evidence-discipline rules enforced on it.
"""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any

from langchain_core.language_models import BaseChatModel

from darkintel._json import loads
from darkintel.llm import complete

_NO_PATH: dict[str, Any] = {
    "entry_point": "",
    "attack_narrative": "No confirmed findings yet — no viable path identified.",
    "steps": [],
    "confidence": "Low",
}


@cache
def _system_prompt() -> str:
    return files("darkintel.prompts").joinpath("dragon.txt").read_text(encoding="utf-8").strip()


def synthesize(
    model: BaseChatModel | None,
    confirmed_findings: list[dict[str, Any]],
    command_history: str,
    nmap_summary: str = "",
) -> dict[str, Any]:
    """Return the exploitation narrative, or a "no path" placeholder.

    Short-circuits (no LLM call) when Dragon isn't configured (``model`` is
    ``None``) or there is nothing confirmed to reason about.
    """
    if model is None or not confirmed_findings:
        return dict(_NO_PATH)

    payload = {
        "confirmed_findings": confirmed_findings,
        "nmap_summary": nmap_summary,
        "command_history": command_history,
    }
    user = (
        json.dumps(payload, indent=2)
        + "\n\nWrite the exploitation narrative and exact steps to reach a foothold, "
        "citing only commands that appear in command_history."
    )
    try:
        result: dict[str, Any] = loads(complete(model, _system_prompt(), user))
    except (ValueError, KeyError) as exc:
        return {**_NO_PATH, "attack_narrative": f"Synthesis failed: {exc}"}
    return result
