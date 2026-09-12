from __future__ import annotations

from pathlib import Path

from intelforge.domain.models import CommandResult, PageAnalysis, Port
from intelforge.domain.state import TargetState
from watchtower.memory import MemoryAgent

from darkintel.bridge import _tool_name, build_context_text, seed_memory


def _sample_state(tmp_path: Path) -> TargetState:
    state = TargetState(data_dir=tmp_path / "data")
    state.set_target("10.10.10.5")
    state.data.add_port(Port(number=80, protocol="tcp", service="http", version="nginx 1.18"))
    state.data.add_command_result(
        CommandResult(
            command="nmap -sV 10.10.10.5",
            purpose="Full TCP scan",
            clean_output="80/tcp open http nginx 1.18",
        )
    )
    state.add_page_analysis(
        PageAnalysis(
            url="http://10.10.10.5/",
            exploit_report={
                "priority_exploit_vectors": [
                    {
                        "keyword": "nginx 1.18",
                        "actionable_exploit": "check known CVEs",
                        "severity": "High",
                    }
                ],
                "final_verdict": "Outdated nginx is the most likely foothold.",
            },
        )
    )
    return state


def test_tool_name_recovered_from_raw_ref() -> None:
    # FinalRecon's own command starts with a Python interpreter path, not
    # "finalrecon" — raw_ref is what actually carries the real tool name.
    result = CommandResult(
        command="/usr/bin/python3 /opt/finalrecon.py --url http://10.10.10.5",
        purpose="FinalRecon OSINT",
        clean_output="...",
        raw_ref="data/raw/finalrecon_10.10.10.5.txt",
    )
    assert _tool_name(result, "10.10.10.5") == "finalrecon"


def test_tool_name_falls_back_to_command_without_raw_ref() -> None:
    result = CommandResult(command="nmap -sV 10.10.10.5", purpose="scan", clean_output="")
    assert _tool_name(result, "10.10.10.5") == "nmap"


def test_build_context_text_includes_ports_and_vectors(tmp_path: Path) -> None:
    text = build_context_text(_sample_state(tmp_path))
    assert "tcp/80: http nginx 1.18" in text
    assert "nginx 1.18" in text
    assert "check known CVEs" in text
    assert "Outdated nginx is the most likely foothold." in text


def test_build_context_text_empty_state_has_no_sections(tmp_path: Path) -> None:
    state = TargetState(data_dir=tmp_path / "data")
    state.set_target("10.10.10.5")
    text = build_context_text(state)
    assert "Open Ports" not in text
    assert "Exploit vectors" not in text


def test_seed_memory_writes_observations_and_findings(tmp_path: Path) -> None:
    state = _sample_state(tmp_path)
    memory = MemoryAgent(db_path=":memory:", vector_enabled=False)
    session_id = memory.create_session(state.data.target)

    seed_memory(state, memory, session_id)

    observations = memory.get_all_observations()
    assert any("80/tcp open http nginx 1.18" in output for _tool, output in observations)

    memories = memory.get_memory_context(session_id, limit=10)
    assert "nginx 1.18" in memories
