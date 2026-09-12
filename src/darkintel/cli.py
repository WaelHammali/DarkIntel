"""``darkintel run <target>`` — the bridge's CLI entry point."""

from __future__ import annotations

import json

import click

from darkintel.bridge import run as run_bridge


@click.group()
def main() -> None:
    """DarkIntel — bridges IntelForge's recon into VoidHawk's memory."""


@main.command()
@click.argument("target")
@click.option(
    "--report-format",
    type=click.Choice(["pdf", "html", "markdown", "all"]),
    default="pdf",
    help="VoidHawk report format(s) to generate.",
)
def run(target: str, report_format: str) -> None:
    """Run IntelForge recon against TARGET, then VoidHawk validation + Dragon synthesis."""
    result = run_bridge(target, report_format=report_format)
    click.echo(f"Session: {result['session_id']}")
    for path in result["report_paths"]:
        click.echo(f"Report: {path}")
    attack_path = result["attack_path"]
    if attack_path.get("entry_point"):
        click.echo(f"\nEntry point: {attack_path['entry_point']}")
        click.echo(attack_path["attack_narrative"])
    else:
        click.echo(f"\n{attack_path['attack_narrative']}")
    click.echo(json.dumps(attack_path, indent=2))


if __name__ == "__main__":
    main()
