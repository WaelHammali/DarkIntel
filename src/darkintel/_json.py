"""Coerce noisy LLM output into parseable JSON."""

from __future__ import annotations

import json
import re
from typing import Any

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_OPEN_RE = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\s*```$")
_OBJECT_RE = re.compile(r"(\{[\s\S]*\}|\[[\s\S]*\])")


def strip_fences(text: str) -> str:
    """Remove ``<think>`` blocks, markdown fences and surrounding prose."""
    text = _THINK_RE.sub("", text or "").strip()
    text = _FENCE_OPEN_RE.sub("", text)
    text = _FENCE_CLOSE_RE.sub("", text)
    match = _OBJECT_RE.search(text)
    return match.group(0).strip() if match else text.strip()


def loads(text: str) -> Any:
    """Parse ``text`` as JSON after stripping fences/reasoning noise."""
    return json.loads(strip_fences(text))
