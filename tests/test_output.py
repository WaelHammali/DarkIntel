from __future__ import annotations

from darkintel.output import print_result


def test_print_result_with_entry_point() -> None:
    result = {
        "session_id": "abc123",
        "report_paths": ["report.pdf"],
        "attack_path": {
            "entry_point": "nginx 1.18 known CVE",
            "attack_narrative": "chain it",
            "steps": [{"order": 1, "action": "scan", "command": "nmap x", "why": "confirms it"}],
            "confidence": "Medium",
        },
    }
    print_result(result)  # must not raise


def test_print_result_without_entry_point() -> None:
    result = {
        "session_id": "abc123",
        "report_paths": [],
        "attack_path": {
            "entry_point": "",
            "attack_narrative": "No confirmed findings yet — no viable path identified.",
            "steps": [],
            "confidence": "Low",
        },
    }
    print_result(result)  # must not raise
