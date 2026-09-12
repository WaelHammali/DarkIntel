"""The bridge: run IntelForge's recon, seed it into VoidHawk's memory, let
VoidHawk's own Planner/Validator/reporting take it from there, then hand
VoidHawk's confirmed findings + the real command history to Dragon.

Neither IntelForge nor VoidHawk is modified or duplicated — this module only
converts one side's output into the other's input shape and drives VoidHawk's
existing graph starting past the recon phase, since IntelForge already did it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from intelforge.console.theme import good, status
from intelforge.domain.models import CommandResult
from intelforge.domain.state import TargetState
from intelforge.graph.pipeline import run as run_intelforge
from intelforge.graph.state import ScanOptions
from watchtower.core.config import config as voidhawk_config
from watchtower.graph import create_agent_graph
from watchtower.memory import MemoryAgent

from darkintel import dragon
from darkintel.config import settings
from darkintel.llm import dragon_model

# Tools VoidHawk itself would use for recon — IntelForge already covered this
# ground, so the bridge excludes them and starts VoidHawk at the scan phase.
# Sourced from watchtower.agents.planner._PHASE_TOOL_HINTS["recon"] (a private
# constant, so it's copied rather than imported to avoid a hard coupling to
# VoidHawk's internal module layout).
RECON_TOOLS: frozenset[str] = frozenset(
    {
        "subfinder",
        "amass",
        "dnsrecon",
        "nmap",
        "masscan",
        "httpx",
        "whatweb",
        "wafw00f",
        "gobuster",
        "ffuf",
        "arjun",
        "kiterunner",
    }
)


def build_context_text(state: TargetState) -> str:
    """A digest of IntelForge's findings for VoidHawk's Planner to read on its
    very first prompt (in addition to whatever it later finds via its own
    semantic search over the seeded memory)."""
    lines = ["## IntelForge Recon Summary"]
    nmap_summary = state.get_nmap_summary()
    if nmap_summary:
        lines += ["", "### Open Ports / Services", nmap_summary]

    for page in state.data.page_analyses:
        vectors = page.exploit_report.get("priority_exploit_vectors", [])
        if vectors:
            lines += ["", f"### Exploit vectors — {page.url}"]
            for vector in vectors:
                lines.append(
                    f"- [{vector.get('severity', '?')}] {vector.get('keyword', '?')}: "
                    f"{vector.get('actionable_exploit', '')}"
                )
        verdict = page.exploit_report.get("final_verdict")
        if verdict:
            lines += ["", f"IntelForge verdict — {page.url}: {verdict}"]

    return "\n".join(lines).strip()


def _tool_name(result: CommandResult, target: str) -> str:
    """Recover the original tool identifier (e.g. "nmap_tcp_full", "finalrecon").

    ``CommandResult`` doesn't keep the name it was recorded under, but
    ``TargetState.record_command`` always saves raw output to
    ``raw/{name}_{target}.txt`` (see ``TargetState.save_raw``), so the name is
    recoverable from ``raw_ref`` without guessing from ``command`` — which for
    FinalRecon would just be a Python interpreter path, not "finalrecon".
    """
    stem = Path(result.raw_ref).stem if result.raw_ref else ""
    suffix = f"_{target}"
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return stem or (result.command.split()[0] if result.command else "intelforge")


def seed_memory(state: TargetState, memory: MemoryAgent, session_id: str) -> None:
    """Write IntelForge's findings into VoidHawk's memory before it starts.

    Command output goes in as observations (embedded for semantic search,
    exactly like a VoidHawk-run tool would be); exploit vectors go in as
    reasoning-step memories the Planner's context/search can retrieve.
    """
    for result in state.data.command_results:
        memory.log_observation(
            state.data.target,
            _tool_name(result, state.data.target),
            result.clean_output,
            clean_result={"clean_summary": f"{result.purpose}: {result.clean_output}"},
        )

    for page in state.data.page_analyses:
        for vector in page.exploit_report.get("priority_exploit_vectors", []):
            memory.add_memory(
                agent="IntelForge",
                action=f"exploit vector: {vector.get('keyword', '?')}",
                details=vector,
                session_id=session_id,
            )


def _format_command_history(observations: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for obs in observations:
        blocks.append(f"$ {obs.get('tool', '?')} — {obs.get('target', '?')}")
        blocks.append(str(obs.get("output", "")).strip() or "(no output)")
        blocks.append("")
    return "\n".join(blocks).strip()


def _generate_reports(
    db_path: str, base_path: str, fmt: str, validation_summary: str
) -> list[Path]:
    """Call VoidHawk's own reporters — same three calls as watchtower/main.py."""
    formats = ["pdf", "html", "markdown"] if fmt == "all" else [fmt]
    paths: list[Path] = []
    for report_fmt in formats:
        if report_fmt == "pdf":
            from watchtower.reporting.reporter import generate_pdf_report

            out = base_path if base_path.endswith(".pdf") else f"{base_path}.pdf"
            generate_pdf_report(db_path, out, validation_summary=validation_summary)
        elif report_fmt == "html":
            from watchtower.reporting.html_reporter import generate_html_report

            out = base_path if base_path.endswith(".html") else f"{base_path}.html"
            generate_html_report(db_path, out, validation_summary=validation_summary)
        elif report_fmt == "markdown":
            from watchtower.reporting.markdown_reporter import generate_markdown_report

            out = base_path if base_path.endswith(".md") else f"{base_path}.md"
            generate_markdown_report(db_path, out, validation_summary=validation_summary)
        else:
            continue
        paths.append(Path(out))
    return paths


def run(target: str, *, report_format: str = "pdf") -> dict[str, Any]:
    """Run the whole bridge: IntelForge recon -> VoidHawk memory + graph -> Dragon."""
    # 1. IntelForge recon.
    status(f"IntelForge — reconnaissance on {target}")
    state = TargetState(data_dir=settings.data_dir / "intelforge")
    state.set_target(target)
    run_intelforge(state, ScanOptions())
    good("IntelForge recon complete")

    # 2. Seed VoidHawk's memory with what IntelForge found.
    memory = MemoryAgent(
        db_path=voidhawk_config.memory_agent_db_path,
        vector_enabled=voidhawk_config.memory_vector_enabled,
        embed_model=voidhawk_config.memory_embed_model,
        cache_enabled=voidhawk_config.memory_cache_enabled,
        cache_ttl_seconds=voidhawk_config.memory_cache_ttl,
    )
    session_id = memory.create_session(target)
    seed_memory(state, memory, session_id)
    context_text = build_context_text(state)

    # 3. VoidHawk's initial state — skip the recon phase, IntelForge did it.
    available_tools = [t for t in voidhawk_config.all_tool_names if t not in RECON_TOOLS]
    initial_state: dict[str, Any] = {
        "scope_targets": [target],
        "available_tools": available_tools,
        "messages": [],
        "error_log": [],
        "findings": [],
        "observations": [],
        "validated_findings": [],
        "rejected_findings": [],
        "retest_requests": [],
        "completed_tools": sorted(RECON_TOOLS),
        "current_plan": "",
        "next_step": "",
        "pending_tools": [],
        "auth_metadata": {},
        "is_finished": False,
        "iteration_count": 0,
        "session_id": session_id,
        "memory_context": context_text,
        "validation_summary": "",
        "memory_agent": memory,
        "cleaner_agent": None,
        "validator_agent": None,
        "clean_result": {},
        "from_cache": False,
        "current_phase": "scan",
        "phase_history": [],
    }

    # 4. Run VoidHawk's own graph (Planner/Worker/Cleaner/Analyst/Validator/Reporter).
    # Everything from here on holds an open MemoryAgent connection, so it's
    # wrapped in try/finally to guarantee it's released even if a node raises
    # something VoidHawk's own per-node error handling didn't already catch.
    try:
        status("VoidHawk — starting at the scan phase (recon already done by IntelForge)")
        graph = create_agent_graph()
        validation_summary = ""
        logged_titles: set[str] = set()
        run_observations: list[dict[str, Any]] = []
        run_findings: list[dict[str, Any]] = []

        for event in graph.stream(
            initial_state, config={"recursion_limit": voidhawk_config.recursion_limit}
        ):
            for node_name, state_updates in event.items():
                status(f"VoidHawk [{node_name}]")
                for message in state_updates.get("messages", []):
                    status(f"  {message}")

                if "observations" in state_updates:
                    clean_res = state_updates.get("clean_result", {})
                    for obs in state_updates["observations"]:
                        memory.log_observation(
                            obs.get("target"),
                            obs.get("tool"),
                            obs.get("output"),
                            clean_result=obs.get("clean_result") or clean_res,
                        )
                        run_observations.append(obs)

                if "validated_findings" in state_updates:
                    for finding in state_updates["validated_findings"]:
                        title = finding.get("title", "Unknown Finding")
                        if title in logged_titles:
                            continue
                        logged_titles.add(title)
                        memory.log_finding(
                            target=finding.get("target", target),
                            vulnerability=title,
                            details=finding,
                            severity=finding.get("severity", "Unknown"),
                            cvss_score=float(finding.get("cvss_score", 0) or 0),
                            validated=True,
                        )
                        run_findings.append(finding)

                if state_updates.get("validation_summary"):
                    validation_summary = state_updates["validation_summary"]

        memory.close_session(session_id)
        good(f"VoidHawk run complete ({len(run_findings)} confirmed finding(s))")

        # 5. VoidHawk's own reporters — CVSS-scored PDF/HTML/Markdown.
        status(f"Writing VoidHawk report(s) ({report_format})")
        report_paths = _generate_reports(
            voidhawk_config.memory_agent_db_path,
            f"darkintel_report_{session_id[:8]}",
            report_format,
            validation_summary,
        )
        good(f"Report(s) written: {', '.join(str(p) for p in report_paths)}")

        # 6. Dragon — chains VoidHawk's confirmed findings into an entry-point narrative.
        # A provider/network failure here must not discard the reports already
        # written in step 5, so this is deliberately broader than the parse-error
        # handling inside dragon.synthesize itself.
        status("Dragon — synthesizing the exploitation path")
        try:
            attack_path = dragon.synthesize(
                dragon_model(),
                confirmed_findings=run_findings,
                command_history=_format_command_history(run_observations),
                nmap_summary=state.get_nmap_summary(),
            )
        except Exception as exc:
            attack_path = {
                "entry_point": "",
                "attack_narrative": f"Dragon failed: {exc}",
                "steps": [],
                "confidence": "Low",
            }
        if attack_path.get("entry_point"):
            good(f"Dragon entry point: {attack_path['entry_point']}")
        else:
            status(f"Dragon: {attack_path['attack_narrative']}")
    finally:
        memory.close()

    return {
        "session_id": session_id,
        "report_paths": [str(p) for p in report_paths],
        "attack_path": attack_path,
    }
