"""``darkintel`` CLI — bare invocation launches the interactive console;
``darkintel run <target>`` runs the bridge non-interactively for scripting.
"""

from __future__ import annotations

import click

from darkintel.bridge import run as run_bridge
from darkintel.output import print_result


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """DarkIntel — bridges IntelForge's recon into VoidHawk's memory."""
    if ctx.invoked_subcommand is None:
        from darkintel.console import main as console_main

        console_main()


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
    try:
        result = run_bridge(target, report_format=report_format)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    print_result(result)


if __name__ == "__main__":
    main()
