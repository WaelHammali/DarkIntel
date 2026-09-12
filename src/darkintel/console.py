"""The interactive DarkIntel console — launched by bare ``darkintel``.

A single command, ``burn <target>``, runs the whole bridge (IntelForge recon
-> VoidHawk memory + validation -> Dragon synthesis) against a target and
prints the result the same way the scriptable ``darkintel run`` command does.
"""

from __future__ import annotations

from intelforge.console.theme import console, error, warn

from darkintel.bridge import run as run_bridge
from darkintel.output import print_result

_PROMPT = "[bold red]DRAgon[/bold red] > "

_BANNER = """\
[bold red]DarkIntel[/bold red] — IntelForge recon -> VoidHawk validation -> Dragon.
Type [bold]help[/bold] for commands, [bold]exit[/bold] to leave.
"""

_HELP = """\
[heading]Commands[/heading]
  burn <target> [pdf|html|markdown|all] - Run the full pipeline against a target
  help - Show this help
  exit / quit - Leave
"""

_VALID_FORMATS = {"pdf", "html", "markdown", "all"}


def _burn(args: list[str]) -> None:
    if not args:
        error("Usage: burn <target> [pdf|html|markdown|all]")
        return
    target, *rest = args
    report_format = rest[0] if rest else "pdf"
    if report_format not in _VALID_FORMATS:
        error(f"Unknown report format {report_format!r} — one of {sorted(_VALID_FORMATS)}")
        return
    try:
        result = run_bridge(target, report_format=report_format)
    except Exception as exc:
        error(f"Run failed: {exc}")
        return
    print_result(result)


def main() -> None:
    console.print(_BANNER)
    while True:
        try:
            line = console.input(_PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not line:
            continue

        command, *args = line.split()
        command = command.lower()
        if command in ("exit", "quit"):
            break
        if command in ("help", "?"):
            console.print(_HELP)
        elif command == "burn":
            _burn(args)
        else:
            warn(f"Unknown command: {command!r} (try 'help')")


if __name__ == "__main__":
    main()
