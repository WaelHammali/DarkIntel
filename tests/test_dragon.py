from __future__ import annotations

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from darkintel import dragon


def test_dragon_short_circuits_without_model() -> None:
    result = dragon.synthesize(None, confirmed_findings=[{"title": "x"}], command_history="")
    assert result["entry_point"] == ""
    assert result["steps"] == []


def test_dragon_short_circuits_without_confirmed_findings() -> None:
    model = FakeListChatModel(responses=["should not be called"])
    result = dragon.synthesize(model, confirmed_findings=[], command_history="$ nmap x")
    assert result["entry_point"] == ""


def test_dragon_synthesizes_from_confirmed_findings() -> None:
    model = FakeListChatModel(
        responses=[
            '{"entry_point": "nginx 1.18 known CVE", "attack_narrative": "chain it",'
            ' "steps": [{"order": 1, "action": "scan", "command": "nmap 10.10.10.5",'
            ' "why": "confirms nginx 1.18"}], "confidence": "Medium"}'
        ]
    )
    result = dragon.synthesize(
        model,
        confirmed_findings=[{"title": "nginx 1.18", "cvss_score": 7.5, "verdict": "confirmed"}],
        command_history="$ nmap 10.10.10.5\n80/tcp open http nginx 1.18",
        nmap_summary="tcp/80: http nginx 1.18",
    )
    assert result["entry_point"] == "nginx 1.18 known CVE"
    assert result["confidence"] == "Medium"
